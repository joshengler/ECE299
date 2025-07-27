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

  // show toggle 24 hour button for TIME and ALARM modes
  const toggleContainer = document.getElementById("formatToggleContainer");

  if (viewId === "TIME" || viewId === "ALARM") {
    toggleContainer.style.display = "flex";
  } else {
    toggleContainer.style.display = "none";
  }

  const alarmToggleContainer = document.getElementById("alarmToggle");

  if (viewId === "TIME") {
    alarmToggleContainer.style.display = "none";
  } else {
    alarmToggleContainer.style.display = "flex";
  }
  
  const isChecked = document.getElementById("24hr_toggle").checked;

    if (isChecked) {
      switchAlarmView("alarm_24hView");
      switchClockView("clock_24hView");
    } else {
      switchClockView("clock_12hView");
      switchAlarmView("alarm_12hView");
    }
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

function switchClockView(viewId) {
  document.querySelectorAll('#TIME .subview').forEach(view => {
  view.classList.remove('active');
  });
  document.getElementById(viewId).classList.add('active');
}

function switchAlarmView(viewId) {
  document.querySelectorAll('#ALARM .subview').forEach(view => {
  view.classList.remove('active');
  });
  document.getElementById(viewId).classList.add('active');
}

function toggle24h() {
  const isChecked = document.getElementById("24hr_toggle").checked;
  const url = isChecked ? "/set_format?format=24" : "/set_format";

  if (isChecked) {
      switchClockView("clock_24hView");
      switchAlarmView("alarm_24hView");
  } else {
      switchClockView("clock_12hView");
      switchAlarmView("alarm_12hView");
  }

  use24hr = isChecked;

  updateAlarmDisplay();

  fetch(url)
      .then(response => {
          if (!response.ok) throw new Error ("toggle failed");
          updateClock();
      })
      .catch(err => {
          console.error("Error:", err);
      });
}

function updateClock() {
  let elapsed = Date.now() - startClient;
  let displayTime = new Date(startTime + elapsed);

  const isChecked = document.getElementById("24hr_toggle").checked;

  if (isChecked) {
    let hh = String(displayTime.getHours()).padStart(2, '0');
    let mm = String(displayTime.getMinutes()).padStart(2, '0');
    let ss = String(displayTime.getSeconds()).padStart(2, '0');
    document.getElementById("time").innerText = `${hh}:${mm}:${ss}`;
  } else {
    let hour = displayTime.getHours();
    let hh = hour === 0 ? "12" : String(hour % 12 || 12).padStart(2, '0');
    let mm = String(displayTime.getMinutes()).padStart(2, '0');
    let ss = String(displayTime.getSeconds()).padStart(2, '0');
    let am_pm = displayTime.getHours() >= 12 ? "PM" : "AM";
    document.getElementById("time").innerText = `${hh}:${mm}:${ss} ${am_pm}`;
  }
}

function setUpClockDisplay() {

  if (use24hr) {
    switchClockView("clock_24hView");
  } else {
    switchClockView("clock_12hView");
  }

  console.log("toggled 24h in setUpClockDisplay()");

  let parts = current.trim().split(":").map(x => parseInt(x.trim()));
  if (parts.length !== 3 || parts.some(isNaN)) {
    console.error("Invalid initial time:", current);
    parts = [0, 0, 0];
  }

  let now = new Date();
  now.setHours(parts[0], parts[1], parts[2], 0);

  startTime = now.getTime();
  startClient = Date.now();

  setInterval(updateClock, 1000);
}

/* ALARM DISPLAY */
function updateAlarmDisplay() {

  let formattedTime;

  const isChecked = document.getElementById("24hr_toggle").checked;

  if (isChecked) {
    formattedTime = `${String(alarmHour).padStart(2, '0')}:${String(alarmMinute).padStart(2, '0')}`;
  } else {
    let am_pm = alarmHour >= 12 ? "PM" : "AM";
    let displayHour = alarmHour % 12;
    if (displayHour === 0) displayHour = 12;
    formattedTime = `${String(displayHour).padStart(2, '0')}:${String(alarmMinute).padStart(2, '0')} ${am_pm}`;
  }

  document.getElementById("alarm").innerText = formattedTime;
}

function toggleAlarm() {

  const isChecked = document.getElementById("alarm_toggle").checked;
  url = isChecked ? "/alarm_enabled" : "/alarm_disabled";

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
  document.getElementById("24hr_toggle").checked = use24hr;

  // apply clock UI view
  switchClockView(use24hr ? "clock_24hView" : "clock_12hView");

  // update starting time
  current = settings.time;
  setUpClockDisplay();

  // update alarm time
  alarmHour = settings.alarm_hour;
  alarmMinute = settings.alarm_minute;
  updateAlarmDisplay();

  // update alarm enabled state = settings.alarm_toggle
  // <div id="alarmToggle" class="container" style="display: flex;">
  //           <input type="checkbox" id="alarm_toggle" onchange="toggleAlarm()" checked="">
  //           <label for="alarm_toggle">Enable Alarm</label>
  //       </div>
  //set the checkbox state based on settings.alarm_toggle
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

    const format = document.getElementById("24hr_toggle").checked ? "24" : "12";
    const am_pm = hours >= 12 ? "PM" : "AM";
    const adjustedHours = format === "12" ? (hours % 12 || 12) : hours;

    const params = new URLSearchParams({
        h: adjustedHours,
        m: minutes,
        s: seconds,
        format: format,
    });

    if (format === "12") {
        params.append("am_pm", am_pm);
    }

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

// New: compute timer‐based alarm and send set_alarm
function setTimer() {
    // read duration from active alarm subview
    const sub = document.querySelector('#ALARM .subview.active');
    const durH = parseInt(sub.querySelector('input[name="h"]').value, 10) || 0;
    const durM = parseInt(sub.querySelector('input[name="m"]').value, 10) || 0;
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
        const is24 = document.getElementById("24hr_toggle").checked;
        const params = new URLSearchParams();
        if (is24) {
          params.append("h", newHour24);
          params.append("m", newMinute);
          params.append("format", "24");
        } else {
          const am_pm = newHour24 >= 12 ? "PM" : "AM";
          const newHour12 = newHour24 % 12 || 12;
          params.append("h", newHour12);
          params.append("m", newMinute);
          params.append("format", "12");
          params.append("am_pm", am_pm);
        }

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




