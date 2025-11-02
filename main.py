from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json, os, time

app = FastAPI(title="CityCare Backend")

# -----------------------------
# CORS for local dev (frontends on 5500 or 3000)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# JSON persistence helpers
# -----------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

PATIENT_FILE   = os.path.join(DATA_DIR, "patients.json")
FACILITY_FILE  = os.path.join(DATA_DIR, "facilities.json")
APPOINT_FILE   = os.path.join(DATA_DIR, "appointments.json")
ALERT_FILE     = os.path.join(DATA_DIR, "alerts.json")

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# -----------------------------
# In-memory state (backed by JSON)
# -----------------------------
patients     = load_json(PATIENT_FILE)
facilities   = load_json(FACILITY_FILE)
appointments = load_json(APPOINT_FILE)
alerts       = load_json(ALERT_FILE)

# Single demo PIN for all doctors (used by map add/remove protected markers)
VALID_DOCTOR_PIN = "1234"   # change as you like

# -----------------------------
# Models
# -----------------------------
class LoginReq(BaseModel):
    user_id: str
    pin: str

class Facility(BaseModel):
    id: str
    name: str
    type: str          # hospital | clinic | pharmacy | etc.
    lat: float
    lon: float
    zone: Optional[str] = ""
    contact: Optional[str] = ""
    beds: Optional[int] = 0

class Patient(BaseModel):
    user_id: str
    pin: str
    name: Optional[str] = ""
    age: Optional[int] = None
    gender: Optional[str] = ""
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    phone: Optional[str] = ""
    email: Optional[str] = ""
    emergency_contact: Optional[str] = ""
    conditions: Optional[str] = ""
    allergies: Optional[str] = ""
    meds: Optional[str] = ""
    consent: Optional[str] = "none"      # none | all | doctors | custom
    share_with: Optional[list] = []
    assigned_doctor_id: Optional[str] = ""
    facility_id: Optional[str] = ""
    created_at: Optional[int] = None
    updated_at: Optional[int] = None

class Appointment(BaseModel):
    patient_id: str
    doctor_id: str
    date: str
    time: str
    reason: str

class Alert(BaseModel):
    title: str
    msg: str
    kind: str                # med | report | emergency | other
    target: Optional[str] = None
    ts: Optional[int] = None

# -----------------------------
# Auth
# -----------------------------
@app.post("/auth/login")
def login(req: LoginReq):
    """
    Demo auth:
    - If user_id starts with DOC → validate doctor PIN.
    - Else treat as patient (no strict check here for hackathon flow).
    """
    if req.user_id.lower().startswith("doc"):
        if req.pin == VALID_DOCTOR_PIN:
            return {"user": {"id": req.user_id, "role": "doctor"}}
        raise HTTPException(status_code=401, detail="Invalid Doctor PIN.")
    return {"user": {"id": req.user_id, "role": "patient"}}

# -----------------------------
# Facilities
# -----------------------------
@app.get("/facilities", response_model=List[Facility])
def get_facilities():
    global facilities
    if not facilities:
        facilities = [
            Facility(id="IND_HSP_001", name="Indore General",      type="hospital", lat=22.757113, lon=75.957443, zone="South",   contact="+91-731-2000001", beds=100),
            Facility(id="IND_HSP_002", name="Vijay Nagar Care",    type="hospital", lat=22.674035, lon=75.899024, zone="East",    contact="+91-731-2000002", beds=120),
            Facility(id="IND_CLN_003", name="Rajwada Clinic",      type="clinic",   lat=22.782558, lon=75.839607, zone="Central", contact="+91-731-2000003", beds=15),
            Facility(id="IND_HSP_004", name="MR-10 Trauma Center", type="hospital", lat=22.674416, lon=75.976310, zone="North",   contact="+91-731-2000004", beds=80),
        ]
        save_json(FACILITY_FILE, [f.dict() for f in facilities])
    return facilities

# -----------------------------
# Patients
# -----------------------------
@app.post("/patients/register")
def register_patient(p: Patient):
    """
    Doctor registers a new patient with user_id + pin (minimal record OK).
    """
    global patients
    now = int(time.time() * 1000)
    p.created_at = now
    p.updated_at = now
    patients.append(p.dict())
    save_json(PATIENT_FILE, patients)
    return {"ok": True, "patient": p}

@app.get("/patients", response_model=List[Patient])
def list_patients():
    return patients

@app.get("/patients/{user_id}")
def get_patient_by_id(user_id: str):
    for rec in patients:
        if rec.get("user_id") == user_id:
            return rec
    raise HTTPException(status_code=404, detail="Patient not found")

@app.post("/patients/update")
def update_patient(p: Patient):
    """
    Patient updates their dashboard (must supply correct user_id + pin).
    """
    global patients
    for i, existing in enumerate(patients):
        if existing["user_id"] == p.user_id and existing["pin"] == p.pin:
            rec = p.dict()
            rec["created_at"] = existing.get("created_at")
            rec["updated_at"] = int(time.time() * 1000)
            patients[i] = rec
            save_json(PATIENT_FILE, patients)
            return {"ok": True, "updated": rec}
    raise HTTPException(status_code=404, detail="Patient not found or invalid PIN.")

# -----------------------------
# Appointments
# -----------------------------
@app.post("/appointments/book")
def book_appointment(a: Appointment):
    global appointments
    appointments.append(a.dict())
    save_json(APPOINT_FILE, appointments)
    return {"ok": True, "appointment": a}

@app.get("/appointments", response_model=List[Appointment])
def list_appointments():
    return appointments

@app.get("/appointments/for_doctor/{doctor_id}", response_model=List[Appointment])
def list_for_doctor(doctor_id: str):
    return [a for a in appointments if a.get("doctor_id") == doctor_id]

# -----------------------------
# Alerts
# -----------------------------
@app.post("/alerts/create")
def create_alert(a: Alert):
    global alerts
    a.ts = int(time.time() * 1000)
    alerts.append(a.dict())
    save_json(ALERT_FILE, alerts)
    return {"ok": True, "alert": a}

@app.get("/alerts", response_model=List[Alert])
def list_alerts():
    return alerts

# -----------------------------
# Health
# -----------------------------
@app.get("/health")
def health():
    return {
        "ok": True,
        "patients": len(patients),
        "appointments": len(appointments),
        "alerts": len(alerts),
        "facilities": len(facilities),
    }