/* Звёздный фон — один на все страницы сайта (<canvas id="bg-canvas">).
   Раньше у каждой страницы была своя копия с разной густотой и яркостью. */
(function () {
  const c = document.getElementById('bg-canvas');
  if (!c) return;
  const ctx = c.getContext('2d');
  function resize() { c.width = innerWidth; c.height = innerHeight; }
  resize(); window.addEventListener('resize', resize, { passive: true });
  const stars = Array.from({ length: 340 }, () => ({
    x: Math.random(), y: Math.random(),
    r: Math.random() * 1.6 + 0.3,
    o: Math.random() * 0.6 + 0.35,
    sp: Math.random() * 0.0004 + 0.00006,
    ph: Math.random() * Math.PI * 2,
  }));
  let f = 0;
  function draw() {
    ctx.clearRect(0, 0, c.width, c.height); f++;
    for (const s of stars) {
      const a = s.o * (0.55 + 0.45 * Math.sin(f * s.sp * 200 + s.ph));
      ctx.beginPath();
      ctx.arc(s.x * c.width, s.y * c.height, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,216,120,${a})`; ctx.fill();
    }
    requestAnimationFrame(draw);
  }
  draw();
})();
