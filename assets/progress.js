/* LifeSpent course progress — stored only in this browser (localStorage). No cookies, no server. */
(function () {
  "use strict";
  var KEY = "lifespent.apologetics.v1";
  var TOTAL = 12;
  var body = document.body;
  var root = body.getAttribute("data-root") || "";
  var unitNow = parseInt(body.getAttribute("data-unit") || "0", 10);

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || { units: {} }; }
    catch (e) { return { units: {} }; }
  }
  function save(s) {
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* private mode: progress just won't persist */ }
  }
  var state = load();
  state.units = state.units || {};
  function u(n) { return (state.units[n] = state.units[n] || { steps: {}, done: false }); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function unitHref(n, section) { return root + "units/unit-" + pad(n) + ".html" + (section ? "#" + section : ""); }
  function doneCount() { var c = 0; for (var i = 1; i <= TOTAL; i++) if (state.units[i] && state.units[i].done) c++; return c; }
  function started() { return !!(state.last && state.last.unit); }

  /* Where to resume: the last unit you were in, unless you finished it — then the next unfinished unit. */
  function resumeTarget() {
    if (!started()) return null;
    var n = state.last.unit;
    if (state.units[n] && state.units[n].done) {
      for (var i = 1; i <= TOTAL; i++) {
        var k = ((n - 1 + i) % TOTAL) + 1;
        if (!(state.units[k] && state.units[k].done)) return { unit: k, section: null };
      }
      return null; /* everything done */
    }
    return { unit: n, section: state.last.section || null };
  }

  /* ---- record visits ---- */
  if (unitNow) {
    u(unitNow).visited = Date.now();
    state.last = { unit: unitNow, section: (state.last && state.last.unit === unitNow) ? state.last.section : null, ts: Date.now() };
    save(state);
  }

  /* ---- Begin / Resume buttons ---- */
  function paintResume() {
    var target = resumeTarget();
    var all = doneCount() === TOTAL;
    document.querySelectorAll("[data-resume-btn]").forEach(function (a) {
      var label = a.querySelector("[data-label]") || a;
      if (all) {
        a.href = root + "index.html#units";
        label.textContent = a.getAttribute("data-label-done") || "Review the course";
      } else if (target) {
        a.href = unitHref(target.unit, target.section);
        var tpl = a.getAttribute("data-label-resume") || "Resume";
        label.textContent = tpl.replace("{n}", target.unit);
      }
    });
    var count = document.querySelector("[data-progress-count]");
    if (count && started()) {
      count.hidden = false;
      count.querySelector("strong").textContent = doneCount() + "/" + TOTAL;
    }
  }

  /* ---- unit tiles, contents rows, progress segments ---- */
  function paintUnits() {
    document.querySelectorAll("[data-unit-link]").forEach(function (el) {
      var n = parseInt(el.getAttribute("data-unit-link"), 10);
      var rec = state.units[n];
      el.classList.toggle("is-done", !!(rec && rec.done));
      el.classList.toggle("is-current", !!(started() && state.last.unit === n && !(rec && rec.done)));
      el.classList.toggle("is-started", !!(rec && rec.visited));
    });
    if (started()) {
      document.querySelectorAll(".u-steps .seg").forEach(function (seg) {
        var n = parseInt(seg.getAttribute("data-unit-link"), 10);
        seg.classList.toggle("on", !!(state.units[n] && state.units[n].done));
      });
    }
  }

  /* ---- unit page: step checklist + mark complete ---- */
  function paintChecklist() {
    if (!unitNow) return;
    var rec = u(unitNow);
    document.querySelectorAll("[data-step]").forEach(function (box) {
      box.checked = !!rec.steps[box.getAttribute("data-step")];
    });
    var btn = document.querySelector("[data-complete-btn]");
    if (btn) {
      btn.classList.toggle("is-done", rec.done);
      btn.setAttribute("aria-pressed", rec.done ? "true" : "false");
      btn.querySelector("[data-label]").textContent = rec.done ? "Unit complete ✓" : "Mark unit complete";
    }
  }
  document.addEventListener("change", function (e) {
    var step = e.target.getAttribute && e.target.getAttribute("data-step");
    if (!step || !unitNow) return;
    var rec = u(unitNow);
    rec.steps[step] = e.target.checked;
    var boxes = document.querySelectorAll("[data-step]");
    var all = Array.prototype.every.call(boxes, function (b) { return b.checked; });
    if (all) rec.done = true;
    save(state); paintChecklist(); paintUnits(); paintResume();
  });
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-complete-btn]");
    if (btn && unitNow) {
      var rec = u(unitNow);
      rec.done = !rec.done;
      if (rec.done) document.querySelectorAll("[data-step]").forEach(function (b) { rec.steps[b.getAttribute("data-step")] = true; });
      save(state); paintChecklist(); paintUnits(); paintResume();
      return;
    }
    var reset = e.target.closest && e.target.closest("[data-reset-progress]");
    if (reset) {
      e.preventDefault();
      if (window.confirm("Clear your saved progress in this browser?")) {
        try { localStorage.removeItem(KEY); } catch (err) {}
        window.location.reload();
      }
    }
  });

  /* ---- unit page: remember the section you were reading ---- */
  function trackSections() {
    if (!unitNow || !("IntersectionObserver" in window)) return;
    var secs = document.querySelectorAll(".u-sec[id]");
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          state.last = { unit: unitNow, section: en.target.id, ts: Date.now() };
          save(state);
        }
      });
    }, { rootMargin: "0px 0px -60% 0px" });
    secs.forEach(function (s) { io.observe(s); });
  }

  /* ---- unit page: offer to jump back to where you stopped ---- */
  function offerPickup(prevSection) {
    if (!unitNow || !prevSection || location.hash || prevSection === "read") return;
    var sec = document.getElementById(prevSection);
    if (!sec) return;
    var title = (sec.querySelector(".u-h2") || {}).textContent || "where you left off";
    var bar = document.createElement("div");
    bar.className = "pickup";
    bar.setAttribute("role", "status");
    bar.innerHTML = '<span>Pick up where you left off:</span> <a href="#' + prevSection + '"></a> <button type="button" aria-label="Dismiss">×</button>';
    bar.querySelector("a").textContent = title;
    bar.querySelector("a").addEventListener("click", function () { bar.remove(); });
    bar.querySelector("button").addEventListener("click", function () { bar.remove(); });
    document.body.appendChild(bar);
    setTimeout(function () { if (bar.parentNode) bar.classList.add("fade"); }, 12000);
    setTimeout(function () { if (bar.parentNode) bar.remove(); }, 13000);
  }

  var prev = load(); /* state before this visit's tracking overwrote it */
  var prevSection = (prev.last && prev.last.unit === unitNow) ? prev.last.section : null;
  paintResume(); paintUnits(); paintChecklist();
  offerPickup(prevSection);
  trackSections();
})();

