/* Humanize avatar maths. One source of truth shared by the dashboard (browser) and the tests (node).
   scripts/avatar.py implements the same parameter derivation; tests/test_avatar_parity.py keeps them equal. */
(function (root) {
  'use strict';
  var subtle = (root.crypto || require('crypto').webcrypto).subtle;

  async function sha256(s) {
    var b = await subtle.digest('SHA-256', new TextEncoder().encode(s));
    return new Uint8Array(b);
  }
  function mulberry32(a) {
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1) >>> 0;
      t ^= (t + Math.imul(t ^ (t >>> 7), t | 61)) >>> 0;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* Pure: seed string in, palette and ribbon shapes out. Order of random draws is part of the contract. */
  async function orbParams(seed) {
    var h = await sha256(seed);
    var base = h[0] / 255 * 360, spread = 28 + h[1] / 255 * 60, comp = 150 + h[2] / 255 * 60, sat = 0.85 + h[3] / 255 * 0.15;
    var hues = [base, (base + spread) % 360, (base - spread + 360) % 360, (base + comp) % 360];
    var lights = [0.58, 0.52, 0.66, 0.5];
    var seedInt = ((h[4] << 24) | (h[5] << 16) | (h[6] << 8) | h[7]) >>> 0;
    var rnd = mulberry32(seedInt);
    var U = function (a, b) { return a + (b - a) * rnd(); };
    var C = function (xs) { return xs[Math.floor(rnd() * xs.length)]; };
    var n = 4 + h[5] % 3, ribbons = [];
    for (var i = 0; i < n; i++) {
      var phase = U(0, Math.PI * 2);
      var a1 = U(0.10, 0.22), a2 = U(0.04, 0.10), f1 = C([1, 2, 3]), f2 = C([2, 3, 5]);
      var p1 = U(0, Math.PI * 2), p2 = U(0, Math.PI * 2), b = U(0.16, 0.30), tilt = U(0.6, 1.0);
      var wHalo = U(0.035, 0.06), wCore = U(0.010, 0.018);
      var drift = U(0.05, 0.14) * (i % 2 ? 1 : -1);
      ribbons.push({ phase: phase, a1: a1, a2: a2, f1: f1, f2: f2, p1: p1, p2: p2, base: b, tilt: tilt, w_halo: wHalo, w_core: wCore, drift: drift });
    }
    return { hues: hues, sat: sat, lights: lights, ribbons: ribbons };
  }

  function colors(params) {
    return params.hues.map(function (h, i) {
      return 'hsl(' + h.toFixed(1) + ' ' + (params.sat * 100).toFixed(0) + '% ' + (params.lights[i] * 100).toFixed(0) + '%)';
    });
  }

  /* Draw one animation frame. tMs is a millisecond clock; disc is the background colour of the disc. */
  function drawOrb(canvas, params, tMs, disc) {
    var ctx = canvas.getContext('2d'), S = canvas.width, t = tMs / 1000, cols = colors(params);
    ctx.clearRect(0, 0, S, S);
    ctx.save();
    ctx.beginPath(); ctx.arc(S / 2, S / 2, S * 0.47, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = disc || '#07070a'; ctx.fillRect(0, 0, S, S);
    ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    params.ribbons.forEach(function (r, idx) {
      var ph = r.phase + t * r.drift;
      ctx.beginPath();
      for (var i = 0; i <= 360; i += 3) {
        var a = i * Math.PI / 180 + ph;
        var rad = S * (r.base + r.a1 * Math.sin(r.f1 * a + r.p1 + t * 0.2) + r.a2 * Math.sin(r.f2 * a + r.p2));
        var x = S / 2 + Math.cos(a) * rad, y = S / 2 + Math.sin(a) * rad * r.tilt;
        if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = cols[idx % 4];
      ctx.globalAlpha = 0.55; ctx.lineWidth = S * r.w_halo; ctx.filter = 'blur(' + (S * 0.045) + 'px)'; ctx.stroke();
      ctx.globalAlpha = 0.95; ctx.lineWidth = S * r.w_core; ctx.filter = 'blur(' + (S * 0.004) + 'px)'; ctx.stroke();
    });
    ctx.filter = 'none'; ctx.globalAlpha = 1;
    var gr = ctx.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S * 0.16);
    gr.addColorStop(0, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = gr; ctx.fillRect(0, 0, S, S);
    ctx.restore();
  }

  root.HZ = { orbParams: orbParams, colors: colors, drawOrb: drawOrb, mulberry32: mulberry32 };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.HZ;
})(typeof window !== 'undefined' ? window : globalThis);
