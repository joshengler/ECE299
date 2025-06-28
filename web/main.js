// display RTC time in web
let startTime, startClient;
let use24hr = true; // default, will be set in setup
let current = "{time}"; // will be overwritten if you fetch later

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
  use24hr = is24hr === true || is24hr === "true";

  if (use24hr) {
    switchClockFormatView("24hView");
  } else {
    switchClockFormatView("12hView");
  }

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

function applySettings(settings) {
  // apply format setting
  use24hr = settings.format_24h === true || settings.format_24h === "true";
  document.getElementById("24hr_toggle").checked = use24hr;

  // apply clock UI view
  switchClockFormatView(use24hr ? "24hView" : "12hView");

  // update starting time
  current = settings.time;
  setUpClockDisplay();

  // start clock update after everything is ready
  setInterval(updateClock, 1000);
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


function switchMainView(viewId) {
    document.querySelectorAll('.view').forEach(view => {
    view.classList.remove('active');
    });
    document.getElementById(viewId).classList.add('active');
}

function switchClockFormatView(viewId) {
    document.querySelectorAll('.subview').forEach(view => {
    view.classList.remove('active');
    });
    document.getElementById(viewId).classList.add('active');
}

function toggle24h() {
    const isChecked = document.getElementById("24hr_toggle").checked;
    const url = isChecked ? "/set_format?format=24" : "/set_format";

    if (isChecked) {
        switchClockFormatView("24hView");
    } else {
        switchClockFormatView("12hView");
    }

    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error ("toggle failed");
            use24hr = isChecked;
            updateClock();
        })
        .catch(err => {
            console.error("Error:", err);
        });
}

// event listeners
//window.addEventListener("load", setUpClockDisplay);
window.addEventListener("load", getSettingsAndStartClock);

setInterval(getSettingsAndStartClock, 5000);  // every 5000 milliseconds = 5 seconds
