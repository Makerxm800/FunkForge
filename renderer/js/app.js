/* ==========================================================================
   FunkForge (Beta) — renderer
   Plain browser JS. Runs unchanged inside Electron and in a normal browser;
   OS-specific features light up only when `window.ff` (the preload bridge)
   is present.
   ========================================================================== */
'use strict';

const DESKTOP = typeof window.ff !== 'undefined';

const state = {
  view: 'discover',
  layout: 'grid',
  items: [],
  page: 1,
  more: true,
  loading: false,
  query: '',
  sort: 'downloads',
  installed: [],
  installedNames: new Set(),
  config: null,
  meta: null,
  selected: null,
  selectedFile: null,
  selectedImages: [],
  imgIndex: 0,
};

/* ------------------------------------------------------------------ helpers */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const esc = (s) => String(s ?? '').replace(/[&<>"']/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const fmtNum = (n) => {
  const v = Number(n) || 0;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}k`;
  return String(v);
};

const fmtSize = (b) => {
  const n = Number(b) || 0;
  if (!n) return '';
  const u = ['B', 'KB', 'MB', 'GB'];
  let i = 0; let v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i += 1; }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${u[i]}`;
};

const fmtDate = (ts) => {
  const t = Number(ts);
  if (!t) return '';
  return new Date(t * 1000).toLocaleDateString(undefined,
    { year: 'numeric', month: 'short', day: 'numeric' });
};

const initials = (s) => String(s || '?')
  .replace(/[^\p{L}\p{N} ]/gu, ' ')
  .split(/\s+/).filter(Boolean).slice(0, 2)
  .map((w) => w[0].toUpperCase()).join('') || '?';

/** "Today" / "Yesterday" / "12 Mar" */
function dayLabel(ms) {
  const d = new Date(ms);
  const today = new Date();
  const startOf = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diffDays = Math.round((startOf(today) - startOf(d)) / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function clockTime(ms) {
  return new Date(ms).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

function setStatus(text) { $('#status').textContent = text; }

function setConn(kind, label) {
  const el = $('#conn');
  el.className = `conn ${kind}`;
  el.querySelector('span').textContent = label;
}

/* -------------------------------------------------------------------- toasts */
function toast(msg, kind = 'info', ms = 3600) {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  const icon = kind === 'ok' ? '✅' : kind === 'err' ? '⚠️' : 'ℹ️';
  el.innerHTML = `<span>${icon}</span><span>${esc(msg)}</span>`;
  $('#toasts').appendChild(el);
  setTimeout(() => {
    el.classList.add('out');
    setTimeout(() => el.remove(), 300);
  }, ms);
}

/* ----------------------------------------------------------------------- api */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
  });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { error: text }; }
  if (!res.ok) {
    const err = new Error(data.error || `HTTP ${res.status}`);
    err.offline = !!data.offline;
    throw err;
  }
  return data;
}

const apiPost = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) });

/* ------------------------------------------------------------------ theming */
function applyTheme(name) {
  const root = document.documentElement;
  // Smooth cross-fade: briefly let transitions run on the colour change.
  root.classList.add('theming');
  root.dataset.theme = name || 'midnight';
  clearTimeout(applyTheme._t);
  applyTheme._t = setTimeout(() => root.classList.remove('theming'), 500);
}

function applyLayout(mode) {
  state.layout = mode;
  $('#grid').classList.toggle('list-view', mode === 'list');
  $$('#viewToggle button, #setViewToggle button').forEach((b) => {
    if (b.dataset.view === mode) b.classList.add('is-active');
    else b.classList.remove('is-active');
  });
}

/* --------------------------------------------------------- nav tab indicator */
function moveNavIndicator() {
  const active = $('.nav-item.is-active');
  const ind = $('#navIndicator');
  if (!active || !ind) return;
  ind.style.height = `${active.offsetHeight - 10}px`;
  ind.style.transform = `translateY(${active.offsetTop + 5}px)`;
  ind.classList.add('on');
}

/* ------------------------------------------------------------------- modal
   Kept visible during the close transition, then hidden, so closing animates
   instead of snapping away. */
let modalCloseTimer = null;

