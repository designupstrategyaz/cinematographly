// SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
// Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
// kits.js — the title kits (references/typography-and-captions.md §6c). Each kit builds one title from
// window.__TITLE (the title spec merged with the project's title card by title.mjs) into #safe, and puts
// one paused GSAP timeline on window.__timelines.main. Rules every kit keeps (house rule, 2026-10-26):
//   - text lands and stops dead: no overshoot, no bounce, no shake on any text, number or UI (C2);
//   - one entrance family and one exit family per title, from the card (motion tokens, K5);
//   - nothing moves at rest: the hold is still;
//   - no Math.random, no clock, no network: the same spec gives the same pixels.
(function () {
  "use strict";
  var T = window.__TITLE, root = document.getElementById("root"), safe = document.getElementById("safe");
  var C = T.content || {};

  // ---------- easing: cubic-bezier as a GSAP ease function (y clamped: no overshoot on text) ----------
  function bezier(p) {
    var x1 = p[0], y1 = Math.min(1, Math.max(0, p[1])), x2 = p[2], y2 = Math.min(1, Math.max(0, p[3]));
    function cx(t) { return 3 * x1 * t * (1 - t) * (1 - t) + 3 * x2 * t * t * (1 - t) + t * t * t; }
    function cy(t) { return 3 * y1 * t * (1 - t) * (1 - t) + 3 * y2 * t * t * (1 - t) + t * t * t; }
    return function (x) {
      if (x <= 0) return 0; if (x >= 1) return 1;
      var lo = 0, hi = 1, t = x;
      for (var i = 0; i < 40; i++) { t = (lo + hi) / 2; if (cx(t) < x) lo = t; else hi = t; }
      return cy(t);
    };
  }
  var EIN = bezier(T.enter.ease), EOUT = bezier(T.exit.ease);

  // ---------- layout ----------
  Object.assign(safe.style, { left: T.safe.left + "px", top: T.safe.top + "px",
    width: (T.W - T.safe.left - T.safe.right) + "px", height: (T.H - T.safe.top - T.safe.bottom) + "px",
    justifyContent: { upper: "flex-start", middle: "center", lower: "flex-end" }[T.position] || "center",
    alignItems: { left: "flex-start", center: "center", right: "flex-end" }[T.align] || "center",
    textAlign: T.align || "center", gap: (T.sizes.label * 0.5) + "px" });
  if (T.page_bg && T.page_bg !== "transparent") root.style.background = T.page_bg;

  function el(tag, cls, parent, text) {
    var e = document.createElement(tag); if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text; (parent || safe).appendChild(e); return e;
  }
  function plate(box) {                     // a plate's padding follows the type scale, not the browser default
    box.style.padding = Math.round(T.sizes.body * 0.42) + "px " + Math.round(T.sizes.body * 0.7) + "px";
    return box;
  }
  function setCase(s, c) { return c === "upper" ? String(s).toUpperCase() : c === "lower" ? String(s).toLowerCase() : String(s); }
  // A line split into words (and, for tracking/char families, characters). The emphasised word is wrapped
  // so a mark can sit behind it.
  function line(text, opts) {
    var L = el("div", "t-line " + (opts.face === "companion" ? "t-companion" : "t-anchor"), opts.parent);
    L.style.fontSize = opts.size + "px";
    if (opts.tracking !== undefined) L.style.letterSpacing = opts.tracking + "em";
    var words = setCase(text, opts.textCase).split(/(\s+)/), em = (opts.emphasis || "").toLowerCase(), marked = null;
    words.forEach(function (w) {
      if (/^\s+$/.test(w)) { L.appendChild(document.createTextNode(w)); return; }
      var W = el("span", "t-word", L), WT = el("span", "t-wtext", W);
      if (T.enter.family === "tracking-in") {
        Array.from(w).forEach(function (ch) { el("span", "t-char", WT, ch); });
      } else WT.textContent = w;
      if (em && !marked && w.toLowerCase().replace(/[^\p{L}\p{N}%$€£.,-]/gu, "") === em.replace(/[^\p{L}\p{N}%$€£.,-]/gu, "")) {
        marked = W; W.classList.add("t-em");
      }
    });
    return { el: L, words: Array.prototype.slice.call(L.querySelectorAll(".t-word")), marked: marked };
  }

  // ---------- entrance and exit families (the card picks one of each) ----------
  var tl = gsap.timeline({ paused: true });
  var RISE = T.rise_px;
  function enter(units, at) {
    var f = T.enter.family, d = T.enter.s, st = T.enter.stagger_s || 0;
    if (f === "tracking-in") {
      // the letters gather from a wider spacing: each glyph's x, not letter-spacing, which snaps to whole
      // pixels under a frame-by-frame seek and stutters (HyperFrames' lint, 2026-10-26)
      units.forEach(function (u, i) {
        var chars = Array.prototype.slice.call(u.querySelectorAll(".t-char"));
        if (!chars.length) chars = [u];
        var c = (chars.length - 1) / 2, spread = 0.24 * parseFloat(getComputedStyle(u).fontSize || "40");
        tl.fromTo(chars, { opacity: 0, x: function (k) { return (k - c) * spread; } },
                         { opacity: 1, x: 0, duration: d, ease: EIN }, at + i * st);
      });
    } else if (f === "mask-reveal") {
      units.forEach(function (u, i) {
        var m = document.createElement("span"); m.style.display = "block"; m.style.overflow = "hidden";
        m.style.paddingBottom = "0.08em"; u.parentNode.insertBefore(m, u); m.appendChild(u);
        tl.fromTo(u, { yPercent: 108 }, { yPercent: 0, duration: d, ease: EIN }, at + i * st);
      });
    } else if (f === "blur-resolve") {
      tl.fromTo(units, { opacity: 0, filter: "blur(10px)" },
                       { opacity: 1, filter: "blur(0px)", duration: d, ease: EIN, stagger: st }, at);
    } else if (f === "cut") {
      tl.set(units, { opacity: 1 }, at);
    } else {                                   // "fade-rise" (lines) and "per-word" (words): opacity + a short rise
      tl.fromTo(units, { opacity: 0, y: RISE }, { opacity: 1, y: 0, duration: d, ease: EIN, stagger: st }, at);
    }
    return at + d + st * Math.max(0, units.length - 1);
  }
  function exit(target, at) {
    var f = T.exit.family, d = T.exit.s;
    if (f === "cut" || d <= 0) return;
    if (f === "fade-up") tl.to(target, { opacity: 0, y: -RISE * 0.5, duration: d, ease: EOUT, immediateRender: false }, at);
    else tl.to(target, { opacity: 0, duration: d, ease: EOUT, immediateRender: false }, at);
  }
  function unitsOf(lines) {
    if (T.enter.family === "per-word") return lines.reduce(function (a, L) { return a.concat(L.words); }, []);
    return lines.map(function (L) { return L.el; });
  }
  function drawMark(L, at) {               // the highlight on the key word: drawn left to right after landing
    if (!L.marked || C.mark === "none") return at;
    var m = document.createElement("span"); m.className = "t-mark";
    if (C.mark === "underline") { m.style.bottom = "-0.04em"; m.style.height = "0.12em"; m.style.zIndex = "2"; }
    else { m.style.top = "0.12em"; m.style.height = "0.86em"; }
    L.marked.insertBefore(m, L.marked.firstChild);          // an earlier sibling paints behind the word
    tl.fromTo(m, { scaleX: 0 }, { scaleX: 1, duration: T.mark_s, ease: EIN }, at);
    return at + T.mark_s;
  }

  // ---------- the kits ----------
  var K = {}, landed = 0, block = safe;
  K["hero-line"] = function () {
    var Ls = (C.lines || []).map(function (s) { return line(s, { size: T.sizes.hero, textCase: T.text_case, tracking: T.tracking_em, emphasis: C.emphasis }); });
    landed = enter(unitsOf(Ls), 0);
    Ls.forEach(function (L) { if (L.marked) landed = drawMark(L, landed + 0.12); });
  };
  K["super"] = function () {
    var box = el("div", C.plate ? "t-plate" : ""); if (C.plate) plate(box);
    var Ls = (C.lines || []).map(function (s) { return line(s, { parent: box, size: T.sizes.body, textCase: T.text_case, tracking: T.tracking_em, face: C.face }); });
    landed = enter(C.plate ? [box] : unitsOf(Ls), 0);
  };
  K["stat"] = function () {
    var size = T.sizes.display, parts = [];
    if (C.label && C.label_pos === "above") parts.push(line(C.label, { size: T.sizes.body, face: "companion", textCase: T.text_case }));
    var N = el("div", "t-line t-anchor t-num"); N.style.fontSize = size + "px";
    if (C.prefix) el("span", "", N, C.prefix);
    var V = el("span", "", N, (C.from || 0).toFixed(C.decimals || 0));
    if (C.suffix) el("span", "", N, C.suffix);
    parts.push({ el: N, words: [N] });
    if (C.label && C.label_pos !== "above") parts.push(line(C.label, { size: T.sizes.body, face: "companion", textCase: T.text_case }));
    landed = enter(parts.map(function (p) { return p.el; }), 0);
    var o = { v: C.from || 0 }, dec = C.decimals || 0;
    // a counter never overshoots its value (H3): the ease is the card's entrance curve, clamped
    tl.to(V, { innerText: C.value, duration: T.count_s, ease: EIN, snap: { innerText: Math.pow(10, -dec) },
               modifiers: { innerText: function (x) { return Number(x).toFixed(dec); } } }, Math.max(0, landed - T.enter.s * 0.5));
    landed = Math.max(landed, landed - T.enter.s * 0.5 + T.count_s);
  };
  K["price-card"] = function () {
    var box = el("div", T.plate_on ? "t-plate" : ""); if (T.plate_on) plate(box);
    if (C.kicker) line(C.kicker, { parent: box, size: T.sizes.label, face: "companion", textCase: "upper", tracking: 0.12 });
    var P = line(C.price, { parent: box, size: T.sizes.display, textCase: "none" }); P.el.classList.add("t-num");
    var W = null;
    if (C.was) { W = line(C.was, { parent: box, size: T.sizes.title, face: "companion", textCase: "none" });
                 Object.assign(W.el.style, { position: "relative", opacity: "0.75", display: "inline-block" }); }
    if (C.note) line(C.note, { parent: box, size: T.sizes.label, face: "companion", textCase: T.text_case });
    landed = enter([box], 0);
    if (W) {
      var s = document.createElement("span"); s.className = "t-mark";
      Object.assign(s.style, { top: "46%", height: "0.08em", zIndex: "1", left: "0", right: "0" });   // the figures' middle, measured on the 2026-10-26 renders (52 % sat on the lower bowl)
      // the strike covers the old price on purpose: HyperFrames' layout check reads the flag on the covered text
      [W.el].concat(Array.prototype.slice.call(W.el.querySelectorAll("*"))).forEach(function (e) {
        e.setAttribute("data-layout-allow-occlusion", ""); });
      W.el.appendChild(s);
      tl.fromTo(s, { scaleX: 0 }, { scaleX: 1, duration: T.mark_s, ease: EIN }, landed + 0.1);
      landed += 0.1 + T.mark_s;
    }
  };
  K["end-card"] = function () {
    var units = [];
    if (C.logo) { var I = el("img", "t-logo"); I.src = C.logo; I.style.height = (T.sizes.display * 1.4) + "px"; units.push(I); }
    if (C.line) units.push(line(C.line, { size: T.sizes.title, textCase: T.text_case }).el);
    if (C.url) { var U = line(C.url, { size: T.sizes.body, face: "companion", textCase: "none", tracking: 0.02 }); units.push(U.el); }
    landed = enter(units, 0);
  };
  K["lockup"] = function () {
    var units = [];
    if (C.kicker) units.push(line(C.kicker, { size: T.sizes.label, face: "companion", textCase: "upper", tracking: 0.18 }).el);
    // the line is set, never shrunk: a line too wide for the frame goes on two (content.lines)
    ((C.lines && C.lines.length) ? C.lines : [C.line]).forEach(function (s) {
      units.push(line(s, { size: T.sizes.hero, textCase: T.text_case, tracking: T.tracking_em }).el); });
    landed = enter(units, 0);
    if (C.rule) {
      var R = el("div", "t-rule"); R.style.width = Math.min(T.W * 0.3, 360) + "px";
      tl.fromTo(R, { scaleX: 0 }, { scaleX: 1, duration: T.mark_s, ease: EIN }, landed);
      landed += T.mark_s;
    }
    if (C.label) {
      var Lb = line(C.label, { size: T.sizes.label, face: "companion", textCase: "upper", tracking: 0.12 }).el;
      tl.fromTo(Lb, { opacity: 0 }, { opacity: 1, duration: T.enter.s * 0.6, ease: EIN }, landed);
      landed += T.enter.s * 0.6;
    }
  };
  K["place-time"] = function () {
    var Ls = [line(C.place, { size: T.sizes.body, face: "companion", textCase: T.text_case, tracking: 0.04 })];
    if (C.time) Ls.push(line(C.time, { size: T.sizes.label, face: "companion", textCase: "upper", tracking: 0.14 }));
    landed = enter(unitsOf(Ls), 0);
  };
  K["main-title"] = function () {
    var units = [line(C.title, { size: T.sizes.display, textCase: T.text_case, tracking: T.tracking_em }).el];
    if (C.subtitle) units.push(line(C.subtitle, { size: T.sizes.body, face: "companion", textCase: "upper", tracking: 0.16 }).el);
    landed = enter(units, 0);
  };
  K["episode-card"] = function () {
    var units = [];
    if (C.kicker) units.push(line(C.kicker, { size: T.sizes.label, face: "companion", textCase: "upper", tracking: 0.2 }).el);
    units.push(line(C.title, { size: T.sizes.hero, textCase: T.text_case, tracking: T.tracking_em }).el);
    landed = enter(units, 0);
  };

  function build() {
    if (!K[T.kit]) throw new Error("unknown kit " + T.kit);
    K[T.kit]();
    var exitAt = T.dur - (T.exit.family === "cut" ? 0 : T.exit.s);
    exit(Array.prototype.slice.call(safe.children), exitAt);
    tl.set({}, {}, T.dur);                                   // the timeline is exactly the title's length
    window.__timelines = window.__timelines || {};
    window.__timelines.main = tl;
    tl.seek(landed, false);
    var r = safe.getBoundingClientRect(), inner = { left: 1e9, top: 1e9, right: -1e9, bottom: -1e9 }, over = [];
    safe.querySelectorAll(".t-line, .t-logo").forEach(function (n) {
      var b = n.getBoundingClientRect();
      inner.left = Math.min(inner.left, b.left); inner.top = Math.min(inner.top, b.top);
      inner.right = Math.max(inner.right, b.right); inner.bottom = Math.max(inner.bottom, b.bottom);
      if (n.scrollWidth > r.width + 1) over.push(n.textContent);
    });
    window.__info = { kit: T.kit, landed: landed, exit_at: exitAt, hold_s: Math.max(0, exitAt - landed),
                      block: inner, overflow: over, safe: { left: r.left, top: r.top, right: r.right, bottom: r.bottom },
                      fonts: Array.prototype.map.call(document.fonts, function (f) { return f.family + ":" + f.status; }) };
    tl.seek(0, false);
  }
  build();
})();
