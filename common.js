<script>
const API = "http://127.0.0.1:8000";
let SESSION = null;

function audienceForAlerts(){
  if(!SESSION) return null;
  return SESSION.user.role==="patient"
    ? `patient:${SESSION.user.id.replace("USR_PAT_","PAT_")}`
    : `role:${SESSION.user.role}`;
}

function mountHeader(active){
  const hdr=document.querySelector("header");
  hdr.innerHTML = `
    <div class="brand">
      <div class="logo"></div>
      <h1>CityCare — Indore</h1>
    </div>

    <nav class="nav">
      <a href="index.html" ${active==='home'?'class="active"':''}>Home</a>
      <a href="map.html" ${active==='map'?'class="active"':''}>Map</a>
      <a href="patients.html" ${active==='patients'?'class="active"':''}>Patients</a>
      <a href="schedule.html" ${active==='schedule'?'class="active"':''}>Scheduling</a>
      <a href="sharing.html" ${active==='sharing'?'class="active"':''}>Data Sharing</a>
      <a href="alerts.html" ${active==='alerts'?'class="active"':''}>Alerts</a>
    </nav>

    <div class="header-tools">
      <span class="theme-chip">Theme:</span>
      <button class="btn-secondary" id="th-aur">Aurora</button>
      <button class="btn-secondary" id="th-ocean">Ocean</button>
      <button class="btn-secondary" id="th-sun">Sunrise</button>

      <input id="user_id" placeholder="User (e.g., USR_PAT_001)" />
      <input id="pin" placeholder="PIN" />
      <button id="btn_login">Login</button>
    </div>`;

  // Login
  document.getElementById("btn_login").onclick = async () => {
    const user = document.getElementById("user_id").value.trim();
    const pin  = document.getElementById("pin").value.trim();
    if(!user || !pin) return alert("Enter user & PIN");
    const r = await fetch(`${API}/auth/login`,{
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({user_id:user, pin})
    });
    if(!r.ok){ alert("Invalid PIN"); return; }
    SESSION = await r.json();
    alert(`Logged in as ${SESSION.user.name} (${SESSION.user.role})`);
  };

  // Theme switching
  const setTheme = (t) => {
    document.body.classList.remove("theme-ocean","theme-sunrise");
    if(t==="ocean") document.body.classList.add("theme-ocean");
    if(t==="sunrise") document.body.classList.add("theme-sunrise");
    localStorage.setItem("citycare_theme", t);
  };
  document.getElementById("th-aur").onclick = ()=>setTheme("aurora");
  document.getElementById("th-ocean").onclick = ()=>setTheme("ocean");
  document.getElementById("th-sun").onclick   = ()=>setTheme("sunrise");

  // Restore saved theme
  const saved = localStorage.getItem("citycare_theme") || "aurora";
  setTheme(saved);
}

/* helpers */
async function getJSON(url){ const r=await fetch(url); if(!r.ok) throw new Error(r.statusText); return r.json(); }
async function postJSON(url, body){ const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}); if(!r.ok) throw new Error(await r.text()); return r.json(); }
</script>