function openModal() {
  clearTimeout(modalCloseTimer);
  const m = $('#modal');
  m.hidden = false;
  requestAnimationFrame(() => m.classList.add('show'));
}

function closeModal() {
  const m = $('#modal');
  if (m.hidden) return;
  m.classList.remove('show');
  clearTimeout(modalCloseTimer);
  modalCloseTimer = setTimeout(() => { m.hidden = true; }, 240);
  state.selected = null;
}

/* ---------------------------------------------------------------- connection */
async function checkHealth() {
  try {
    await api('/api/health');
    setConn('ok', 'Online');
    return true;
  } catch (_) {
    setConn('err', 'Backend offline');
    return false;
  }
}

/* ------------------------------------------------------------------- render */
function cardHtml(item, index) {
  const isLocal = !!item.local;
  const img = isLocal
    ? (item.preview ? `/api/local-img?path=${encodeURIComponent(item.preview)}` : '')
    : (item.images && item.images[0]
      ? `/api/img?url=${encodeURIComponent(item.images[0])}` : '');

  const badges = [];
  if (item.model && item.model !== 'Mod') badges.push(`<span class="badge badge-type">${esc(item.model)}</span>`);
  if (item.engine) badges.push(`<span class="badge badge-engine">⚙ ${esc(String(item.engine).replace(' Engine', ''))}</span>`);
  if (isLocal && item.size) badges.push(`<span class="badge badge-size">${fmtSize(item.size)}</span>`);

  const meta = isLocal
    ? `<span class="author">${esc(item.name)}</span><span>📦 ${fmtSize(item.size)}</span>`
    : `<span class="author">👤 ${esc(item.author)}</span><span>⬇ ${fmtNum(item.downloads)}</span>`;

  // Stagger the entrance, but cap it so late cards don't crawl in.
  const delay = Math.min(index, 14) * 28;

  return `
    <article class="card" style="--d:${delay}ms"
             data-id="${esc(isLocal ? item.dir : item.id)}" data-local="${isLocal ? 1 : 0}">
      <div class="card-img-wrap">
        ${img
          ? `<img class="card-img" loading="lazy" src="${esc(img)}" alt=""
                 onload="this.classList.add('loaded')"
                 onerror="this.style.display='none';this.nextElementSibling.style.display='grid'">`
          : ''}
        <div class="card-img-fallback" style="${img ? 'display:none' : ''}">${esc(initials(item.name))}</div>
        ${item.official ? '<span class="card-official">🌟 OFFICIAL</span>' : ''}
        ${(isLocal || item.installed) ? '<span class="card-installed">✓ INSTALLED</span>' : ''}
      </div>
      <div class="card-body">
        <div class="card-title">${esc(item.name)}</div>
        <div class="card-meta">${meta}</div>
        <div class="card-badges">${badges.join('')}</div>
      </div>
    </article>`;
}

function renderItems() {
  const grid = $('#grid');
  grid.innerHTML = state.items.map(cardHtml).join('');

  const empty = !state.items.length;
  $('#empty').hidden = !empty;
  if (empty) {
    $('#emptyArt').textContent = state.view === 'installed' ? '📦' : '🎤';
    $('#emptyTitle').textContent = state.view === 'installed'
      ? 'No mods installed yet'
      : (state.query ? `No results for “${state.query}”` : 'Nothing to show');
    $('#emptyText').textContent = state.view === 'installed'
      ? 'Install something from Discover, or drop a mod folder into your mods folder.'
      : (state.query ? 'Try a different search term.' : 'Check your connection and try again.');
  }
  $('#resultsCount').textContent =
    `${state.items.length} ${state.view === 'installed' ? 'installed' : 'result'}${state.items.length === 1 ? '' : 's'}`;
  $('#loadMore').hidden = state.view === 'installed' || !state.more || empty;
}

function showSkeletons(on) {
  const wrap = $('#skeletons');
  if (!on) { wrap.innerHTML = ''; wrap.hidden = true; return; }
  wrap.hidden = false;
  wrap.innerHTML = Array.from({ length: 8 }, () => `
    <div class="skel"><div class="skel-img"></div>
      <div class="skel-line"></div><div class="skel-line short"></div></div>`).join('');
}

