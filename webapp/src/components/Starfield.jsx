import { useEffect, useRef } from "react";

/** Twinkling star field rendered behind the app content.
 *  Pass `shootingStars` to spawn occasional streaking comets — used on the
 *  loading splash for a bit more life than the plain background use gets. */
export default function Starfield({ shootingStars = false }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let stars = [];
    let comets = [];
    let raf;
    let nextCometAt = 0;

    function resize() {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    }
    function init() {
      stars = Array.from({ length: 150 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.6 + 0.4,
        a: Math.random(),
        s: Math.random() * 0.008 + 0.003,
      }));
    }
    function spawnComet() {
      const fromLeft = Math.random() > 0.5;
      const x = fromLeft ? Math.random() * canvas.width * 0.4 : canvas.width * 0.6 + Math.random() * canvas.width * 0.4;
      comets.push({
        x,
        y: -20,
        vx: (fromLeft ? 1 : -1) * (1.6 + Math.random() * 1.2),
        vy: 2.4 + Math.random() * 1.6,
        len: 70 + Math.random() * 50,
        life: 1,
      });
    }
    function draw(t) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      stars.forEach((s) => {
        s.a += s.s;
        if (s.a > 1 || s.a < 0) s.s *= -1;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,184,0,${s.a * 0.85})`;
        ctx.shadowColor = "rgba(255,184,0,.8)";
        ctx.shadowBlur = s.r * 2.5;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      if (shootingStars) {
        if (t > nextCometAt) {
          spawnComet();
          nextCometAt = t + 1800 + Math.random() * 2600;
        }
        comets = comets.filter((c) => c.life > 0 && c.y < canvas.height + 40);
        comets.forEach((c) => {
          c.x += c.vx;
          c.y += c.vy;
          c.life -= 0.012;
          const angle = Math.atan2(c.vy, c.vx);
          const tailX = c.x - Math.cos(angle) * c.len;
          const tailY = c.y - Math.sin(angle) * c.len;
          const grad = ctx.createLinearGradient(c.x, c.y, tailX, tailY);
          grad.addColorStop(0, `rgba(255,226,150,${c.life})`);
          grad.addColorStop(1, "rgba(255,226,150,0)");
          ctx.strokeStyle = grad;
          ctx.lineWidth = 1.4;
          ctx.beginPath();
          ctx.moveTo(c.x, c.y);
          ctx.lineTo(tailX, tailY);
          ctx.stroke();
        });
      }

      raf = requestAnimationFrame(draw);
    }

    resize();
    init();
    raf = requestAnimationFrame(draw);
    const onResize = () => {
      resize();
      init();
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [shootingStars]);

  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full z-0 pointer-events-none" />;
}
