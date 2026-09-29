==================================================
  🎵 FunkForge - FNF Mod Manager 🎵
==================================================

Version: 0.1.0
Author:  Your Name
License: MIT

--------------------------------------------------
✨ WHAT IS FUNKFORGE?
--------------------------------------------------
FunkForge is a lightweight, standalone mod manager for
Friday Night Funkin'. It lets you enable or disable
mods without digging through game folders by hand.

Simple. Fast. Safe. 🔥

--------------------------------------------------
🔒 PRIVACY & SAFETY (READ THIS)
--------------------------------------------------
✅ NO VIRUS        - 100% clean source code, open for
                     anyone to inspect.
✅ NO TELEMETRY    - We do NOT track you. Ever.
✅ NO ANALYTICS    - No Google Analytics, no tracking
                     pixels, no hidden callbacks.
✅ NO ADS          - Zero ads, zero sponsors.
✅ NO ACCOUNTS     - No sign-up, no login, no email.
✅ NO INTERNET     - Works 100% offline. The app never
                     phones home.
✅ NO DATA SOLD    - Nothing is sold, shared, or
                     uploaded. Because nothing leaves
                     your PC.

📁 WHAT USER DATA IS STORED?
   FunkForge saves ONE small config file locally on
   YOUR computer only (~/.funkforge.json):
     - Your mods folder path
     - Your game executable path

   That's it. Nothing else. You can delete it anytime
   and the app will just ask you to set it up again.

🌐 IS ANYTHING SENT ONLINE?
   Nope. Not a single byte. Unplug your WiFi and
   FunkForge still works perfectly.

🧪 HOW TO VERIFY
   Don't trust me? Good — don't trust anyone blindly.
   1. Read the source code (it's all in app.py).
   2. Search the code for "http", "requests", "socket",
      "urllib", "urlopen" — you'll find nothing.
   3. The only imports are: os, json, shutil, subprocess,
      tkinter, pathlib. All standard library.
   4. Run it in a sandbox or VM for extra peace of mind.

--------------------------------------------------
🚀 FEATURES (what's actually built)
--------------------------------------------------
- 🔍 Scans your mods folder automatically
- ✅ Enable / disable mods with one click
- 💾 Saves your mods folder + game path locally
- 🎮 Launch the game straight from the app
- 🎨 Clean, simple interface (tkinter)
- 📴 Fully offline

--------------------------------------------------
🗺️ ROADMAP (NOT built yet — future ideas)
--------------------------------------------------
[ ] Drag-and-drop mod priority ordering
[ ] Mod dependency detection
[ ] Profile system (save multiple loadouts)
[ ] Mod conflict warnings
[ ] Dark mode
[ ] Auto-update checker (opt-in only)

--------------------------------------------------
📦 INSTALLATION
--------------------------------------------------
1. Clone the repo:

   git clone https://github.com/yourname/funkforge.git

2. Make sure Python 3.10+ is installed.
   (tkinter is included with most Python installs.
    On Linux you may need: sudo apt install python3-tk)

3. No dependencies to install. Just run:

   python app.py

--------------------------------------------------
🕹️ USAGE
--------------------------------------------------
1. Open FunkForge.
2. Click "Browse" next to "Mods folder" and pick your
   FNF mods directory.
3. Click "Browse" next to "Game exe" and pick your
   FNF executable.
4. Check / uncheck mods to enable or disable them.
   (Disabled mods get a .disabled suffix on the folder.)
5. Click "Save" to remember your settings.
6. Click "Launch Game" to start FNF.

--------------------------------------------------
⚙️ REQUIREMENTS
--------------------------------------------------
- Python 3.10 or newer
- tkinter (bundled with Python on Windows/macOS)
- Windows / macOS / Linux
- No internet connection required 🌐❌
- No pip install needed — zero dependencies

--------------------------------------------------
🤝 CONTRIBUTING
--------------------------------------------------
Pull requests are welcome! For major changes,
open an issue first so we can talk it over.

--------------------------------------------------
📜 LICENSE
--------------------------------------------------
MIT License - free to use, modify, and share.
See LICENSE file for full text.

--------------------------------------------------
🙏 CREDITS
--------------------------------------------------
Built with ❤️ by Your Name.

Friday Night Funkin' is made by The Funkin' Crew Inc.
FunkForge is an UNOFFICIAL fan tool and is not
affiliated with or endorsed by them.

--------------------------------------------------
💬 QUESTIONS?
--------------------------------------------------
Open an issue on GitHub and I'll reply when I can.
No email required, no account required, no tracking.

Stay funky. 🎤🔥
