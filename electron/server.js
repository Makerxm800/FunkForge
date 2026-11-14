'use strict';
/**
 * FunkForge (Beta) — local backend.
 *
 * Runs inside the Electron main process, and also standalone (`--serve-only`)
 * for development and browser previews. Because the renderer talks to it over
 * plain HTTP, the exact same UI works in the packaged app and in a browser.
 *
 * Owns everything the renderer can't do for itself:
 *   • proxying + caching the GameBanana API and its images
 *   • reading/writing the local mods folder
 *   • downloading and extracting mod archives
 *   • launching the game, and OS-level folder/notifications
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');
const os = require('os');
const zlib = require('zlib');
const crypto = require('crypto');
const { spawn } = require('child_process');

// Guard the require with `process.versions.electron` rather than a bare
// try/catch: electron's npm shim *synchronously* spawns its installer when
// path.txt is missing (spawnSync), which would block startup -- potentially
// for a long time on a slow network -- just because we peeked at the module.
// `process.versions.electron` is only set when we're really inside Electron.
const inElectron = !!process.versions.electron;
let electron = null;
if (inElectron) {
  try { electron = require('electron'); } catch (_) { /* not usable */ }
}

const GB_API = 'https://gamebanana.com/apiv11';
const FNF_GAME_ID = 8694;
const UA = 'FunkForge/2.0.0';
const DEFAULT_MODS_FOLDER = path.join(os.homedir(), 'FunkForgeMods');
// Shared images (the logo) live outside renderer/ and are served under /assets/
const ASSETS_DIR = path.join(__dirname, '..', 'assets');
const META_FILE = '.funkforge_meta.json';

const DEFAULT_CONFIG = {
  modsFolder: DEFAULT_MODS_FOLDER,
  gameExe: '',
  theme: 'midnight',
  view: 'grid',
  perPage: 48,
  minDownloads: 0,
  useProxyImages: true,
  osNotifications: true,
};

// ---------------------------------------------------------------- data dirs

function dataDir() {
  if (inElectron) {
    try { return electron.app.getPath('userData'); } catch (_) { /* fall through */ }
  }
  return path.join(os.homedir(), '.funkforge');
}

const DIRS = {
  root: dataDir(),
  cache: path.join(dataDir(), 'cache'),
  images: path.join(dataDir(), 'cache', 'images'),
  mods: null, // set from config
};

function configPath() { return path.join(DIRS.root, 'config.json'); }
function historyPath() { return path.join(DIRS.root, 'history.json'); }

function ensureDirs() {
  for (const d of [DIRS.root, DIRS.cache, DIRS.images]) {
    try { fs.mkdirSync(d, { recursive: true }); } catch (_) { /* ignore */ }
  }
}

function loadConfig() {
  try {
    const raw = fs.readFileSync(configPath(), 'utf8');
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch (_) {
    return { ...DEFAULT_CONFIG };
  }
}

function saveConfig(cfg) {
  ensureDirs();
  fs.writeFileSync(configPath(), JSON.stringify(cfg, null, 2));
  DIRS.mods = cfg.modsFolder;
  return cfg;
}

function readHistory() {
  try { return JSON.parse(fs.readFileSync(historyPath(), 'utf8')); } catch (_) { return []; }
}

function writeHistory(entries) {
  ensureDirs();
  try { fs.writeFileSync(historyPath(), JSON.stringify(entries.slice(0, 500), null, 2)); } catch (_) { /* ignore */ }
}

function logHistory(kind, name, detail = '') {
  const entries = readHistory();
  entries.unshift({ kind, name, detail, ts: Date.now() });
  writeHistory(entries);
  return entries;
}

// ------------------------------------------------------------------- http up

function httpsGet(url, { timeout = 20000, headers = {} } = {}) {
  return new Promise((resolve, reject) => {
    let req;
    try {
      req = https.get(url, { headers: { 'User-Agent': UA, Accept: '*/*', ...headers } }, (res) => {
        // Follow redirects (GameBanana CDN uses them for downloads).
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume();
          const next = new URL(res.headers.location, url).toString();
          httpsGet(next, { timeout, headers }).then(resolve, reject);
          return;
        }
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          let buf = Buffer.concat(chunks);
          const enc = (res.headers['content-encoding'] || '').toLowerCase();
          try {
            if (enc === 'gzip') buf = zlib.gunzipSync(buf);
            else if (enc === 'deflate') buf = zlib.inflateSync(buf);
            else if (enc === 'br') buf = zlib.brotliDecompressSync(buf);
          } catch (_) { /* leave as-is */ }
          resolve({ status: res.statusCode, headers: res.headers, body: buf });
        });
      });
    } catch (err) { reject(err); return; }
    req.setTimeout(timeout, () => req.destroy(new Error('timeout')));
    req.on('error', reject);
  });
}