/* ------------------------------------------------------------------ loading */
async function loadDiscover(reset = true) {
  if (state.loading) return;
  state.loading = true;
  if (reset) { state.page = 1; state.items = []; showSkeletons(true); $('#grid').innerHTML = ''; $('#empty').hidden = true; }
  setStatus(state.query ? `Searching for “${state.query}”…` : 'Browsing mods…');
  setConn('loading', 'Loading…');

  try {
    const q = state.query
      ? `/api/search?q=${encodeURIComponent(state.query)}&page=${state.page}`
      : `/api/browse?page=${state.page}&sort=${state.sort}`;
    const data = await api(q);
    const fresh = (data.items || []).map((it) => ({
      ...it,
      installed: state.installedNames.has(String(it.name).toLowerCase().trim()),
    }));
    state.items = reset ? fresh : state.items.concat(fresh);
    state.more = !!data.more;
    showSkeletons(false);
    renderItems();
    setStatus(state.query ? `Found ${state.items.length} results` : `Loaded ${state.items.length} mods`);
    setConn('ok', 'Online');
  } catch (err) {
    showSkeletons(false);
    state.items = reset ? [] : state.items;
    renderItems();
    setConn('err', 'GameBanana unreachable');
    setStatus(`Couldn't reach GameBanana: ${err.message}`);
    if (reset) toast(`Couldn't load mods: ${err.message}`, 'err', 5200);
  } finally {
    state.loading = false;
  }
}

async function loadInstalled() {
  showSkeletons(true);
  $('#grid').innerHTML = '';
  $('#empty').hidden = true;
  try {
    const data = await api('/api/local');
    state.installed = data.mods || [];
    state.installedNames = new Set(state.installed.map((m) => String(m.name).toLowerCase().trim()));
    state.items = state.installed.map((m) => ({ ...m, local: true }));
    showSkeletons(false);
    renderItems();
    setStatus(`${state.installed.length} mod(s) in ${data.folder}`);
    setConn('ok', 'Online');
  } catch (err) {
    showSkeletons(false);
    state.items = [];
    renderItems();
    setStatus(`Couldn't read the mods folder: ${err.message}`);
    setConn('err', 'Backend offline');
  }
}

/* ------------------------------------------------------------------ history
   Grouped by day on a timeline, newest day first. */
const HISTORY_ICONS = {
  install: '📥', uninstall: '🗑', launch: '🎮', settings: '⚙',
};

async function loadHistory() {
  const box = $('#historyList');
  let entries;
  try {
    entries = await api('/api/history');
  } catch (_) {
    box.innerHTML = '<div class="empty"><div class="empty-art">⚠️</div><h3>Couldn’t load history</h3></div>';
    return;
  }
  if (!entries.length) {
    box.innerHTML = `<div class="empty">
      <div class="empty-art">🕘</div>
      <h3>No activity yet</h3>
      <p>Things you install, launch or change show up here.</p></div>`;
    return;
  }

  const days = new Map();
  for (const e of entries) {
    const key = dayLabel(e.ts);
    if (!days.has(key)) days.set(key, []);
    days.get(key).push(e);
  }

  box.innerHTML = Array.from(days.entries()).map(([day, list], di) => `
    <div class="timeline-day" style="animation-delay:${Math.min(di, 6) * 50}ms">
      <div class="timeline-day-label">${esc(day)}</div>
      <div class="timeline-items">
        ${list.map((e) => `
          <div class="history-item">
            <div class="history-icon k-${esc(e.kind || 'other')}">${HISTORY_ICONS[e.kind] || '•'}</div>
            <div class="history-main">
              <strong>${esc(e.name)}</strong>
              ${e.detail ? `<small>${esc(e.detail)}</small>` : ''}
            </div>
            <div class="history-time">${clockTime(e.ts)}</div>
          </div>`).join('')}
      </div>
    </div>`).join('');
}

