// Hide ugly scrollbar
window.parent.document.getElementsByTagName('html').item(0).style.overflow = "hidden";

// Copy yhe content of the Lovelace example to the clipboard.
function CopyToLovelaceExampleToClipboard() {
    var copyText = document.getElementById("LovelaceExample");
    copyText.select();
    document.execCommand("copy");
}

// Show progress bar
function ShowProgressBar() {
    document.getElementById('progressbar').style.display = 'block';
}