async function gbGet(pathname, params = {}, tries = 2) {
  const url = new URL(`${GB_API}/${String(pathname).replace(/^\//, '')}`);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  }
  let lastErr;
  for (let attempt = 0; attempt < tries; attempt += 1) {
    try {
      const res = await httpsGet(url.toString(), { headers: { Accept: 'application/json' } });
      if (res.status === 200) return JSON.parse(res.body.toString('utf8'));
      if (res.status < 500 && res.status !== 429) {
        throw new Error(`GameBanana returned HTTP ${res.status}`);
      }
      lastErr = new Error(`HTTP ${res.status}`);
    } catch (err) {
      lastErr = err;
    }
    await new Promise((r) => setTimeout(r, 350 * (attempt + 1)));
  }
  throw lastErr || new Error('request failed');
}

// ------------------------------------------------------------- normalization

const ENGINES = [
  ['Psych Engine', ['psych']],
  ['Kade Engine', ['kade']],
  ['Codename Engine', ['codename']],
  ['Forever Engine', ['forever']],
  ['Andromeda Engine', ['andromeda']],
  ['V-Slice', ['v-slice', 'vslice', 'vanilla']],
  ['FPS Plus', ['fps plus']],
  ["Mic'd Up", ["mic'd up", 'micdup']],
];

function detectEngine(text = '') {
  const t = String(text).toLowerCase();
  for (const [name, keys] of ENGINES) {
    if (keys.some((k) => t.includes(k))) return name;
  }
  return 'Other';
}

const OFFICIAL_SUBMITTERS = new Set([
  'ninjamuffin99', 'phantomarcade', 'phantomarcade3k', 'evilsk8r',
  'kawaisprite', "funkin' crew", 'funkin crew', 'the funkin crew',
]);

function isOfficial(rec) {
  const sub = String(rec?._aSubmitter?._sName || '').toLowerCase().trim();
  return OFFICIAL_SUBMITTERS.has(sub);
}

function previewImages(rec) {
  const imgs = rec?._aPreviewMedia?._aImages || [];
  return imgs.map((i) => `${i._sBaseUrl || ''}/${i._sFile || ''}`.replace(/([^:])\/{2,}/g, '$1/'))
    .filter((u) => u && u !== '/');
}

function normalize(rec, model = 'Mod') {
  const imgs = previewImages(rec);
  return {
    id: rec._idRow,
    model: rec._sModelName || model,
    name: rec._sName || 'Untitled',
    author: rec._aSubmitter?._sName || 'Unknown',
    downloads: rec._nDownloadCount || 0,
    likes: rec._nLikeCount || 0,
    views: rec._nViewCount || 0,
    added: rec._tsDateAdded || 0,
    modified: rec._tsDateModified || rec._tsDateAdded || 0,
    images: imgs,
    engine: detectEngine(rec._sName || ''),
    official: isOfficial(rec),
    url: rec._sProfileUrl || `https://gamebanana.com/mods/${rec._idRow}`,
  };
}

function parseList(data, perPage) {
  if (!data) return { records: [], more: false };
  if (Array.isArray(data)) return { records: data, more: data.length >= perPage };
  const records = data._aRecords || [];
  const meta = data._aMetadata || {};
  const more = '_bIsComplete' in meta ? !meta._bIsComplete : records.length >= perPage;
  return { records, more };
}

const SORT_MAP = {
  best_match: 'Generic_MostDownloaded',
  downloads: 'Generic_MostDownloaded',
  likes: 'Generic_MostLiked',
  new: 'Generic_Newest',
  updated: 'Generic_LastUpdated',
  name: 'Generic_Alphabetical',
};

async function browse({ page = 1, perPage = 48, sort = 'downloads' }) {
  const apiSort = SORT_MAP[sort] || SORT_MAP.downloads;
  try {
    const data = await gbGet('Mod/Index', {
      _nPerpage: perPage,
      _nPage: page,
      '_aFilters[Generic_Game]': FNF_GAME_ID,
      _sSort: apiSort,
    });
    const { records, more } = parseList(data, perPage);
    const mods = records.filter((r) => (r._sModelName || 'Mod') === 'Mod');
    if (mods.length || page === 1) return { items: mods.map((r) => normalize(r)), more };
  } catch (err) {
    console.warn('[gb] Mod/Index failed:', err.message);
  }
  const data = await gbGet(`Game/${FNF_GAME_ID}/Subfeed`, {
    _nPage: page, _nPerpage: perPage, _sSort: 'default',
  });
  const { records, more } = parseList(data, perPage);
  return {
    items: records.filter((r) => (r._sModelName || 'Mod') === 'Mod').map((r) => normalize(r)),
    more,
  };
}

