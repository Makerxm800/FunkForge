<div align="center">

# 🎵 FunkForge

**A lightweight, standalone mod manager for Friday Night Funkin'**

Enable or disable mods without digging through game folders by hand.
Simple. Fast. Safe. 🔥

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/Makerxm800/funkforge)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Privacy](#-privacy--safety) • [Roadmap](#-roadmap)

</div>

---

## ✨ What is FunkForge?

FunkForge is a **zero-dependency**, **fully offline** mod manager for *Friday Night Funkin'*. It scans your mods folder, lets you toggle mods on and off with a single click, and launches the game — all from one clean tkinter interface.

No installers. No background services. No internet required.

---

## 🔒 Privacy & Safety

> **TL;DR — FunkForge never phones home. Not a single byte.**

| | |
|---|---|
| ✅ **No viruses** | 100% clean source code, open for anyone to inspect. |
| ✅ **No telemetry** | We do NOT track you. Ever. |
| ✅ **No analytics** | No Google Analytics, no tracking pixels, no hidden callbacks. |
| ✅ **No ads** | Zero ads, zero sponsors. |
| ✅ **No accounts** | No sign-up, no login, no email. |
| ✅ **No internet** | Works 100% offline. Unplug your WiFi and it still works. |
| ✅ **No data sold** | Nothing is sold, shared, or uploaded — because nothing leaves your PC. |

### 📁 What user data is stored?

FunkForge saves **one small config file** locally on your computer only (`~/.funkforge.json`) containing:

- Your mods folder path
- Your game executable path

That's it. Delete it anytime — the app will simply ask you to set it up again.

### 🌐 Is anything sent online?

Nope. Not a single byte.

### 🧪 How to verify

Don't trust me? **Good — don't trust anyone blindly.**

1. **Read the source code** — it's all in `app.py`.
2. **Search for network calls** — grep the code for `http`, `requests`, `socket`, `urllib`, `urlopen`. You'll find nothing.
3. **Check the imports** — the only imports are `os`, `json`, `shutil`, `subprocess`, `tkinter`, and `pathlib`. All standard library.
4. **Run it in a sandbox or VM** for extra peace of mind.

---

## 🚀 Features

- 🔍 **Automatic mod scanning** — detects mods in your folder
- ✅ **One-click enable/disable** — toggles a `.disabled` suffix on folders
- 💾 **Local settings** — saves your mods folder + game path
- 🎮 **Game launcher** — start FNF straight from the app
- 🎨 **Clean interface** — simple tkinter UI
- 📴 **Fully offline** — no internet, ever

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Makerxm800/funkforge.git
cd funkforge
```

### 2. Make sure Python 3.10+ is installed

tkinter is included with most Python installs. On Linux you may need:

```bash
sudo apt install python3-tk
```

### 3. Run it

No dependencies to install. Just:

```bash
python app.py
```

---

## 🕹️ Usage

1. Open FunkForge (`python app.py`).
2. Click **Browse** next to **Mods folder** and select your FNF mods directory.
3. Click **Browse** next to **Game exe** and select your FNF executable.
4. **Check / uncheck** mods to enable or disable them.
   - Disabled mods get a `.disabled` suffix on the folder name.
5. Click **Save** to remember your settings.
6. Click **Launch Game** to start FNF.

---

## ⚙️ Requirements

- **Python** 3.10 or newer
- **tkinter** (bundled with Python on Windows/macOS; `python3-tk` on Linux)
- **OS:** Windows / macOS / Linux
- **No internet required** 🌐❌
- **No `pip install` needed** — zero dependencies

---

## 🗺️ Roadmap

These are **future ideas** — not built yet.

- [ ] Drag-and-drop mod priority ordering
- [ ] Mod dependency detection
- [ ] Profile system (save multiple loadouts)
- [ ] Mod conflict warnings
- [ ] Dark mode
- [ ] Auto-update checker (opt-in only)

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first so we can talk it over.

---

## 📜 License

**MIT License** — free to use, modify, and share.
See the [LICENSE](LICENSE) file for full text.

---

## 🙏 Credits

Built with ❤️ by **Your Name**.

*Friday Night Funkin'* is made by **The Funkin' Crew Inc.**
FunkForge is an **UNOFFICIAL fan tool** and is not affiliated with or endorsed by them.

---

## 💬 Questions?

Open an [issue](https://github.com/Makerxm800/funkforge/issues) on GitHub — no email required, no account required, no tracking.

**Stay funky. 🎤🔥**
