/* GLOBAL VARIABLES */
// display RTC time in web
let startTime, startClient;
let current = "{time}"; // will be overwritten if you fetch later
let alarmHour;
let alarmMinute;
let use24hr = true;        // control 12/24 display, default is 24h

/* SWITCH BETWEEN MODES */
function switchMainView(viewId) {
  document.querySelectorAll('.view').forEach(view => {
  view.classList.remove('active');
  }); // hide all modes
  document.getElementById(viewId).classList.add('active'); // only show active mode
}

function openView(viewId) {
  switchMainView(viewId);
    fetch(`/set_mode?mode=${viewId}`)
    .then(response => {
      if (!response.ok) throw new Error("Failed to set mode");
      console.log(`Mode switched to ${viewId}`);
    })
    .catch(err => {
      console.error("Error switching mode:", err);
    });
}

/* TIME DISPLAY */
function updateClock() {
  let elapsed = Date.now() - startClient;
  let dt = new Date(startTime + elapsed);
  let hh = dt.getHours(), suffix = "";
  if (!use24hr) {
    suffix = hh < 12 ? " AM" : " PM";
    hh = hh % 12 || 12;
  }
  let H = String(hh).padStart(2,'0'),
      M = String(dt.getMinutes()).padStart(2,'0'),
      S = String(dt.getSeconds()).padStart(2,'0');
  document.getElementById("time").innerText = `${H}:${M}:${S}${suffix}`;
}

function setUpClockDisplay() { // runs every 5s
  document.getElementById("clock_24hView").classList.add('active');

  let parts = current.trim().split(":").map(x=>parseInt(x,10));
  if (parts.length!==3||parts.some(isNaN)) parts=[0,0,0];

  let now = new Date();
  now.setHours(parts[0],parts[1],parts[2],0);

  startTime = now.getTime();
  startClient = Date.now();

  setInterval(updateClock,1000);
  updateSubviewVisibility(); //update subviews to prevent both 12/24h views visible
}

/* ALARM DISPLAY */
function updateAlarmDisplay() {
  let hh = alarmHour, suffix="";
  if (!use24hr) {
    suffix = hh < 12 ? " AM" : " PM";
    hh = hh % 12 || 12;
  }
  let H = String(hh).padStart(2,'0'),
      M = String(alarmMinute).padStart(2,'0');
  document.getElementById("alarm").innerText = `${H}:${M}${suffix}`;
}

function toggleAlarm() {
  const url = document.getElementById("alarm_toggle").checked
            ? "/alarm_enabled" : "/alarm_disabled";
  fetch(url)
    .then(response => {
        if (!response.ok) throw new Error ("toggle failed");
        // do nothing
    })
    .catch(err => {
        console.error("Error:", err);
    });
}

function applyFormatView() {
  fetch("/toggle_format")
    .catch(console.error);
  updateClock();   // re-render displays
  updateAlarmDisplay();
  updateSubviewVisibility(); 
}

function toggleFormat() {
  use24hr = !use24hr;
  applyFormatView();
}

// add helper to toggle clock/alarm subviews based on use24hr
function updateSubviewVisibility() {
  // toggle subviews for clock
  document.getElementById("clock_24hView").classList.toggle('active', use24hr);
  document.getElementById("clock_12hView").classList.toggle('active', !use24hr);
  // toggle subviews for alarm
  document.getElementById("alarm_24hView").classList.toggle('active', use24hr);
  document.getElementById("alarm_12hView").classList.toggle('active', !use24hr);
}


/* GRAB AND DISPLAY SETTINGS FROM PICO */
function applySettings(settings) {
  use24hr = settings.format_24h === true || settings.format_24h === "true"; // apply format setting
  // update starting time
  current = settings.time;
  setUpClockDisplay();

  // update alarm time
  alarmHour = settings.alarm_hour;
  alarmMinute = settings.alarm_minute;
  updateAlarmDisplay();

  // update alarm enabled state = settings.alarm_toggle
  const alarmToggle = document.getElementById("alarm_toggle");
  if (settings.alarm_toggle === true || settings.alarm_toggle === "true") {
    alarmToggle.checked = true;
  } else {
    alarmToggle.checked = false;
  }

  // sync checkbox
  document.getElementById("format_toggle").checked = !use24hr;

  // update radio display if present
  if (settings.radio_frequency !== undefined) {
    document.getElementById("radio_freq").innerText = settings.radio_frequency.toFixed(1);
    document.getElementById("radio_vol").innerText = settings.radio_volume;
  }

  // start clock update after everything is ready
  setInterval(updateClock, 1000);

  // update subviews
  updateSubviewVisibility();
}

