(function () {
  // ── Dark mode ──
  const html = document.documentElement;
  const btn  = document.getElementById('darkToggle');

  function applyTheme(dark) {
    if (dark) html.classList.add('dark');
    else       html.classList.remove('dark');
  }

  // Persist across pages
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved === 'dark' || (!saved && prefersDark));

  if (btn) {
    btn.addEventListener('click', () => {
      const isDark = html.classList.toggle('dark');
      localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
  }

  // ── Smooth scroll for anchor links ──
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
})();