/* ------------------------------------------------------------------- detail */
async function openDetail(item) {
  state.selected = item;
  state.selectedFile = null;
  state.imgIndex = 0;
  $('#installProgress').textContent = '';

  if (item.local) {
    $('#modalTitle').textContent = item.name;
    $('#modalBadges').innerHTML = [
      '<span class="badge badge-installed">✓ Installed</span>',
      item.engine ? `<span class="badge badge-engine">⚙ ${esc(item.engine)}</span>` : '',
      item.size ? `<span class="badge badge-size">${fmtSize(item.size)}</span>` : '',
    ].join('');
    $('#modalMeta').innerHTML = `<span>📁 ${esc(item.dir)}</span>`;
    $('#modalDesc').textContent = item.exe
      ? 'An executable was found in this mod folder, so you can launch it directly.'
      : 'No executable detected in this folder.';
    $('#modalFiles').hidden = true;
    state.selectedImages = item.preview ? [`/api/local-img?path=${encodeURIComponent(item.preview)}`] : [];
    const btn = $('#installBtn');
    btn.textContent = item.exe ? '🎮 Launch' : '🗑 Uninstall';
    btn.className = item.exe ? 'btn btn-primary' : 'btn btn-danger';
    btn.disabled = false;
    $('#openPageBtn').hidden = true;
    updateGallery();
    openModal();
    return;
  }

  $('#modalTitle').textContent = item.name;
  $('#modalBadges').innerHTML = [
    item.official ? '<span class="badge badge-official">🌟 Official</span>' : '',
    item.installed ? '<span class="badge badge-installed">✓ Installed</span>' : '',
    item.engine ? `<span class="badge badge-engine">⚙ ${esc(item.engine)}</span>` : '',
    item.model && item.model !== 'Mod' ? `<span class="badge badge-type">${esc(item.model)}</span>` : '',
  ].join('');
  $('#modalMeta').innerHTML = `
    <span>👤 ${esc(item.author)}</span>
    <span>⬇ ${fmtNum(item.downloads)}</span>
    <span>❤️ ${fmtNum(item.likes)}</span>
    ${item.added ? `<span>📅 ${fmtDate(item.added)}</span>` : ''}`;
  $('#modalDesc').textContent = 'Loading description…';
  state.selectedImages = (item.images || []).map((u) => `/api/img?url=${encodeURIComponent(u)}`);
  const btn = $('#installBtn');
  btn.textContent = item.installed ? '✓ Installed' : '📥 Install';
  btn.className = 'btn btn-primary';
  btn.disabled = true;
  $('#openPageBtn').hidden = false;
  updateGallery();
  openModal();

  try {
    const data = await api(`/api/details/${encodeURIComponent(item.model || 'Mod')}/${item.id}`);
    $('#modalDesc').textContent = data.description || '(no description)';
    const files = data.files || [];
    if (files.length) {
      state.selectedFile = files[0];
      $('#modalFiles').hidden = false;
      $('#filesList').innerHTML = files.slice(0, 8).map((f) => `
        <div class="file-opt ${f === files[0] ? 'active' : ''}" data-url="${esc(f.url)}">
          <span>📦</span><span class="fname">${esc(f.name)}</span>
          <span class="fsize">${fmtSize(f.size)}</span>
        </div>`).join('');
      $$('#filesList .file-opt').forEach((el) => {
        el.addEventListener('click', () => {
          $$('#filesList .file-opt').forEach((o) => o.classList.remove('active'));
          el.classList.add('active');
          state.selectedFile = { url: el.dataset.url };
        });
      });
    } else {
      $('#modalFiles').hidden = true;
      state.selectedFile = { url: `https://gamebanana.com/dl/${item.id}` };
    }
    btn.disabled = false;
  } catch (err) {
    $('#modalDesc').textContent = `Couldn't load the description (${err.message}).`;
    state.selectedFile = { url: `https://gamebanana.com/dl/${item.id}` };
    btn.disabled = false;
  }
}

function updateGallery() {
  const imgs = state.selectedImages || [];
  const img = $('#modalImage');
  if (!imgs.length) {
    img.style.display = 'none';
    $('#imgCounter').textContent = '0 / 0';
    return;
  }
  img.style.display = '';
  img.classList.remove('loaded');
  img.onload = () => img.classList.add('loaded');
  img.src = imgs[state.imgIndex];
  $('#imgCounter').textContent = `${state.imgIndex + 1} / ${imgs.length}`;
}

