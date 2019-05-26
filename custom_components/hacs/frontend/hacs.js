// Hide ugly scrollbar
window.parent.document.getElementsByTagName('html').item(0).style.overflow = "hidden";

// Copy yhe content of the Lovelace example to the clipboard.
function CopyToLovelaceExampleToClipboard() {
    window.getSelection().selectAllChildren( document.getElementById("LovelaceExample"));
    document.execCommand("copy");
    document.getSelection().empty()
    document.getElementById('lovelacecopy').style.color = 'forestgreen';
}

// Show progress bar
function ShowProgressBar() {
    document.getElementById('progressbar').style.display = 'block';
}
