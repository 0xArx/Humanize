/* Humanize site behaviour. No dependencies, no network requests. Avatar maths comes from orb.js,
   which is the same file the dashboard uses, so a name draws the same mark here as in the product. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var root = document.documentElement;
  var REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SEEDS = ["Ari Vale", "Mira Chen", "Tomas Reyes", "Noor Haddad", "Iris Moreau", "Kai Tanaka", "Sana Okafor", "Idris Silva"];
  var WALLET = "0x4b7C1a9E2f3D4c5B6a7F8e9D0c1B2a3F4e5D6c7B";
  var cache = {};
  var seed = SEEDS[0];
  var heroParams = null, heroVisible = true, fillToken = 0;

  var disc = function () { return getComputedStyle(root).getPropertyValue("--disc").trim() || "#0b0b10"; };
  var params = function (s) { return cache[s] ? Promise.resolve(cache[s]) : HZ.orbParams(s).then(function (p) { cache[s] = p; return p; }); };

  /* ---------- theme ---------- */
  var themeBtn = $("#theme");
  function paintTheme() { themeBtn.textContent = root.getAttribute("data-theme") === "dark" ? "Light" : "Dark"; }
  themeBtn.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("hz-site-theme", next); } catch (e) {}
    paintTheme(); drawStatic();
  });
  paintTheme();

  /* ---------- avatar: hero, brand mark, gallery ---------- */
  var heroCv = $("#heroOrb"), brandCv = $("#brandOrb"), row = $("#seedRow"), seedBtns = {};

  function drawStatic() {
    var bg = disc();
    if (brandCv && heroParams) HZ.drawOrb(brandCv, heroParams, 2200, bg);
    SEEDS.forEach(function (s, i) { if (cache[s] && seedBtns[s]) HZ.drawOrb($("canvas", seedBtns[s]), cache[s], 1500 + i * 650, bg); });
    if (heroParams && REDUCED) HZ.drawOrb(heroCv, heroParams, 0, bg);
  }

  function frame(t) {
    if (heroParams && heroVisible && !document.hidden) HZ.drawOrb(heroCv, heroParams, REDUCED ? 0 : t, disc());
    if (!REDUCED) requestAnimationFrame(frame);
  }

  function buildGallery() {
    SEEDS.forEach(function (s) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "seed"; b.setAttribute("aria-pressed", s === seed ? "true" : "false");
      b.setAttribute("aria-label", "Show the avatar for " + s);
      var c = document.createElement("canvas"); c.width = 144; c.height = 144; c.setAttribute("aria-hidden", "true");
      var l = document.createElement("span"); l.textContent = s;
      b.appendChild(c); b.appendChild(l); row.appendChild(b); seedBtns[s] = b;
      b.addEventListener("click", function () { setSeed(s); });
    });
  }

  /* ---------- the passport fills itself in ---------- */
  var rows = { email: $("#ppEmail"), phone: $("#ppPhone"), wallet: $("#ppWallet"), git: $("#ppGit") };
  var fillFrom = [4, 9, 13, 17];

  function values(name) {
    var p = name.toLowerCase().split(" "), first = p[0], last = p[p.length - 1];
    return { email: first + "." + last + "@agentmail.to", phone: "+1 415 555 0123", wallet: WALLET.slice(0, 8) + "…" + WALLET.slice(-5), git: first.charAt(0) + last };
  }
  function setBar(n) { $("#ppNum").textContent = n; $("#ppFill").style.width = Math.round(n / 24 * 100) + "%"; }

  function fill(name) {
    var token = ++fillToken, v = values(name), keys = ["email", "phone", "wallet", "git"];
    $("#ppName").textContent = name;
    keys.forEach(function (k) { rows[k].textContent = ""; rows[k].classList.remove("typing"); });
    setBar(0);
    if (REDUCED) { keys.forEach(function (k, i) { rows[k].textContent = v[k]; }); setBar(17); return; }
    var i = 0;
    (function next() {
      if (token !== fillToken || i >= keys.length) return;
      var k = keys[i], text = v[k], n = 0, el = rows[k];
      el.classList.add("typing");
      (function type() {
        if (token !== fillToken) return;
        n++; el.textContent = text.slice(0, n);
        if (n < text.length) return void setTimeout(type, 22);
        el.classList.remove("typing"); setBar(fillFrom[i]); i++; setTimeout(next, 260);
      })();
    })();
  }

  function setSeed(s) {
    return params(s).then(function (p) {
      seed = s; heroParams = p;
      HZ.colors(p).forEach(function (c, i) { root.style.setProperty("--c" + (i + 1), c); });
      SEEDS.forEach(function (n) { if (seedBtns[n]) seedBtns[n].setAttribute("aria-pressed", n === s ? "true" : "false"); });
      heroCv.setAttribute("aria-label", "The avatar for " + s + ", drawn live from the name");
      HZ.drawOrb(heroCv, p, 0, disc());   // paint at once; the animation loop takes over on its first frame
      fill(s); drawStatic();
    });
  }

  function startAvatar() {
    if (!window.HZ || !(window.crypto && crypto.subtle)) { $(".orb-wrap").hidden = true; $(".seeds").hidden = true; fill(SEEDS[0]); return; }
    buildGallery();
    Promise.all(SEEDS.map(params)).then(function () { return setSeed(SEEDS[0]); }).then(function () { requestAnimationFrame(frame); });
    if ("IntersectionObserver" in window) new IntersectionObserver(function (e) { heroVisible = e[0].isIntersecting; }, { threshold: 0.05 }).observe(heroCv);
  }

  /* ---------- layers: filter and expand ---------- */
  var state = { group: "all", need: "all" }, cards = $$(".lcard");
  function applyFilter() {
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (state.group === "all" || c.dataset.group === state.group) && (state.need === "all" || c.dataset.need === state.need);
      c.hidden = !ok; if (ok) shown++;
    });
    $("#layerCount").textContent = "Showing " + shown + " of " + cards.length;
    $("#layerEmpty").hidden = shown > 0;
  }
  function segment(id, key) {
    $("#" + id).addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      state[key] = b.dataset[key];
      $$("button", this).forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      applyFilter();
    });
  }
  segment("segGroup", "group"); segment("segNeed", "need");
  $("#lgrid").addEventListener("click", function (e) {
    var b = e.target.closest(".more"); if (!b) return;
    var open = b.getAttribute("aria-expanded") === "true";
    b.setAttribute("aria-expanded", open ? "false" : "true");
    document.getElementById(b.getAttribute("aria-controls")).hidden = open;
  });

  /* ---------- tabs ---------- */
  var tabs = $$('[role="tab"]');
  function pick(t) {
    tabs.forEach(function (x) {
      var on = x === t; x.setAttribute("aria-selected", on ? "true" : "false"); x.tabIndex = on ? 0 : -1;
      document.getElementById(x.getAttribute("aria-controls")).hidden = !on;
    });
  }
  tabs.forEach(function (t, i) {
    t.tabIndex = i === 0 ? 0 : -1;
    t.addEventListener("click", function () { pick(t); });
    t.addEventListener("keydown", function (e) {
      var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0; if (!d) return;
      var n = tabs[(i + d + tabs.length) % tabs.length]; pick(n); n.focus(); e.preventDefault();
    });
  });

  /* ---------- copy ---------- */
  $$(".copy").forEach(function (b) {
    b.addEventListener("click", function () {
      var text = document.getElementById(b.dataset.target).innerText.replace(/\n+$/, "");
      var done = function (msg) { var old = b.textContent; b.textContent = msg; setTimeout(function () { b.textContent = old; }, 1400); };
      (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(function () { done("Copied"); }, function () { done("Select it"); });
    });
  });

  /* ---------- nav highlight and reveals ---------- */
  var links = {}; $$(".nav nav a").forEach(function (a) { links[a.dataset.sec] = a; });
  var showAll = /(^|[?&])reveal=all(&|$)/.test(location.search) || matchMedia("print").matches;   // for printing and screenshots
  if ("IntersectionObserver" in window && !showAll) {
    var secObs = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        Object.keys(links).forEach(function (k) { links[k].removeAttribute("aria-current"); });
        if (links[e.target.id]) links[e.target.id].setAttribute("aria-current", "true");
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    Object.keys(links).forEach(function (k) { var s = document.getElementById(k); if (s) secObs.observe(s); });

    $$(".reveal").forEach(function (el, i) { el.style.setProperty("--i", String(i % 4)); });
    var revObs = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); revObs.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });
    $$(".reveal").forEach(function (el) { revObs.observe(el); });
  } else {
    $$(".reveal").forEach(function (el) { el.classList.add("in"); });
  }

  applyFilter();
  startAvatar();
})();