// Click-to-load media: the Vimeo player (and its requests) load only after the visitor clicks play.
document.addEventListener("click", function (e) {
  var btn = e.target.closest && e.target.closest(".media-play");
  if (!btn) return;
  var box = btn.parentElement, id = box.getAttribute("data-vimeo");
  if (!id || !/^\d+$/.test(id)) return;
  var f = document.createElement("iframe");
  f.src = "https://player.vimeo.com/video/" + id + "?dnt=1&autoplay=1";
  f.title = box.getAttribute("data-title") || "Video";
  f.allow = "autoplay; fullscreen; picture-in-picture";
  f.allowFullscreen = true;
  box.replaceChildren(f);
});

// Light/dark theme: the choice is saved in this browser (localStorage), like course progress.
(function () {
  var KEY = "lifespent.theme", root = document.documentElement;
  function label() {
    var dark = root.getAttribute("data-bs-theme") === "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach(function (b) {
      b.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
      b.setAttribute("aria-pressed", dark ? "true" : "false");
    });
  }
  document.addEventListener("click", function (e) {
    if (!(e.target.closest && e.target.closest("[data-theme-toggle]"))) return;
    var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-bs-theme", next);
    try { localStorage.setItem(KEY, next); } catch (err) {}
    label();
  });
  label();
})();

// Sticky header gets a soft shadow once the page scrolls.
(function () {
  var nav = document.querySelector(".site-nav");
  if (!nav) return;
  function onScroll() { nav.classList.toggle("is-scrolled", window.scrollY > 8); }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
})();

// While the mobile menu is open, lock the page so scrolling moves the menu, not the page behind it.
(function () {
  var menu = document.getElementById("nav");
  if (!menu) return;
  menu.addEventListener("show.bs.collapse", function () { document.documentElement.classList.add("menu-open"); });
  menu.addEventListener("hidden.bs.collapse", function () { document.documentElement.classList.remove("menu-open"); });
})();
