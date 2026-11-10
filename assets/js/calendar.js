// Calendar filter: show all events or one category.
// Without JavaScript the filter bar stays hidden and every event is shown.
(function () {
  var bar = document.getElementById("cal-filter");
  if (!bar) return;
  var buttons = Array.prototype.slice.call(bar.querySelectorAll("button[data-filter]"));
  var sections = Array.prototype.slice.call(document.querySelectorAll(".cal-section"));
  var known = ["space", "facility", "conference"];

  function apply(filter) {
    buttons.forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-filter") === filter));
    });
    sections.forEach(function (section) {
      var shown = 0;
      section.querySelectorAll(".ev").forEach(function (ev) {
        var match = filter === "all" || ev.getAttribute("data-cat") === filter;
        ev.hidden = !match;
        if (match) shown++;
      });
      var empty = section.querySelector(".cal-empty");
      if (empty) empty.hidden = shown > 0;
    });
    try {
      history.replaceState(null, "", filter === "all" ? location.pathname : "#" + filter);
    } catch (e) { /* file:// or sandboxed: ignore */ }
  }

  buttons.forEach(function (b) {
    b.addEventListener("click", function () { apply(b.getAttribute("data-filter")); });
  });

  bar.hidden = false;
  var initial = (location.hash || "").slice(1);
  apply(known.indexOf(initial) >= 0 ? initial : "all");
})();
