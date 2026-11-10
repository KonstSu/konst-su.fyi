// Retro details: a clock in the menu bar (as in Norton Commander) and the
// classic "Last modified" line in the footer. Purely cosmetic; sends nothing.
(function () {
  "use strict";
  var header = document.querySelector(".site-header");
  if (header) {
    var clock = document.createElement("span");
    clock.className = "clock";
    clock.setAttribute("aria-hidden", "true");
    header.appendChild(clock);
    var tick = function () {
      var d = new Date();
      clock.textContent = ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
    };
    tick();
    setInterval(tick, 15000);
  }
  // document.lastModified falls back to "now" when the server sends no date; hide it then.
  var el = document.querySelector("[data-lastmod]");
  if (el) {
    var m = new Date(document.lastModified);
    if (!isNaN(m) && Math.abs(Date.now() - m.getTime()) > 60000) {
      var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      el.textContent = "Last modified: " + m.getDate() + " " + months[m.getMonth()] + " " + m.getFullYear();
    }
  }
})();
