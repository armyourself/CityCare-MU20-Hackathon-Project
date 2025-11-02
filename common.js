// common.js — CityCare header + auth + theme (no template literals, DOM-only)
// Drop this in place of the old file.

var CityCare = window.CityCare || {};
CityCare.API = CityCare.API || "http://127.0.0.1:8000";
CityCare.SESSION = CityCare.SESSION || null;

/* helpers */
function getEl(id) {
  return document.getElementById(id);
}
function bySelector(sel) {
  return document.querySelector(sel);
}

/* audienceForAlerts */
function audienceForAlerts() {
  if (!CityCare.SESSION || !CityCare.SESSION.user) return null;
  try {
    var role = CityCare.SESSION.user.role || "";
    var id = CityCare.SESSION.user.id || "";
    if (role === "patient") {
      return "patient:" + id.replace("USR_PAT_", "PAT_");
    }
    return "role:" + role;
  } catch (e) {
    return null;
  }
}

/* ensure header element exists */
function ensureHeader() {
  var hdr = bySelector("header");
  if (!hdr) {
    hdr = document.createElement("header");
    // Insert at top of body
    if (document.body.firstChild) {
      document.body.insertBefore(hdr, document.body.firstChild);
    } else {
      document.body.appendChild(hdr);
    }
  }
  return hdr;
}

/* set theme safely */
function setTheme(theme) {
  // remove individually to avoid any weird parser complaints
  document.body.classList.remove("theme-ocean");
  document.body.classList.remove("theme-sunrise");
  if (theme === "ocean") document.body.classList.add("theme-ocean");
  if (theme === "sunrise") document.body.classList.add("theme-sunrise");
  try {
    localStorage.setItem("citycare_theme", theme);
  } catch (e) {
    // ignore storage errors
  }
}

/* build nav link helper */
function makeNavLink(href, text, active) {
  var a = document.createElement("a");
  a.setAttribute("href", href);
  if (active) a.className = "active";
  a.appendChild(document.createTextNode(text));
  return a;
}

/* mount header */
function mountHeader(active) {
  var hdr = ensureHeader();

  // clear anything existing
  while (hdr.firstChild) hdr.removeChild(hdr.firstChild);

  // brand
  var brand = document.createElement("div");
  brand.className = "brand";
  var logo = document.createElement("div");
  logo.className = "logo";
  var h1 = document.createElement("h1");
  h1.appendChild(document.createTextNode("CityCare — Indore"));
  brand.appendChild(logo);
  brand.appendChild(h1);
  hdr.appendChild(brand);

  // nav
  var nav = document.createElement("nav");
  nav.className = "nav";
  nav.appendChild(makeNavLink("index.html", "Home", active === "home"));
  nav.appendChild(makeNavLink("map.html", "Map", active === "map"));
  nav.appendChild(makeNavLink("patients.html", "Patients", active === "patients"));
  nav.appendChild(makeNavLink("schedule.html", "Scheduling", active === "schedule"));
  nav.appendChild(makeNavLink("sharing.html", "Data Sharing", active === "sharing"));
  nav.appendChild(makeNavLink("alerts.html", "Alerts", active === "alerts"));
  hdr.appendChild(nav);

  // header tools container
  var tools = document.createElement("div");
  tools.className = "header-tools";

  // theme label + buttons
  var themeLabel = document.createElement("span");
  themeLabel.className = "theme-chip";
  themeLabel.appendChild(document.createTextNode("Theme:"));
  tools.appendChild(themeLabel);

  var thAur = document.createElement("button");
  thAur.className = "btn-secondary";
  thAur.id = "th-aur";
  thAur.appendChild(document.createTextNode("Aurora"));
  tools.appendChild(thAur);

  var thOcean = document.createElement("button");
  thOcean.className = "btn-secondary";
  thOcean.id = "th-ocean";
  thOcean.appendChild(document.createTextNode("Ocean"));
  tools.appendChild(thOcean);

  var thSun = document.createElement("button");
  thSun.className = "btn-secondary";
  thSun.id = "th-sun";
  thSun.appendChild(document.createTextNode("Sunrise"));
  tools.appendChild(thSun);

  // login inputs
  var userInput = document.createElement("input");
  userInput.id = "cc_user_id";
  userInput.setAttribute("placeholder", "User (e.g., USR_PAT_001)");
  tools.appendChild(userInput);

  var pinInput = document.createElement("input");
  pinInput.id = "cc_pin";
  pinInput.setAttribute("placeholder", "PIN");
  tools.appendChild(pinInput);

  var loginBtn = document.createElement("button");
  loginBtn.id = "cc_btn_login";
  loginBtn.appendChild(document.createTextNode("Login"));
  tools.appendChild(loginBtn);

  hdr.appendChild(tools);

  // wire theme buttons
  if (thAur) thAur.onclick = function () { setTheme("aurora"); };
  if (thOcean) thOcean.onclick = function () { setTheme("ocean"); };
  if (thSun) thSun.onclick = function () { setTheme("sunrise"); };

  // restore saved theme
  try {
    var saved = localStorage.getItem("citycare_theme") || "aurora";
    setTheme(saved);
  } catch (e) {
    setTheme("aurora");
  }

  // login action
  if (loginBtn) {
    loginBtn.onclick = function () {
      var user = (document.getElementById("cc_user_id") || { value: "" }).value.trim();
      var pin = (document.getElementById("cc_pin") || { value: "" }).value.trim();
      if (!user || !pin) {
        alert("Enter user & PIN");
        return;
      }

      // perform fetch (use native fetch)
      fetch(CityCare.API + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user, pin: pin })
      }).then(function (res) {
        if (!res.ok) {
          return res.text().then(function (t) {
            throw new Error(t || res.statusText || "Auth failed");
          });
        }
        return res.json();
      }).then(function (json) {
        CityCare.SESSION = json;
        var id = (CityCare.SESSION && CityCare.SESSION.user && CityCare.SESSION.user.id) ? CityCare.SESSION.user.id : "unknown";
        var role = (CityCare.SESSION && CityCare.SESSION.user && CityCare.SESSION.user.role) ? CityCare.SESSION.user.role : "unknown";
        alert("Logged in as " + id + " (" + role + ")");
      }).catch(function (err) {
        console.error("Login error:", err);
        alert("Login failed or backend unreachable. Check server on port 8000.");
      });
    };
  }
}

/* minimal getJSON/postJSON helpers */
function getJSON(url) {
  return fetch(url).then(function (res) {
    if (!res.ok) throw new Error(res.statusText || "Request failed");
    return res.json();
  });
}
function postJSON(url, body) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).then(function (res) {
    if (!res.ok) return res.text().then(function (t) { throw new Error(t || res.statusText); });
    return res.json();
  });
}

/* expose on global for debugging */
window.CityCare = CityCare;
CityCare.mountHeader = mountHeader;
CityCare.getJSON = getJSON;
CityCare.postJSON = postJSON;
CityCare.audienceForAlerts = audienceForAlerts;

/* mount header once DOM ready */
if (document.readyState === "loading") {
  window.addEventListener("DOMContentLoaded", function () { mountHeader(); });
} else {
  mountHeader();
}