async function search({ query, page = 1, perPage = 48 }) {
  const models = ['Mod', 'Tool', 'Sound'];
  const results = await Promise.all(models.map(async (m) => {
    try {
      const data = await gbGet('Util/Search/Results', {
        _sModelName: m,
        _sSearchString: query,
        _idGameRow: FNF_GAME_ID,
        _nPerpage: perPage,
        _nPage: page,
      });
      return parseList(data, perPage).records.map((r) => normalize(r, m));
    } catch (_) { return []; }
  }));
  const seen = new Set();
  const items = [];
  for (const list of results) {
    for (const it of list) {
      const key = `${it.model}:${it.id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      items.push(it);
    }
  }
  return { items, more: items.length >= perPage };
}

// ------------------------------------------------------------------ zip tool

/** Minimal, dependency-free zip extractor (stored + deflate, no zip64). */
async function extractZip(zipPath, dest) {
  const buf = await fsp.readFile(zipPath);

  // Locate the End Of Central Directory record.
  let eocd = -1;
  for (let i = buf.length - 22; i >= 0 && i > buf.length - 66000; i -= 1) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error('not a valid zip (no EOCD)');

  const count = buf.readUInt16LE(eocd + 10);
  let ptr = buf.readUInt32LE(eocd + 16);

  await fsp.mkdir(dest, { recursive: true });

  for (let n = 0; n < count; n += 1) {
    if (buf.readUInt32LE(ptr) !== 0x02014b50) break;
    const method = buf.readUInt16LE(ptr + 10);
    const compSize = buf.readUInt32LE(ptr + 20);
    const nameLen = buf.readUInt16LE(ptr + 28);
    const extraLen = buf.readUInt16LE(ptr + 30);
    const commentLen = buf.readUInt16LE(ptr + 32);
    const localOff = buf.readUInt32LE(ptr + 42);
    const name = buf.toString('utf8', ptr + 46, ptr + 46 + nameLen);

    // The local header can carry a different extra-field length.
    const lNameLen = buf.readUInt16LE(localOff + 26);
    const lExtraLen = buf.readUInt16LE(localOff + 28);
    const dataStart = localOff + 30 + lNameLen + lExtraLen;
    const data = buf.subarray(dataStart, dataStart + compSize);

    const safe = path.normalize(name).replace(/^(\.\.[/\\])+/, '').replace(/\\/g, '/');
    const outPath = path.join(dest, safe);
    if (!outPath.startsWith(path.resolve(dest))) {
      ptr += 46 + nameLen + extraLen + commentLen;
      continue; // path traversal guard
    }

    if (name.endsWith('/')) {
      await fsp.mkdir(outPath, { recursive: true });
    } else {
      await fsp.mkdir(path.dirname(outPath), { recursive: true });
      let content = data;
      if (method === 8) content = zlib.inflateRawSync(data);
      else if (method !== 0) { ptr += 46 + nameLen + extraLen + commentLen; continue; }
      await fsp.writeFile(outPath, content);
    }
    ptr += 46 + nameLen + extraLen + commentLen;
  }
  return dest;
}

/**
 * Strip a redundant wrapper folder.
 *
 * Most mod archives ship as `MyMod/...` inside the zip, so extracting straight
 * into `mods/MyMod/` would leave an annoying extra nesting level. If the
 * archive's entire content is a single top-level folder, lift it out — the same
 * thing GitHub's ZIPs and Extract-Here do.
 *
 * We deliberately stop after one level: a mod whose only top-level entry is a
 * real content folder (e.g. `assets/`) should keep its structure.
 */
async function unwrapIfNeeded(dir) {
  let entries = await fsp.readdir(dir, { withFileTypes: true });
  entries = entries.filter((e) => !e.name.startsWith('.'));
  if (entries.length !== 1 || !entries[0].isDirectory()) return dir;

  const inner = path.join(dir, entries[0].name);
  const tmp = `${dir}.unwrap-${Date.now()}`;
  await fsp.rename(inner, tmp);
  for (const e of await fsp.readdir(tmp)) {
    await fsp.rename(path.join(tmp, e), path.join(dir, e));
  }
  await fsp.rm(tmp, { recursive: true, force: true });
  return dir;
}

// ------------------------------------------------------------- local library

const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']);

async function dirSize(dir) {
  let total = 0;
  const walk = async (d, depth = 0) => {
    if (depth > 6) return;
    let entries;
    try { entries = await fsp.readdir(d, { withFileTypes: true }); } catch (_) { return; }
    for (const e of entries) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) await walk(p, depth + 1);
      else {
        try { total += (await fsp.stat(p)).size; } catch (_) { /* ignore */ }
      }
    }
  };
  await walk(dir);
  return total;
}

async function findFiles(dir, predicate, maxDepth = 3, depth = 0) {
  const out = [];
  if (depth > maxDepth) return out;
  let entries;
  try { entries = await fsp.readdir(dir, { withFileTypes: true }); } catch (_) { return out; }
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...await findFiles(p, predicate, maxDepth, depth + 1));
    else if (predicate(p, e.name)) out.push(p);
  }
  return out;
}

async function scanLocalMods() {
  const root = DIRS.mods || loadConfig().modsFolder;
  if (!root) return { folder: '', mods: [] };
  let entries;
  try { entries = await fsp.readdir(root, { withFileTypes: true }); } catch (_) {
    return { folder: root, mods: [], missing: true };
  }
  const mods = [];
  for (const e of entries) {
    if (!e.isDirectory() || e.name.startsWith('.')) continue;
    const dir = path.join(root, e.name);
    const [size, exes, imgs] = await Promise.all([
      dirSize(dir),
      findFiles(dir, (p, n) => /\.exe$/i.test(n) && !/unins|crashpad|vcredist/i.test(n), 3),
      findFiles(dir, (p, n) => IMAGE_EXT.has(path.extname(n).toLowerCase()), 2),
    ]);
    let meta = {};
    try { meta = JSON.parse(await fsp.readFile(path.join(dir, META_FILE), 'utf8')); } catch (_) { /* none */ }
    imgs.sort();
    mods.push({
      name: e.name,
      dir,
      size,
      engine: detectEngine(e.name),
      exe: exes[0] || null,
      preview: imgs[0] || null,
      installedAt: meta.installedAt || null,
      sourceId: meta.sourceId || null,
      sourceName: meta.sourceName || null,
    });
  }
  mods.sort((a, b) => a.name.localeCompare(b.name));
  return { folder: root, mods };
}

// ----------------------------------------------------------------- downloads

async function downloadInstall({ name, url, sourceId, sourceName }) {
  const cfg = loadConfig();
  const root = cfg.modsFolder;
  await fsp.mkdir(root, { recursive: true });

  const safeName = String(name).replace(/[<>:"'/\\|?*\u0000-\u001f]/g, '_').trim().slice(0, 120) || 'mod';
  let target = path.join(root, safeName);
  let n = 1;
  while (fs.existsSync(target)) { n += 1; target = path.join(root, `${safeName} (${n})`); }

  const res = await httpsGet(url, { timeout: 180000 });
  if (res.status !== 200 || !res.body.length) throw new Error(`download failed (HTTP ${res.status})`);

  const isZip = url.toLowerCase().includes('.zip') || res.body.slice(0, 2).toString() === 'PK';
  if (isZip) {
    const tmpZip = path.join(DIRS.cache, `dl-${crypto.randomBytes(6).toString('hex')}.zip`);
    await fsp.writeFile(tmpZip, res.body);
    await extractZip(tmpZip, target);
    await unwrapIfNeeded(target);
    await fsp.rm(tmpZip, { force: true });
  } else {
    // A bare file (e.g. an .exe or .json tool): drop it in its own folder.
    await fsp.mkdir(target, { recursive: true });
    const fname = path.basename(new URL(url).pathname) || `${safeName}.bin`;
    await fsp.writeFile(path.join(target, fname), res.body);
  }

  await fsp.writeFile(path.join(target, META_FILE), JSON.stringify({
    installedAt: Date.now(), sourceId, sourceName,
  }, null, 2));

  logHistory('install', safeName, `installed to ${target}`);
  return { ok: true, dir: target, name: safeName };
}

// ------------------------------------------------------------ image caching

const inflight = new Map();

function imageCacheFile(url) {
  const key = crypto.createHash('sha1').update(url).digest('hex');
  const ext = (path.extname(new URL(url).pathname) || '.img').slice(0, 8);
  return path.join(DIRS.images, `${key}${ext}`);
}

async function fetchImage(url) {
  ensureDirs();
  const file = imageCacheFile(url);
  try {
    const st = await fsp.stat(file);
    if (st.size > 0) return { body: await fsp.readFile(file), cached: true };
  } catch (_) { /* not cached */ }

  if (inflight.has(url)) return inflight.get(url);
  const p = (async () => {
    const res = await httpsGet(url, { timeout: 20000 });
    if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
    try { await fsp.writeFile(file, res.body); } catch (_) { /* ignore */ }
    return { body: res.body, cached: false };
  })();
  inflight.set(url, p);
  try { return await p; } finally { inflight.delete(url); }
}

// ------------------------------------------------------------------- routing

function sendJson(res, code, obj) {
  const body = Buffer.from(JSON.stringify(obj));
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': body.length,
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
};

function serveStatic(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not found');
      return;
    }
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream',
      'Content-Length': data.length,
      'Cache-Control': 'no-cache',
    });
    res.end(data);
  });
}

function readBody(req) {
  return new Promise((resolve) => {
    let raw = '';
    req.on('data', (c) => { raw += c; if (raw.length > 2e6) req.destroy(); });
    req.on('end', () => { try { resolve(raw ? JSON.parse(raw) : {}); } catch (_) { resolve({}); } });
  });
}

async function handleApi(req, res, url) {
  const pathname = url.pathname;
  const q = url.searchParams;

  try {
    if (pathname === '/api/health') {
      return sendJson(res, 200, { ok: true, electron: inElectron, version: '2.0.0' });
    }

    if (pathname === '/api/meta') {
      const cfg = loadConfig();
      DIRS.mods = cfg.modsFolder;
      return sendJson(res, 200, {
        version: '2.0.0',
        name: 'FunkForge (Beta)',
        platform: process.platform,
        electron: inElectron,
        config: cfg,
        canOpenFolder: inElectron,
      });
    }

    if (pathname === '/api/config' && req.method === 'GET') {
      return sendJson(res, 200, loadConfig());
    }

    if (pathname === '/api/config' && req.method === 'POST') {
      const patch = await readBody(req);
      const next = { ...loadConfig(), ...patch };
      if (patch.modsFolder) {
        try { await fsp.mkdir(patch.modsFolder, { recursive: true }); } catch (_) { /* ignore */ }
      }
      saveConfig(next);
      logHistory('settings', 'Configuration', 'settings updated');
      return sendJson(res, 200, next);
    }

    if (pathname === '/api/history') {
      return sendJson(res, 200, readHistory());
    }

    if (pathname === '/api/browse') {
      const data = await browse({
        page: Number(q.get('page') || 1),
        perPage: Number(q.get('perPage') || 48),
        sort: q.get('sort') || 'downloads',
      });
      return sendJson(res, 200, data);
    }

    if (pathname === '/api/search') {
      const data = await search({
        query: q.get('q') || '',
        page: Number(q.get('page') || 1),
        perPage: Number(q.get('perPage') || 48),
      });
      return sendJson(res, 200, data);
    }

    if (pathname.startsWith('/api/details/')) {
      const [, , , model, id] = pathname.split('/');
      const data = await gbGet(`${model || 'Mod'}/${id}/ProfilePage`);
      const files = (data._aFiles || []).map((f) => ({
        id: f._idRow,
        name: f._sFile || `${model}-${id}.zip`,
        size: f._nFilesize || 0,
        url: f._sDownloadUrl || `https://gamebanana.com/dl/${f._idRow}`,
        added: f._tsDateAdded || 0,
      })).sort((a, b) => b.size - a.size);
      const text = String(data._sText || '').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '');
      return sendJson(res, 200, { description: text.trim() || '(no description)', files });
    }

    if (pathname === '/api/local') {
      const data = await scanLocalMods();
      return sendJson(res, 200, data);
    }

    if (pathname === '/api/install' && req.method === 'POST') {
      const body = await readBody(req);
      if (!body.url) return sendJson(res, 400, { error: 'missing download url' });
      const out = await downloadInstall(body);
      return sendJson(res, 200, out);
    }

    if (pathname === '/api/uninstall' && req.method === 'POST') {
      const { dir } = await readBody(req);
      const cfg = loadConfig();
      const root = path.resolve(cfg.modsFolder);
      const target = path.resolve(dir || '');
      if (!target || !target.startsWith(root)) {
        return sendJson(res, 400, { error: 'refusing to delete outside the mods folder' });
      }
      await fsp.rm(target, { recursive: true, force: true });
      logHistory('uninstall', path.basename(target), target);
      return sendJson(res, 200, { ok: true });
    }

    if (pathname === '/api/launch' && req.method === 'POST') {
      const { exe, cwd } = await readBody(req);
      if (!exe || !fs.existsSync(exe)) return sendJson(res, 400, { error: 'executable not found' });
      spawn(exe, [], { cwd: cwd || path.dirname(exe), detached: true, stdio: 'ignore' }).unref();
      logHistory('launch', path.basename(exe), exe);
      return sendJson(res, 200, { ok: true });
    }

    if (pathname === '/api/open-folder' && req.method === 'POST') {
      const { dir } = await readBody(req);
      if (!inElectron) return sendJson(res, 200, { ok: false, reason: 'not available in browser mode' });
      electron.shell.openPath(dir);
      return sendJson(res, 200, { ok: true });
    }

    if (pathname === '/api/img') {
      const target = q.get('url');
      if (!target || !/^https?:\/\//i.test(target)) {
        return sendJson(res, 400, { error: 'bad url' });
      }
      const { body, cached } = await fetchImage(target);
      res.writeHead(200, {
        'Content-Type': 'image/*',
        'Content-Length': body.length,
        'Cache-Control': 'public, max-age=86400',
        'X-FF-Cache': cached ? 'hit' : 'miss',
      });
      return res.end(body);
    }

    // Local file served from disk (previews inside installed mods).
    if (pathname === '/api/local-img') {
      const file = q.get('path');
      const cfg = loadConfig();
      const root = path.resolve(cfg.modsFolder);
      const target = path.resolve(file || '');
      if (!target.startsWith(root)) return sendJson(res, 400, { error: 'outside mods folder' });
      const data = await fsp.readFile(target);
      res.writeHead(200, { 'Content-Type': 'image/*', 'Content-Length': data.length });
      return res.end(data);
    }

    return sendJson(res, 404, { error: `no route for ${pathname}` });
  } catch (err) {
    console.error('[api]', pathname, err.message);
    return sendJson(res, 502, { error: err.message, offline: true });
  }
}

