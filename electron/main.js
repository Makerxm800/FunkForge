'use strict';
/**
 * Electron main process.
 *
 * Starts the local backend (electron/server.js), then points a BrowserWindow
 * at it. Because the renderer is loaded over HTTP from our own server, the UI
 * is byte-for-byte the same in the packaged app and in a plain browser —
 * which is what makes the browser preview a faithful one.
 */

const path = require('path');
const {
  app, BrowserWindow, ipcMain, dialog, shell, Notification, nativeImage,
} = require('electron');

const { startServer, dataDir } = require('./server');

const isMac = process.platform === 'darwin';
const APP_NAME = 'FunkForge (Beta)';

let mainWindow = null;
let serverInfo = null;

function iconFile() {
  // electron-builder picks build/icon.* per platform; at runtime we just need
  // one embeddable image for the window/dock.
  const candidates = ['icon.png', path.join('..', 'assets', 'logo_1024.png')];
  for (const c of candidates) {
    try {
      const p = path.isAbsolute(c) ? c : path.join(__dirname, c);
      const img = nativeImage.createFromPath(p);
      if (!img.isEmpty()) return img;
    } catch (_) { /* try next */ }
  }
  return undefined;
}

async function createWindow() {
  const { url } = serverInfo;

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 940,
    minHeight: 620,
    show: false,
    backgroundColor: '#0b0c12',
    icon: iconFile(),
    title: APP_NAME,
    // Frameless on Windows/Linux with our own titlebar; on macOS we keep the
    // native traffic lights via a hidden titlebar so it still feels native.
    frame: false,
    titleBarStyle: isMac ? 'hidden' : undefined,
    titleBarOverlay: isMac
      ? { color: '#0b0c12', symbolColor: '#eceef4', height: 52 }
      : undefined,
    trafficLightPosition: isMac ? { x: 18, y: 18 } : undefined,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, // renderer never gets raw Node
      nodeIntegration: false,
      webSecurity: true,
      spellcheck: false,
    },
  });

  mainWindow.loadURL(url);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (!app.isPackaged) mainWindow.webContents.openDevTools({ mode: 'detach' });
  });

  mainWindow.on('closed', () => { mainWindow = null; });

  // Keep in-app links in the user's real browser.
  mainWindow.webContents.setWindowOpenHandler(({ url: target }) => {
    if (/^https?:/i.test(target)) { shell.openExternal(target); return { action: 'deny' }; }
    return { action: 'allow' };
  });
}

/* ------------------------------------------------------------------ IPC glue */

function send(win, channel, payload) {
  if (win && !win.isDestroyed()) win.webContents.send(channel, payload);
}

function registerIpc() {
  ipcMain.handle('app:info', () => ({
    name: APP_NAME,
    version: app.getVersion(),
    platform: process.platform,
    arch: process.arch,
    electron: process.versions.electron,
    node: process.versions.node,
    chrome: process.versions.chrome,
    isMaximized: !!(mainWindow && mainWindow.isMaximized()),
    dataDir: dataDir(),
  }));

  ipcMain.on('window:minimize', () => mainWindow && mainWindow.minimize());
  ipcMain.on('window:close', () => mainWindow && mainWindow.close());
  ipcMain.on('window:maximize', () => {
    if (!mainWindow) return;
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
    send(mainWindow, 'window:maximized', mainWindow.isMaximized());
  });
  ipcMain.handle('window:isMaximized', () => !!(mainWindow && mainWindow.isMaximized()));

  /** Real native folder picker — this is the "Browse" button. */
  ipcMain.handle('dialog:pickFolder', async (_e, opts = {}) => {
    if (!mainWindow) return null;
    const res = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory', 'createDirectory'],
      title: opts.title || 'Choose your mods folder',
      defaultPath: opts.defaultPath || undefined,
      buttonLabel: opts.buttonLabel || 'Use this folder',
    });
    if (res.canceled || !res.filePaths.length) return null;
    return res.filePaths[0];
  });

  /** Real native file picker (used for the game executable). */
  ipcMain.handle('dialog:pickFile', async (_e, opts = {}) => {
    if (!mainWindow) return null;
    const res = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      title: opts.title || 'Select the game executable',
      filters: opts.filters || [{ name: 'Executables', extensions: ['exe', 'app', 'sh', 'bin'] }],
    });
    if (res.canceled || !res.filePaths.length) return null;
    return res.filePaths[0];
  });

  ipcMain.handle('shell:openPath', async (_e, target) => {
    if (!target) return { ok: false };
    const err = await shell.openPath(target);
    return { ok: !err, error: err || null };
  });

  ipcMain.handle('app:notify', (_e, { title, body } = {}) => {
    if (!Notification.isSupported()) return false;
    new Notification({ title: title || APP_NAME, body: body || '' }).show();
    return true;
  });

  ipcMain.handle('app:openExternal', async (_e, target) => {
    if (!/^https?:/i.test(target || '')) return false;
    await shell.openExternal(target);
    return true;
  });
}

/* ------------------------------------------------------------------ lifecycle */

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    if (isMac) app.dock.setIcon(iconFile());
    serverInfo = await startServer({
      rendererDir: path.join(__dirname, '..', 'renderer'),
      host: '127.0.0.1',
      port: 0, // let the OS pick a free port
    });
    console.log(`[FunkForge] backend on ${serverInfo.url}`);
    registerIpc();
    await createWindow();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });

  app.on('window-all-closed', () => {
    if (serverInfo && serverInfo.server) {
      try { serverInfo.server.close(); } catch (_) { /* ignore */ }
    }
    if (!isMac) app.quit();
  });
}
