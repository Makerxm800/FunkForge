# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FunkForge (Beta).

Builds a genuine native binary -- no Electron, no bundled Chromium, no
Node runtime.  Just Python + tkinter, frozen by PyInstaller:

  Windows : dist/FunkForge (Beta).exe      (~25 MB, single file)
  macOS   : dist/FunkForge (Beta).app      (real .app bundle)
  Linux   : dist/FunkForge (Beta)/         (one-folder build)

Usage:
  pyinstaller FunkForge.spec --noconfirm
"""

import os
import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH)
APP_NAME = "FunkForge (Beta)"

# Read the version straight out of app.py so the spec can never drift from it.
def _read_version(default="1.5.0"):
    import re
    try:
        src = (SPEC_DIR / "app.py").read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', src, re.M)
        if m:
            return m.group(1)
    except Exception:
        pass
    return default


APP_VERSION = _read_version()
print(f"[spec] FunkForge (Beta) v{APP_VERSION}")

# --------------------------------------------------------------------------
# Data files the app needs at runtime.
#   index.html            -> required by the built-in web UI ("Web version")
#   assets/logo.png       -> window/taskbar icon
#   assets/logo.ico/.icns -> platform icons
# --------------------------------------------------------------------------
datas = []
for rel in ("index.html", "requirements.txt", "License"):
    src = SPEC_DIR / rel
    if src.exists():
        datas.append((str(src), "."))

assets_dir = SPEC_DIR / "assets"
if assets_dir.is_dir():
    # Keep the folder name so resource_path("assets/logo.png") keeps working.
    datas.append((str(assets_dir), "assets"))

# --------------------------------------------------------------------------
# Modules PyInstaller's static analysis can't always see.
# --------------------------------------------------------------------------
hiddenimports = [
    "requests",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageTk",
    "PIL._tkinter_finder",
    "urllib3",
    "charset_normalizer",
    "idna",
    "certifi",
]

# Trim fat we never import -- keeps the download small.
excludes = [
    "matplotlib", "numpy", "pandas", "scipy", "PyQt5", "PyQt6", "PySide2",
    "PySide6", "IPython", "jupyter", "notebook", "pytest", "setuptools",
    "wheel", "pip", "tkinter.test", "test", "unittest", "doctest",
    "pydoc", "pdb", "lib2to3", "distutils",
]

icon_path = str(assets_dir / ("logo.icns" if sys.platform == "darwin"
                              else "logo.ico"))
if not os.path.exists(icon_path):
    icon_path = None

a = Analysis(
    [str(SPEC_DIR / "app.py")],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

if sys.platform == "darwin":
    # ---------------- macOS: a real .app bundle ----------------
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,          # no terminal window for a GUI app
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name=APP_NAME,
    )

    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon_path,
        bundle_identifier="com.makerxm800.funkforge",
        version=APP_VERSION,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "CFBundleIdentifier": "com.makerxm800.funkforge",
            "NSHighResolutionCapable": True,
            "NSSupportsAutomaticTermination": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSApplicationCategoryType": "public.app-category.utilities",
            "CFBundleDocumentTypes": [],
            "NSHumanReadableCopyright": "Copyright (c) 2026 Makerxm800",
        },
    )

elif sys.platform == "win32":
    # ---------------- Windows: one self-contained .exe ----------------
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=False,          # GUI app: no console window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
        version=None,
    )

else:
    # ---------------- Linux / other ----------------
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name=APP_NAME,
    )