// ------------------------------------------------------------------- startup

function startServer({ rendererDir, port = 0, host = '127.0.0.1' } = {}) {
  ensureDirs();
  DIRS.mods = loadConfig().modsFolder;

  const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    if (req.method === 'OPTIONS') {
      res.writeHead(204, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
      });
      return res.end();
    }
    if (url.pathname.startsWith('/api/')) return handleApi(req, res, url);

    // /assets/* -> the shared assets folder, so the renderer can use the logo
    // without us keeping a second copy inside renderer/.
    if (url.pathname.startsWith('/assets/')) {
      const rel = path.normalize(decodeURIComponent(url.pathname.slice(8)))
        .replace(/^(\.\.[/\\])+/, '');
      return serveStatic(res, path.join(ASSETS_DIR, rel));
    }

    let rel = decodeURIComponent(url.pathname);
    if (rel === '/' || rel === '') rel = '/index.html';
    const filePath = path.join(rendererDir, path.normalize(rel).replace(/^(\.\.[/\\])+/, ''));
    if (!filePath.startsWith(path.resolve(rendererDir))) {
      res.writeHead(403); return res.end('forbidden');
    }
    return serveStatic(res, filePath);
  });

  return new Promise((resolve, reject) => {
    server.on('error', reject);
    server.listen(port, host, () => {
      const actual = server.address().port;
      resolve({ server, port: actual, url: `http://127.0.0.1:${actual}/` });
    });
  });
}

// Allow `node electron/server.js --serve-only --host 0.0.0.0 --port 8756`
if (require.main === module) {
  const argv = process.argv.slice(2);
  const get = (flag, dflt) => {
    const i = argv.indexOf(flag);
    return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
  };
  const host = get('--host', '127.0.0.1');
  const port = Number(get('--port', 8756));
  startServer({
    rendererDir: path.join(__dirname, '..', 'renderer'),
    host,
    port,
  }).then(({ url, port: p }) => {
    console.log(`[FunkForge] server ready at http://${host}:${p}/  (${url})`);
  }).catch((err) => {
    console.error('[FunkForge] failed to start:', err);
    process.exit(1);
  });
}

module.exports = { startServer, loadConfig, saveConfig, DIRS, dataDir, logHistory, scanLocalMods };
