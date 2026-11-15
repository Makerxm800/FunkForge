'use strict';
/**
 * Preload bridge.
 *
 * The renderer runs with nodeIntegration disabled and contextIsolation on, so
 * the only way it reaches the OS is through this small, explicit API. Nothing
 * here is required for the core browsing/managing features — the renderer also
 * works unmodified in a plain browser, it just detects that `window.ff` is
 * missing and hides the OS-only buttons.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('ff', {
  /** True only inside the real desktop app. */
  isDesktop: true,
  platform: process.platform,

  info: () => ipcRenderer.invoke('app:info'),

  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
  onMaximizedChange: (cb) => {
    const listener = (_e, value) => cb(value);
    ipcRenderer.on('window:maximized', listener);
    return () => ipcRenderer.removeListener('window:maximized', listener);
  },

  /** Native folder picker — returns an absolute path or null. */
  pickFolder: (opts) => ipcRenderer.invoke('dialog:pickFolder', opts),
  pickFile: (opts) => ipcRenderer.invoke('dialog:pickFile', opts),
  openPath: (target) => ipcRenderer.invoke('shell:openPath', target),
  notify: (opts) => ipcRenderer.invoke('app:notify', opts),
  openExternal: (url) => ipcRenderer.invoke('app:openExternal', url),
});
