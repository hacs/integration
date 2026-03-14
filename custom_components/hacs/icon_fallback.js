// Fallback handler for HACS integration icons.
// When an <img> with a brands.home-assistant.io/_/ URL fails to load,
// redirect it to the local HACS icon resolver which tries the repo's
// own brand/ directory on GitHub.
(function () {
  var desc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
  if (!desc || !desc.set) return;
  var origSet = desc.set;

  function attachFallback(img, url) {
    if (
      typeof url === "string" &&
      url.indexOf("brands.home-assistant.io/_/") !== -1
    ) {
      var m = url.match(/brands\.home-assistant\.io\/_\/([^/]+)\//);
      if (m) {
        var domain = m[1];
        var dark = url.indexOf("dark_") !== -1 ? "?dark=1" : "";
        img.addEventListener(
          "error",
          function () {
            origSet.call(img, "/api/hacs/icon/domain/" + domain + dark);
          },
          { once: true }
        );
      }
    }
  }

  Object.defineProperty(HTMLImageElement.prototype, "src", {
    get: desc.get,
    set: function (value) {
      attachFallback(this, value);
      origSet.call(this, value);
    },
    enumerable: desc.enumerable,
    configurable: desc.configurable,
  });

  var origSetAttr = HTMLImageElement.prototype.setAttribute;
  HTMLImageElement.prototype.setAttribute = function (name, value) {
    if (name === "src") attachFallback(this, value);
    return origSetAttr.call(this, name, value);
  };
})();
