from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json, os, time, threading

app = FastAPI(title="CityCare Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------
# In-memory stores (plus JSON persistence for patients)
# ---------------------------------------------
patients_mem: List[Dict[str, Any]] = []
appointments: List[Dict[str, Any]] = []
facilities:   List[Dict[str, Any]] = []
alerts:       List[Dict[str, Any]] = []

CITYCARE_TOKEN = "supersecret123"

# ---- Persistence (patients only) ----
DATA_DIR = "data"
PATIENTS_FILE = os.path.join(DATA_DIR, "patients.json")
_lock = threading.Lock()
os.makedirs(DATA_DIR, exist_ok=True)

def _load_patients_file() -> List[Dict[str, Any]]:
    if not os.path.exists(PATIENTS_FILE):
        return []
    try:
        with open(PATIENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_patients_file(arr: List[Dict[str, Any]]):
    with _lock:
        with open(PATIENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(arr, f, ensure_ascii=False, indent=2)

# Boot: load into memory
patients_mem = _load_patients_file()

def _find_patient_idx(user_id: str) -> int:
    for i, p in enumerate(patients_mem):
        if p.get("user_id") == user_id:
            return i
    return -1

def _require_patient(user_id: str) -> Dict[str, Any]:
    i = _find_patient_idx(user_id)
    if i < 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patients_mem[i]

def _check_pin(p: Dict[str, Any], pin: str):
    if not pin or p.get("pin") != pin:
        raise HTTPException(status_code=401, detail="Invalid PIN")

# ---------------------------------------------
# MODELS
# ---------------------------------------------
class LoginReq(BaseModel):
    user_id: str
    pin: str

class Facility(BaseModel):
    id: str
    name: str
    type: str           # hospital / clinic / pharmacy / etc
    lat: float
    lon: float
    zone: str
    contact: str
    beds: Optional[int] = 0

# Minimal registration (what doctors create)
class PatientMinimal(BaseModel):
    user_id: str
    pin: str
    assigned_doctor_id: Optional[str] = None
    facility_id: Optional[str] = None

# Full patient model (dashboard). All optional except user_id/pin for updates.
class PatientUpdate(BaseModel):
    user_id: str
    pin: str
    # profile
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact: Optional[str] = None
    # medical
    conditions: Optional[str] = None
    allergies: Optional[str] = None
    meds: Optional[str] = None
    # linkage
    assigned_doctor_id: Optional[str] = None
    facility_id: Optional[str] = None
    # sharing/consent
    consent: Optional[str] = None              # "none" | "all" | "doctors" | "custom"
    share_with: Optional[List[str]] = None     # list of user_ids allowed when consent=="custom"

class Appointment(BaseModel):
    patient_id: str
    doctor_id: str
    date: str
    time: str
    reason: str

class Alert(BaseModel):
    title: str
    msg: str
    kind: str       # med|report|emergency|other
    target: Optional[str] = None
    ts: Optional[int] = None

# ---------------------------------------------
# AUTH
# ---------------------------------------------
@app.post("/auth/login")
def login(req: LoginReq):
    # Demo: any ID/PIN works to obtain a "session envelope"
    role = "doctor" if "DOC" in req.user_id.upper() else "patient"
    return {"user": {"id": req.user_id, "role": role, "name": req.user_id}}

# ---------------------------------------------
# FACILITIES
# ---------------------------------------------
@app.get("/facilities", response_model=List[Facility])
def get_facilities():
    if not facilities:
        facilities.extend([
            Facility(id="IND_HSP_001", name="Indore General",      type="hospital", lat=22.757113, lon=75.957443, zone="South",   contact="+91-731-2000001", beds=100),
            Facility(id="IND_HSP_002", name="Vijay Nagar Care",    type="hospital", lat=22.674035, lon=75.899024, zone="East",    contact="+91-731-2000002", beds=120),
            Facility(id="IND_CLN_003", name="Rajwada Clinic",      type="clinic",   lat=22.782558, lon=75.839607, zone="Central", contact="+91-731-2000003", beds=15),
            Facility(id="IND_HSP_004", name="MR-10 Trauma Center", type="hospital", lat=22.674416, lon=75.976310, zone="North",   contact="+91-731-2000004", beds=80),
        ])
    return facilities

# ---------------------------------------------
# PATIENTS — Registration, read, update (PERSISTENT)
# ---------------------------------------------

@app.post("/patients/register")   # doctor creates minimal record (keeps compat with your old code path)
def register_patient_minimal(p: PatientMinimal):
    now = int(time.time() * 1000)
    i = _find_patient_idx(p.user_id)
    base = {
        "user_id": p.user_id,
        "pin": p.pin,
        "name": "—",
        "age": None,
        "gender": None,
        "height_cm": None,
        "weight_kg": None,
        "bmi": None,
        "phone": None,
        "email": None,
        "emergency_contact": None,
        "conditions": None,
        "allergies": None,
        "meds": None,
        "assigned_doctor_id": p.assigned_doctor_id,
        "facility_id": p.facility_id,
        "consent": "none",
        "share_with": [],
        "created_at": now,
        "updated_at": now
    }
    if i >= 0:
        # overwrite minimal pieces but preserve any existing filled fields
        existing = patients_mem[i]
        for k, v in base.items():
            if k in ("pin", "assigned_doctor_id", "facility_id"):
                existing[k] = v
        existing["updated_at"] = now
        _save_patients_file(patients_mem)
        return {"ok": True, "patient": existing, "updated": True}
    else:
        patients_mem.append(base)
        _save_patients_file(patients_mem)
        return {"ok": True, "patient": base, "created": True}

@app.get("/patients", response_model=List[Dict[str, Any]])
def list_patients():
    return patients_mem

@app.get("/patients/{user_id}", response_model=Dict[str, Any])
def get_patient(user_id: str):
    return _require_patient(user_id)

@app.post("/patients/update")  # patient fills dashboard; requires correct PIN
def update_patient(pu: PatientUpdate):
    p = _require_patient(pu.user_id)
    _check_pin(p, pu.pin)

    allowed_fields = [
        "name","age","gender","height_cm","weight_kg","bmi",
        "phone","email","emergency_contact",
        "conditions","allergies","meds",
        "assigned_doctor_id","facility_id",
        "consent","share_with"
    ]
    changed = False
    for f in allowed_fields:
        val = getattr(pu, f)
        if val is not None:
            p[f] = val
            changed = True

    p["updated_at"] = int(time.time() * 1000)
    if changed:
        _save_patients_file(patients_mem)
    return {"ok": True, "patient": p, "changed": changed}

# ---------------------------------------------
# SCHEDULING
# ---------------------------------------------
@app.post("/appointments/book")
def book_appointment(a: Appointment):
    appointments.append(a.dict())
    return {"ok": True, "appointment": a}

@app.get("/appointments", response_model=List[Appointment])
def list_appointments():
    return appointments

@app.get("/appointments/for_doctor/{doctor_id}")
def list_for_doctor(doctor_id: str):
    return [a for a in appointments if a.get("doctor_id")==doctor_id]

# ---------------------------------------------
# ALERTS
# ---------------------------------------------
@app.post("/alerts/create")
def create_alert(a: Alert):
    a.ts = int(time.time() * 1000)
    alerts.append(a.dict())
    return {"ok": True, "alert": a}

@app.get("/alerts", response_model=List[Alert])
def list_alerts():
    return alerts

# ---------------------------------------------
# HEALTH CHECK
# ---------------------------------------------
@app.get("/health")
def health():
    return {
        "ok": True,
        "patients": len(patients_mem),
        "appointments": len(appointments),
        "alerts": len(alerts),
        "facilities": len(facilities)
    }
@app.get("/sensor/{patient_id}/{stat}")
def get_sensor_data(patient_id: str, stat: str):
    # Here you’d actually fetch from IoT hardware, e.g. via serial, MQTT, or REST
    simulated = {
        "heart_rate": random.randint(60, 100),
        "o2": round(random.uniform(95, 99), 1),
        "temperature": round(random.uniform(36.0, 37.5), 1)
    }
    return {"patient": patient_id, "stat": stat, "value": simulated.get(stat, None)}
# ============================================================
# 📡 IOT SENSOR MONITORING (Simulated + SQLite Logging)
# ============================================================

import sqlite3, random, time
from fastapi.middleware.cors import CORSMiddleware

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

DB_PATH = "sensors.db"

# ----------------- Initialize Database -----------------
def init_sensor_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        stat TEXT,
        value REAL,
        timestamp REAL
    )''')
    conn.commit()
    conn.close()

init_sensor_db()

# ----------------- Helper Functions -----------------
def generate_vitals():
    """Simulate realistic IoT sensor readings."""
    return {
        "heart_rate": random.randint(60, 110),
        "o2": round(random.uniform(94.0, 99.5), 1),
        "temperature": round(random.uniform(36.0, 37.8), 1)
    }

def save_reading(patient_id, stat, value):
    """Save each simulated reading to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO readings (patient_id, stat, value, timestamp) VALUES (?,?,?,?)",
              (patient_id, stat, value, time.time()))
    conn.commit()
    conn.close()

# ----------------- API Endpoints -----------------
@app.get("/sensor/{patient_id}/{stat}")
def get_sensor_data(patient_id: str, stat: str):
    """Simulate & store a single stat reading for a patient."""
    vitals = generate_vitals()
    value = vitals.get(stat)
    if value is None:
        return {"error": "Invalid stat", "available": list(vitals.keys())}

    save_reading(patient_id, stat, value)
    return {
        "patient": patient_id,
        "stat": stat,
        "value": value,
        "unit": "bpm" if stat=="heart_rate" else "%" if stat=="o2" else "°C",
        "timestamp": time.time()
    }

@app.get("/sensor/{patient_id}")
def get_all_stats(patient_id: str):
    """Return all simulated stats for a patient."""
    vitals = generate_vitals()
    for stat, val in vitals.items():
        save_reading(patient_id, stat, val)
    return {"patient": patient_id, "vitals": vitals, "timestamp": time.time()}

@app.get("/sensor/{patient_id}/history/{stat}")
def get_history(patient_id: str, stat: str, limit: int = 30):
    """Get last few readings for chart plotting."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT value, timestamp FROM readings 
                 WHERE patient_id=? AND stat=? 
                 ORDER BY timestamp DESC LIMIT ?""",
              (patient_id, stat, limit))
    rows = c.fetchall()
    conn.close()
    rows.reverse()
    return {"patient": patient_id, "stat": stat, "history": rows}

@app.get("/patients")
def get_patients():
    """List distinct patients who have sensor readings."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT patient_id FROM readings ORDER BY patient_id")
    patients = [r[0] for r in c.fetchall()]
    conn.close()
    return {"patients": patients}

@app.get("/iot/latest")
def get_iot_data(patient: str):
    import random
    return {
        "patient": patient,
        "heart_rate": random.randint(60,110),
        "o2_sat": random.randint(92,100),
        "temp": round(random.uniform(36.0, 37.5),1),
        "bp": f"{random.randint(100,130)}/{random.randint(70,90)}"
    }

# ============================================================