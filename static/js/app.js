// Shared accessibility toggles (theme + contrast + text size), remembered between visits.
(function () {
  const MIN = 14, MAX = 28, STEP = 2;
  const body = document.body, root = document.documentElement;
  const get = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const set = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };

  let size = parseInt(get('sc_font') || '18', 10);
  const down = document.getElementById('fontDown'), up = document.getElementById('fontUp');
  function applyFont() {
    root.style.setProperty('--fs', size + 'px');
    set('sc_font', size);
    if (down) down.disabled = size <= MIN;
    if (up) up.disabled = size >= MAX;
  }

  if (down) down.onclick = () => { size = Math.max(MIN, size - STEP); applyFont(); };
  if (up) up.onclick = () => { size = Math.min(MAX, size + STEP); applyFont(); };

  const themeToggle = document.getElementById('themeToggle');
  const savedTheme = get('sc_theme') || 'dark';
  const applyTheme = (theme) => {
    body.setAttribute('data-theme', theme);
    if (themeToggle) {
      themeToggle.textContent = theme === 'dark' ? '🌙' : '☀️';
      themeToggle.setAttribute('aria-label', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
    }
    set('sc_theme', theme);
  };
  if (savedTheme === 'light') applyTheme('light');
  else applyTheme('dark');
  if (themeToggle) themeToggle.onclick = () => {
    const current = body.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  };

  if (get('sc_hc') === '1') body.classList.add('hc');
  const cb = document.getElementById('contrastBtn');
  if (cb) {
    cb.setAttribute('aria-pressed', body.classList.contains('hc'));
    cb.onclick = () => {
      const on = body.classList.toggle('hc');
      cb.setAttribute('aria-pressed', on);
      set('sc_hc', on ? '1' : '0');
    };
  }

  const navToggle = document.getElementById('navToggle');
  const nav = document.getElementById('primaryNav');
  if (navToggle && nav) {
    navToggle.onclick = () => {
      const expanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', String(!expanded));
      nav.classList.toggle('open');
    };
  }

  applyFont();
})();
