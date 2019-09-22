
function Search() {
    var input = document.getElementById("Search");
    if (input) {
        var filter = input.value.toLowerCase();
        var nodes = document.getElementsByClassName('hacs-card');
        for (var i = 0; i < nodes.length; i++) {
            if (nodes[i].innerHTML.toLowerCase().includes(filter)) {
                nodes[i].style.display = "block";
            } else {
                nodes[i].style.display = "none";
            }
        }
        var nodes = document.getElementsByClassName('hacs-table-row');
        for (i = 0; i < nodes.length; i++) {
            if (nodes[i].innerHTML.toLowerCase().includes(filter)) {
                nodes[i].style.display = "table-row";
            } else {
                nodes[i].style.display = "none";
            }
        }
    }
}

class HacsStoreSearch extends HTMLElement {
    render() {
        this.innerHTML = `
        <div class='hacs-overview-container'>
            <input type="text" id="Search" onkeyup="Search()"
                placeholder="${hass.localize("component.hacs.store.placeholder_search")}"
                autofocus style="color: var(--primary-text-color)">
        </div>`;
    }

    connectedCallback() {
        this.render();
    }
}

customElements.define('hacs-store-search', HacsStoreSearch);