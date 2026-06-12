/* main.js — Core site JavaScript */

// ─── Navbar Toggle ─────────────────────────────────────────────────────────
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');
if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', navLinks.classList.contains('open'));
  });
  document.addEventListener('click', e => {
    if (!navLinks.contains(e.target) && !navToggle.contains(e.target)) {
      navLinks.classList.remove('open');
    }
  });
}

// ─── Navbar scroll shadow ──────────────────────────────────────────────────
const navbar = document.getElementById('navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.style.boxShadow = window.scrollY > 10 ? '0 2px 12px rgba(0,0,0,.08)' : '';
  }, { passive: true });
}

// ─── Auto-resize textarea ──────────────────────────────────────────────────
document.querySelectorAll('textarea').forEach(ta => {
  ta.addEventListener('input', () => {
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 300) + 'px';
  });
});

// ─── Flash message auto-dismiss ────────────────────────────────────────────
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(el => {
    el.style.transition = 'opacity .4s ease, transform .4s ease';
    el.style.opacity    = '0';
    el.style.transform  = 'translateX(20px)';
    setTimeout(() => el.remove(), 400);
  });
}, 4000);

// ─── Loading state on form submit ──────────────────────────────────────────
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', () => {
    const btn = form.querySelector('button[type="submit"]');
    if (btn && !btn.dataset.noLoad) {
      btn.disabled = true;
      const orig = btn.innerHTML;
      btn.dataset.orig = orig;
      btn.innerHTML = `<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg> Processing…`;
    }
  });
});

// CSS for spin
const spinStyle = document.createElement('style');
spinStyle.textContent = '.spin{animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}';
document.head.appendChild(spinStyle);

// ─── Skeleton loaders ──────────────────────────────────────────────────────
function showSkeleton(container, count = 3) {
  container.innerHTML = Array(count).fill(
    `<div class="skeleton" style="height:80px;border-radius:10px;background:linear-gradient(90deg,#f0f0f0 25%,#e0e0e0 50%,#f0f0f0 75%);background-size:200% 100%;animation:shimmer 1.5s infinite"></div>`
  ).join('');
}
const shimmerStyle = document.createElement('style');
shimmerStyle.textContent = '@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}';
document.head.appendChild(shimmerStyle);

// ─── Tool form: show loading state with message ─────────────────────────────
document.querySelectorAll('.tool-form').forEach(form => {
  form.addEventListener('submit', () => {
    const result = document.querySelector('.result-card');
    if (result) {
      result.innerHTML = `<div style="display:flex;flex-direction:column;gap:1rem;padding:1rem">
        <div class="skeleton" style="height:60px;border-radius:10px;background:linear-gradient(90deg,#f0f0f0 25%,#e0e0e0 50%,#f0f0f0 75%);background-size:200% 100%;animation:shimmer 1.5s infinite"></div>
        <div class="skeleton" style="height:40px;border-radius:10px;background:linear-gradient(90deg,#f0f0f0 25%,#e0e0e0 50%,#f0f0f0 75%);background-size:200% 100%;animation:shimmer 1.5s infinite"></div>
        <p style="text-align:center;color:#6b7280;font-size:.875rem">Sending request to bot… (~3–5 seconds)</p>
      </div>`;
    }
  });
});

// ─── Announce slider auto-scroll ────────────────────────────────────────────
const annSlider = document.getElementById('annSlider');
if (annSlider && annSlider.children.length > 1) {
  let idx = 0;
  const cards = annSlider.querySelectorAll('.ann-card');
  setInterval(() => {
    idx = (idx + 1) % cards.length;
    cards[idx].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
  }, 4500);
}

// ─── Hover card lift ─────────────────────────────────────────────────────────
document.querySelectorAll('.tool-card,.guild-card,.partner-card,.feature-card').forEach(card => {
  card.addEventListener('mouseenter', () => { card.style.willChange = 'transform'; });
  card.addEventListener('mouseleave', () => { card.style.willChange = ''; });
});

