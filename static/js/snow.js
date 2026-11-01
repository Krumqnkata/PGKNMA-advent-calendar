/* Падащ сняг върху canvas. Спазва prefers-reduced-motion и може да се изключи. */
(function () {
  "use strict";

  var STORAGE_KEY = "advent-snow";
  var canvas = document.getElementById("snow");
  var toggle = document.getElementById("snow-toggle");
  if (!canvas || !canvas.getContext) return;

  var ctx = canvas.getContext("2d");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var flakes = [];
  var width = 0;
  var height = 0;
  var rafId = null;
  var lastTime = 0;

  function readPreference() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function savePreference(on) {
    try {
      window.localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
    } catch (e) { /* без значение */ }
  }

  var stored = readPreference();
  var enabled = stored ? stored === "on" : !reduceMotion.matches;

  function makeFlake(randomY) {
    var r = Math.random() * 2.4 + 0.8;
    return {
      x: Math.random() * width,
      y: randomY ? Math.random() * height : -10,
      r: r,
      speed: 18 + r * 16 + Math.random() * 12,
      sway: Math.random() * 0.8 + 0.3,
      phase: Math.random() * Math.PI * 2,
      alpha: Math.random() * 0.5 + 0.4
    };
  }

  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var target = Math.min(170, Math.round((width * height) / 9000));
    while (flakes.length < target) flakes.push(makeFlake(true));
    flakes.length = target;
  }

  function frame(now) {
    var dt = Math.min((now - lastTime) / 1000, 0.05);
    lastTime = now;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#ffffff";

    for (var i = 0; i < flakes.length; i++) {
      var f = flakes[i];
      f.phase += dt * f.sway;
      f.y += f.speed * dt;
      f.x += Math.sin(f.phase) * 18 * dt;

      if (f.y - f.r > height) {
        flakes[i] = makeFlake(false);
        continue;
      }
      if (f.x < -5) f.x = width + 5;
      if (f.x > width + 5) f.x = -5;

      ctx.globalAlpha = f.alpha;
      ctx.beginPath();
      ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    rafId = window.requestAnimationFrame(frame);
  }

  function start() {
    if (rafId !== null) return;
    canvas.hidden = false;
    resize();
    lastTime = performance.now();
    rafId = window.requestAnimationFrame(frame);
  }

  function stop() {
    if (rafId !== null) window.cancelAnimationFrame(rafId);
    rafId = null;
    ctx.clearRect(0, 0, width, height);
    canvas.hidden = true;
  }

  function apply() {
    if (enabled && !document.hidden) start();
    else stop();
    if (toggle) {
      toggle.setAttribute("aria-pressed", enabled ? "true" : "false");
      toggle.title = enabled ? "Спри снега" : "Пусни снега";
    }
  }

  window.addEventListener("resize", function () {
    if (rafId !== null) resize();
  });

  // Не рисуваме, докато табът е скрит.
  document.addEventListener("visibilitychange", apply);

  // Ако потребителят не е избирал ръчно, следваме системната настройка.
  reduceMotion.addEventListener("change", function () {
    if (readPreference() === null) {
      enabled = !reduceMotion.matches;
      apply();
    }
  });

  if (toggle) {
    toggle.addEventListener("click", function () {
      enabled = !enabled;
      savePreference(enabled);
      apply();
    });
  }

  apply();
})();
