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
  function setHeight() {
    var menu = document.getElementById("nav");
    if (menu && menu.classList.contains("show")) return;  // measure the closed header only
    document.documentElement.style.setProperty("--nav-h", nav.offsetHeight + "px");
  }
  setHeight();
  window.addEventListener("resize", setHeight);
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

// Unit pages: highlight the current section in "On this page" and, on small screens,
// show a slim bar with the unit name once the title has scrolled away.
(function () {
  if (!("IntersectionObserver" in window)) return;
  var links = {};
  document.querySelectorAll(".u-toc a[href^='#']").forEach(function (a) { links[a.getAttribute("href").slice(1)] = a; });
  var bar = document.querySelector("[data-unit-bar]");
  var barSec = document.querySelector("[data-unit-bar-section]");
  var targets = document.querySelectorAll(".u-video[id], .u-sec[id]");
  if (targets.length) {
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var id = en.target.id;
        Object.keys(links).forEach(function (k) { links[k].classList.toggle("is-active", k === id); });
        if (barSec && links[id]) barSec.textContent = links[id].textContent;
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    targets.forEach(function (t) { spy.observe(t); });
  }
  var title = document.querySelector(".u-h1");
  var card = document.querySelector(".toc-unit");
  if (title && (bar || card)) {
    new IntersectionObserver(function (entries) {
      var shown = !entries[0].isIntersecting && entries[0].boundingClientRect.top < 0;
      if (bar) {
        bar.classList.toggle("is-shown", shown);
        bar.setAttribute("aria-hidden", shown ? "false" : "true");
      }
      if (card) card.classList.toggle("is-shown", shown);
    }).observe(title);
  }
})();

// Mini player: after a unit video starts, keep it in a small window bottom-right while you read (tablet/desktop only).
(function () {
  var fig = document.querySelector(".u-video");
  var player = fig && fig.querySelector(".media-player");
  if (!player || !("IntersectionObserver" in window)) return;
  var wide = window.matchMedia("(min-width: 768px)");
  var footer = document.querySelector(".site-footer");
  var spacer = null, dismissed = false, outOfView = false;
  var bar = document.createElement("div");
  bar.className = "dock-bar";
  bar.innerHTML = '<button type="button" class="dock-btn" data-dock-return aria-label="Return to the video at the top of this unit"><i class="bi bi-arrow-up"></i> Return to video</button>' +
                  '<button type="button" class="dock-btn dock-x" data-dock-close aria-label="Close the mini player and keep the video in its place on the page"><i class="bi bi-x-lg"></i></button>';
  function playing() { return !!player.querySelector("iframe"); }
  function lift() {
    if (!player.classList.contains("is-docked") || !footer) return;
    var overlap = window.innerHeight - footer.getBoundingClientRect().top;
    player.style.bottom = Math.max(20, overlap + 20) + "px";
  }
  function dock() {
    if (player.classList.contains("is-docked")) return;
    spacer = document.createElement("div");
    spacer.style.height = player.offsetHeight + "px";
    player.parentNode.insertBefore(spacer, player);
    if (!bar.isConnected) player.appendChild(bar);  // the click-to-play swap clears the box
    player.classList.add("is-docked");
    lift();
  }
  function undock() {
    if (!player.classList.contains("is-docked")) return;
    player.classList.remove("is-docked");
    player.style.bottom = "";
    if (spacer) { spacer.remove(); spacer = null; }
  }
  function update() { (wide.matches && outOfView && playing() && !dismissed) ? dock() : undock(); }
  new IntersectionObserver(function (entries) {
    var e = entries[0];
    outOfView = !e.isIntersecting && e.boundingClientRect.top < 0;
    update();
  }).observe(fig);
  if (wide.addEventListener) wide.addEventListener("change", update);
  window.addEventListener("scroll", lift, { passive: true });
  window.addEventListener("resize", lift);
  player.addEventListener("click", function (e) { if (e.target.closest(".media-play")) setTimeout(update, 50); });
  bar.addEventListener("click", function (e) {
    if (e.target.closest("[data-dock-close]")) { dismissed = true; undock(); }
    else if (e.target.closest("[data-dock-return]")) { fig.scrollIntoView({ block: "start" }); }
  });
})();
