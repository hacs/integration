// Sett hass
var hass = parent.document.querySelector('home-assistant').hass

// Copy active HA theme
document.getElementsByTagName("html").item(0).setAttribute("style", parent.document.getElementsByTagName("html").item(0).style.cssText)

// Copy yhe content of the Lovelace example to the clipboard.
function CopyToLovelaceExampleToClipboard() {
    window.getSelection().selectAllChildren(document.getElementById("LovelaceExample"));
    document.execCommand("copy");
    document.getSelection().empty()
    document.getElementById('lovelacecopy').style.color = 'forestgreen';
}

// Show progress bar
function ShowProgressBar() {
    document.getElementById('progressbar').style.display = 'block';
}

// Hard reloading
function HardReload() {
    parent.location.reload(true)
}

// Dropdown
document.addEventListener('DOMContentLoaded', function () {
    var elems = document.querySelectorAll('.dropdown-trigger');
    M.Dropdown.init(elems, { hover: false, constrainWidth: false });
});

// Modal
document.addEventListener('DOMContentLoaded', function () {
    var elems = document.querySelectorAll('.modal');
    M.Modal.init(elems, {});
});


// Loader
function toggleLoading() {
    var loadingOverlay = document.querySelector('.loading');
    loadingOverlay.classList.remove('hidden')
    document.activeElement.blur();
}


// Check if we can reload
function sleep(time) {
    return new Promise((resolve) => setTimeout(resolve, time));
}
function CheckIfWeCanReload() {
    var data = true;
    const hacsrequest = new XMLHttpRequest()
    hacsrequest.open('GET', '/hacs_task', true)
    hacsrequest.onload = function () {
        data = JSON.parse(this.response)
        data = data["task"]
        if (!data) {
            console.log("Background task is no longer running, reloading in 5s...")
            sleep(5000).then(() => {
                location.reload()
            });
        }
    }
    hacsrequest.send()
}

function IsTaskRunning() {
    let retval = false;
    let disp = document.getElementsByClassName("progress")
    if (disp) {
        disp = disp.item(0).style.display;
        if (disp == "block") {
            retval = true
        } else {
            retval = false
        }
    }
    return retval
}

window.setInterval(function () {
    var running = false;
    running = IsTaskRunning();
    if (running) {
        CheckIfWeCanReload();
    }
}, 10000);


