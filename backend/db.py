import sqlite3
import json
import os

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "triage.db"))

COLUMNS = [
    "id", "name", "language", "raw_symptoms", "translated_symptoms",
    "anatomy", "vitals", "urgency_flag", "esi_label", "risk_score",
    "immediate_action", "differentials", "body_systems", "follow_up_questions",
    "clarification_summary", "clinical_rationale", "medical_history",
    "clinical_notes", "timestamp", "admitted"
]

JSON_COLUMNS = {"anatomy", "vitals", "differentials", "body_systems", "follow_up_questions"}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT,
                language TEXT,
                raw_symptoms TEXT,
                translated_symptoms TEXT,
                anatomy TEXT,
                vitals TEXT,
                urgency_flag TEXT,
                esi_label TEXT,
                risk_score INTEGER,
                immediate_action TEXT,
                differentials TEXT,
                body_systems TEXT,
                follow_up_questions TEXT,
                clarification_summary TEXT,
                clinical_rationale TEXT,
                medical_history TEXT,
                clinical_notes TEXT,
                timestamp TEXT,
                admitted INTEGER DEFAULT 0
            )
        """)


def _serialize(patient):
    row = {}
    for col in COLUMNS:
        val = patient.get(col)
        if col in JSON_COLUMNS:
            row[col] = json.dumps(val) if val is not None else "[]"
        elif col == "admitted":
            row[col] = int(val) if val else 0
        else:
            row[col] = val
    return row


def _deserialize(row):
    patient = dict(row)
    for col in JSON_COLUMNS:
        try:
            patient[col] = json.loads(patient[col]) if patient[col] else []
        except (json.JSONDecodeError, TypeError):
            patient[col] = []
    patient.pop("admitted", None)
    return patient


def insert_patient(patient):
    row = _serialize(patient)
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    with get_conn() as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO patients ({cols}) VALUES ({placeholders})",
            list(row.values())
        )


def get_active_queue():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM patients WHERE admitted = 0 ORDER BY CAST(SUBSTR(urgency_flag, 5) AS INTEGER) ASC, risk_score DESC"
        ).fetchall()
    return [_deserialize(r) for r in rows]


def admit_patient(patient_id):
    with get_conn() as conn:
        conn.execute("UPDATE patients SET admitted = 1 WHERE id = ?", (patient_id,))


def get_all_patients():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM patients ORDER BY timestamp DESC"
        ).fetchall()
    return [_deserialize(r) for r in rows]
