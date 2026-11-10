// Science & Space: countdown to the next events, and filters for the card grids.
// Without JavaScript every card is shown and the dates are shown as written.
(function () {
  "use strict";
  var DAY = 864e5;
  function utcDay(s) {
    var p = (s || "").split("-");
    return Date.UTC(+p[0], +p[1] - 1, +p[2]);
  }
  var now = new Date();
  var today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());

  // "Next up": drop events that have started since the last build, mark the first one,
  // and turn its date into "in N days".
  Array.prototype.forEach.call(document.querySelectorAll(".next-list"), function (list) {
    var show = parseInt(list.getAttribute("data-show") || "4", 10);
    var shown = 0;
    Array.prototype.forEach.call(list.querySelectorAll(".nx"), function (li) {
      var start = utcDay(li.getAttribute("data-start"));
      li.classList.remove("is-lead");
      if (start < today || shown >= show) { li.hidden = true; return; }
      li.hidden = false;
      li.classList.remove("is-spare");
      var lead = shown === 0;
      if (lead) li.classList.add("is-lead");
      shown++;
      var c = li.querySelector("[data-count]");
      if (!c) return;
      var days = Math.round((start - today) / DAY);
      var t = days > 1 ? "in " + days + " days" : days === 1 ? "tomorrow" : "today";
      c.textContent = lead ? t.charAt(0).toUpperCase() + t.slice(1) : t;
    });
    if (!shown) {
      var p = document.createElement("p");
      p.className = "cal-empty";
      p.textContent = "Nothing with a fixed date in the next weeks.";
      list.parentNode.insertBefore(p, list.nextSibling);
    }
  });

  // Card grids: two chip groups (data-a, data-b) and a text search (data-q).
  Array.prototype.forEach.call(document.querySelectorAll(".grid-tools"), function (tools) {
    var section = tools.parentNode;
    var cards = Array.prototype.slice.call(section.querySelectorAll(".card"));
    var empty = section.querySelector(".cal-empty");
    var input = tools.querySelector("input[type=search]");
    var state = { a: "all", b: "all", q: "" };

    function apply() {
      var n = 0;
      cards.forEach(function (card) {
        var ok = (state.a === "all" || card.getAttribute("data-a") === state.a) &&
                 (state.b === "all" || card.getAttribute("data-b") === state.b) &&
                 (!state.q || (card.getAttribute("data-q") || "").indexOf(state.q) >= 0);
        card.hidden = !ok;
        if (ok) n++;
      });
      if (empty) empty.hidden = n > 0;
    }

    tools.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-key]");
      if (!b) return;
      var key = b.getAttribute("data-key");
      state[key] = b.getAttribute("data-val");
      Array.prototype.forEach.call(tools.querySelectorAll('button[data-key="' + key + '"]'), function (x) {
        x.setAttribute("aria-pressed", String(x === b));
      });
      apply();
    });
    if (input) {
      input.addEventListener("input", function () {
        state.q = input.value.trim().toLowerCase();
        apply();
      });
    }
    tools.hidden = false;
    apply();
  });
})();
