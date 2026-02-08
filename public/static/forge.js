/**
 * ZUUP FORGE — VT100-era UI logic
 */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadPlatforms();
  loadStatus();
});

function initTabs() {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
      document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
      tab.classList.add('active');
      const panelId = 'panel-' + tab.dataset.panel;
      document.getElementById(panelId)?.classList.add('active');
    });
  });
}

async function loadPlatforms() {
  const el = document.getElementById('platform-list');
  try {
    const res = await fetch('/api/platforms');
    const data = await res.json();
    if (!data.platforms || data.platforms.length === 0) {
      el.innerHTML = '<p class="muted">No platforms detected. Run: forge init aureon --from specs/aureon.platform.yaml</p>';
      return;
    }
    el.innerHTML = data.platforms
      .map(
        (p) => `
      <div class="platform-card" data-spec="${p.name}">
        <div class="name">${escapeHtml(p.display_name || p.name)}</div>
        <div class="domain">${escapeHtml(p.domain || '-')}</div>
        <div class="desc">${escapeHtml(p.description || '')}</div>
      </div>
    `
      )
      .join('');
    document.querySelectorAll('.platform-card').forEach((card) => {
      card.addEventListener('click', () => loadSpec(card.dataset.spec));
    });
  } catch (e) {
    el.innerHTML = '<p class="muted">Could not load platforms. Is the server running?</p>';
  }
}

async function loadSpec(name) {
  document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
  document.querySelector('[data-panel="spec"]')?.classList.add('active');
  document.getElementById('panel-spec')?.classList.add('active');

  document.getElementById('spec-name').textContent = name;
  const el = document.getElementById('spec-content');
  el.textContent = 'Loading...';
  try {
    const res = await fetch(`/api/spec/${name}`);
    const data = await res.json();
    el.textContent = data.content || data.error || 'No content';
  } catch (e) {
    el.textContent = 'Error loading spec.';
  }
}

async function loadStatus() {
  try {
    const [versionRes, platformsRes] = await Promise.all([
      fetch('/api/status/version'),
      fetch('/api/platforms'),
    ]);
    const versionData = versionRes.ok ? await versionRes.json() : { version: 'unknown' };
    const platformsData = platformsRes.ok ? await platformsRes.json() : { platforms: [] };
    document.getElementById('version-out').textContent = versionData.version || 'zuup-forge 0.1.0';
    document.getElementById('platforms-out').textContent =
      (platformsData.platforms || []).map((p) => p.name).join(', ') || 'none';
  } catch (_) {
    document.getElementById('version-out').textContent = 'zuup-forge 0.1.0';
    document.getElementById('platforms-out').textContent = 'n/a (check server)';
  }
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}