/* ------------------------------------------------------------------ install */
async function doInstall() {
  const item = state.selected;
  if (!item) return;
  const btn = $('#installBtn');
  const prog = $('#installProgress');

  if (item.local) {
    if (item.exe) {
      await apiPost('/api/launch', { exe: item.exe, cwd: item.dir }).catch(() => {});
      toast(`Launched ${item.name}`, 'ok');
      return;
    }
    if (!confirm(`Delete “${item.name}” from your mods folder? This can’t be undone.`)) return;
    btn.disabled = true; prog.textContent = 'Removing…';
    try {
      await apiPost('/api/uninstall', { dir: item.dir });
      toast(`Removed ${item.name}`, 'ok');
      closeModal();
      loadInstalled();
      refreshCounts();
    } catch (err) { toast(`Couldn't remove: ${err.message}`, 'err'); }
    btn.disabled = false; prog.textContent = '';
    return;
  }

  if (!state.selectedFile || !state.selectedFile.url) {
    toast('No downloadable file found for this mod.', 'err');
    return;
  }
  btn.disabled = true;
  prog.textContent = 'Downloading…';
  try {
    const out = await apiPost('/api/install', {
      name: item.name,
      url: state.selectedFile.url,
      sourceId: item.id,
      sourceName: item.name,
    });
    prog.textContent = 'Done';
    toast(`Installed ${out.name}`, 'ok', 5000);
    item.installed = true;
    state.installedNames.add(String(item.name).toLowerCase().trim());
    btn.textContent = '✓ Installed';
    renderItems();
    if (DESKTOP) window.ff.notify({ title: 'FunkForge', body: `Installed ${out.name}` });
    refreshCounts();
    if (state.view === 'installed') loadInstalled();
  } catch (err) {
    prog.textContent = '';
    toast(`Install failed: ${err.message}`, 'err', 6000);
  }
  btn.disabled = false;
}

/* -------------------------------------------------------------- mods folder */
async function changeFolder() {
  let picked = null;
  if (DESKTOP) {
    picked = await window.ff.pickFolder({
      title: 'Choose your mods folder',
      defaultPath: state.config?.modsFolder,
    });
  } else {
    const typed = prompt('Mods folder path:', state.config?.modsFolder || '');
    picked = typed && typed.trim() ? typed.trim() : null;
  }
  if (!picked) return;
  await saveConfig({ modsFolder: picked });
  toast(`Mods folder set to ${picked}`, 'ok');
  refreshFolderCard();
  if (state.view === 'installed') loadInstalled();
}

async function openFolder() {
  const dir = state.config?.modsFolder;
  if (!dir) return;
  if (!DESKTOP) { toast('Opening folders is only available in the desktop app.', 'info'); return; }
  const res = await window.ff.openPath(dir);
  if (!res.ok) toast(`Couldn't open the folder${res.error ? `: ${res.error}` : ''}`, 'err');
}

async function refreshFolderCard() {
  const p = state.config?.modsFolder || '—';
  $('#folderPath').textContent = p;
  $('#folderPath').title = p;
  $('#setModsFolder').value = state.config?.modsFolder || '';
  $('#folderHint').textContent = DESKTOP ? '' : 'Browser preview: native picking is disabled here.';
}

/* -------------------------------------------------------------------- config */
async function saveConfig(patch) {
  state.config = { ...(state.config || {}), ...patch };
  await apiPost('/api/config', patch);
  refreshFolderCard();
  if (patch.theme) applyTheme(patch.theme);
}

/* --------------------------------------------------------------- navigation */
/**
 * Switch panes without touching the search box.
 *
 * This is separate from setView() on purpose: the search handler calls this
 * after setting state.query. Routing it through setView() used to wipe the
 * query it had just set, so every search silently reset to "browse all".
 */
function switchPane(view) {
  $$('.nav-item').forEach((b) => b.classList.toggle('is-active', b.dataset.view === view));
  moveNavIndicator();
  $('#resultsView').hidden = !['discover', 'installed'].includes(view);
  $('#historyView').hidden = view !== 'history';
  $('#settingsView').hidden = view !== 'settings';
  $('#toolbar').hidden = !['discover', 'installed'].includes(view);
  $('#loadMore').hidden = true;
}

