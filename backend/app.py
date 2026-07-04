from flask import Flask, render_template, request, jsonify
import os, time, requests, json, base64
from triage import build_gemini_payload, process_triage_response

app = Flask(__name__, template_folder="templates", static_folder=".")

API_KEY = os.environ.get("GEMINI_API_KEY", "")

triage_queue = [
    {
        "id": "PT-4091",
        "name": "José R. Silva",
        "language": "Spanish",
        "raw_symptoms": "Me duele mucho el pecho izquierdo...",
        "translated_symptoms": "My left chest hurts and radiates to my arm...",
        "anatomy": ["left chest", "arm"],
        "vitals": ["pain: 9/10", "duration: 30m"],
        "urgency_flag": "ESI-2",
        "esi_label": "Level 2: Emergent",
        "risk_score": 88,
        "immediate_action": "ECG within 10 minutes",
        "differentials": ["Acute Coronary Syndrome", "Pulmonary Embolism"],
        "timestamp": time.strftime('%I:%M %p'),
        "clinical_rationale": "Possible ACS or PE."
    }
]

def get_api_key(data):
    return data.get("api_key") or API_KEY


def sanitize_mime_type(mime_type):
    if not mime_type:
        return "audio/webm"
    return mime_type.split(";")[0].strip()


def call_gemini_generate(payload, key, models=None, versions=None):
    if models is None:
        models = [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-1.0",
            "gemini-pro-latest",
            "gemini-flash-latest",
            "gemini-3.1-pro-preview",
            "gemini-3.1-flash-lite",
        ]
    if versions is None:
        versions = ["v1beta", "v1"]

    method_order = ["generateContent"]

    attempts = []
    last_error = None

    for version in versions:
        for model in models:
            for method in method_order:
                url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:{method}?key={key}"
                try:
                    res = requests.post(url, json=payload, timeout=30)
                    attempts.append({
                        "url": url,
                        "status_code": res.status_code,
                        "body": res.text[:200]
                    })
                    res.raise_for_status()
                    return res.json()
                except requests.exceptions.HTTPError as e:
                    last_error = e
                    if e.response is not None and e.response.status_code in {404, 405, 429}:
                        continue
                    raise
                except requests.exceptions.RequestException as e:
                    last_error = e
                    attempts.append({"url": url, "error": str(e)})
                    continue

    message = "No supported Gemini model/method combination succeeded."
    if last_error is not None:
        if hasattr(last_error, "response") and last_error.response is not None:
            message = last_error.response.text or str(last_error)
        else:
            message = str(last_error)
    raise RuntimeError(f"{message}\nAttempts: {json.dumps(attempts, indent=2)}")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/config')
def config():
    return jsonify({"server_key_configured": bool(API_KEY)})


@app.route('/api/queue', methods=['GET'])
def get_queue():
    triage_queue.sort(key=lambda p: (int(p["urgency_flag"].split("-")[1]), -p.get("risk_score", 0)))
    return jsonify(triage_queue)


@app.route('/api/admit/<patient_id>', methods=['DELETE'])
def admit(patient_id):
    global triage_queue
    triage_queue = [p for p in triage_queue if p["id"] != patient_id]
    return jsonify({"success": True})


# ---------------- VOICE ----------------
@app.route('/api/voice-intake', methods=['OPTIONS'])
def voice_intake_options():
    return jsonify({"success": True}), 200


@app.route('/api/voice-intake', methods=['POST'])
def voice_intake():
    key = get_api_key(request.form)
    if not key:
        return jsonify({"success": False, "error": "Missing API key"}), 400

    if "audio_data" not in request.files:
        return jsonify({"success": False, "error": "No audio"}), 400

    audio = request.files["audio_data"].read()
    mime_type = sanitize_mime_type(request.form.get("mime_type", "audio/webm"))
    b64 = base64.b64encode(audio).decode()

    payload = {
        "contents": [{
            "parts": [
                {"inlineData": {"mimeType": mime_type, "data": b64}},
                {"text": "Transcribe exactly what the speaker says in the original language. Include all spoken words and do not add or remove text."}
            ]
        }]
    }

    try:
        data = call_gemini_generate(payload, key)

        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        return jsonify({"success": True, "transcription": text})

    except requests.exceptions.HTTPError as e:
        response_text = e.response.text if e.response is not None else str(e)
        status_code = e.response.status_code if e.response is not None else 502
        return jsonify({"success": False, "error": f"Gemini API error {status_code}: {response_text}"}), status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "error": f"Network error: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/check-condition', methods=['OPTIONS'])
