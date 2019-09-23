/*
From: https://github.com/thomasloven/card-tools/blob/82b795df63b3874e5b3c5e48e363c6366d8cc3ca/hass.js
--------------------------------------
MIT License

Copyright (c) 2019 Thomas Lovén

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
export function load_lovelace() {
    if (customElements.get("hui-view")) return true;

    const res = document.createElement("partial-panel-resolver");
    res.hass = document.querySelector('home-assistant').hass;
    res.route = { path: "/lovelace/" };
    // res._updateRoutes();
    try {
        document.querySelector("home-assistant").appendChild(res).catch((error) => { });
    } catch (error) {
        document.querySelector("home-assistant").removeChild(res);
    }
    if (customElements.get("hui-view")) return true;
    return false;

}