/** User-driven navigation (nav click): resets search and reloads. */
function setView(view) {
  state.view = view;
  if (view === 'discover') {
    state.query = '';
    $('#search').value = '';
    $('#clearSearch').hidden = true;
  }
  switchPane(view);

  if (view === 'discover') loadDiscover();
  else if (view === 'installed') loadInstalled();
  else if (view === 'history') loadHistory();
}

/** Search: keeps the typed query intact (this is the bug fix). */
function runSearch(q) {
  state.query = q;
  if (state.view !== 'discover') {
    state.view = 'discover';
    switchPane('discover');
  }
  loadDiscover();
}

/* ------------------------------------------------------------------ settings */
function fillSettings() {
  const c = state.config || {};
  $('#setModsFolder').value = c.modsFolder || '';
  $('#setGameExe').value = c.gameExe || '';
  $('#setTheme').value = c.theme || 'midnight';
  $('#setMinDownloads').value = c.minDownloads ?? 0;
  applyTheme(c.theme || 'midnight');
  applyLayout(c.view || 'grid');
}

async function pickExe() {
  let picked = null;
  if (DESKTOP) {
    picked = await window.ff.pickFile({
      title: 'Select the game executable',
      filters: [{ name: 'Executables', extensions: ['exe', 'app', 'bin', 'sh'] }],
    });
  } else {
    const typed = prompt('Game executable path:', state.config?.gameExe || '');
    picked = typed && typed.trim() ? typed.trim() : null;
  }
  if (!picked) return;
  $('#setGameExe').value = picked;
}

async function refreshCounts() {
  try {
    const d = await api('/api/local');
    state.installed = d.mods || [];
    state.installedNames = new Set(state.installed.map((m) => String(m.name).toLowerCase().trim()));
    const el = $('#installedCount');
    el.textContent = String(state.installed.length);
    // Little bump so a change is noticeable.
    el.animate(
      [{ transform: 'scale(1)' }, { transform: 'scale(1.28)' }, { transform: 'scale(1)' }],
      { duration: 340, easing: 'cubic-bezier(.22,1,.36,1)' },
    );
  } catch (_) { /* ignore */ }
}

