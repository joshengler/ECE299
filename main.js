window.onload = function () {

  let use24hr = is24hr === true || is24hr === "true";
  
  if (use24hr) {
      switchClockFormatView("24hView")
  } else {
      switchClockFormatView("12hView")
  }
  
  
  let current = "{time}";
  let parts = current.trim().split(":").map(x => parseInt(x.trim()));
  let now = new Date();
  now.setHours(parts[0], parts[1], parts[2], 0);
  
  let startTime = now.getTime();
  let startClient = Date.now();

  function updateClock() {
    let elapsed = Date.now() - startClient;
    let displayTime = new Date(startTime + elapsed);

    const isChecked = document.getElementById("24hr_toggle").checked;

    // handle format displayed in browser
    if (isChecked){
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
    console.log(`Time updated: ${hh}:${mm}:${ss}`);
  }
  
  setInterval(updateClock, 1000);
};

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

