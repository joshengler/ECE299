/* GLOBAL VARIABLES */


// display RTC time in web
let startTime, startClient;
//let use24hr = true; // default, will be set in setup
let current = "{time}"; // will be overwritten if you fetch later

let alarmHour;
let alarmMinute;


/* SWITCH BETWEEN MODES */
function switchMainView(viewId) {

  // hide all modes
  document.querySelectorAll('.view').forEach(view => {
  view.classList.remove('active');
  });

  // show active mode
  document.getElementById(viewId).classList.add('active');

  // only show alarm toggle on ALARM view
  const alarmToggleContainer = document.getElementById("alarmToggle");

  alarmToggleContainer.style.display = (viewId === "ALARM") ? "flex" : "none";
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
  let hh = String(dt.getHours()).padStart(2,'0');
  let mm = String(dt.getMinutes()).padStart(2,'0');
  let ss = String(dt.getSeconds()).padStart(2,'0');
  document.getElementById("time").innerText = `${hh}:${mm}:${ss}`;
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
}

/* ALARM DISPLAY */
function updateAlarmDisplay() {

  let hh = String(alarmHour).padStart(2,'0');
  let mm = String(alarmMinute).padStart(2,'0');

  document.getElementById("alarm").innerText = `${hh}:${mm}`;
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


  // update radio display if present
  if (settings.radio_frequency !== undefined) {
    document.getElementById("radio_freq").innerText = settings.radio_frequency.toFixed(1);
    document.getElementById("radio_vol").innerText = settings.radio_volume;
  }

  // start clock update after everything is ready
  setInterval(updateClock, 1000);
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

