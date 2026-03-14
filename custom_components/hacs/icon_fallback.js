// HACS icon fallback: route brands.home-assistant.io/_/ URLs through the
// local HACS icon resolver so integrations without official brand icons
// can fall back to the repo's own brand/ directory.
(function () {
  var BRANDS_PREFIX = "brands.home-assistant.io/_/";
  var BRANDS_RE = /brands\.home-assistant\.io\/_\/([^/]+)\/(dark_)?(\w+)\.png/;

  function rewrite(url) {
    if (typeof url !== "string" || url.indexOf(BRANDS_PREFIX) === -1) return url;
    var m = url.match(BRANDS_RE);
    if (!m) return url;
    var domain = m[1];
    var dark = m[2] === "dark_" ? "?dark=1" : "";
    return "/api/hacs/icon/domain/" + domain + dark;
  }

  // Patch HTMLImageElement.prototype.src
  var desc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
  if (desc && desc.set) {
    var origSet = desc.set;
    Object.defineProperty(HTMLImageElement.prototype, "src", {
      get: desc.get,
      set: function (value) {
        origSet.call(this, rewrite(value));
      },
      enumerable: desc.enumerable,
      configurable: desc.configurable,
    });
  }

  // Patch setAttribute("src", ...)
  var origSetAttr = HTMLImageElement.prototype.setAttribute;
  HTMLImageElement.prototype.setAttribute = function (name, value) {
    if (name === "src") value = rewrite(value);
    return origSetAttr.call(this, name, value);
  };
})();
