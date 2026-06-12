/* animations.js — Count-up, fade-in, slide-in animations */

// ─── Count-up animation ────────────────────────────────────────────────────
function countUp(el, target, duration = 1800) {
  let start = 0;
  const step = target / (duration / 16);
  const timer = setInterval(() => {
    start += step;
    if (start >= target) {
      el.textContent = target.toLocaleString();
      clearInterval(timer);
    } else {
      el.textContent = Math.floor(start).toLocaleString();
    }
  }, 16);
}

// Trigger count-up when elements enter the viewport
const countEls = document.querySelectorAll('[data-count]');
if (countEls.length) {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el     = entry.target;
        const target = parseInt(el.dataset.count, 10);
        if (!isNaN(target)) countUp(el, target);
        obs.unobserve(el);
      }
    });
  }, { threshold: 0.3 });
  countEls.forEach(el => obs.observe(el));
}

// ─── Fade-in on scroll ─────────────────────────────────────────────────────
const fadeStyle = document.createElement('style');
fadeStyle.textContent = `
  .fade-in { opacity: 0; transform: translateY(20px); transition: opacity .55s ease, transform .55s ease; }
  .fade-in.visible { opacity: 1; transform: none; }
`;
document.head.appendChild(fadeStyle);

function initFadeIn() {
  const candidates = [
    '.tool-card', '.tool-full-card', '.feature-card', '.partner-card',
    '.partner-full-card', '.guild-card', '.guild-full-card', '.ann-full-card',
    '.support-card', '.support-full-card', '.faq-item', '.status-card',
    '.result-card', '.admin-form-section', '.admin-nav-card'
  ];
  const els = document.querySelectorAll(candidates.join(','));
  els.forEach((el, i) => {
    el.classList.add('fade-in');
    el.style.transitionDelay = (i % 6) * 0.06 + 's';
  });
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.fade-in').forEach(el => obs.observe(el));
}

document.addEventListener('DOMContentLoaded', initFadeIn);

// ─── Particle hero background ──────────────────────────────────────────────
const canvas_el = document.getElementById('particles');
if (canvas_el) {
  const canvas = document.createElement('canvas');
  canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:.35';
  canvas_el.appendChild(canvas);
  const ctx = canvas.getContext('2d');

  let W, H, particles = [];

  function resize() {
    W = canvas.width  = canvas_el.offsetWidth;
    H = canvas.height = canvas_el.offsetHeight;
  }
  resize();
  window.addEventListener('resize', resize, { passive: true });

  const PRIMARY = getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() || '#0070f3';

  for (let i = 0; i < 50; i++) {
    particles.push({
      x: Math.random() * 1200,
      y: Math.random() * 600,
      r: Math.random() * 2 + 1,
      dx: (Math.random() - .5) * .4,
      dy: (Math.random() - .5) * .4,
    });
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = PRIMARY;
    particles.forEach(p => {
      p.x += p.dx; p.y += p.dy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    });

    // Draw connecting lines for nearby particles
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.strokeStyle = PRIMARY;
          ctx.globalAlpha = (1 - dist / 120) * 0.3;
          ctx.lineWidth = 0.5;
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
}

// ─── Hero badge shimmer ────────────────────────────────────────────────────
const heroBadge = document.querySelector('.hero-badge');
if (heroBadge) {
  const s = document.createElement('style');
  s.textContent = `.hero-badge{background-size:200% 100%;animation:badgeShimmer 3s ease infinite;}
  @keyframes badgeShimmer{0%,100%{background-position:0%}50%{background-position:100%}}`;
  document.head.appendChild(s);
}

// ─── Smooth page load transition ──────────────────────────────────────────
const pageStyle = document.createElement('style');
pageStyle.textContent = `
  body { animation: pageLoad .35s ease both; }
  @keyframes pageLoad { from { opacity: 0; } to { opacity: 1; } }
`;
document.head.appendChild(pageStyle);
