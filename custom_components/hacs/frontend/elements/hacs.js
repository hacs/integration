// Copy active HA theme
document.getElementsByTagName("html").item(0).setAttribute("style", parent.document.getElementsByTagName("html").item(0).style.cssText)

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

// Searchbar
function Search() {
    var input = document.getElementById("Search");
    if (input) {
        var filter = input.value.toLowerCase();
        var nodes = document.getElementsByClassName('hacs-card');
        for (i = 0; i < nodes.length; i++) {
            if (nodes[i].innerHTML.toLowerCase().includes(filter)) {
            nodes[i].style.display = "block";
            } else {
            nodes[i].style.display = "none";
            }
        }
    }
}


// Dropdown
document.addEventListener('DOMContentLoaded', function() {
    var elems = document.querySelectorAll('.dropdown-trigger');
    var instances = M.Dropdown.init(elems, {hover: true, constrainWidth: false});
  });