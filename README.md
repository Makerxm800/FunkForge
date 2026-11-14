<div align="center">

<img src="assets/logo.png" alt="FunkForge" width="128" height="128">

# FunkForge (Beta)

**A fast, native mod browser, downloader and manager for Friday Night Funkin'**

Browse, install and launch FNF mods without digging through game folders.

[![Version](https://img.shields.io/badge/version-1.5.0%20(Beta)-blue.svg)](https://github.com/Makerxm800/FunkForge/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](License)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![No Electron](https://img.shields.io/badge/electron-none-green.svg)]()

[Download](#-download) • [Features](#-features) • [Run from source](#-run-from-source) • [Build](#-building-the-real-exe--app) • [Privacy](#-privacy--safety)

</div>

---

## ✨ What is FunkForge (Beta)?

FunkForge is a **native desktop app** for finding, installing and managing
*Friday Night Funkin'* mods. It talks to the public
[GameBanana](https://gamebanana.com) API to show real mods with real previews,
download counts and files — then keeps them tidy on your disk.

Two front-ends, one codebase:

| | |
|---|---|
| 🖥️ **Desktop app** | A custom tkinter UI (Windows / macOS / Linux) |
| 🌐 **Web UI** | The same app in your browser — `python app.py --web` |

Both are **real native builds**. No Electron, no bundled Chromium, no Node
runtime — just Python and tkinter, frozen with PyInstaller. The Windows
download is a single portable `.exe`; macOS is a genuine `.app` bundle in a
`.dmg`.

---

## 📦 Download

Grab the build for your platform from the
**[Releases](https://github.com/Makerxm800/FunkForge/releases)** page:

| Platform | File | How to install |
|---|---|---|
| **Windows 10/11 (64-bit)** | `FunkForge-Beta-Windows-x64.zip` | Extract anywhere → run **FunkForge (Beta).exe** |
| **macOS** (Apple Silicon + Intel) | `FunkForge-Beta-macOS.dmg` | Open the DMG → drag **FunkForge (Beta).app** into Applications |

> **First-launch warnings you may see** (both are normal for unsigned, free,
> open-source software — code-signing certificates cost hundreds per year):
>
> - **Windows SmartScreen:** *"Windows protected your PC"* → click
>   **More info → Run anyway**.
> - **macOS Gatekeeper:** right-click the app → **Open** once, or allow it in
>   *System Settings → Privacy & Security*.

---

## 🚀 Features

### Browse & download
- 🔍 Search GameBanana across **Mods, Tools and Sounds** at once
- 🖼️ Rich result cards with preview art, author, downloads and engine tag
- ⚙️ Automatic **engine detection** (Psych, Kade, V-Slice, Codename, …)
- 🌟 Flags **official** Funkin' Crew releases
- 📄 Full mod pages: description, image gallery, file picker, one-click install
- ⬇️ Smart install — handles nested zips, wrapper folders and archives
  automatically

### Manage
- 📁 Local mods library with **list and grid** views
- ✅ Installed / official badges, folder sizes, per-mod EXE detection
- 🗂️ Reorder, rename-friendly naming, zip backup, delete
- 🎮 **Launch** the game or a specific mod straight from the app
- 🕘 Full activity history

### Interface
- 🎨 7 themes (Midnight, Dark, Light, Ocean, Sunset, Forest, Rosegold)
- 🔔 Native OS notifications
- ⚡ Cached thumbnails and a bounded worker pool, so scrolling stays smooth
  with hundreds of results

---

## 🔒 Privacy & Safety

> **TL;DR — FunkForge sends nothing anywhere except GameBanana, and only to
> look up mods you asked for. No telemetry, ever.**

| | |
|---|---|
| ✅ **No telemetry** | We do not track you. Ever. |
| ✅ **No analytics** | No Google Analytics, no pixels, no hidden callbacks. |
| ✅ **No ads** | Zero ads, zero sponsors. |
| ✅ **No accounts** | No sign-up, no login, no email. |
| ✅ **No data sold** | Nothing is shared or sold, because nothing is collected. |

### What does it talk to?
Only **`gamebanana.com`** — the public mod database — and only to search,
preview and download mods you requested. Nothing else. No FunkForge server
exists; there is no backend to phone home to.

### 📁 What is stored locally?
Everything lives on your own machine:

| Path | Purpose |
|---|---|
| `~/.funkforge.json` | Your settings (mods folder, game path, theme) |
| `~/.funkforge_history.json` | Your activity history |
| `~/.funkforge/cache/` | Cached thumbnails (trimmed at 256 MB) |

Delete them any time — the app simply re-creates what it needs.

### 🧪 Verify it yourself
Don't take our word for it:
1. Read the source — it's all here.
2. `grep -rn "http" app.py` — the only remote host is `gamebanana.com`.
3. Block it in your firewall and watch the app still launch fine.

---

## 🕹️ Usage

1. Open FunkForge.
2. **Browse** the feed, or search for something (e.g. `whitty`).
3. Click a mod to see its description, gallery and files.
4. Hit **Install** — FunkForge downloads, extracts and cleans it up.
5. Go to the **Mods** tab to launch, zip, or delete what you have.

Set your *mods folder* and *game executable* in **Settings** (⚙). The app
auto-detects a Steam/itch install of the official game when it can.

---

## 🛠️ Run from source

Requires **Python 3.10+**.

```bash
git clone https://github.com/Makerxm800/FunkForge.git
cd FunkForge

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python app.py                  # desktop app
```

Extra modes:

```bash
python app.py --web            # desktop app + open the web UI
python app.py --web-only       # just the local web server (no GUI needed)
python app.py --web-only --host 0.0.0.0 --port 8756
```

> `tkinter` ships with Python on Windows and macOS. On Debian/Ubuntu you may
> need `sudo apt install python3-tk`. The `--web-only` mode needs no GUI
> toolkit at all, so it works headless.

---

## 🏗️ Building the real .exe / .app

Everything is automated in GitHub Actions — **`.github/workflows/build-release.yml`**.
Pushing a `v*` tag builds Windows and macOS binaries on real Windows and macOS
runners and publishes them to a Release:

```bash
git tag v1.5.0
git push origin v1.5.0
```

To build locally with [PyInstaller](https://pyinstaller.org):

```bash
pip install -r requirements-build.txt
python tools/make_icons.py    # regenerate assets/logo.ico + logo.icns

# Windows
build_windows.bat             # -> dist\FunkForge (Beta).exe

# macOS
./build_mac.sh                # -> dist/FunkForge (Beta).app

# Linux
./build_linux.sh              # -> dist/FunkForge (Beta)/
```

Or invoke the spec directly on any platform:

```bash
pyinstaller FunkForge.spec --noconfirm --clean
```

`FunkForge.spec` bundles `index.html` and `assets/` into the binary, so the
built-in web UI works from inside the packaged app.

---

## ⚙️ Requirements

- **Runtime:** Python 3.10+, `requests`, `pillow`, `tkinter` (GUI only)
- **Build:** Python 3.10+, `pyinstaller`
- **OS:** Windows 10/11, macOS 11+, Linux
- **Network:** only needed for browsing/downloading mods

---

## 🗺️ Roadmap

- [ ] Mod profiles / loadouts
- [ ] Dependency & conflict detection
- [ ] Auto-update check (opt-in only)
- [ ] Code-signing once the project can justify a certificate

---

## 📜 License

**MIT** — free to use, modify and share. See [License](License).

---

## 🙏 Credits

Built by **Makerxm800**.

*Friday Night Funkin'* is made by **The Funkin' Crew Inc.**
FunkForge is an **UNOFFICIAL fan tool** and is not affiliated with or endorsed
by them. Mod data comes from **GameBanana**; all mods belong to their
respective creators.

---

**FunkForge (Beta) v1.5.0** · stay funky 🎤🔥