/* --------------------------------------------------------------------- wiring */
function wire() {
  if (DESKTOP) {
    $('#windowControls').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-act]');
      if (!btn) return;
      const act = btn.dataset.act;
      if (act === 'minimize') window.ff.minimize();
      else if (act === 'maximize') window.ff.maximize();
      else if (act === 'close') window.ff.close();
    });
  } else {
    $('#windowControls').hidden = true;
  }

  $('#nav').addEventListener('click', (e) => {
    const btn = e.target.closest('.nav-item');
    if (btn) setView(btn.dataset.view);
  });

  /* ---------------- search (fixed) ---------------- */
  let debounce;
  $('#search').addEventListener('input', (e) => {
    const v = e.target.value;
    $('#clearSearch').hidden = !v;
    clearTimeout(debounce);
    debounce = setTimeout(() => runSearch(v.trim()), 360);
  });
  $('#search').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      clearTimeout(debounce);
      runSearch(e.target.value.trim());
    }
    if (e.key === 'Escape' && e.target.value) {
      e.target.value = '';
      $('#clearSearch').hidden = true;
      runSearch('');
    }
  });
  $('#clearSearch').addEventListener('click', () => {
    $('#search').value = '';
    $('#clearSearch').hidden = true;
    runSearch('');
    $('#search').focus();
  });

  $('#sort').addEventListener('change', (e) => {
    state.sort = e.target.value;
    if (state.view === 'discover') loadDiscover();
  });

  const layoutHandler = (e) => {
    const btn = e.target.closest('[data-view]');
    if (!btn) return;
    applyLayout(btn.dataset.view);
    saveConfig({ view: btn.dataset.view });
  };
  $('#viewToggle').addEventListener('click', layoutHandler);
  $('#setViewToggle').addEventListener('click', layoutHandler);

  $('#loadMore').addEventListener('click', () => {
    state.page += 1;
    loadDiscover(false);
  });

  $('#grid').addEventListener('click', (e) => {
    const card = e.target.closest('.card');
    if (!card) return;
    const id = card.dataset.id;
    const local = card.dataset.local === '1';
    const item = state.items.find((it) => String(local ? it.dir : it.id) === id);
    if (item) openDetail(item);
  });

  $('#modalClose').addEventListener('click', closeModal);
  $('#modal').addEventListener('click', (e) => { if (e.target === $('#modal')) closeModal(); });
  $('#prevImg').addEventListener('click', () => {
    if (!state.selectedImages.length) return;
    state.imgIndex = (state.imgIndex - 1 + state.selectedImages.length) % state.selectedImages.length;
    updateGallery();
  });
  $('#nextImg').addEventListener('click', () => {
    if (!state.selectedImages.length) return;
    state.imgIndex = (state.imgIndex + 1) % state.selectedImages.length;
    updateGallery();
  });
  $('#installBtn').addEventListener('click', doInstall);
  $('#openPageBtn').addEventListener('click', () => {
    const item = state.selected;
    if (!item || !item.url) return;
    if (DESKTOP) window.ff.openExternal(item.url);
    else window.open(item.url, '_blank', 'noopener');
  });

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    if (btn.dataset.act === 'change-folder') changeFolder();
    else if (btn.dataset.act === 'open-folder') openFolder();
    else if (btn.dataset.act === 'pick-exe') pickExe();
  });

  $('#saveSettings').addEventListener('click', async () => {
    await saveConfig({
      modsFolder: $('#setModsFolder').value.trim(),
      gameExe: $('#setGameExe').value.trim(),
      theme: $('#setTheme').value,
      view: state.layout,
      minDownloads: Number($('#setMinDownloads').value) || 0,
    });
    fillSettings();
    const note = $('#saveNote');
    note.textContent = 'Saved ✓';
    note.animate([{ opacity: 0, transform: 'translateY(4px)' }, { opacity: 1, transform: 'none' }],
      { duration: 260, easing: 'cubic-bezier(.22,1,.36,1)' });
    setTimeout(() => { note.textContent = ''; }, 2200);
  });
  // Live preview the theme, persist only on Save.
  $('#setTheme').addEventListener('change', (e) => applyTheme(e.target.value));

  $('#clearHistory').addEventListener('click', async () => {
    if (!confirm('Clear all activity history?')) return;
    try {
      await apiPost('/api/history/clear');
      toast('History cleared', 'ok');
      loadHistory();
    } catch (err) {
      toast(`Couldn't clear history: ${err.message}`, 'err');
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
    if (e.key === '/' && document.activeElement !== $('#search')) {
      e.preventDefault();
      $('#search').focus();
    }
    if (!$('#modal').hidden) {
      if (e.key === 'ArrowLeft') $('#prevImg').click();
      if (e.key === 'ArrowRight') $('#nextImg').click();
    }
  });

  $('#content').addEventListener('scroll', () => {
    const el = $('#content');
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 420) {
      if (state.view === 'discover' && state.more && !state.loading) {
        state.page += 1;
        loadDiscover(false);
      }
    }
  });

  window.addEventListener('resize', moveNavIndicator);
}

/* ---------------------------------------------------------------------- init */
async function init() {
  wire();
  try {
    state.meta = await api('/api/meta');
    state.config = state.meta.config;
    fillSettings();
    refreshFolderCard();
    $('#platformNote').textContent = state.meta.electron
      ? `Electron · ${state.meta.platform}`
      : `Browser preview · ${state.meta.platform}`;
    if (DESKTOP) {
      const info = await window.ff.info().catch(() => null);
      if (info) {
        $('#verLabel').textContent = `v${info.version}`;
        $('#dataDirLabel').textContent = info.dataDir || '~/.funkforge';
      }
    } else {
      $('#dataDirLabel').textContent = '~/.funkforge';
    }
  } catch (err) {
    setConn('err', 'Backend offline');
    setStatus(`Backend unreachable: ${err.message}`);
    return;
  }

  moveNavIndicator();
  await checkHealth();
  loadDiscover();
  refreshCounts();
}

init();
