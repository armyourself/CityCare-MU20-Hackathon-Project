from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json, os, time

app = FastAPI(title="CityCare Backend")

# ----------------------------------------------------------------
# ✅ Allow CORS for your Live Server (frontend: http://127.0.0.1:5500)
# ----------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------
# 📂 File paths for persistent data
# ----------------------------------------------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

PATIENT_FILE = os.path.join(DATA_DIR, "patients.json")
FACILITY_FILE = os.path.join(DATA_DIR, "facilities.json")
APPOINT_FILE = os.path.join(DATA_DIR, "appointments.json")
ALERT_FILE = os.path.join(DATA_DIR, "alerts.json")

# ----------------------------------------------------------------
# 🧠 Helper functions to save/load JSON
# ----------------------------------------------------------------
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ----------------------------------------------------------------
# Initialize storage
# ----------------------------------------------------------------
patients = load_json(PATIENT_FILE)
facilities = load_json(FACILITY_FILE)
appointments = load_json(APPOINT_FILE)
alerts = load_json(ALERT_FILE)

# ----------------------------------------------------------------
# 🔐 Fake Doctor PIN system (for map verification)
# ----------------------------------------------------------------
VALID_DOCTOR_PIN = "1234"   # you can change this freely


# ----------------------------------------------------------------
# 🧾 MODELS
# ----------------------------------------------------------------
class LoginReq(BaseModel):
    user_id: str
    pin: str

class Facility(BaseModel):
    id: str
    name: str
    type: str
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
    consent: Optional[str] = "private"
    share_with: Optional[list] = []
    created_at: Optional[int] = None

class Appointment(BaseModel):
    patient_id: str
    doctor_id: str
    date: str
    time: str
    reason: str

class Alert(BaseModel):
    title: str
    msg: str
    kind: str
    target: Optional[str] = None
    ts: Optional[int] = None


# ----------------------------------------------------------------
# 🔑 AUTH
# ----------------------------------------------------------------
@app.post("/auth/login")
def login(req: LoginReq):
    """
    For doctors → checks PIN; for patients → accepts any ID & PIN.
    """
    if req.user_id.startswith("DOC") or req.user_id.startswith("doc"):
        if req.pin == VALID_DOCTOR_PIN:
            return {"user": {"id": req.user_id, "role": "doctor"}}
        raise HTTPException(status_code=401, detail="Invalid Doctor PIN.")
    else:
        return {"user": {"id": req.user_id, "role": "patient"}}


# ----------------------------------------------------------------
# 🏥 FACILITIES
# ----------------------------------------------------------------
@app.get("/facilities", response_model=List[Facility])
def get_facilities():
    """
    Return all facilities; populate defaults if empty.
    """
    global facilities
    if not facilities:
        facilities = [
            Facility(id="IND_HSP_001", name="Indore General", type="hospital", lat=22.757113, lon=75.957443, zone="South", contact="+91-731-2000001", beds=100),
            Facility(id="IND_HSP_002", name="Vijay Nagar Care", type="hospital", lat=22.674035, lon=75.899024, zone="East", contact="+91-731-2000002", beds=120),
            Facility(id="IND_CLN_003", name="Rajwada Clinic", type="clinic", lat=22.782558, lon=75.839607, zone="Central", contact="+91-731-2000003", beds=15),
            Facility(id="IND_HSP_004", name="MR-10 Trauma Center", type="hospital", lat=22.674416, lon=75.976310, zone="North", contact="+91-731-2000004", beds=80)
        ]
        save_json(FACILITY_FILE, [f.dict() for f in facilities])
    return facilities


# ----------------------------------------------------------------
# 👩‍⚕️ PATIENT MANAGEMENT
# ----------------------------------------------------------------
@app.post("/patients/register")
def register_patient(p: Patient):
    """
    Doctors use this to register new patients with ID + PIN.
    """
    global patients
    p.created_at = int(time.time() * 1000)
    patients.append(p.dict())
    save_json(PATIENT_FILE, patients)
    return {"ok": True, "patient": p}

@app.get("/patients", response_model=List[Patient])
def list_patients():
    return patients

@app.post("/patients/update")
def update_patient(p: Patient):
    """
    Patients use this to update their health dashboard.
    """
    global patients
    for i, existing in enumerate(patients):
        if existing["user_id"] == p.user_id and existing["pin"] == p.pin:
            patients[i] = p.dict()
            save_json(PATIENT_FILE, patients)
            return {"ok": True, "updated": p}
    raise HTTPException(status_code=404, detail="Patient not found or invalid PIN.")


# ----------------------------------------------------------------
# 📅 APPOINTMENTS
# ----------------------------------------------------------------
@app.post("/appointments/book")
def book_appointment(a: Appointment):
    global appointments
    appointments.append(a.dict())
    save_json(APPOINT_FILE, appointments)
    return {"ok": True, "appointment": a}

@app.get("/appointments", response_model=List[Appointment])
def list_appointments():
    return appointments


# ----------------------------------------------------------------
# 🔔 ALERTS
# ----------------------------------------------------------------
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


# ----------------------------------------------------------------
# 🧭 HEALTH CHECK
# ----------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "ok": True,
        "patients": len(patients),
        "appointments": len(appointments),
        "alerts": len(alerts),
        "facilities": len(facilities)
    }

# ----------------------------------------------------------------
# Run with:
# uvicorn main:app --reload --port 8000
# ----------------------------------------------------------------
