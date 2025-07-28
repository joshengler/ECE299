/* GLOBAL VARIABLES */


// display RTC time in web
let startTime, startClient;
//let use24hr = true; // default, will be set in setup
let current = "{time}"; // will be overwritten if you fetch later

let alarmHour;
let alarmMinute;

let use24hr = true;        // control 12/24 display

/* SWITCH BETWEEN MODES */
function switchMainView(viewId) {

  // hide all modes
  document.querySelectorAll('.view').forEach(view => {
  view.classList.remove('active');
  });

  // show active mode
  document.getElementById(viewId).classList.add('active');

  // only show alarm toggle on ALARM view
  // const alarmToggleContainer = document.getElementById("alarmToggle");

  // alarmToggleContainer.style.display = (viewId === "ALARM") ? "flex" : "none";
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

function setUpClockDisplay() {
  document.getElementById("clock_24hView").classList.add('active');

  let parts = current.trim().split(":").map(x=>parseInt(x,10));
  if (parts.length!==3||parts.some(isNaN)) parts=[0,0,0];

  let now = new Date();
  now.setHours(parts[0],parts[1],parts[2],0);

  startTime = now.getTime();
  startClient = Date.now();

  setInterval(updateClock,1000);

  // update subviews
  updateSubviewVisibility();
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
  fetch("/set_format?format=" + (use24hr ? "24" : "12"))
    .catch(console.error);


  // re-render displays
  updateClock();
  updateAlarmDisplay();

  // update subviews
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
  // apply format setting
  use24hr = settings.format_24h === true || settings.format_24h === "true";
  //document.getElementById("24hr_toggle").checked = use24hr;

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
        //format: format,
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

/* New: accept (event, form), read values directly, prevent default */
function setTimer(event, form) {
  event.preventDefault();
  const durH = parseInt(form.elements['h'].value, 10) || 0;
  const durM = parseInt(form.elements['m'].value, 10) || 0;
  const totalMin = durH * 60 + durM;
  if (totalMin < 1) return;

  // fetch actual device clock time
  fetch("/get_settings")
    .then(res => res.json())
    .then(settings => {
      // parse RTC time
      const parts = settings.time.split(":").map(x => parseInt(x, 10));
      const now = new Date();
      now.setHours(parts[0], parts[1], parts[2], 0);

      // add the timer duration
      now.setMinutes(now.getMinutes() + totalMin);
      const newHour24 = now.getHours();
      const newMinute = now.getMinutes();

      // build query based on 24h setting
      const params = new URLSearchParams({
        h: newHour24,
        m: newMinute,
        format: "24",
        mode: "timer"
      });

      // send to set_alarm
      fetch(`/set_alarm?${params.toString()}#ALARM`)
        .then(resp => {
          if (!resp.ok) throw new Error("Failed to set timer alarm");
          // always enable alarm after setting it
          return fetch("/alarm_enabled");
        })
        .then(resp2 => {
          if (!resp2.ok) throw new Error("Failed to enable alarm");
          return getSettingsAndStartClock();
        })
        .catch(err => console.error("Error setting timer or enabling alarm:", err));
    })
    .catch(err => console.error("Error fetching settings for timer:", err));
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
  if (form.format.value==="12") {
    let pm = form.ampm.value==="PM";
    if (h===12) h = pm ? 12 : 0;
    else if (pm) h += 12;
  }
  const params = new URLSearchParams({h,m,format:24,mode:"alarm"});
  fetch(`/set_alarm?${params.toString()}#ALARM`)
    .then(r=>r.ok?fetch("/alarm_enabled").then(_=>getSettingsAndStartClock()):Promise.reject())
    .catch(console.error);
}

// timer form (both 24 & 12 share same handler)
function handleTimer(evt, form) {
  evt.preventDefault();
  setTimer(evt, form);
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

// ...rest of existing code (getSettingsAndStartClock, setTimer, etc.)...

