// Copy yhe content of the Lovelace example to the clipboard.
function CopyToLovelaceExampleToClipboard() {
    var copyText = document.getElementById("LovelaceExample");
    copyText.select();
    document.execCommand("copy");
}

