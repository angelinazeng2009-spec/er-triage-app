import json
import random
import time
from typing import List
from pydantic import BaseModel, Field

class TriageOutput(BaseModel):
    id: str = Field(description="Unique patient identifier, e.g., PT-XXXX")
    name: str
    language: str
    raw_symptoms: str
    translated_symptoms: str
    anatomy: List[str]
    vitals: List[str]
    urgency_flag: str
    esi_label: str
    risk_score: int
    immediate_action: str
    differentials: List[str]
    body_systems: List[str]
    follow_up_questions: List[str]
    clarification_summary: str
    clinical_rationale: str
    medical_history: str
    clinical_notes: str
    timestamp: str

def format_vitals_for_prompt(vitals_obj):
    if not isinstance(vitals_obj, dict):
        return str(vitals_obj)
    return (
        f"BP: {vitals_obj.get('bp', 'N/A')} (mmHg), "
        f"HR: {vitals_obj.get('hr', 'N/A')} bpm, "
        f"Temp: {vitals_obj.get('temp', 'N/A')} °F, "
        f"O2: {vitals_obj.get('o2', 'N/A')} %, "
        f"RR: {vitals_obj.get('rr', 'N/A')} breaths/min"
    )

def build_triage_prompt(data):
    medical_history = data.get('medical_history', 'None reported')
    clinical_notes = data.get('clinical_notes', 'None recorded')
    vitals_str = format_vitals_for_prompt(data.get('vitals', {}))
    clarification = data.get('clarification', '').strip()

    clarification_block = ""
    if clarification:
        clarification_block = f"\nClarification from clinician: {clarification}\n"

    return f"""
You are an expert ER triage AI. Analyze the patient intake data below and accurately populate the requested clinical triage schema.

Patient Information:
- Name: {data.get('name', 'Unknown')}
- Intake Language: {data.get('language', 'English')}
- Symptoms reported: {data.get('symptoms', 'None')}
- Medical History: {medical_history}
- Clinical Notes: {clinical_notes}
- Vitals Matrix: {vitals_str}
{clarification_block}
Return JSON matching the schema with these fields:
- differentials: 3-5 possible conditions or diagnoses.
- body_systems: the body systems affected (e.g., respiratory, cardiovascular, neurologic).
- follow_up_questions: 3-5 short questions the clinician should ask next to narrow the differential.
- clarification_summary: a concise summary of what clarification is still needed.
- clinical_rationale: brief rationale for the current differential.
"""
def build_gemini_payload(data):
    prompt = build_triage_prompt(data)
    generated_id = f"PT-{random.randint(1000, 9999)}"
    current_time = time.strftime('%I:%M %p')

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": TriageOutput.model_json_schema()
        }
    }
    return payload, generated_id, current_time

def process_triage_response(res_json, generated_id, current_time):
    raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
    patient_data = json.loads(raw_text)
    patient_data["id"] = generated_id
    patient_data["timestamp"] = current_time
    return patient_data