def check_condition_options():
    return jsonify({"success": True}), 200


@app.route('/api/check-condition', methods=['POST'])
def check_condition():
    data = request.get_json() or {}
    key = get_api_key(data)

    if not key:
        return jsonify({"success": False, "error": "Missing API key"}), 400

    symptoms = data.get("symptoms", "")
    medical_history = data.get("medical_history", "")
    clinical_notes = data.get("clinical_notes", "")
    name = data.get("name", "Patient")

    prompt = f"""
You are an ER clinical reasoning assistant.
Using only the information below, summarize the most likely condition or difficulty the patient is experiencing and list the top 2-3 possible problems.
Do not provide medical advice, only a reasoned differential based on the symptoms.

Patient: {name}
Symptoms: {symptoms}
Medical history: {medical_history}
Clinical notes: {clinical_notes}

Respond in a short plain text summary.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        data = call_gemini_generate(payload, key)
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return jsonify({"success": True, "condition": text})
    except requests.exceptions.HTTPError as e:
        response_text = e.response.text if e.response is not None else str(e)
        status_code = e.response.status_code if e.response is not None else 502
        return jsonify({"success": False, "error": f"Gemini API error {status_code}: {response_text}"}), status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "error": f"Network error: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- TRIAGE ----------------
@app.route('/api/triage', methods=['OPTIONS'])
def triage_options():
    return jsonify({"success": True}), 200


@app.route('/api/triage', methods=['POST'])
def triage():
    data = request.get_json() or {}
    key = get_api_key(data)

    if not key:
        return jsonify({"success": False, "error": "Missing API key"}), 400

    # Group UI form items into the vitals dictionary expected by triage.py
    if "vitals" not in data or not isinstance(data["vitals"], dict):
        data["vitals"] = {
            "bp": f"{data.get('bpSystolic') or 'N/A'}/{data.get('bpDiastolic') or 'N/A'}",
            "hr": data.get("heartRate") or "N/A",
            "temp": data.get("temperature") or "N/A",
            "o2": data.get("o2Saturation") or "N/A",
            "rr": data.get("respiratoryRate") or "N/A"
        }

    # 1. Build payload using structured template config tools
    payload, generated_id, current_time = build_gemini_payload(data)

    try:
        res_data = call_gemini_generate(payload, key)

        # 3. Complete structured generation transformation output mapping
        patient = process_triage_response(res_data, generated_id, current_time)

        triage_queue.insert(0, patient)
        return jsonify({"success": True, "patient": patient})

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if 'res' in locals() and res.text:
            error_msg = res.text
        return jsonify({"success": False, "error": f"API request failed: {error_msg}"}), 502
    except Exception as e:
        return jsonify({"success": False, "error": f"Internal processing error: {str(e)}"}), 500


# ---------------- STATS ----------------
@app.route('/api/stats')
def stats():
    return jsonify({
        "total": len(triage_queue),
        "esi_distribution": {
            "ESI-1": len([p for p in triage_queue if p["urgency_flag"] == "ESI-1"]),
            "ESI-2": len([p for p in triage_queue if p["urgency_flag"] == "ESI-2"]),
            "ESI-3": len([p for p in triage_queue if p["urgency_flag"] == "ESI-3"]),
            "ESI-4": len([p for p in triage_queue if p["urgency_flag"] == "ESI-4"]),
            "ESI-5": len([p for p in triage_queue if p["urgency_flag"] == "ESI-5"])
        }
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)