const API = "http://127.0.0.1:8000";
let chart, session = {};

function qs(id){return document.getElementById(id);}

qs('btn_login').onclick = async ()=>{
  const user = qs('doc_user').value.trim();
  const pin = qs('doc_pin').value.trim();
  if(!user || !pin) return alert("Enter credentials");
  session.user = user;
  localStorage.setItem('doctor_session', JSON.stringify(session));
  await loadPatients();
  qs('monitor_section').style.display = '';
};

async function loadPatients(){
  try {
    const r = await fetch(`${API}/patients`);
    const data = await r.json();
    const sel = qs('patient_select');
    sel.innerHTML = data.patients.length
      ? data.patients.map(p=>`<option>${p}</option>`).join('')
      : '<option>No patients yet</option>';
  } catch {
    console.error("Failed to load patients");
  }
}

qs('btn_start').onclick = async ()=>{
  session.patient = qs('patient_select').value;
  session.stat = qs('stat_select').value;
  localStorage.setItem('monitor_session', JSON.stringify(session));

  initChart(session.stat);
  await loadHistory(session.patient, session.stat);
  updateLive();
  clearInterval(window.monitorLoop);
  window.monitorLoop = setInterval(updateLive, 3000);
};

async function loadHistory(patient, stat){
  try {
    const r = await fetch(`${API}/sensor/${patient}/history/${stat}?limit=30`);
    const data = await r.json();
    const ds = chart.data.datasets[0].data;
    const labels = chart.data.labels;
    ds.length = 0; labels.length = 0;

    data.history.forEach(([val, ts])=>{
      ds.push(val);
      labels.push(new Date(ts*1000).toLocaleTimeString());
    });
    chart.update();
  } catch {
    console.warn("No history found for this patient/stat yet.");
  }
}

async function updateLive(){
  try {
    const r = await fetch(`${API}/sensor/${session.patient}/${session.stat}`);
    const data = await r.json();
    if(!data.value) return;
    qs('live_value').textContent = `${data.value} ${data.unit}`;
    addChartPoint(data.value);
  } catch {
    qs('live_value').textContent = "⚠️ Unable to fetch data";
  }
}

function initChart(stat){
  const ctx = qs('chart').getContext('2d');
  if(chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: stat.replace('_',' ').toUpperCase(),
        data: [],
        borderColor: '#1a5bff',
        tension: 0.3,
        fill: false,
        pointRadius: 2
      }]
    },
    options: {
      animation: false,
      scales: {
        x: { display: false },
        y: {
          beginAtZero: false,
          title: { display: true, text: stat === "heart_rate" ? "BPM" : stat === "o2" ? "%" : "°C" }
        }
      }
    }
  });
}

function addChartPoint(value){
  const maxPoints = 30;
  const ds = chart.data.datasets[0].data;
  const labels = chart.data.labels;
  ds.push(value);
  labels.push(new Date().toLocaleTimeString());
  if(ds.length > maxPoints){ ds.shift(); labels.shift(); }
  chart.update();
}

// Auto-load previous session
window.onload = async ()=>{
  const s = JSON.parse(localStorage.getItem('monitor_session') || '{}');
  if(s.patient && s.stat){
    session = s;
    qs('monitor_section').style.display = '';
    await loadPatients();
    qs('patient_select').value = s.patient;
    qs('stat_select').value = s.stat;
    initChart(s.stat);
    await loadHistory(s.patient, s.stat);
    updateLive();
    window.monitorLoop = setInterval(updateLive, 3000);
  }
};