// helper to send a radio control GET and then refresh settings/UI
function sendRadio(path) {
  fetch(path)
    .then(response => {
      if (!response.ok) throw new Error("Radio control failed");
      return getSettingsAndStartClock();  // re‐fetch all settings (including radio) and update UI
    })
    .catch(err => console.error("Error:", err));
}

function getSettingsAndStartClock() {
  fetch("/get_settings")
    .then(response => response.json())
    .then(settings => {
      console.log("Received settings:", settings);
      applySettings(settings);
    })
    .catch(err => {
      console.error("Failed to fetch settings", err);
      // fallback to default
      setUpClockDisplay();
      setInterval(updateClock, 1000);
    });
}

// event listeners
//window.addEventListener("load", setUpClockDisplay);
window.addEventListener("load", getSettingsAndStartClock);
window.addEventListener("load", () => {
  const hash = window.location.hash.replace("#", "") || "TIME";
  openView(hash);
});

setInterval(getSettingsAndStartClock, 5000);  // every 5000 milliseconds = 5 seconds

function setToSystemTime() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const seconds = now.getSeconds();
    const params = new URLSearchParams({
        h: hours,
        m: minutes,
        s: seconds,
    });
    fetch(`/set_time?${params.toString()}#TIME`)
        .then(response => {
            if (!response.ok) throw new Error("Failed to set system time");
            console.log("System time set successfully");
            getSettingsAndStartClock(); // Refresh settings and UI
        })
        .catch(err => {
            console.error("Error setting system time:", err);
        });
}

/* FORM SUBMISSION HANDLERS */
// time form (24h & 12h)
function handleTimeSet(evt, form) {
  evt.preventDefault();
  let h = parseInt(form.h.value,10),
      m = parseInt(form.m.value,10),
      s = parseInt(form.s.value,10)||0;
  if (form.format.value==="12") {
    let pm = form.ampm.value==="PM";
    if (h===12) h = pm ? 12 : 0;
    else if (pm) h += 12;
  }
  const params = new URLSearchParams({h,m,s,format:24});
  fetch(`/set_time?${params.toString()}#TIME`)
    .then(r=>r.ok?getSettingsAndStartClock():Promise.reject())
    .catch(console.error);
}

// alarm form (24h & 12h)
function handleAlarmSet(evt, form) {
  evt.preventDefault();
  let h = parseInt(form.h.value,10),
      m = parseInt(form.m.value,10);
  if (form.format.value==="12") { // convert to 24h
    let pm = form.ampm.value==="PM";
    if (h===12) h = pm ? 12 : 0;
    else if (pm) h += 12;
  }
  const params = new URLSearchParams({h,m});
  fetch(`/set_alarm?${params.toString()}#ALARM`)
    .then(r=>r.ok?fetch("/alarm_enabled").then(_=>getSettingsAndStartClock()):Promise.reject())
    .catch(console.error);
}

/* ATTACH LISTENERS ON LOAD */
window.addEventListener("load",()=>{
  document.getElementById("time_form_24").  addEventListener("submit", e=>handleTimeSet(e,e.target));
  document.getElementById("time_form_12").  addEventListener("submit", e=>handleTimeSet(e,e.target));
  document.getElementById("alarm_form_24"). addEventListener("submit", e=>handleAlarmSet(e,e.target));
  document.getElementById("alarm_form_12"). addEventListener("submit", e=>handleAlarmSet(e,e.target));
  document.getElementById("timer_form").    addEventListener("submit", e=>handleTimer(e,e.target));
  document.getElementById("timer_form_12"). addEventListener("submit", e=>handleTimer(e,e.target));
});
