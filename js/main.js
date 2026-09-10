/* Portfolio — minimal progressive enhancement. No dependencies. */

(function () {
  "use strict";

  /* --- Current year in footer --- */
  var yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  /* --- Mobile nav toggle --- */
  var toggle = document.querySelector(".nav__toggle");
  var menu = document.getElementById("nav-menu");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    menu.addEventListener("click", function (e) {
      if (e.target.tagName === "A" && menu.classList.contains("is-open")) {
        menu.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* --- Light / dark theme toggle (persisted in localStorage) --- */
  var root = document.documentElement;
  var themeBtn = document.querySelector(".nav__theme");
  function isDark() { return root.getAttribute("data-theme") === "dark"; }
  // orbit turn counter — only ever increases, so the sun/moon always sweep clockwise
  var themeTurn = isDark() ? 1 : 0;
  function syncTheme() {
    if (!themeBtn) return;
    themeBtn.style.setProperty("--turn", String(themeTurn));
    themeBtn.setAttribute("aria-label", isDark() ? "Switch to light mode" : "Switch to dark mode");
    themeBtn.setAttribute("aria-pressed", String(isDark()));
  }
  syncTheme();
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      themeTurn += 1;
      syncTheme();
    });
  }

  /* --- For Fun photo carousel: auto-advances, hover/focus pauses, click-through --- */
  (function () {
    var car = document.querySelector("[data-funcar]");
    if (!car) return;
    var track = car.querySelector(".funcar__track");
    var slides = Array.prototype.slice.call(car.querySelectorAll(".funcar__slide"));
    if (!track || slides.length < 2) return;
    var prevBtn = car.querySelector(".funcar__nav--prev");
    var nextBtn = car.querySelector(".funcar__nav--next");
    var dotWrap = car.querySelector(".funcar__dots");
    var slow = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var index = 0;
    var timer = null;
    var DELAY = 4500;

    var dots = slides.map(function (_, i) {
      var d = document.createElement("button");
      d.type = "button";
      d.className = "funcar__dot";
      d.setAttribute("aria-label", "Show photo " + (i + 1) + " of " + slides.length);
      d.addEventListener("click", function () { go(i); restart(); });
      if (dotWrap) dotWrap.appendChild(d);
      return d;
    });

    function go(i) {
      index = (i + slides.length) % slides.length;
      track.style.transform = "translateX(" + (-index * 100) + "%)";
      dots.forEach(function (d, di) { d.classList.toggle("is-active", di === index); });
      slides.forEach(function (s, si) { s.setAttribute("aria-hidden", si === index ? "false" : "true"); });
    }
    function start() { if (!slow && !timer) timer = setInterval(function () { go(index + 1); }, DELAY); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function restart() { stop(); start(); }

    if (prevBtn) prevBtn.addEventListener("click", function () { go(index - 1); restart(); });
    if (nextBtn) nextBtn.addEventListener("click", function () { go(index + 1); restart(); });
    car.addEventListener("mouseenter", stop);
    car.addEventListener("mouseleave", start);
    car.addEventListener("focusin", stop);
    car.addEventListener("focusout", start);
    car.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { go(index - 1); restart(); }
      else if (e.key === "ArrowRight") { go(index + 1); restart(); }
    });
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) { stop(); } else { start(); }
    });

    go(0);
    start();
  })();

  /* --- Scroll reveal (Apple-style fade-up) --- */
  var reveals = document.querySelectorAll(".reveal");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (!("IntersectionObserver" in window) || reduce) {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-in");
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });

  reveals.forEach(function (el, i) {
    // slight stagger for groups of tiles
    el.style.transitionDelay = (i % 4) * 60 + "ms";
    io.observe(el);
  });
})();
