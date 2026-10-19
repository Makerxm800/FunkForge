# app.py
# FunkForge Browser - FNF Mod Browser & Downloader
# MIT License

import base64, io, json, os, re, shutil, subprocess, sys, tempfile
import threading, time, traceback, webbrowser, zipfile
import argparse, functools, http.server, socket, socketserver
from datetime import datetime
from pathlib import Path

try:
    import requests
    from PIL import Image, ImageDraw, ImageTk, ImageFilter
except ImportError as _e:
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        _r = _tk.Tk(); _r.withdraw()
        _mb.showerror("FunkForge - missing package",
                      f"{_e}\n\nInstall the requirements, then start again:\n\n"
                      "pip install requests pillow")
    except Exception:
        print(f"Missing package: {_e}\nRun: pip install requests pillow")
    raise SystemExit(1)
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox

PROGRAM_NAME = "FunkForge Browser"
VERSION = "1.4.1"
AUTHOR = "Your Name"
GB_API = "https://gamebanana.com/apiv11"
FNF_GAME_ID = 8694
HEADERS = {"User-Agent": f"FunkForge/{VERSION}"}
CONFIG_PATH = Path.home() / ".funkforge.json"
HISTORY_PATH = Path.home() / ".funkforge_history.json"
DEFAULT_MODS_FOLDER = Path.home() / "FunkForgeMods"
MOD_META_FILE = ".funkforge_meta.json"
PER_PAGE = 48
STARTUP_PAGES = 6  # auto-fetch 6 pages on open/search — no "Load more" spam
LOAD_ALL_MAX_PAGES = 30
BROWSE_RENDER_LIMIT = 48  # paint first N browse cards; "Show more" paints the rest — kills load lag
THUMB_CONCURRENCY = 6
PREVIEW_SIZE = (440, 250)
STRIP_SIZE = (90, 50)
FADE_STEPS = 5
SEARCH_PER_PAGE = 48
PREVIEW_INTERVAL_MS = 3500
SEARCH_MODELS = ("Mod", "Tool", "Sound")
MODEL_SLUGS = {"Mod": "mods", "Tool": "tools", "Sound": "sounds", "Wip": "wips"}
MODEL_ICONS = {"Mod": "🎮", "Tool": "🧰", "Sound": "🔊"}

WEB_PORT_DEFAULT = 8756
_web_server = None

ENGINES = [
    ("Psych Engine", ["psych"]), ("Kade Engine", ["kade"]),
    ("V-Slice / Vanilla", ["v-slice", "vslice", "vanilla", "base game", "official"]),
    ("Codename Engine", ["codename"]), ("Forever Engine", ["forever"]),
    ("Andromeda Engine", ["andromeda"]),
    ("Mic'd Up", ["mic'd up", "micd up", "micdup"]),
    ("FPS Plus", ["fps plus"]), ("Other / Unknown", []),
]


OFFICIAL_SUBMITTERS = {"ninjamuffin99", "phantomarcade", "phantomarcade3k",
                       "evilsk8r", "kawaisprite", "funkin' crew", "funkin crew",
                       "the funkin' crew", "funkincrew"}
OFFICIAL_PREFIXES = ("friday night funkin", "fnf base game", "funkin' base game",
                     "funkin base game", "base game", "official release")
NOT_OFFICIAL_HINTS = (" vs", "vs.", " mod", "remix", "fan", "reskin", " ft.",
                      "port", "edition", "recreation", "clone", "demake")

BROWSE_SORT_OPTIONS = [
    ("Best Match", "best_match"), ("Most Downloaded", "downloads"),
    ("Most Liked", "likes"), ("Newest", "new"), ("Updated", "updated"),
    ("A → Z", "name"), ("Installed Only", "installed_only"),
    ("Officials Only", "officials_only"), ("Officials First", "officials_first"),
]
MODS_SORT_OPTIONS = [
    ("A → Z", "name_asc"), ("Z → A", "name_desc"),
    ("Newest installed", "new_installed"), ("Oldest installed", "old_installed"),
    ("Largest first", "size_desc"), ("Smallest first", "size_asc"),
    ("Has EXE first", "has_exe"), ("Official first", "official"),
]
HISTORY_SORT_OPTIONS = [("Newest first", "ts_desc"), ("Oldest first", "ts_asc"),
                        ("A → Z", "name_asc")]

THEMES = {
    "light": {"bg": "#f4f5fa", "fg": "#161824", "panel": "#ffffff",
              "panel2": "#eceef6", "border": "#dcdfeb", "accent": "#6c4cf5",
              "accent_hover": "#8266ff", "accent_dark": "#5a3de0",
              "accent_fg": "#ffffff", "subtle": "#6b7086",
              "preview_bg": "#e6e8f0", "entry_bg": "#ffffff",
              "entry_fg": "#161824", "hover": "#e4e7f3", "select": "#e0dcff",
              "tab_active": "#ffffff", "strip": "#e9ebf4", "danger": "#dc2626",
              "success": "#16a34a", "zipped": "#f59e0b", "card_hover": "#eef0f8"},
    "dark":  {"bg": "#0e0f14", "fg": "#eceef4", "panel": "#171922",
              "panel2": "#1e212c", "border": "#272b38", "accent": "#7c5cff",
              "accent_hover": "#9479ff", "accent_dark": "#6446e6",
              "accent_fg": "#ffffff", "subtle": "#8f94a8",
              "preview_bg": "#0a0b0f", "entry_bg": "#12141b",
              "entry_fg": "#eceef4", "hover": "#262a39", "select": "#2c2560",
              "tab_active": "#171922", "strip": "#12141b", "danger": "#e5484d",
              "success": "#30a46c", "zipped": "#f5a524", "card_hover": "#232636"},
    "midnight":  {"bg": "#0e0f14", "fg": "#eceef4", "panel": "#171922",
              "panel2": "#1e212c", "border": "#272b38", "accent": "#7c5cff",
              "accent_hover": "#9479ff", "accent_dark": "#6446e6",
              "accent_fg": "#ffffff", "subtle": "#8f94a8",
              "preview_bg": "#0a0b0f", "entry_bg": "#12141b",
              "entry_fg": "#eceef4", "hover": "#262a39", "select": "#2c2560",
              "tab_active": "#171922", "strip": "#12141b", "danger": "#e5484d",
              "success": "#30a46c", "zipped": "#f5a524", "card_hover": "#232636"},
    "ocean":  {"bg": "#06283a", "fg": "#e8f4f8", "panel": "#0a3448",
              "panel2": "#0e4258", "border": "#174d63", "accent": "#0ea5e9",
              "accent_hover": "#38bdf8", "accent_dark": "#0284c7",
              "accent_fg": "#ffffff", "subtle": "#8fb3c1",
              "preview_bg": "#062433", "entry_bg": "#0a3448",
              "entry_fg": "#e8f4f8", "hover": "#134a5f", "select": "#0c4a6e",
              "tab_active": "#0a3448", "strip": "#0a3448", "danger": "#e5484d",
              "success": "#30a46c", "zipped": "#f5a524", "card_hover": "#134a5f"},
    "sunset":  {"bg": "#2b0e20", "fg": "#fdf0f5", "panel": "#3d1530",
              "panel2": "#4e1c3d", "border": "#5f2749", "accent": "#ec4899",
              "accent_hover": "#f472b6", "accent_dark": "#be185d",
              "accent_fg": "#ffffff", "subtle": "#c99ab0",
              "preview_bg": "#230a1a", "entry_bg": "#3d1530",
              "entry_fg": "#fdf0f5", "hover": "#57204a", "select": "#831843",
              "tab_active": "#3d1530", "strip": "#3d1530", "danger": "#e5484d",
              "success": "#30a46c", "zipped": "#f5a524", "card_hover": "#57204a"},
    "forest":  {"bg": "#071a13", "fg": "#eaf7f0", "panel": "#0b241b",
              "panel2": "#103026", "border": "#1a4032", "accent": "#10b981",
              "accent_hover": "#34d399", "accent_dark": "#047857",
              "accent_fg": "#ffffff", "subtle": "#93b8a6",
              "preview_bg": "#05130e", "entry_bg": "#0b241b",
              "entry_fg": "#eaf7f0", "hover": "#143c2d", "select": "#065f46",
              "tab_active": "#0b241b", "strip": "#0b241b", "danger": "#e5484d",
              "success": "#30a46c", "zipped": "#f5a524", "card_hover": "#143c2d"},
    "rosegold":  {"bg": "#220f16", "fg": "#fdf0f3", "panel": "#301722",
              "panel2": "#3e1e2e", "border": "#4e2a3c", "accent": "#f472b6",
              "accent_hover": "#f9a8d4", "accent_dark": "#db2777",
              "accent_fg": "#ffffff", "subtle": "#c99aae",
              "preview_bg": "#1c0c13", "entry_bg": "#301722",
              "entry_fg": "#fdf0f3", "hover": "#482335", "select": "#831843",
              "tab_active": "#301722", "strip": "#301722", "danger": "#e5484d",
              "success": "#30a46c", "zipped": "#f5a524", "card_hover": "#482335"},
}
THEME_ORDER = ["midnight", "dark", "light", "ocean", "sunset", "forest", "rosegold"]
THEME_LABELS = {"midnight": "Midnight", "dark": "Dark", "light": "Light",
                "ocean": "Ocean", "sunset": "Sunset", "forest": "Forest",
                "rosegold": "Rosegold"}

HISTORY_STYLES = {
    "install": ("#3ba55d", "📥"), "download": ("#5865f2", "⬇"),
    "launch": ("#a855f7", "🎮"), "delete": ("#ed4245", "🗑"),
    "zip": ("#faa61a", "📦"), "import": ("#06b6d4", "➕"),
    "folder": ("#9a9da3", "📁"), "official": ("#f59e0b", "🌟"),
    "theme": ("#8b5cf6", "🎨"), "engine": ("#00bcd4", "⚙"),
}

EXE_SKIP = {"unins000.exe", "uninstall.exe", "setup.exe", "installer.exe",
            "vc_redist.x64.exe", "vc_redist.x86.exe", "dxwebsetup.exe",
            "unitycrashhandler64.exe", "unitycrashhandler32.exe",
            "crashpad_handler.exe"}
EXE_NAME_HINTS = ("fnf", "funkin", "psych", "kade", "codename",
                  "forever", "andromeda", "game", "vs ", "vs_")
ARCHIVE_EXTS = (".zip", ".rar", ".7z", ".tar", ".gz")
THUMB_SEM = threading.Semaphore(THUMB_CONCURRENCY)


# ========== UTILITIES ==========

def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return {"theme": "dark", "mods_folder": str(DEFAULT_MODS_FOLDER),
            "game_exe": "", "official_mods": [], "auto_zip_backup": True,
            "os_notifications": True, "mods_view": "list"}


def save_config(cfg):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception:
        pass


def load_history():
    if HISTORY_PATH.exists():
        try:
            d = json.loads(HISTORY_PATH.read_text())
            return d if isinstance(d, list) else []
        except Exception:
            pass
    return []


def save_history(h):
    try:
        HISTORY_PATH.write_text(json.dumps(h[:500], indent=2))
    except Exception:
        pass


def detect_engine(text):
    t = (text or "").lower()
    for name, keys in ENGINES:
        for k in keys:
            if k in t:
                return name
    return "Other / Unknown"


def is_official_rec(rec, official_set):
    """Official = user-marked, published by the Funkin' Crew accounts on
    GameBanana, or clearly the base game (not a 'vs' / remix / fan mod)."""
    name = (rec.get("_sName") or "").strip()
    if name and name in official_set:
        return True
    sub = ((rec.get("_aSubmitter") or {}).get("_sName") or "").strip().lower()
    if sub and sub in OFFICIAL_SUBMITTERS:
        return True
    nl = name.lower()
    if not nl or any(h in nl for h in NOT_OFFICIAL_HINTS):
        return False
    return any(nl.startswith(p) for p in OFFICIAL_PREFIXES)


def is_official_name(name, official_set):
    return is_official_rec({"_sName": name}, official_set)


def fetch_image(url, size):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        img.thumbnail(size, Image.LANCZOS)
        return img
    except Exception:
        return None


def strip_html(html):
    text = re.sub(r"<br\s*/?>", "\n", html or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def safe_name(s):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip(" .") or "mod"


def human_size(n):
    if not n:
        return "?"
    n = float(n)
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_date(ts):
    if not ts:
        return "?"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%b %d, %Y")
    except Exception:
        return "?"


def fmt_ago(ts):
    try:
        d = int(time.time() - int(ts))
    except Exception:
        return "?"
    if d < 60: return f"{d}s ago"
    if d < 3600: return f"{d // 60}m ago"
    if d < 86400: return f"{d // 3600}h ago"
    return f"{d // 86400}d ago"


def folder_size(p):
    try:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    except Exception:
        return 0


def find_mod_exe(folder):
    if not folder or not Path(folder).is_dir():
        return None
    folder = Path(folder)
    exes = []
    for p in folder.rglob("*.exe"):
        ln = p.name.lower()
        if ln in EXE_SKIP: continue
        parts = [x.lower() for x in p.parts]
        if any(x in ("__macosx", "redist", "dotnet", "$recycle.bin") for x in parts):
            continue
        try: sz = p.stat().st_size
        except Exception: sz = 0
        hinted = 0 if any(h in ln for h in EXE_NAME_HINTS) else 1
        depth = len(p.relative_to(folder).parts)
        exes.append((hinted, depth, -sz, p))
    if not exes: return None
    exes.sort()
    return exes[0][3]


def find_mod_preview(folder):
    folder = Path(folder)
    if not folder.is_dir(): return None
    PRI = ["preview", "banner", "screenshot", "thumbnail", "icon",
           "logo", "cover", "art", "title"]
    EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".bmp")
    ICO_MIN = 500
    DIRS = ["", "images", "assets", "assets/images", "meta",
            "preview", "art", "media", "ui", "title"]
    cands = []
    for base_name in DIRS:
        base = folder / base_name if base_name else folder
        if not base.is_dir(): continue
        for name in PRI:
            for ext in EXTS:
                for p in base.glob(f"{name}{ext}"):
                    if not p.is_file(): continue
                    try:
                        sz = p.stat().st_size
                        if sz < (ICO_MIN if p.suffix.lower() in (".ico", ".bmp") else 3000): continue
                        d = len(p.relative_to(folder).parts)
                        cands.append((PRI.index(name), d, -sz, p))
                    except Exception: continue
    if not cands:
        for name in PRI:
            for p in folder.rglob("*"):
                if not p.is_file() or p.suffix.lower() not in EXTS: continue
                if p.stem.lower() == name:
                    try:
                        sz = p.stat().st_size
                        if sz < (ICO_MIN if p.suffix.lower() in (".ico", ".bmp") else 3000): continue
                        d = len(p.relative_to(folder).parts)
                        cands.append((PRI.index(name) + 10, d, -sz, p))
                    except Exception: continue
    if not cands:
        for p in folder.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXTS: continue
            try:
                sz = p.stat().st_size
                if sz < (ICO_MIN if p.suffix.lower() in (".ico", ".bmp") else 20000): continue
                d = len(p.relative_to(folder).parts)
                cands.append((99, d, -sz, p))
            except Exception: continue
    if not cands: return None
    cands.sort()
    return cands[0][3]


def find_zip_wrapper(folder):
    folder = Path(folder)
    if not folder.is_dir(): return None
    entries = [e for e in folder.iterdir() if not e.name.startswith(".")]
    if len(entries) != 1: return None
    e = entries[0]
    if e.is_file() and e.suffix.lower() in ARCHIVE_EXTS:
        return e
    return None


ZIP_PREVIEW_CACHE = Path.home() / ".funkforge_cache" / "zip_previews"
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".bmp")
_ZIP_PRI = ("preview", "banner", "screenshot", "thumbnail", "icon",
            "logo", "cover", "art", "title")


def find_zip_preview(zp):
    """Peek inside a .zip for a preview/icon image and extract it to cache.
    Returns cached Path or None. .rar/.7z are skipped (no stdlib reader)."""
    zp = Path(zp)
    if zp.suffix.lower() != ".zip": return None
    cache = ZIP_PREVIEW_CACHE / (zp.stem.lower() + ".img")
    if cache.is_file() and cache.stat().st_size > 0: return cache
    try:
        with zipfile.ZipFile(zp) as z:
            scored = []
            for info in z.infolist():
                if info.is_dir() or info.file_size < 500: continue
                name = Path(info.filename).name.lower()
                stem = Path(name).stem
                ext = Path(name).suffix
                if ext not in _IMG_EXTS: continue
                pri = _ZIP_PRI.index(stem) if stem in _ZIP_PRI else 99
                depth = info.filename.count("/")
                scored.append((pri, depth, -info.file_size, info))
            if not scored: return None
            scored.sort()
            info = scored[0][3]
            ZIP_PREVIEW_CACHE.mkdir(parents=True, exist_ok=True)
            data = z.read(info)
            cache.write_bytes(data)
            return cache
    except Exception:
        return None


def analyze_mod_structure(folder):
    """Analyze folder to detect engine, dependencies, and structure."""
    folder = Path(folder)
    if not folder.is_dir():
        return {"engine": "Unknown", "hints": [], "exe": None,
                "has_assets": False, "has_mods": False, "has_lua": False,
                "has_hx": False, "has_manifest": False}

    info = {
        "engine": "Unknown", "hints": [],
        "exe": find_mod_exe(folder),
        "has_assets": (folder / "assets").is_dir(),
        "has_mods": (folder / "mods").is_dir() or (folder / "mods").exists(),
        "has_lua": False, "has_hx": False, "has_manifest": False,
        "has_songs": (folder / "songs").is_dir() or (folder / "assets" / "songs").is_dir(),
        "has_data": (folder / "data").is_dir() or (folder / "assets" / "data").is_dir(),
    }

    # Scan for key files (limited depth to stay fast)
    try:
        for root, dirs, files in os.walk(folder):
            depth = len(Path(root).relative_to(folder).parts)
            if depth > 4:
                dirs[:] = []
                continue
            for f in files:
                fl = f.lower()
                if fl.endswith(".lua"):
                    info["has_lua"] = True
                elif fl.endswith(".hx") or fl.endswith(".hscript"):
                    info["has_hx"] = True
                elif fl == "manifest.json" or fl == "manifest.txt":
                    info["has_manifest"] = True
            if info["has_lua"] and info["has_hx"] and info["has_manifest"]:
                break
    except Exception:
        pass

    # Score engines
    scores = {}
    # Codename
    if info["has_hx"]:
        scores["Codename Engine"] = scores.get("Codename Engine", 0) + 4
        info["hints"].append("Haxe scripts (.hx)")
    # Psych
    if info["has_lua"]:
        scores["Psych Engine"] = scores.get("Psych Engine", 0) + 3
        info["hints"].append("Lua scripts (.lua)")
    if info["has_mods"]:
        scores["Psych Engine"] = scores.get("Psych Engine", 0) + 2
        info["hints"].append("mods/ folder")
    # V-Slice
    if info["has_manifest"]:
        scores["V-Slice / Vanilla"] = scores.get("V-Slice / Vanilla", 0) + 4
        info["hints"].append("manifest.json present")
    # Kade
    if info["has_data"] and info["has_songs"] and not info["has_lua"] and not info["has_hx"]:
        scores["Kade Engine"] = scores.get("Kade Engine", 0) + 2
        info["hints"].append("data/ + songs/ layout")
    # Standalone (has exe, no scripts)
    if info["exe"] and not scores:
        info["hints"].append(f"Standalone build ({info['exe'].name})")

    if scores:
        info["engine"] = max(scores.items(), key=lambda x: x[1])[0]
    else:
        info["engine"] = detect_engine(folder.name)

    return info


def read_mod_meta(folder):
    p = Path(folder) / MOD_META_FILE
    if not p.is_file(): return None
    try: return json.loads(p.read_text())
    except Exception: return None


def write_mod_meta(folder, meta):
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / MOD_META_FILE).write_text(json.dumps(meta, indent=2))
    except Exception:
        pass


def is_zip_flat(zf):
    names = [n for n in zf.namelist() if n and not n.startswith("__MACOSX")]
    tops = {n.split("/")[0] for n in names if n.split("/")[0]}
    if len(tops) != 1: return None
    top = tops.pop()
    if all(n == top or n.startswith(top + "/") for n in names):
        return top
    return None


def extract_zip_smart(zp, dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp) as z:
        top = is_zip_flat(z)
        if top:
            tmp = dest.parent / f".{dest.name}_tmp_ff"
            if tmp.exists(): shutil.rmtree(tmp, ignore_errors=True)
            z.extractall(tmp)
            inner = tmp / top
            if inner.is_dir():
                for item in inner.iterdir():
                    tgt = dest / item.name
                    if tgt.exists():
                        if tgt.is_dir(): shutil.rmtree(tgt, ignore_errors=True)
                        else: tgt.unlink()
                    shutil.move(str(item), str(tgt))
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            z.extractall(dest)


def zip_folder(folder, zip_path, compresslevel=6):
    folder = Path(folder)
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=compresslevel) as z:
        for f in folder.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(folder.parent))


def normalize_mod_name(name):
    if not name: return ""
    s = name.lower()
    s = re.sub(r"\bv?\d+(\.\d+)*\b", " ", s)
    s = re.sub(r"\b(demo|full|beta|alpha|release|update|final|port|remake|"
               r"remaster|redux|edition|version|ver)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def extract_tokens(name):
    if not name: return set()
    s = name.lower()
    s = re.sub(r"\bv?\d+(\.\d+)*\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    stop = {"the", "a", "of", "and", "vs", "fnf", "funkin", "friday",
            "night", "week", "mod", "demo", "full", "beta", "v", "ver", "exe"}
    return {t for t in s.split() if t and t not in stop and len(t) > 1}


# ========== LOCAL WEB SERVER ==========

def _find_index_html():
    """Locate index.html next to app.py, in web/, or in cwd."""
    here = Path(__file__).parent.resolve()
    candidates = [
        here / "index.html",
        here / "web" / "index.html",
        Path.cwd() / "index.html",
        Path.cwd() / "web" / "index.html",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _free_port(start=WEB_PORT_DEFAULT, tries=20):
    for p in range(start, start + tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", p))
                return p
        except OSError:
            continue
    raise OSError("No free port available")


def serve_web(port=None, open_browser=True, silent=False):
    """Serve index.html on localhost + proxy /api/* to GameBanana.
    Returns (httpd, url). Safe to call repeatedly — reuses the running server."""
    global _web_server
    if _web_server is not None:
        url = getattr(_web_server, "_ff_url", "")
        if open_browser and url:
            webbrowser.open(url)
        return _web_server, url

    index_path = _find_index_html()
    if index_path is None:
        msg = ("index.html not found.\n\n"
               "Put index.html in the same folder as app.py, or in a "
               "'web/' subfolder next to it.")
        if not silent:
            try:
                _r = tk.Tk(); _r.withdraw()
                messagebox.showerror("FunkForge - Web", msg)
                _r.destroy()
            except Exception:
                print("[FunkForge] " + msg)
        raise FileNotFoundError(msg)

    root = index_path.parent
    if port is None:
        port = _free_port()

    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

        def end_headers(self):
            # Let the browser call us from any origin (needed for CORS proxy)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            super().end_headers()

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()

        def do_GET(self):
            # /api/<path> → proxy to GameBanana v11
            if self.path.startswith("/api/"):
                return self._proxy_gamebanana()
            return super().do_GET()

        def _proxy_gamebanana(self):
            target = "https://gamebanana.com/apiv11/" + self.path[5:]
            try:
                r = requests.get(
                    target,
                    headers={"User-Agent": f"FunkForge/{VERSION}",
                             "Accept": "application/json"},
                    timeout=25)
                self.send_response(r.status_code)
                self.send_header("Content-Type",
                                 r.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(r.content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(r.content)
            except Exception as e:
                body = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

    handler = functools.partial(_QuietHandler, directory=str(root))

    class _Reusable(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    httpd = _Reusable(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/{index_path.name}"
    try: httpd._ff_url = url
    except Exception: pass

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    _web_server = httpd

    if not silent:
        print(f"[FunkForge] Web version running at {url}")
        print(f"[FunkForge] API proxy at http://127.0.0.1:{port}/api/")
    if open_browser:
        webbrowser.open(url)
    return httpd, url


def stop_web():
    global _web_server
    if _web_server is not None:
        try: _web_server.shutdown()
        except Exception: pass
        try: _web_server.server_close()
        except Exception: pass
        _web_server = None


# ========== OS NOTIFICATIONS ==========

def _win_notify(title, message):
    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
    xml = ('<toast><visual><binding template="ToastGeneric">'
           f"<text>{esc(title)}</text><text>{esc(message)}</text>"
           "</binding></visual></toast>").replace("'", "''")
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager, "
        "Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, "
        "ContentType = WindowsRuntime] | Out-Null\n"
        "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
        f"$xml.LoadXml('{xml}')\n"
        "$toast = New-Object Windows.UI.Notifications.ToastNotification $xml\n"
        "[Windows.UI.Notifications.ToastNotificationManager]::"
        "CreateToastNotifier('FunkForge').Show($toast)\n")
    enc = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive",
                         "-WindowStyle", "Hidden", "-EncodedCommand", enc],
                         creationflags=0x08000000 if sys.platform.startswith("win") else 0,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL)
    except Exception:
        pass


def _mac_notify(title, message):
    try:
        subprocess.Popen(["osascript", "-e",
                         f'display notification {json.dumps(message)} '
                         f'with title {json.dumps(title)}'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _linux_notify(title, message):
    for cmd in (["notify-send", "-a", "FunkForge", "-u", "normal", "-t", "5000",
                 title, message],
                ["kdialog", "--passivepopup", message, "5", "--title", title]):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue
        except Exception:
            pass


def os_notify(title, message):
    try:
        if sys.platform.startswith("win"):
            threading.Thread(target=_win_notify, args=(title, message), daemon=True).start()
        elif sys.platform == "darwin":
            threading.Thread(target=_mac_notify, args=(title, message), daemon=True).start()
        else:
            threading.Thread(target=_linux_notify, args=(title, message), daemon=True).start()
    except Exception:
        pass



# ========== PREMIUM WIDGETS ==========

def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(c1, c2, t):
    """Blend two #rrggbb colours (t=0 -> c1, t=1 -> c2)."""
    try:
        a, b = _hex_rgb(c1), _hex_rgb(c2)
        return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    except Exception:
        return c1


def _parent_bg(w, fallback="#171922"):
    try:
        return w.cget("background")
    except Exception:
        pass
    try:
        st = str(w.cget("style")) or w.winfo_class()
        c = ttk.Style().lookup(st, "background")
        if c:
            return c
    except Exception:
        pass
    return fallback


class FButton(tk.Canvas):
    """Rounded, animated drop-in replacement for tk.Button."""

    def __init__(self, master, text="", command=None, background=None,
                 foreground=None, activebackground=None, activeforeground=None,
                 padx=12, pady=6, cursor="hand2", font=None, radius=9, **_ignored):
        self._text = text; self._cmd = command
        self._bg = background or "#2b2d31"; self._fg = foreground or "#ffffff"
        self._abg = activebackground; self._afg = activeforeground or self._fg
        self._padx, self._pady, self._radius = padx, pady, radius
        try:
            self._font = tkfont.Font(font=font) if font else tkfont.nametofont("TkDefaultFont")
        except Exception:
            self._font = tkfont.nametofont("TkDefaultFont")
        super().__init__(master, highlightthickness=0, borderwidth=0,
                         cursor=cursor, background=_parent_bg(master))
        self._cur = self._bg; self._job = None
        self._hover = False; self._down = False
        self._resize()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _resize(self):
        self._bw = self._font.measure(self._text) + 2 * self._padx + 6
        self._bw = max(self._bw, getattr(self, "_minw", 0))
        self._bh = self._font.metrics("linespace") + 2 * self._pady
        tk.Canvas.configure(self, width=self._bw, height=self._bh)
        self._draw(self._cur)

    def _draw(self, color):
        try:
            self.delete("all")
            w, h = self._bw, self._bh
            r = min(self._radius, h // 2)
            pts = [r, 0, w - r, 0, w, 0, w, r, w, h - r, w, h, w - r, h,
                   r, h, 0, h, 0, h - r, 0, r, 0, 0]
            self.create_polygon(pts, smooth=True, fill=color, outline=color)
            self.create_text(w / 2, h / 2 + (1 if self._down else 0),
                             text=self._text, font=self._font,
                             fill=self._afg if self._hover else self._fg)
        except tk.TclError:
            pass

    def _hover_color(self):
        try:
            b = _hex_rgb(self._bg)
            if self._abg:
                a = _hex_rgb(self._abg)
                if sum(abs(a[i] - b[i]) for i in range(3)) >= 24:
                    return self._abg
            dark = sum(b) / 3 < 150
            return _mix(self._bg, "#ffffff" if dark else "#000000",
                        0.14 if dark else 0.08)
        except Exception:
            return self._bg

    def _fade_to(self, target, steps=6):
        if self._job:
            try: self.after_cancel(self._job)
            except Exception: pass
        start = self._cur

        def step(i=1):
            try:
                self._cur = _mix(start, target, i / steps)
                self._draw(self._cur)
                self._job = self.after(14, lambda: step(i + 1)) if i < steps else None
            except tk.TclError:
                self._job = None
        step()

    def _on_enter(self, _e):
        self._hover = True; self._fade_to(self._hover_color())

    def _on_leave(self, _e):
        self._hover = False; self._down = False; self._fade_to(self._bg)

    def _on_press(self, _e):
        self._down = True; self._draw(_mix(self._hover_color(), "#000000", 0.18))

    def _on_release(self, e):
        was = self._down; self._down = False
        self._draw(self._cur)
        if was and 0 <= e.x <= self._bw and 0 <= e.y <= self._bh:
            self.invoke()

    def invoke(self):
        if self._cmd:
            self._cmd()

    def configure(self, cnf=None, **kw):
        if cnf: kw.update(cnf)
        remap = {"background": "_bg", "foreground": "_fg",
                 "activebackground": "_abg", "activeforeground": "_afg",
                 "command": "_cmd"}
        redraw = False
        if "parent_bg" in kw:
            tk.Canvas.configure(self, background=kw.pop("parent_bg"))
        for k in list(kw):
            if k in remap:
                setattr(self, remap[k], kw.pop(k)); redraw = True
            elif k == "text":
                self._text = kw.pop(k); redraw = True
            elif k == "state":
                kw.pop(k)
        if kw:
            tk.Canvas.configure(self, **kw)
        if redraw:
            self._cur = self._bg; self._resize()
    config = configure


class ToggleSwitch(tk.Canvas):
    """Animated pill switch bound to a tk.BooleanVar."""

    def __init__(self, master, variable, command=None, theme=None, bg=None,
                 width=44, height=24):
        self._t = theme or THEMES["dark"]
        self._var = variable; self._cmd = command
        self._bw, self._bh = width, height
        super().__init__(master, width=width, height=height, highlightthickness=0,
                         borderwidth=0, cursor="hand2", takefocus=1,
                         background=bg or _parent_bg(master))
        self._pos = 1.0 if variable.get() else 0.0
        self._job = None
        self._draw()
        self.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<space>", lambda e: self.toggle())
        self._trace = variable.trace_add("write", self._on_var)
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, e):
        if e.widget is self:
            try: self._var.trace_remove("write", self._trace)
            except Exception: pass

    def set_theme(self, theme, bg=None):
        self._t = theme
        try:
            tk.Canvas.configure(self, background=bg or _parent_bg(self.master))
        except tk.TclError:
            pass
        self._draw()

    def toggle(self):
        self._var.set(not self._var.get())
        if self._cmd:
            self._cmd()

    def _on_var(self, *_):
        if self._job is None:
            self._animate()

    def _animate(self):
        target = 1.0 if self._var.get() else 0.0
        try:
            self._pos += (target - self._pos) * 0.38
            if abs(target - self._pos) < 0.02:
                self._pos = target; self._job = None
            else:
                self._job = self.after(14, self._animate)
            self._draw()
        except tk.TclError:
            self._job = None

    def _draw(self):
        try:
            self.delete("all")
            w, h, t = self._bw, self._bh, self._t
            off = _mix(t["border"], t["subtle"], 0.35)
            col = _mix(off, t["accent"], self._pos)
            self.create_oval(0, 0, h, h, fill=col, outline=col)
            self.create_oval(w - h, 0, w, h, fill=col, outline=col)
            self.create_rectangle(h / 2, 0, w - h / 2, h, fill=col, outline=col)
            r = (h - 8) / 2
            cx = h / 2 + self._pos * (w - h)
            cy = h / 2
            self.create_oval(cx - r, cy - r + 1, cx + r, cy + r + 1,
                             fill=_mix(col, "#000000", 0.35), outline="")
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill="#ffffff", outline="")
        except tk.TclError:
            pass



def _rrect(c, x0, y0, x1, y1, r, fill):
    r = min(r, (y1 - y0) / 2, (x1 - x0) / 2)
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, fill=fill, outline=fill)


class PillSelect(FButton):
    """Modern dropdown pill with a floating, themed option list."""

    def __init__(self, master, variable, values=(), theme=None, font_family="Segoe UI",
                 on_change=None, prefix=""):
        self._var = variable; self._values = list(values)
        self._on_change = on_change; self._prefix = prefix
        self._pt = theme or THEMES["dark"]; self._ff = font_family
        self._top = None; self._minw = 0
        t = self._pt
        super().__init__(master, text=self._label(), command=self._open,
                         background=t["panel2"], foreground=t["fg"],
                         activebackground=t["hover"], activeforeground=t["fg"],
                         padx=14, pady=6, font=(font_family, 9, "bold"), radius=12)
        self._fit()
        variable.trace_add("write", lambda *a: self._refresh())
        self.winfo_toplevel().bind("<Button-1>", self._outside, add="+")
        self.winfo_toplevel().bind("<Configure>", self._root_moved, add="+")

    def _label(self):
        return f"{self._prefix}  {self._var.get()}  ▾".strip()

    def _fit(self):
        widths = []
        for v in (self._values or [self._var.get()]):
            widths.append(self._font.measure(f"{self._prefix}  {v}  ▾") + 2 * self._padx + 6)
        self._minw = max(widths)
        self._resize()

    def _refresh(self):
        try: FButton.configure(self, text=self._label())
        except Exception: pass

    def configure(self, cnf=None, **kw):
        if "values" in kw:
            self._values = list(kw.pop("values")); self._fit()
        if kw or cnf:
            FButton.configure(self, cnf, **kw)
    config = configure

    def set_theme(self, t, bg):
        self._pt = t
        FButton.configure(self, background=t["panel2"], foreground=t["fg"],
                          activebackground=t["hover"], activeforeground=t["fg"],
                          parent_bg=bg)

    def _outside(self, e):
        if self._top is None or e.widget is self:
            return
        if str(e.widget).startswith(str(self._top)):
            return
        self._close()

    def _close(self):
        if self._top is not None:
            try: self._top.destroy()
            except Exception: pass
            self._top = None

    def _choose(self, v):
        self._close()
        if v != self._var.get():
            self._var.set(v)
            if self._on_change:
                self._on_change()

    def _paint(self, hi):
        t = self._pt
        self._hi = hi
        for i, (row, mark, txt, active) in enumerate(self._rows):
            over = i == hi
            if active:
                bg = _mix(t["select"], "#ffffff", 0.07) if over else t["select"]
                fg = t["accent"]
            else:
                bg = t["hover"] if over else t["panel"]
                fg = t["fg"]
            for w in (row, mark, txt):
                w.configure(background=bg)
            mark.configure(foreground=t["accent"])
            txt.configure(foreground=fg)

    def _key_move(self, d):
        n = len(self._rows)
        if not n: return
        start = self._hi if self._hi is not None else (
            self._values.index(self._var.get()) if self._var.get() in self._values else -1)
        self._paint((start + d) % n)

    def _key_pick(self):
        if self._hi is not None:
            self._choose(self._values[self._hi])

    def _root_moved(self, e):
        if self._top is not None and e.widget is self.winfo_toplevel():
            self._close()

    def _open(self):
        if self._top is not None:
            self._close(); return
        t = self._pt
        top = tk.Toplevel(self)
        top.overrideredirect(True)
        try: top.attributes("-topmost", True)
        except Exception: pass
        top.configure(background=t["border"])
        inner = tk.Frame(top, background=t["panel"])
        inner.pack(padx=1, pady=1)
        cur = self._var.get()
        wide = max(self.winfo_width(),
                   max(self._font.measure(v) for v in self._values) + 84)
        tk.Frame(inner, width=wide, height=1, background=t["panel"]).pack()
        self._rows = []; self._hi = None
        last = len(self._values) - 1
        for i, v in enumerate(self._values):
            row = tk.Frame(inner, cursor="hand2")
            row.pack(fill="x", padx=4, pady=(4 if i == 0 else 1, 4 if i == last else 1))
            mark = tk.Label(row, text="✓" if v == cur else "", width=2,
                            font=(self._ff, 9, "bold"))
            mark.pack(side="left", padx=(8, 0))
            txt = tk.Label(row, text=v, anchor="w", pady=6, padx=6,
                           font=(self._ff, 9, "bold" if v == cur else "normal"))
            txt.pack(side="left", fill="x", expand=True, padx=(0, 16))
            for w in (row, mark, txt):
                w.bind("<Enter>", lambda e, k=i: self._paint(k))
                w.bind("<Button-1>", lambda e, val=v: self._choose(val))
            self._rows.append((row, mark, txt, v == cur))
        self._paint(None)
        top.bind("<Leave>", lambda e: self._paint(None) if e.widget is top else None)
        top.bind("<Escape>", lambda e: self._close())
        top.bind("<Up>", lambda e: self._key_move(-1))
        top.bind("<Down>", lambda e: self._key_move(1))
        top.bind("<Return>", lambda e: self._key_pick())
        top.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 6
        if y + top.winfo_reqheight() > self.winfo_screenheight() - 40:
            y = max(0, self.winfo_rooty() - top.winfo_reqheight() - 6)
        top.geometry(f"+{x}+{y}")
        self._top = top
        try: top.focus_force()
        except Exception: pass

class SegmentedControl(tk.Canvas):
    """Compact segmented switch (e.g. List / Grid)."""

    def __init__(self, master, options, value, command, theme, font_family="Segoe UI"):
        self._opts = list(options); self._val = value; self._cmd = command
        self._st = theme
        self._font = tkfont.Font(font=(font_family, 9, "bold"))
        self._segs = [self._font.measure(l) + 30 for _, l in self._opts]
        self._tw = sum(self._segs) + 8
        self._th = self._font.metrics("linespace") + 12 + 8
        super().__init__(master, width=self._tw, height=self._th, highlightthickness=0,
                         borderwidth=0, cursor="hand2", background=_parent_bg(master))
        self.bind("<Button-1>", self._click)
        self._draw()

    def set_theme(self, t, bg):
        self._st = t
        tk.Canvas.configure(self, background=bg)
        self._draw()

    def set(self, value):
        if value != self._val:
            self._val = value; self._draw()

    def _click(self, e):
        x = 4
        for (key, _), w in zip(self._opts, self._segs):
            if x <= e.x <= x + w:
                if key != self._val:
                    self._val = key; self._draw()
                    if self._cmd: self._cmd(key)
                return
            x += w

    def _draw(self):
        try:
            self.delete("all")
            t = self._st
            _rrect(self, 0, 0, self._tw, self._th, 13, t["panel2"])
            x = 4
            for (key, label), w in zip(self._opts, self._segs):
                on = key == self._val
                if on:
                    _rrect(self, x, 4, x + w, self._th - 4, 10, t["accent"])
                self.create_text(x + w / 2, self._th / 2, text=label, font=self._font,
                                 fill=t["accent_fg"] if on else t["subtle"])
                x += w
        except tk.TclError:
            pass


def toggle_row(parent, text, var, command, t, font_family, subtitle=None):
    row = tk.Frame(parent, background=t["panel"])
    row.pack(fill="x", padx=16, pady=6)
    box = tk.Frame(row, background=t["panel"])
    box.pack(side="left", fill="x", expand=True)
    lbl = tk.Label(box, text=text, background=t["panel"], foreground=t["fg"],
                   font=(font_family, 10), anchor="w", cursor="hand2")
    lbl.pack(anchor="w")
    if subtitle:
        tk.Label(box, text=subtitle, background=t["panel"],
                 foreground=t["subtle"], font=(font_family, 8),
                 anchor="w").pack(anchor="w")
    sw = ToggleSwitch(row, var, command=command, theme=t, bg=t["panel"])
    sw.pack(side="right")
    lbl.bind("<Button-1>", lambda e: sw.toggle())
    return sw


# ========== GAMEBANANA API ==========

_TLS = threading.local()


def gb_session():
    s = getattr(_TLS, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update(HEADERS)
        s.headers["Accept"] = "application/json"
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            retry = Retry(total=3, backoff_factor=0.6,
                          status_forcelist=(429, 500, 502, 503, 504),
                          allowed_methods=frozenset(["GET"]),
                          respect_retry_after_header=True)
            s.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=8,
                                            pool_maxsize=8))
        except Exception:
            pass
        _TLS.s = s
    return s


def gb_get(path, params=None, timeout=15, tries=2):
    """GET a GameBanana v11 endpoint -> parsed JSON, or None on failure."""
    url = f"{GB_API}/{path.lstrip('/')}"
    for attempt in range(tries):
        try:
            r = gb_session().get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and data.get("_sErrorCode"):
                    print(f"[FunkForge] API error on {path}: "
                          f"{data.get('_sErrorCode')} {data.get('_sErrorMessage', '')}")
                    return None
                return data
            if r.status_code < 500 and r.status_code != 429:
                print(f"[FunkForge] {path} -> HTTP {r.status_code}")
                return None
        except Exception as e:
            print(f"[FunkForge] {path} failed: {e}")
        time.sleep(0.5 * (attempt + 1))
    return None


def gb_records(data, per_page):
    """(records, has_more) from any v11 list response."""
    if data is None:
        return [], False
    if isinstance(data, list):
        return data, len(data) >= per_page
    recs = data.get("_aRecords") or []
    meta = data.get("_aMetadata") or {}
    more = (not meta["_bIsComplete"]) if "_bIsComplete" in meta else len(recs) >= per_page
    return recs, bool(recs) and more


def gb_page_url(model, rid):
    slug = MODEL_SLUGS.get(model) or (str(model).lower() + "s")
    return f"https://gamebanana.com/{slug}/{rid}"


def gb_page_url_rec(rec):
    return rec.get("_sProfileUrl") or gb_page_url(rec.get("_sModelName") or "Mod",
                                                   rec.get("_idRow"))


def rec_uid(r):
    return r.get("_uid") or r.get("_idRow")


def is_fnf_record(rec):
    g = rec.get("_aGame")
    if isinstance(g, dict):
        gid = g.get("_idRow")
        if gid is not None and str(gid) != str(FNF_GAME_ID):
            return False
    return True


def normalize_record(rec, model="Mod"):
    if not isinstance(rec, dict) or rec.get("_idRow") is None:
        return None
    if not is_fnf_record(rec):
        return None
    m = rec.get("_sModelName") or model
    rec["_sModelName"] = m
    rec["_uid"] = f"{m}:{rec['_idRow']}"
    if not rec.get("_sProfileUrl"):
        rec["_sProfileUrl"] = gb_page_url(m, rec["_idRow"])
    return rec


def query_tokens(q):
    return re.findall(r"[\w']+", (q or "").lower())


def gb_search(query, page, per_page, models=SEARCH_MODELS):
    """Search everything FNF-modding related (mods, tools, sounds) in parallel.
    Returns (records, has_more)."""
    results = {}

    def work(model):
        base = {"_sModelName": model, "_sSearchString": query,
                "_idGameRow": FNF_GAME_ID, "_nPerpage": per_page, "_nPage": page}
        data = gb_get("Util/Search/Results", dict(base, _sOrder="best_match"))
        if data is None:  # some servers reject _sOrder -> retry plain
            data = gb_get("Util/Search/Results", base)
        recs, more = gb_records(data, per_page)
        for r in recs:
            if isinstance(r, dict):
                r.setdefault("_sModelName", model)
        results[model] = (recs, more)

    threads = [threading.Thread(target=work, args=(m,), daemon=True) for m in models]
    for th in threads: th.start()
    for th in threads: th.join(timeout=30)
    # Fallback: model-less search if every typed search came back empty
    if not any(results.get(m, ([], False))[0] for m in models):
        data = gb_get("Util/Search/Results",
                      {"_sSearchString": query, "_idGameRow": FNF_GAME_ID,
                       "_nPerpage": per_page, "_nPage": page})
        recs, more = gb_records(data, per_page)
        recs = [r for r in recs if (r.get("_sModelName") or "Mod") in models]
        results = {"Mod": (recs, more)}
    from itertools import zip_longest
    ordered = [results.get(m, ([], False))[0] for m in models if m in results]
    merged, seen = [], set()
    for group in zip_longest(*ordered):
        for r in group:
            if r is None: continue
            k = (r.get("_sModelName") or "Mod", r.get("_idRow"))
            if k in seen: continue
            seen.add(k); merged.append(r)
    more = any(v[1] for v in results.values())
    return merged, more


def gb_subfeed_search(query, per_page=50, max_pages=4):
    """Last-resort search: scan the FNF feed and filter client-side."""
    toks = query_tokens(query)
    out = []
    for p in range(1, max_pages + 1):
        data = gb_get(f"Game/{FNF_GAME_ID}/Subfeed",
                      {"_nPage": p, "_nPerpage": per_page, "_sSort": "default"})
        recs, more = gb_records(data, per_page)
        for r in recs:
            if (r.get("_sModelName") or "Mod") not in SEARCH_MODELS:
                continue
            hay = ((r.get("_sName") or "") + " " +
                   ((r.get("_aSubmitter") or {}).get("_sName") or "")).lower()
            if all(t in hay for t in toks):
                out.append(r)
        if not more:
            break
    return out


def gb_browse(page, popular=False):
    """Browse FNF mods. popular=True -> most downloaded first.
    The normal feed (popular=False) keeps every mod, remakes included.
    Returns (records, has_more)."""
    sort = "Generic_MostDownloaded" if popular else "default"
    data = gb_get("Mod/Index", {"_nPerpage": PER_PAGE, "_nPage": page,
                                "_aFilters[Generic_Game]": FNF_GAME_ID,
                                "_sSort": sort}, timeout=20)
    recs, more = gb_records(data, PER_PAGE)
    if not recs and popular:  # sort key rejected -> plain feed, ranked locally
        data = gb_get("Mod/Index", {"_nPerpage": PER_PAGE, "_nPage": page,
                                    "_aFilters[Generic_Game]": FNF_GAME_ID,
                                    "_sSort": "default"}, timeout=20)
        recs, more = gb_records(data, PER_PAGE)
    if not recs:
        data = gb_get(f"Game/{FNF_GAME_ID}/Subfeed",
                      {"_nPage": page, "_nPerpage": PER_PAGE, "_sSort": "default"},
                      timeout=20)
        recs, more = gb_records(data, PER_PAGE)
        recs = [r for r in recs if (r.get("_sModelName") or "Mod") == "Mod"]
    if popular:
        recs = sorted(recs, key=lambda r: r.get("_nDownloadCount") or 0, reverse=True)
    return recs, more


# ========== OFFICIAL GAME AUTO-DETECT ==========

OFFICIAL_EXE_NAMES = {"funkin.exe", "friday night funkin.exe", "funkin",
                      "funkin.x86_64", "friday night funkin"}
ENGINE_EXE_NAMES = {"psychengine.exe", "psych engine.exe", "kade.exe",
                    "kade engine.exe", "codename.exe", "codenameengine.exe"}
_SKIP_DIRS = {"node_modules", "appdata", "windows", "$recycle.bin", "system32",
              "__pycache__", "site-packages", "cache", "temp", "tmp"}


def _steam_common_dirs():
    out = []
    bases = [Path("C:/Program Files (x86)/Steam"), Path("C:/Program Files/Steam"),
             Path.home() / ".steam/steam", Path.home() / ".local/share/Steam",
             Path.home() / "Library/Application Support/Steam"]
    for b in bases:
        if not b.exists():
            continue
        out.append(b / "steamapps" / "common")
        try:
            text = (b / "steamapps" / "libraryfolders.vdf").read_text(errors="ignore")
            for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                out.append(Path(m.group(1).replace("\\\\", "\\")) / "steamapps" / "common")
        except Exception:
            pass
    for d in "CDEFG":
        out.append(Path(f"{d}:/SteamLibrary/steamapps/common"))
    return out


def find_official_game(max_seconds=8.0):
    """Look for the official Friday Night Funkin' executable.
    Returns (path, is_official) or (None, False). Falls back to a known
    engine build only if the official game can't be found."""
    deadline = time.time() + max_seconds
    home = Path.home()
    itch = [Path(os.environ.get("APPDATA", str(home))) / "itch" / "apps",
            home / ".config/itch/apps", home / "Library/Application Support/itch/apps"]
    named = ("Friday Night Funkin", "Friday Night Funkin'", "Funkin", "funkin", "FNF")
    priority = _steam_common_dirs() + itch

    def scan(d, names):
        try:
            for p in d.iterdir():
                if p.is_file() and p.name.lower() in names:
                    return p
        except Exception:
            pass
        return None

    for root in priority:
        if not root.exists():
            continue
        for sub in named:
            hit = scan(root / sub, OFFICIAL_EXE_NAMES)
            if hit: return hit, True
        for base, dirs, files in os.walk(root):
            if time.time() > deadline: break
            if len(Path(base).parts) - len(root.parts) >= 3:
                dirs[:] = []
            for fn in files:
                if fn.lower() in OFFICIAL_EXE_NAMES:
                    return Path(base) / fn, True
    fallback = None
    walk_roots = [home / "Desktop", home / "Downloads", home / "Games",
                  Path("C:/Games"), Path("C:/Program Files"),
                  Path("C:/Program Files (x86)"), Path("D:/Games"), home]
    for root in walk_roots:
        if not root.exists():
            continue
        base_depth = len(root.parts)
        for base, dirs, files in os.walk(root):
            if time.time() > deadline:
                return (fallback, False) if fallback else (None, False)
            depth = len(Path(base).parts) - base_depth
            dirs[:] = ([] if depth >= 3 else
                       [d for d in dirs if not d.startswith(".")
                        and d.lower() not in _SKIP_DIRS])
            for fn in files:
                low = fn.lower()
                if low in OFFICIAL_EXE_NAMES:
                    return Path(base) / fn, True
                if low in ENGINE_EXE_NAMES and fallback is None:
                    fallback = Path(base) / fn
    return (fallback, False) if fallback else (None, False)


# ========== ICON ==========

def make_icon(size=64, rotation=0.0):
    s = size
    base = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.22),
                        fill=(88, 101, 242, 255))
    d.rounded_rectangle((0, 0, s - 1, int(s * 0.5)), radius=int(s * 0.22),
                        fill=(114, 127, 255, 255))
    d.rectangle((0, int(s * 0.4), s - 1, int(s * 0.5)), fill=(101, 114, 248, 255))
    white = (255, 255, 255, 255)
    hx, hy = int(s * 0.22), int(s * 0.60)
    hw, hh = int(s * 0.30), int(s * 0.22)
    d.ellipse((hx, hy, hx + hw, hy + hh), fill=white)
    sx = hx + hw - int(s * 0.055)
    sy_top = int(s * 0.18)
    sy_bot = hy + hh // 2
    d.rectangle((sx, sy_top, sx + int(s * 0.06), sy_bot), fill=white)
    d.polygon([(sx + int(s * 0.06), sy_top),
               (sx + int(s * 0.30), sy_top + int(s * 0.05)),
               (sx + int(s * 0.27), sy_top + int(s * 0.17)),
               (sx + int(s * 0.06), sy_top + int(s * 0.13))], fill=white)
    if rotation:
        base = base.rotate(rotation, resample=Image.BICUBIC, expand=False)
    return base


# ========== LOADING SPINNER ==========

class LoadingSpinner:
    def __init__(self, label, bg_color="#111214", fg_color="#5865f2",
                 size=70, interval=60):
        self.label = label; self.fg = fg_color; self.size = size
        self.interval = interval; self.angle = 0; self.running = False
        self._ref = None
        try: self._bg = self.label.cget("background")
        except Exception: self._bg = bg_color

    def start(self):
        if self.running: return
        self.running = True; self._spin()

    def stop(self): self.running = False

    def _spin(self):
        if not self.running: return
        try:
            if not self.label.winfo_exists():
                self.running = False; return
            s = self.size
            img = Image.new("RGB", (s, s), self._bg)
            d = ImageDraw.Draw(img)
            cx, cy = s // 2, s // 2
            r = s // 2 - 6
            d.ellipse((cx - r, cy - r, cx + r, cy + r),
                      outline=(120, 120, 130), width=4)
            d.arc((cx - r, cy - r, cx + r, cy + r),
                  self.angle, self.angle + 90, fill=self.fg, width=4)
            tkimg = ImageTk.PhotoImage(img)
            self.label.configure(image=tkimg, text="")
            self._ref = tkimg
            self.angle = (self.angle + 20) % 360
            self.label.after(self.interval, self._spin)
        except tk.TclError:
            self.running = False


# ========== SEARCH SUGGESTIONS ==========

class SearchSuggestions(tk.Toplevel):
    """Dropdown showing related search suggestions."""
    def __init__(self, app, entry):
        super().__init__(app)
        self.app = app; self.entry = entry
        self.overrideredirect(True)
        try: self.attributes("-topmost", False)
        except tk.TclError: pass
        self.withdraw()
        self._req_id = 0; self._last_query = ""; self._items = []
        t = THEMES[app.theme]
        self.configure(background=t["panel"])
        self.inner = tk.Frame(self, background=t["panel"],
                              highlightbackground=t["border"], highlightthickness=1)
        self.inner.pack(fill="both", expand=True)
        self.header = tk.Label(self.inner, text="RELATED SUGGESTIONS",
                               background=t["panel"], foreground=t["subtle"],
                               font=(app.font_family, 8, "bold"), anchor="w")
        self.header.pack(fill="x", padx=14, pady=(10, 4))
        self.items_frame = tk.Frame(self.inner, background=t["panel"])
        self.items_frame.pack(fill="both", expand=True, pady=(0, 8))
        self.bind("<Escape>", lambda e: self.hide())

    def show(self, query):
        if not query or len(query) < 2:
            self.hide(); return
        if query == self._last_query: return
        self._last_query = query
        job = getattr(self, "_deb", None)
        if job:
            try: self.after_cancel(job)
            except Exception: pass
        self._deb = self.after(260, lambda q=query: self._kick(q))

    def _kick(self, query):
        self._req_id += 1
        rid = self._req_id
        threading.Thread(target=self._fetch, args=(query, rid), daemon=True).start()

    def _fetch(self, query, rid):
        names, seen = [], set()

        def add(recs):
            for rec in recs:
                n = (rec.get("_sName") or "").strip()
                if n and n.lower() not in seen:
                    seen.add(n.lower()); names.append(n)

        try:
            recs, _ = gb_search(query, 1, 10, ("Mod", "Tool"))
            add(recs)
        except Exception:
            pass
        if len(names) < 3:
            try: add(gb_subfeed_search(query, max_pages=2))
            except Exception: pass
        if rid == self._req_id and names:
            self.after(0, lambda n=names[:8]: self._show_items(n))

    def _show_items(self, names):
        if not names:
            self.hide(); return
        t = THEMES[self.app.theme]
        for w in self.items_frame.winfo_children():
            w.destroy()
        self._items = names
        for name in self._items:
            row = tk.Frame(self.items_frame, background=t["panel"], cursor="hand2")
            row.pack(fill="x")
            lbl = tk.Label(row, text=f"🔍  {name}", background=t["panel"],
                           foreground=t["fg"], font=(self.app.font_family, 9),
                           anchor="w", padx=14, pady=6)
            lbl.pack(fill="x")
            def on_enter(_e, r=row, l=lbl, tt=t):
                r.configure(background=tt["select"]); l.configure(background=tt["select"])
            def on_leave(_e, r=row, l=lbl, tt=t):
                r.configure(background=tt["panel"]); l.configure(background=tt["panel"])
            def on_click(_e, n=name): self._pick(n)
            for w in (row, lbl):
                w.bind("<Enter>", on_enter); w.bind("<Leave>", on_leave)
                w.bind("<Button-1>", on_click)
        self._position()
        try: self.deiconify(); self.lift()
        except Exception: pass

    def _pick(self, name):
        self.hide()
        self.app.query.set(name)
        self.app.do_search()

    def _position(self):
        try:
            self.update_idletasks()
            e = self.entry
            x = e.winfo_rootx()
            y = e.winfo_rooty() + e.winfo_height() + 2
            w = max(e.winfo_width(), 340)
            h = self.winfo_reqheight()
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception: pass

    def hide(self):
        self._last_query = ""
        try: self.withdraw()
        except Exception: pass

    def update_theme(self):
        t = THEMES[self.app.theme]
        try:
            self.configure(background=t["panel"])
            self.inner.configure(background=t["panel"],
                                 highlightbackground=t["border"])
            self.header.configure(background=t["panel"], foreground=t["subtle"])
            self.items_frame.configure(background=t["panel"])
        except Exception: pass


# ========== SPLASH ==========

class SplashScreen(tk.Toplevel):
    def __init__(self, parent, on_done, duration_ms=1200):
        super().__init__(parent)
        self.parent = parent; self.on_done = on_done
        self.duration_ms = duration_ms
        self.t = parent.theme_obj
        self.start_ts = time.time(); self.angle = 0
        self.overrideredirect(True)
        try: self.attributes("-topmost", True)
        except tk.TclError: pass
        self.configure(background=self.t["bg"])
        w, h = 460, 320
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.frame = tk.Frame(self, background=self.t["panel"],
                              highlightbackground=self.t["accent"],
                              highlightthickness=2)
        self.frame.pack(fill="both", expand=True, padx=2, pady=2)
        self.icon_label = tk.Label(self.frame, background=self.t["panel"])
        self.icon_label.pack(pady=(50, 18))
        tk.Label(self.frame, text="FunkForge", background=self.t["panel"],
                 foreground=self.t["fg"],
                 font=(parent.font_family, 24, "bold")).pack()
        tk.Label(self.frame, text="FNF Mod Browser & Manager",
                 background=self.t["panel"], foreground=self.t["subtle"],
                 font=(parent.font_family, 10)).pack(pady=(2, 24))
        self.bar_canvas = tk.Canvas(self.frame, height=6, highlightthickness=0,
                                    background=self.t["panel"], borderwidth=0)
        self.bar_canvas.pack(fill="x", padx=60)
        self._bar_bg = self.bar_canvas.create_rectangle(0, 0, 0, 6,
                                                        fill=self.t["border"], outline="")
        self._bar_fg = self.bar_canvas.create_rectangle(0, 0, 0, 6,
                                                        fill=self.t["accent"], outline="")
        self.status_lbl = tk.Label(self.frame, text="Starting…",
                                   background=self.t["panel"],
                                   foreground=self.t["subtle"],
                                   font=(parent.font_family, 9))
        self.status_lbl.pack(pady=(10, 4))
        self.bar_canvas.bind("<Configure>", self._resize_bar)
        try: self.attributes("-alpha", 0.0)
        except tk.TclError: pass
        self._anim()

    def _resize_bar(self, _e):
        w = self.bar_canvas.winfo_width()
        self.bar_canvas.coords(self._bar_bg, 0, 0, w, 6)

    def _anim(self):
        elapsed = (time.time() - self.start_ts) * 1000
        progress = min(1.0, elapsed / self.duration_ms)
        self.angle = (self.angle + 5) % 360
        img = make_icon(96, rotation=self.angle)
        tkimg = ImageTk.PhotoImage(img)
        self.icon_label.configure(image=tkimg); self.icon_label.image = tkimg
        w = max(self.bar_canvas.winfo_width(), 1)
        self.bar_canvas.coords(self._bar_fg, 0, 0, int(w * progress), 6)
        txt = ("Loading…" if progress < 0.3 else
               "Preparing interface…" if progress < 0.7 else "Ready!")
        self.status_lbl.configure(text=txt)
        if progress < 0.3:
            try: self.attributes("-alpha", progress / 0.3)
            except tk.TclError: pass
        if progress >= 1.0:
            self._finish(); return
        self.after(33, self._anim)

    def _finish(self):
        try: self.destroy()
        except Exception: pass
        try: self.on_done()
        except Exception: traceback.print_exc()


# ========== SETTINGS ==========

class SettingsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Settings"); self.resizable(False, False); self.transient(app)
        t = THEMES[app.theme]
        self.configure(background=t["bg"])
        tk.Label(self, text="Settings", background=t["bg"], foreground=t["fg"],
                 font=(app.font_family, 14, "bold")).pack(anchor="w", padx=20,
                                                          pady=(18, 2))
        tk.Label(self, text="All preferences save automatically.",
                 background=t["bg"], foreground=t["subtle"],
                 font=(app.font_family, 9)).pack(anchor="w", padx=20, pady=(0, 16))
        card = tk.Frame(self, background=t["panel"],
                        highlightbackground=t["border"], highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 12))
        tk.Label(card, text="Theme — pick your vibe (1 click)", background=t["panel"], foreground=t["fg"],
                 font=(app.font_family, 10, "bold")).pack(anchor="w", padx=16,
                                                          pady=(14, 6))
        trow = tk.Frame(card, background=t["panel"])
        trow.pack(fill="x", padx=12, pady=(0, 6))
        self._theme_btns = {}
        for key in THEME_ORDER:
            lab = {"midnight": "Midnight", "dark": "Dark", "light": "Light",
                   "ocean": "Ocean", "sunset": "Sunset", "forest": "Forest",
                   "rosegold": "Rose"}.get(key, key)
            b = FButton(trow, text=lab,
                        command=lambda k=key: self._on_pick_theme(k),
                        background=(t["accent"] if app.theme == key else t["bg"]),
                        foreground=(t["accent_fg"] if app.theme == key else t["fg"]),
                        activebackground=t["hover"], activeforeground=t["fg"],
                        padx=10, pady=5, radius=12,
                        font=(app.font_family, 8, "bold"))
            b.pack(side="left", padx=3, pady=3)
            self._theme_btns[key] = b
        tk.Frame(card, background=t["panel"], height=8).pack()
        cn = tk.Frame(self, background=t["panel"],
                      highlightbackground=t["border"], highlightthickness=1)
        cn.pack(fill="x", padx=20, pady=(0, 12))
        tk.Label(cn, text="Notifications", background=t["panel"],
                 foreground=t["fg"], font=(app.font_family, 10, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6))
        self.os_notif_var = tk.BooleanVar(value=app.os_notifications)
        toggle_row(cn, "Native system notifications", self.os_notif_var,
                   self._on_os_notif, t, app.font_family,
                   "Show desktop alerts for downloads and launches")
        self.zip_var = tk.BooleanVar(value=app.auto_zip_backup)
        toggle_row(cn, "Auto-zip backup on install", self.zip_var,
                   self._on_zip, t, app.font_family,
                   "Keep a .zip copy in the _backups folder")
        tk.Frame(cn, background=t["panel"], height=8).pack()
        c2 = tk.Frame(self, background=t["panel"],
                      highlightbackground=t["border"], highlightthickness=1)
        c2.pack(fill="x", padx=20, pady=(0, 12))
        tk.Label(c2, text="Mods Folder", background=t["panel"],
                 foreground=t["fg"], font=(app.font_family, 10, "bold")).pack(
            anchor="w", padx=16, pady=(14, 2))
        self.fl = tk.Label(c2, text=app.mods_folder, background=t["panel"],
                           foreground=t["accent"], font=(app.font_family, 9),
                           wraplength=320, justify="left")
        self.fl.pack(anchor="w", padx=16, pady=(0, 8))
        r = tk.Frame(c2, background=t["panel"])
        r.pack(anchor="w", padx=16, pady=(0, 14))
        FButton(r, text="Browse…", command=self._pick_folder,
                  background=t["accent"], foreground=t["accent_fg"],
                  activebackground=t["accent"], activeforeground=t["accent_fg"],
                  borderwidth=0, padx=14, pady=5, cursor="hand2",
                  font=(app.font_family, 9)).pack(side="left")
        FButton(r, text="Reset", command=self._reset_folder,
                  background=t["bg"], foreground=t["fg"],
                  activebackground=t["hover"], activeforeground=t["fg"],
                  borderwidth=0, padx=14, pady=5, cursor="hand2",
                  font=(app.font_family, 9)).pack(side="left", padx=6)
        c3 = tk.Frame(self, background=t["panel"],
                      highlightbackground=t["border"], highlightthickness=1)
        c3.pack(fill="x", padx=20, pady=(0, 16))
        tk.Label(c3, text="Game Executable", background=t["panel"],
                 foreground=t["fg"], font=(app.font_family, 10, "bold")).pack(
            anchor="w", padx=16, pady=(14, 2))
        self.el = tk.Label(c3, text=app.game_exe or "(not set)",
                           background=t["panel"],
                           foreground=t["accent"] if app.game_exe else t["subtle"],
                           font=(app.font_family, 9), wraplength=320,
                           justify="left")
        self.el.pack(anchor="w", padx=16, pady=(0, 8))
        r2 = tk.Frame(c3, background=t["panel"])
        r2.pack(anchor="w", padx=16, pady=(0, 14))
        FButton(r2, text="Browse…", command=self._pick_exe,
                  background=t["accent"], foreground=t["accent_fg"],
                  activebackground=t["accent"], activeforeground=t["accent_fg"],
                  borderwidth=0, padx=14, pady=5, cursor="hand2",
                  font=(app.font_family, 9)).pack(side="left")
        FButton(r2, text="Auto-detect", command=self._auto_exe,
                  background=t["bg"], foreground=t["fg"],
                  activebackground=t["hover"], activeforeground=t["fg"],
                  borderwidth=0, padx=14, pady=5, cursor="hand2",
                  font=(app.font_family, 9)).pack(side="left", padx=6)
        FButton(self, text="Close", command=self.destroy,
                  background=t["accent"], foreground=t["accent_fg"],
                  activebackground=t["accent"], activeforeground=t["accent_fg"],
                  borderwidth=0, padx=28, pady=7, cursor="hand2",
                  font=(app.font_family, 10, "bold")).pack(pady=(0, 18))
        try: self.attributes("-alpha", 0.0)
        except tk.TclError: pass
        self.after(60, self._pos)

    def _pos(self):
        try:
            self.update_idletasks()
            w = self.winfo_width() or self.winfo_reqwidth()
            h = self.winfo_height() or self.winfo_reqheight()
            x = self.app.winfo_rootx() + (self.app.winfo_width() - w) // 2
            y = self.app.winfo_rooty() + (self.app.winfo_height() - h) // 2
            self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        except Exception: pass
        self._fade(0.0)

    def _fade(self, a):
        a = min(1.0, a + 0.12)
        try: self.attributes("-alpha", a)
        except tk.TclError: return
        if a < 1.0: self.after(16, lambda: self._fade(a))

    def _on_pick_theme(self, key):
        self.app.set_theme(key)
        self.destroy(); SettingsWindow(self.app)

    def _on_os_notif(self): self.app.set_os_notifications(self.os_notif_var.get())
    def _on_zip(self): self.app.set_zip_backup(self.zip_var.get())

    def _pick_folder(self):
        d = filedialog.askdirectory(initialdir=self.app.mods_folder)
        if d:
            self.app.set_mods_folder(d); self.fl.config(text=d)

    def _reset_folder(self):
        self.app.set_mods_folder(str(DEFAULT_MODS_FOLDER))
        self.fl.config(text=str(DEFAULT_MODS_FOLDER))

    def _pick_exe(self):
        f = filedialog.askopenfilename(
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if f:
            self.app.set_game_exe(f)
            self.el.config(text=f, foreground=THEMES[self.app.theme]["accent"])

    def _auto_exe(self):
        self.el.config(text="Searching for Friday Night Funkin'…",
                       foreground=THEMES[self.app.theme]["subtle"])
        self.update_idletasks()
        found = self.app.auto_detect_game_exe()
        if not found:
            self.el.config(text=self.app.game_exe or "(not set)",
                           foreground=THEMES[self.app.theme]["subtle"])
        if found:
            self.el.config(text=found, foreground=THEMES[self.app.theme]["accent"])


# ========== MAIN APP ==========

class FunkForgeBrowser(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{PROGRAM_NAME} v{VERSION}")
        self.geometry("1180x780"); self.minsize(1000, 640)
        try:
            self.font_family = tkfont.nametofont("TkDefaultFont").actual("family")
        except Exception:
            self.font_family = "Segoe UI"
        try:
            self._icon_ref = ImageTk.PhotoImage(make_icon(64))
            self.iconphoto(True, self._icon_ref)
        except Exception: pass
        cfg = load_config()
        self.theme = cfg.get("theme", "dark") if cfg.get("theme") in THEMES else "dark"
        self.theme_obj = THEMES[self.theme]
        self.mods_folder = cfg.get("mods_folder") or str(DEFAULT_MODS_FOLDER)
        self.game_exe = cfg.get("game_exe") or ""
        self.official_mods = set(cfg.get("official_mods") or [])
        self.auto_zip_backup = bool(cfg.get("auto_zip_backup", True))
        self.os_notifications = bool(cfg.get("os_notifications", True))
        self.mods_view = cfg.get("mods_view", "list")
        self.history = load_history()

        self.query = tk.StringVar(value="")
        self.sort_var = tk.StringVar(value=BROWSE_SORT_OPTIONS[0][0])
        self.animate_var = tk.BooleanVar(value=False)  # default OFF now

        self.mode = "browse"
        self.all_records = []; self.local_records = []
        self.history_records = []
        self.browse_page = 0; self.browse_has_more = True
        self.browse_loading = False; self.browse_query = ""; self.browse_feed = "all"
        self._browse_limit = BROWSE_RENDER_LIMIT
        self._load_generation = 0
        self._page_more = True
        self.local_id_map = {}; self.local_token_map = {}
        self._mod_scan_cache = {}; self._mod_scan_lock = threading.Lock()
        self.current_previews = []; self.preview_tk = []
        self.thumb_strip_tk = []; self.preview_idx = 0
        self.preview_job = None; self.selected_mod = None
        self.thumb_refs = []; self.row_thumb_refs = []
        self.download_lock = threading.Lock()
        self.spinner = None; self._strip_labels = []
        self._transition_ref = None

        self.withdraw()
        self._build_ui()
        self._apply_theme()
        self._update_mode_ui()
        self.bind("<Configure>", self._on_window_resize)
        self.bind_all("<Button-1>", self._global_click, add="+")
        SplashScreen(self, on_done=self._after_splash, duration_ms=1200)

    def _after_splash(self):
        try:
            self.deiconify(); self.lift(); self.focus_force()
        except Exception: pass
        threading.Thread(target=self._scan_local_bg, daemon=True).start()
        self.after(100, self.browse_all)
        if not self.game_exe or not Path(self.game_exe).exists():
            threading.Thread(target=self._auto_detect_bg, daemon=True).start()

    def _auto_detect_bg(self):
        try:
            path, official = find_official_game(max_seconds=6.0)
        except Exception:
            return
        if path and official:
            self.after(0, lambda p=str(path): (
                self.set_game_exe(p),
                self.set_status(f"🌟 Official game detected: {p}")))

    def _global_click(self, event):
        try:
            w = event.widget
            while w is not None:
                if w is self._suggestions: return
                try: w = w.master
                except Exception: break
            self._suggestions.hide()
        except Exception: pass

    def _scan_local_bg(self):
        try: recs = self._scan_local_mods()
        except Exception:
            traceback.print_exc(); recs = []
        self.after(0, lambda: self._apply_local_scan(recs))

    def _apply_local_scan(self, recs):
        self.local_records = recs
        self._rebuild_local_index()
        if self.mode in ("mods", "browse"): self._rerender()

    def _rebuild_local_index(self):
        self.local_id_map.clear(); self.local_token_map.clear()
        for r in self.local_records:
            name = r.get("_sName") or ""
            norm = normalize_mod_name(name)
            if norm: self.local_id_map[norm] = r
            toks = frozenset(extract_tokens(name))
            if toks: self.local_token_map[toks] = r

    def _on_window_resize(self, event):
        if event.widget is not self: return
        try:
            if self.mode == "browse":
                w = self.winfo_width()
                if w >= 1100:
                    self.body.columnconfigure(0, weight=3, minsize=420)
                    self.body.columnconfigure(1, weight=2, minsize=440)
                else:
                    self.body.columnconfigure(0, weight=1, minsize=300)
                    self.body.columnconfigure(1, weight=1, minsize=320)
        except Exception: pass

    # ---------- BUILD ----------

    def _build_ui(self):
        self.tab_bar = tk.Frame(self)
        self.tab_bar.pack(fill="x", padx=14, pady=(12, 8))
        self.tab_buttons = {}
        self.tab_holders = {}; self.tab_lines = {}
        for key, label in [("browse", "🔍  Browse Mods"), ("mods", "📁  My Mods"),
                           ("history", "📜  History")]:
            holder = tk.Frame(self.tab_bar)
            holder.pack(side="left", padx=(0, 6))
            lbl = tk.Label(holder, text=label, padx=16, pady=8,
                           font=(self.font_family, 10, "bold"), cursor="hand2")
            lbl.pack()
            line = tk.Frame(holder, height=3)
            line.pack(fill="x")
            for w in (lbl, holder, line):
                w.bind("<Button-1>", lambda e, k=key: self.set_mode(k))
            lbl.bind("<Enter>", lambda e, k=key: self._tab_hover(k, True))
            lbl.bind("<Leave>", lambda e, k=key: self._tab_hover(k, False))
            self.tab_buttons[key] = lbl
            self.tab_holders[key] = holder
            self.tab_lines[key] = line
        self.accent_bar = tk.Canvas(self, height=3, highlightthickness=0,
                                    borderwidth=0)
        self.accent_bar.pack(fill="x", padx=14, pady=(0, 10))
        self.accent_bar.bind("<Configure>", lambda e: self._draw_accent_bar())

        self.row_search = ttk.Frame(self, padding=(14, 0, 14, 8))
        self.row_search.pack(fill="x")
        self.row_controls = ttk.Frame(self, padding=(14, 0, 14, 10))
        ttk.Label(self.row_search, text="🔍").pack(side="left", padx=(0, 6))
        self.search_entry = ttk.Entry(self.row_search, textvariable=self.query,
                                      font=(self.font_family, 10))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_entry.bind("<Return>", lambda e: self._on_enter())
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_keyrelease())

        self.btn_search = ttk.Button(self.row_search, text="Search",
                                     style="Accent.TButton", command=self.do_search)
        _t = THEMES[self.theme]
        _pill = dict(background=_t["panel2"], foreground=_t["fg"],
                     activebackground=_t["hover"], activeforeground=_t["fg"],
                     padx=14, pady=6, radius=12, font=(self.font_family, 9, "bold"))
        self.btn_show_all = FButton(self.row_controls, text="↻  Show All",
                                    command=self.browse_all, **_pill)
        self.btn_load_all = FButton(self.row_controls, text="⬇  Load All Mods",
                                    command=self.load_all_pages, **_pill)
        self.btn_add_folder = ttk.Button(self.row_search, text="➕  Add folder",
                                         command=self.add_mod_folder)
        self.btn_open_folder = ttk.Button(self.row_search, text="📂  Mods folder",
                                          command=self.open_mods_folder)
        self.btn_refresh_mods = ttk.Button(self.row_search, text="↻  Refresh",
                                           command=self.refresh_local_mods)
        self.btn_clear_history = ttk.Button(self.row_search, text="🗑  Clear",
                                            command=self.clear_history)
        ttk.Button(self.row_search, text="🌐  Web",
                   command=self.open_web).pack(side="right", padx=(0, 6))
        ttk.Button(self.row_search, text="⚙  Settings",
                   command=self.open_settings).pack(side="right")

        self.row_controls.pack(fill="x", after=self.row_search)
        self.sort_cb = PillSelect(self.row_controls, self.sort_var,
                                  values=[n for n, _ in BROWSE_SORT_OPTIONS],
                                  theme=_t, font_family=self.font_family,
                                  on_change=self._on_sort_change, prefix="⇅  Sort:")
        self.sort_cb.pack(side="left", padx=(0, 8))
        self.view_seg = SegmentedControl(
            self.row_controls, [("list", "☰  List"), ("grid", "▦  Grid")],
            self.mods_view, self.set_view, _t, self.font_family)
        self.feed_seg = SegmentedControl(
            self.row_controls, [("all", "🌐  All Mods"), ("popular", "🔥  Popular")],
            self.browse_feed, self._set_feed, _t, self.font_family)
        self.btn_launch_game = FButton(
            self.row_controls, text="🎮  Launch Game", command=self.launch_game,
            background=_t["accent"], foreground=_t["accent_fg"],
            activebackground=_t["accent_hover"], activeforeground=_t["accent_fg"],
            padx=16, pady=6, radius=12, font=(self.font_family, 9, "bold"))
        self.btn_launch_game.pack(side="right", padx=(6, 0))
        self.count_label = ttk.Label(self.row_controls, text="",
                                     style="Subtle.TLabel")
        self.count_label.pack(side="right", padx=8)

        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.body.columnconfigure(0, weight=3, minsize=420)
        self.body.columnconfigure(1, weight=2, minsize=440)
        self.body.rowconfigure(0, weight=1)

        self.left_frame = ttk.Frame(self.body)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.results_canvas = tk.Canvas(self.left_frame, highlightthickness=0,
                                        borderwidth=0)
        sb = ttk.Scrollbar(self.left_frame, orient="vertical",
                           command=self._on_scrollbar)
        self.results_frame = ttk.Frame(self.results_canvas)
        self.results_frame.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(
                scrollregion=self.results_canvas.bbox("all")))
        self.canvas_window = self.results_canvas.create_window(
            (0, 0), window=self.results_frame, anchor="nw")
        self.results_canvas.bind(
            "<Configure>",
            lambda e: self.results_canvas.itemconfig(self.canvas_window,
                                                     width=e.width))
        self.results_canvas.configure(yscrollcommand=sb.set)
        self.results_canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.results_canvas.bind_all("<MouseWheel>", lambda e: self._on_mousewheel(e))

        self.detail_frame = ttk.Frame(self.body)
        self.detail_frame.grid(row=0, column=1, sticky="nsew")

        self.preview_wrapper = tk.Frame(self.detail_frame, width=440, height=250,
                                        highlightthickness=1, borderwidth=0,
                                        background=THEMES[self.theme]["preview_bg"],
                                        cursor="hand2")
        self.preview_wrapper.pack_propagate(False)
        self.preview_wrapper.pack(pady=(0, 4))
        self.preview_label = tk.Label(self.preview_wrapper, borderwidth=0,
                                      text="Select a mod →", foreground="#888",
                                      font=(self.font_family, 10), cursor="hand2")
        self.preview_label.pack(fill="both", expand=True)
        self.preview_wrapper.bind("<Button-1>", self._on_preview_click)
        self.preview_label.bind("<Button-1>", self._on_preview_click)

        self.strip = tk.Frame(self.detail_frame, height=60)
        self.strip.pack(fill="x", pady=(6, 6))
        self.strip.pack_propagate(False)

        anim_row = ttk.Frame(self.detail_frame)
        anim_row.pack(fill="x", pady=(0, 6))
        self.anim_toggle = ToggleSwitch(anim_row, self.animate_var,
                                        command=self._on_animate_toggle,
                                        theme=THEMES[self.theme])
        self.anim_toggle.pack(side="left", padx=(0, 8))
        ttk.Label(anim_row, text="🎞  Auto-cycle preview").pack(side="left")
        ttk.Label(anim_row, text="(click preview / thumb to advance)",
                  style="Subtle.TLabel",
                  font=(self.font_family, 8)).pack(side="left", padx=(8, 0))

        self.title_label = ttk.Label(self.detail_frame, text="Select a mod →",
                                     style="Heading.TLabel", wraplength=400,
                                     justify="left")
        self.title_label.pack(anchor="w", pady=(0, 2))
        self.badge_label = tk.Label(self.detail_frame, text="", borderwidth=0,
                                    padx=6, pady=1,
                                    font=(self.font_family, 8, "bold"))
        self.badge_label.pack(anchor="w", pady=(0, 4))
        self.meta_label = ttk.Label(self.detail_frame, text="",
                                    style="Subtle.TLabel", wraplength=400,
                                    justify="left")
        self.meta_label.pack(anchor="w", pady=(0, 6))
        self.desc = tk.Text(self.detail_frame, height=6, wrap="word",
                            relief="flat", borderwidth=0, padx=6, pady=6,
                            font=(self.font_family, 9))
        self.desc.pack(fill="both", expand=True, pady=(0, 8))
        self.desc.config(state="disabled")
        self.btn_row = ttk.Frame(self.detail_frame)
        self.btn_row.pack(fill="x")
        ttk.Button(self.btn_row, text="⬇  Download", style="Accent.TButton",
                   command=self.download_mod).pack(side="left")
        ttk.Button(self.btn_row, text="🌐  Open page",
                   command=self.open_page).pack(side="left", padx=6)
        ttk.Button(self.btn_row, text="📁  Add local",
                   command=self.add_local_file).pack(side="left")

        self.status = ttk.Label(self, text="Ready.", style="Subtle.TLabel",
                                anchor="w", padding=(14, 4))
        self.status.pack(fill="x", side="bottom")
        self._suggestions = SearchSuggestions(self, self.search_entry)

    def _tab_hover(self, key, entering):
        if key == self.mode: return
        t = THEMES[self.theme]
        bg = t["hover"] if entering else t["bg"]
        self.tab_buttons[key].configure(
            background=bg,
            foreground=_mix(t["subtle"], t["fg"], 0.7) if entering else t["subtle"])
        self.tab_holders[key].configure(background=bg)
        self.tab_lines[key].configure(background=t["border"] if entering else t["bg"])

    def _draw_accent_bar(self):
        try:
            c = self.accent_bar; t = THEMES[self.theme]
            w = max(c.winfo_width(), 4)
            c.configure(background=t["bg"]); c.delete("all")
            a, b, end = t["accent"], "#ff5fa2", t["bg"]
            steps = max(4, w // 3)
            for i in range(steps):
                p = i / (steps - 1)
                col = _mix(a, b, p * 2) if p < 0.5 else _mix(b, end, (p - 0.5) * 2)
                x0 = int(i * w / steps); x1 = int((i + 1) * w / steps) + 1
                c.create_rectangle(x0, 0, x1, 3, fill=col, outline=col)
        except Exception:
            pass

    def set_view(self, v):
        if v not in ("list", "grid"): return
        self.mods_view = v
        self._persist(); self._update_mode_ui(); self._rerender()

    def _on_scrollbar(self, *args):
        self.results_canvas.yview(*args); self._maybe_load_more()

    def _on_mousewheel(self, e):
        self.results_canvas.yview_scroll(int(-e.delta / 120), "units")
        self._maybe_load_more()

    def _maybe_load_more(self):
        if self.mode != "browse": return
        if self.browse_loading or not self.browse_has_more: return
        try:
            if self.results_canvas.yview()[1] > 0.9: self.load_more_browse()
        except Exception: pass

    # ---------- MODE ----------

    def set_mode(self, mode):
        if mode not in ("browse", "mods", "history"): return
        if self.mode == mode: return
        self.mode = mode
        if mode == "mods":
            self._update_mode_ui(); self._rerender()
            threading.Thread(target=self._scan_local_bg, daemon=True).start()
            return
        if mode == "history":
            self.history_records = self._build_history_records()
        self._update_mode_ui(); self._rerender()

    def _current_sort_options(self):
        if self.mode == "browse": return BROWSE_SORT_OPTIONS
        if self.mode == "mods": return MODS_SORT_OPTIONS
        return HISTORY_SORT_OPTIONS

    def _update_mode_ui(self):
        t = THEMES[self.theme]
        for key, lbl in self.tab_buttons.items():
            active = key == self.mode
            lbl.configure(background=t["tab_active"] if active else t["bg"],
                          foreground=t["fg"] if active else t["subtle"])
            self.tab_holders[key].configure(
                background=t["tab_active"] if active else t["bg"])
            self.tab_lines[key].configure(
                background=t["accent"] if active else t["bg"])
        self.tab_bar.configure(background=t["bg"])
        for w in (self.btn_search, self.btn_show_all, self.btn_load_all,
                  self.btn_add_folder, self.btn_open_folder, self.btn_refresh_mods,
                  self.btn_clear_history,
                  self.btn_launch_game, self.view_seg, self.feed_seg):
            w.pack_forget()
        opts = self._current_sort_options()
        self.sort_cb.configure(values=[n for n, _ in opts])
        names = [n for n, _ in opts]
        if self.sort_var.get() not in names: self.sort_var.set(names[0])
        if self.mode == "browse":
            self.btn_search.pack(side="left", padx=(0, 6))
            self.feed_seg.set(self.browse_feed)
            self.feed_seg.pack(side="left", padx=(0, 8), before=self.sort_cb)
            self.btn_show_all.pack(side="left", padx=(0, 6))
            self.btn_load_all.pack(side="left", padx=(0, 6))
            self.btn_launch_game.pack(side="right", padx=(6, 0))
            self.search_entry.configure(state="normal")
            self.detail_frame.grid(row=0, column=1, sticky="nsew")
            self.left_frame.grid_configure(columnspan=1, padx=(0, 10))
            self.body.columnconfigure(0, weight=3)
            self.body.columnconfigure(1, weight=2, minsize=440)
            self.set_status("Browse — auto-loading mods. Scroll for more.")
        elif self.mode == "mods":
            self.btn_add_folder.pack(side="left", padx=(0, 6))
            self.btn_open_folder.pack(side="left", padx=(0, 6))
            self.btn_refresh_mods.pack(side="left", padx=(0, 6))
            self.view_seg.set(self.mods_view)
            self.view_seg.pack(side="right", padx=(0, 6))
            self.search_entry.configure(state="normal")
            self.detail_frame.grid_remove()
            self.left_frame.grid_configure(columnspan=2, padx=0)
            self.body.columnconfigure(0, weight=1)
            self.body.columnconfigure(1, weight=0, minsize=0)
            self.set_status(f"My Mods — {self.mods_view} view.")
        elif self.mode == "history":
            self.btn_clear_history.pack(side="left", padx=(0, 6))
            self.search_entry.configure(state="normal")
            self.detail_frame.grid_remove()
            self.left_frame.grid_configure(columnspan=2, padx=0)
            self.body.columnconfigure(0, weight=1)
            self.body.columnconfigure(1, weight=0, minsize=0)
            self.set_status("History — activity log.")

    # ---------- THEME / PERSIST ----------

    def set_theme(self, name):
        if name not in THEMES: return
        self.theme = name; self.theme_obj = THEMES[name]
        self._persist(); self._apply_theme()
        try: self._suggestions.update_theme()
        except Exception: pass
        self._rerender()
        self.log_history("theme", f"Theme → {name}")

    def set_mods_folder(self, path):
        self.mods_folder = path
        try: Path(path).mkdir(parents=True, exist_ok=True)
        except Exception: pass
        with self._mod_scan_lock: self._mod_scan_cache.clear()
        self._persist()
        threading.Thread(target=self._scan_local_bg, daemon=True).start()
        self.set_status(f"Mods folder set to: {path}")
        self.log_history("folder", f"Mods folder → {path}")
        self.notify("Mods folder saved", f"Now using: {Path(path).name}")

    def set_game_exe(self, path):
        self.game_exe = path; self._persist()
        if path: self.log_history("folder", f"Game exe → {path}")

    def set_os_notifications(self, on):
        self.os_notifications = bool(on); self._persist()

    def set_zip_backup(self, on):
        self.auto_zip_backup = bool(on); self._persist()

    def _persist(self):
        save_config({"theme": self.theme, "mods_folder": self.mods_folder,
                     "game_exe": self.game_exe,
                     "official_mods": sorted(self.official_mods),
                     "auto_zip_backup": self.auto_zip_backup,
                     "os_notifications": self.os_notifications,
                     "mods_view": self.mods_view})

    def _apply_theme(self):
        t = THEMES[self.theme]
        style = ttk.Style()
        try: style.theme_use("clam")
        except tk.TclError: pass
        f = self.font_family
        self.configure(background=t["bg"])
        style.configure(".", font=(f, 9), background=t["bg"], foreground=t["fg"],
                        fieldbackground=t["entry_bg"], bordercolor=t["border"])
        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"], font=(f, 9))
        style.configure("Subtle.TLabel", background=t["bg"],
                        foreground=t["subtle"], font=(f, 9))
        style.configure("Heading.TLabel", background=t["bg"], foreground=t["fg"],
                        font=(f, 12, "bold"))
        style.configure("TButton", background=t["panel"], foreground=t["fg"],
                        bordercolor=t["border"], focuscolor=t["accent"],
                        padding=(10, 5), relief="flat", font=(f, 9))
        style.map("TButton", background=[("active", t["hover"]),
                                          ("pressed", t["hover"])])
        style.configure("Accent.TButton", background=t["accent"],
                        foreground=t["accent_fg"], padding=(12, 5),
                        relief="flat", font=(f, 9, "bold"))
        style.map("Accent.TButton", background=[("active", t["accent"]),
                                                 ("pressed", t["accent"])])
        style.configure("TEntry", fieldbackground=t["entry_bg"],
                        foreground=t["entry_fg"], bordercolor=t["border"],
                        insertcolor=t["fg"], padding=6, font=(f, 10))
        style.configure("TCombobox", fieldbackground=t["entry_bg"],
                        foreground=t["entry_fg"], background=t["panel"],
                        bordercolor=t["border"], arrowcolor=t["fg"],
                        padding=3, font=(f, 9))
        style.map("TCombobox", fieldbackground=[("readonly", t["entry_bg"])],
                  foreground=[("readonly", t["entry_fg"])])
        style.configure("TScrollbar", background=t["panel"], troughcolor=t["bg"],
                        bordercolor=t["bg"], arrowcolor=t["fg"])
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"],
                        focuscolor=t["bg"], font=(f, 9))
        style.map("TCheckbutton", background=[("active", t["bg"])])
        style.configure("Result.TFrame", background=t["panel"], borderwidth=0)
        style.configure("Result.TLabel", background=t["panel"],
                        foreground=t["fg"], font=(f, 10, "bold"))
        style.configure("ResultSubtle.TLabel", background=t["panel"],
                        foreground=t["subtle"], font=(f, 9))
        style.configure("Selected.TFrame", background=t["select"], borderwidth=0)
        style.configure("Selected.TLabel", background=t["select"],
                        foreground=t["fg"], font=(f, 10, "bold"))
        style.configure("SelectedSubtle.TLabel", background=t["select"],
                        foreground=t["subtle"], font=(f, 9))
        # --- premium polish (buttons, inputs, scrollbar) ---
        pb = t["panel2"]
        style.configure("TButton", background=pb, foreground=t["fg"],
                        bordercolor=pb, lightcolor=pb, darkcolor=pb,
                        focuscolor=pb, focusthickness=0, borderwidth=0,
                        padding=(14, 7), relief="flat", font=(f, 9))
        style.map("TButton",
                  background=[("pressed", t["select"]), ("active", t["hover"])],
                  bordercolor=[("active", t["hover"])],
                  lightcolor=[("active", t["hover"])],
                  darkcolor=[("active", t["hover"])])
        ac = t["accent"]
        style.configure("Accent.TButton", background=ac, foreground=t["accent_fg"],
                        bordercolor=ac, lightcolor=ac, darkcolor=ac,
                        focuscolor=ac, focusthickness=0, borderwidth=0,
                        padding=(16, 7), relief="flat", font=(f, 9, "bold"))
        style.map("Accent.TButton",
                  background=[("pressed", t["accent_dark"]),
                              ("active", t["accent_hover"])],
                  bordercolor=[("active", t["accent_hover"])],
                  lightcolor=[("active", t["accent_hover"])],
                  darkcolor=[("active", t["accent_hover"])])
        style.configure("TEntry", lightcolor=t["border"], darkcolor=t["border"],
                        padding=8)
        style.map("TEntry", bordercolor=[("focus", ac)],
                  lightcolor=[("focus", ac)], darkcolor=[("focus", ac)])
        style.configure("TCombobox", lightcolor=t["border"], darkcolor=t["border"],
                        arrowcolor=t["subtle"], padding=5)
        style.map("TCombobox", bordercolor=[("focus", ac)],
                  lightcolor=[("focus", ac)], darkcolor=[("focus", ac)],
                  background=[("active", t["hover"])])
        try:
            style.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough",
                {"sticky": "ns", "children": [("Vertical.Scrollbar.thumb",
                    {"expand": "1", "sticky": "nswe"})]})])
        except tk.TclError:
            pass
        style.configure("TScrollbar", background=t["border"], troughcolor=t["bg"],
                        bordercolor=t["bg"], lightcolor=t["border"],
                        darkcolor=t["border"], gripcount=0, width=10)
        style.map("TScrollbar", background=[("active", t["subtle"])])
        self.results_canvas.configure(background=t["bg"], highlightthickness=0)
        self.preview_wrapper.configure(background=t["preview_bg"],
                                       highlightbackground=t["border"])
        self.preview_label.configure(background=t["preview_bg"],
                                     foreground=t["subtle"])
        self.strip.configure(background=t["strip"])
        self.desc.configure(background=t["bg"], foreground=t["fg"],
                            insertbackground=t["fg"], selectbackground=t["select"])
        self.option_add("*TCombobox*Listbox.background", t["entry_bg"])
        self.option_add("*TCombobox*Listbox.foreground", t["entry_fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", t["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", t["accent_fg"])
        self.option_add("*TCombobox*Listbox.font", (f, 9))
        if hasattr(self, "anim_toggle"):
            self.anim_toggle.set_theme(t, t["bg"])
        if hasattr(self, "accent_bar"):
            self._draw_accent_bar()
        if hasattr(self, "view_seg"):
            self.sort_cb.set_theme(t, t["bg"])
            self.view_seg.set_theme(t, t["bg"])
            self.feed_seg.set_theme(t, t["bg"])
            for b in (self.btn_show_all, self.btn_load_all):
                b.configure(background=t["panel2"], foreground=t["fg"],
                            activebackground=t["hover"], activeforeground=t["fg"],
                            parent_bg=t["bg"])
            self.btn_launch_game.configure(
                background=t["accent"], foreground=t["accent_fg"],
                activebackground=t["accent_hover"], activeforeground=t["accent_fg"],
                parent_bg=t["bg"])
        self._update_mode_ui()
        if self.selected_mod: self._refresh_badge()

    # ---------- NOTIFICATIONS / HISTORY ----------

    def notify(self, title, message):
        if self.os_notifications: os_notify(title, message)

    def log_history(self, kind, name, detail=""):
        self.history.insert(0, {"ts": int(time.time()), "kind": kind,
                                "name": name, "detail": detail})
        self.history = self.history[:500]
        save_history(self.history)
        if self.mode == "history":
            self.history_records = self._build_history_records(); self._rerender()

    def _build_history_records(self):
        out = []
        for i, h in enumerate(self.history):
            out.append({"_sName": h.get("name", "?"), "_idRow": None,
                        "_history": True, "_history_idx": i,
                        "_kind": h.get("kind", "info"),
                        "_tsDateAdded": h.get("ts", 0),
                        "_detail": h.get("detail", ""),
                        "_aSubmitter": {"_sName": "History"},
                        "_nDownloadCount": 0, "_nLikeCount": 0})
        return out

    def clear_history(self):
        if not self.history: return
        if not messagebox.askyesno("Clear History", "Delete all history entries?"):
            return
        self.history = []; save_history([])
        self.history_records = []; self._rerender()
        self.notify("History cleared", "All log entries removed.")

    # ---------- SEARCH ----------

    def _on_enter(self):
        self._suggestions.hide()
        if self.mode == "browse": self.do_search()

    def _on_keyrelease(self):
        text = self.query.get().strip()
        if self.mode == "browse" and text and len(text) >= 2:
            self._suggestions.show(text)
        else:
            self._suggestions.hide()
        if self.mode in ("mods", "history"): self._rerender()

    def _set_feed(self, key):
        """Switch between the full catalogue and the Popular feed."""
        self.browse_feed = key
        self.sort_var.set("Most Downloaded" if key == "popular"
                          else BROWSE_SORT_OPTIONS[0][0])
        self.do_search()
        if key == "popular":
            self.set_status("🔥 Popular mods — most downloaded first. "
                            "Switch to All Mods to see everything, remakes included.")

    def browse_all(self):
        if self.mode != "browse": self.set_mode("browse")
        if self.browse_feed != "all":
            self.browse_feed = "all"; self.feed_seg.set("all")
            self.sort_var.set(BROWSE_SORT_OPTIONS[0][0])
        self._suggestions.hide()
        self._load_generation += 1; gen = self._load_generation
        self.set_status("Loading all FNF mods…")
        self.browse_page = 0; self.browse_has_more = True
        self.browse_query = ""; self.all_records = []
        self._clear_results()
        self.count_label.config(text="Loading…")
        threading.Thread(target=self._auto_bulk_load,
                         args=(gen, ""), daemon=True).start()

    def _auto_bulk_load(self, gen, query):
        self.browse_loading = True
        total = 0
        for p in range(1, STARTUP_PAGES + 1):
            if gen != self._load_generation:
                self.browse_loading = False; return
            try:
                recs = self._fetch_page(query, p)
                if not recs:
                    self.browse_has_more = False; break
                self.browse_page = p
                ids = {rec_uid(r) for r in self.all_records}
                new = [r for r in recs if rec_uid(r) not in ids]
                self.all_records.extend(new); total += len(new)
                print(f"[FunkForge] p{p}: {len(recs)} ({total} total, q='{query}')")
                # paint as each page lands — cards appear instantly, no waiting
                if gen == self._load_generation:
                    snap = self.all_records[:]
                    self.after(0, lambda s=snap: self._on_results(s, p > 1))
                    self.after(0, lambda n=total:
                               self.count_label.config(text=f"{n} loaded…"))
                if not self._page_more:
                    self.browse_has_more = False; break
            except Exception as e:
                print(f"[FunkForge] p{p} failed: {e}"); break
        self.browse_loading = False
        if gen != self._load_generation: return
        self.after(0, lambda: self._on_results(self.all_records, False))

    def load_more_browse(self):
        if self.browse_loading or not self.browse_has_more: return
        self.browse_loading = True
        gen = self._load_generation
        self._add_loading_row()
        threading.Thread(target=self._load_more_worker,
                         args=(gen, self.browse_query, self.browse_page + 1),
                         daemon=True).start()

    def _load_more_worker(self, gen, query, page):
        try:
            recs = self._fetch_page(query, page)
            if gen != self._load_generation: return
            self.browse_page = page
            self.after(0, lambda: self._on_results(recs, True))
        except Exception as e:
            traceback.print_exc(); self.browse_loading = False
            self.after(0, lambda: self.set_status(f"Load failed: {e}"))

    def load_all_pages(self):
        if self.mode != "browse": self.set_mode("browse")
        if self.browse_loading:
            self.notify("Already loading", "Wait for current load."); return
        self.set_status("Loading ALL mods…")
        self.count_label.config(text="Loading all…")
        gen = self._load_generation
        threading.Thread(target=self._load_all_worker, args=(gen,), daemon=True).start()

    def _load_all_worker(self, gen):
        self.browse_loading = True
        q = self.browse_query or ""
        total = len(self.all_records)
        start = (self.browse_page + 1) if self.browse_page else 1
        last_update = time.time()
        for p in range(start, start + LOAD_ALL_MAX_PAGES):
            if gen != self._load_generation:
                self.browse_loading = False; return
            try:
                recs = self._fetch_page(q, p)
                if not recs:
                    self.browse_has_more = False; break
                self.browse_page = p
                ids = {rec_uid(r) for r in self.all_records}
                new = [r for r in recs if rec_uid(r) not in ids]
                if not new and not self._page_more:
                    self.browse_has_more = False; break
                self.all_records.extend(new); total += len(new)
                print(f"[FunkForge] LoadAll p{p}: {len(recs)} ({total} total)")
                now = time.time()
                if now - last_update > 4.0:
                    self.after(0, lambda n=total:
                               self.count_label.config(text=f"{n} loaded…"))
                    last_update = now
                    self.after(0, lambda: self._on_results(self.all_records, False))
                if not self._page_more:
                    self.browse_has_more = False; break
            except Exception as e:
                print(f"[FunkForge] LoadAll p{p} failed: {e}"); break
        self.browse_loading = False
        if gen != self._load_generation: return
        self.after(0, lambda: self._on_results(self.all_records, False))
        self.after(0, lambda: self.set_status(f"✅ Loaded {total} mods."))

    def _fetch_page(self, query, page):
        """Search (mods + tools + sounds) or browse; returns normalized records
        and sets self._page_more."""
        query = " ".join((query or "").split())
        if query:
            recs, more = gb_search(query, page, SEARCH_PER_PAGE)
            if not recs and page == 1:
                print("[FunkForge] search empty -> scanning feed")
                recs, more = gb_subfeed_search(query), False
            print(f"[FunkForge] Search '{query}' p{page}: {len(recs)}")
        else:
            popular = self.browse_feed == "popular"
            recs, more = gb_browse(page, popular=popular)
            print(f"[FunkForge] Browse{' (popular)' if popular else ''} p{page}: {len(recs)}")
        out = [x for x in (normalize_record(r) for r in recs) if x]
        self._page_more = bool(more) and bool(out)
        return out

    def do_search(self):
        if self.mode != "browse": self.set_mode("browse")
        self._suggestions.hide()
        q = self.query.get().strip()
        self._load_generation += 1; gen = self._load_generation
        self.browse_query = q
        self.set_status(f"Searching for '{q}'…" if q else "Loading all mods…")
        self.browse_page = 0; self.browse_has_more = True
        self.all_records = []
        self._clear_results()
        self.count_label.config(text="Loading…")
        threading.Thread(target=self._auto_bulk_load,
                         args=(gen, q), daemon=True).start()

    def _clear_results(self):
        for w in self.results_frame.winfo_children(): w.destroy()
        self.selected_mod = None
        if self.mode == "browse":
            self.title_label.config(text="Select a mod →")
            self.badge_label.config(text="", background=THEMES[self.theme]["bg"])
            self.meta_label.config(text="")
            self.desc.config(state="normal")
            self.desc.delete("1.0", "end")
            self.desc.config(state="disabled")
            t = THEMES[self.theme]
            if self.spinner: self.spinner.stop(); self.spinner = None
            self.preview_label.config(image="", text="Select a mod →",
                                      fg=t["subtle"], bg=t["preview_bg"])
            for w in self.strip.winfo_children(): w.destroy()
            if self.preview_job:
                try: self.after_cancel(self.preview_job)
                except Exception: pass
                self.preview_job = None
            self.preview_tk = []; self.thumb_strip_tk = []
            self._strip_labels = []

    def _add_loading_row(self):
        t = THEMES[self.theme]
        tk.Label(self.results_frame, text="  Loading more…",
                 background=t["panel"], foreground=t["subtle"],
                 font=(self.font_family, 10, "italic"), pady=10).pack(
            fill="x", padx=2, pady=6)

    def _on_results(self, records, append):
        self.browse_loading = False
        if not append:
            self.all_records = records
            self._browse_limit = BROWSE_RENDER_LIMIT
        else:
            ids = {rec_uid(r) for r in self.all_records}
            new = [r for r in records if rec_uid(r) not in ids]
            self.all_records.extend(new)
            if not self._page_more: self.browse_has_more = False
        self._rerender()

    def _on_sort_change(self): self._rerender()

    # ---------- LOCAL MODS ----------

    def _analyze_mod_folder(self, d):
        zipped = find_zip_wrapper(d)
        meta = read_mod_meta(d) or {}
        info = analyze_mod_structure(d)
        engine = meta.get("engine") or info["engine"]
        if zipped:
            try: sz = zipped.stat().st_size
            except Exception: sz = 0
            zp = find_zip_preview(zipped)
            return {"_sName": d.name, "_idRow": meta.get("gb_id"),
                    "_folder": str(d), "_local": True, "_zipped": True,
                    "_zip_path": str(zipped),
                    "_preview_path": str(zp) if zp else None,
                    "_exe_path": None, "_size": sz,
                    "_nDownloadCount": 0, "_nLikeCount": 0,
                    "_tsDateAdded": int(d.stat().st_mtime),
                    "_aSubmitter": {"_sName": "Local"},
                    "_aPreviewMedia": None, "_aTags": [],
                    "_engine_hint": engine, "_structure": info}
        preview = find_mod_preview(d)
        size = folder_size(d)
        return {"_sName": d.name, "_idRow": meta.get("gb_id"),
                "_folder": str(d), "_local": True, "_zipped": False,
                "_preview_path": str(preview) if preview else None,
                "_exe_path": str(info["exe"]) if info["exe"] else None,
                "_size": size, "_nDownloadCount": 0, "_nLikeCount": 0,
                "_tsDateAdded": int(d.stat().st_mtime),
                "_aSubmitter": {"_sName": "Local"},
                "_aPreviewMedia": None, "_aTags": [],
                "_engine_hint": engine, "_structure": info}

    def _scan_local_mods(self, force=False):
        recs = []
        folder = Path(self.mods_folder)
        if not folder.is_dir(): return recs
        with self._mod_scan_lock:
            valid = {str(x) for x in folder.iterdir() if x.is_dir()}
            for k in list(self._mod_scan_cache.keys()):
                if k not in valid: del self._mod_scan_cache[k]
        for d in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if not d.is_dir() or d.name.startswith(("_", ".")): continue
            try: mtime = d.stat().st_mtime
            except Exception: continue
            ck = str(d)
            with self._mod_scan_lock:
                cached = self._mod_scan_cache.get(ck)
            if not force and cached and cached.get("mtime") == mtime:
                rec = cached["data"].copy()
            else:
                try: rec = self._analyze_mod_folder(d)
                except Exception as e:
                    print(f"[FunkForge] analyze failed {d}: {e}"); continue
                with self._mod_scan_lock:
                    self._mod_scan_cache[ck] = {"mtime": mtime, "data": rec.copy()}
            recs.append(rec)
        return recs

    def refresh_local_mods(self, force=True):
        if force:
            with self._mod_scan_lock: self._mod_scan_cache.clear()
        threading.Thread(target=self._scan_local_bg, daemon=True).start()

    def _local_match(self, online_rec):
        for r in self.local_records:
            if (r.get("_idRow") and online_rec.get("_idRow")
                    and (online_rec.get("_sModelName") or "Mod") == "Mod"
                    and r["_idRow"] == online_rec["_idRow"]):
                return r
        name = (online_rec.get("_sName") or "").strip()
        if not name: return None
        norm = normalize_mod_name(name)
        if norm and norm in self.local_id_map: return self.local_id_map[norm]
        toks = frozenset(extract_tokens(name))
        if toks:
            if toks in self.local_token_map: return self.local_token_map[toks]
            best = None; best_s = 0.0
            for lt, rec in self.local_token_map.items():
                if not lt: continue
                inter = toks & lt
                if not inter: continue
                s = len(inter) / max(1, min(len(toks), len(lt)))
                if s > best_s: best_s = s; best = rec
            if best and best_s >= 0.6: return best
        return None

    # ---------- SORT / FILTER ----------

    def _sort_key(self):
        for name, key in self._current_sort_options():
            if name == self.sort_var.get(): return key
        return self._current_sort_options()[0][1]

    def _sorted_records(self, records):
        key = self._sort_key()
        recs = list(records)
        try:
            if key == "downloads":
                recs.sort(key=lambda r: r.get("_nDownloadCount", 0) or 0, reverse=True)
            elif key == "likes":
                recs.sort(key=lambda r: r.get("_nLikeCount", 0) or 0, reverse=True)
            elif key == "new":
                recs.sort(key=lambda r: r.get("_tsDateAdded", 0) or 0, reverse=True)
            elif key == "updated":
                recs.sort(key=lambda r: (r.get("_tsDateModified")
                                          or r.get("_tsDateAdded", 0)) or 0, reverse=True)
            elif key == "name":
                recs.sort(key=lambda r: (r.get("_sName") or "").lower())
            elif key == "installed_only":
                recs = [r for r in recs if self._local_match(r) is not None]
            elif key == "officials_only":
                recs = [r for r in recs
                        if is_official_rec(r, self.official_mods)]
            elif key == "officials_first":
                recs.sort(key=lambda r: (
                    0 if is_official_rec(r, self.official_mods)
                    else 1, (r.get("_sName") or "").lower()))
            elif key == "name_asc":
                recs.sort(key=lambda r: (r.get("_sName") or "").lower())
            elif key == "name_desc":
                recs.sort(key=lambda r: (r.get("_sName") or "").lower(), reverse=True)
            elif key == "new_installed":
                recs.sort(key=lambda r: r.get("_tsDateAdded", 0) or 0, reverse=True)
            elif key == "old_installed":
                recs.sort(key=lambda r: r.get("_tsDateAdded", 0) or 0)
            elif key == "size_desc":
                recs.sort(key=lambda r: r.get("_size", 0) or 0, reverse=True)
            elif key == "size_asc":
                recs.sort(key=lambda r: r.get("_size", 0) or 0)
            elif key == "has_exe":
                recs.sort(key=lambda r: (0 if r.get("_exe_path") else 1,
                                          (r.get("_sName") or "").lower()))
            elif key == "official":
                recs.sort(key=lambda r: (0 if r.get("_sName") in self.official_mods
                                          else 1, (r.get("_sName") or "").lower()))
            elif key == "ts_desc":
                recs.sort(key=lambda r: r.get("_tsDateAdded", 0) or 0, reverse=True)
            elif key == "ts_asc":
                recs.sort(key=lambda r: r.get("_tsDateAdded", 0) or 0)
        except Exception: pass
        return recs

    def _filtered_records(self):
        if self.mode == "browse": source = self.all_records
        elif self.mode == "mods": source = self.local_records
        else: source = self.history_records
        if self.mode in ("mods", "history"):
            q = self.query.get().strip().lower()
            if q:
                source = [r for r in source
                          if q in (r.get("_sName") or "").lower()
                          or q in (r.get("_detail") or "").lower()]
        return self._sorted_records(source)

    def _rerender(self):
        records = self._filtered_records()
        for w in self.results_frame.winfo_children(): w.destroy()
        self.thumb_refs.clear(); self.row_thumb_refs.clear()
        if not records:
            q = self.query.get().strip()
            msg = {"mods": ("Scanning mods folder…" if not self.local_records
                            else "No mods installed yet."),
                   "history": "No history yet.",
                   "browse": (f"No mods found for '{q}'." if q else "No mods found."),
                   }.get(self.mode, "No items.")
            ttk.Label(self.results_frame, text=msg, style="Subtle.TLabel",
                      padding=14).pack(anchor="w")
            self.count_label.config(text="0 results")
            self.set_status("No results."); return
        if self.mode == "mods":
            # Folder path lives in the count label — always visible, like wine labels every bottle
            self.count_label.config(
                text=f"{len(records)} mods  •  📁 {self.mods_folder}")
        else:
            self.count_label.config(
                text=f"{len(records)} item{'s' if len(records) != 1 else ''}")
        if self.mode == "history":
            for rec in records: self._build_history_row(rec)
        elif self.mode == "mods":
            if self.mods_view == "grid": self._build_mods_grid(records)
            else:
                for rec in records: self._build_mod_row(rec)
        else:
            # Lag fix: paint first N only, "Show more" paints the rest
            shown = records[:self._browse_limit]
            for rec in shown: self._build_row(rec)
            if len(records) > self._browse_limit:
                t = THEMES[self.theme]
                FButton(self.results_frame,
                        text=f"Show more ({len(records) - self._browse_limit} left)",
                        command=self._show_more_browse,
                        background=t["panel2"], foreground=t["fg"],
                        activebackground=t["hover"], activeforeground=t["fg"],
                        padx=18, pady=7, radius=12,
                        font=(self.font_family, 9, "bold")).pack(pady=10)
        if self.mode == "browse":
            t = THEMES[self.theme]
            note = ("Scroll or click 'Load All Mods' for more…"
                    if self.browse_has_more else "— End of results —")
            tk.Label(self.results_frame, text=note, background=t["bg"],
                     foreground=t["subtle"],
                     font=(self.font_family, 9, "italic"),
                     pady=10).pack(fill="x")
        self.set_status("Ready.")

    def _show_more_browse(self):
        self._browse_limit += BROWSE_RENDER_LIMIT
        self._rerender()

    # ---------- BROWSE ROW ----------

    def _build_row(self, rec):
        t = THEMES[self.theme]
        row = ttk.Frame(self.results_frame, style="Result.TFrame", padding=8)
        row.pack(fill="x", padx=2, pady=3)
        thumb = tk.Label(row, width=12, height=4, borderwidth=0, cursor="hand2")
        thumb.pack(side="left", padx=(0, 10))
        info = ttk.Frame(row, style="Result.TFrame")
        info.pack(side="left", fill="x", expand=True)
        name = rec.get("_sName", "Unknown")
        local = self._local_match(rec)
        installed = local is not None
        official = is_official_rec(rec, self.official_mods)
        display_name = name + ("   🌟" if official else "")
        name_lbl = ttk.Label(info, text=display_name, style="Result.TLabel",
                             wraplength=340, justify="left")
        name_lbl.pack(anchor="w")
        kind = rec.get("_sModelName") or "Mod"
        who = (rec.get("_aSubmitter") or {}).get("_sName") or "Unknown"
        sub_text = f"👤 {who}" if kind == "Mod" else \
            f"{MODEL_ICONS.get(kind, '🧩')} {kind}   •   👤 {who}"
        if installed and local.get("_exe_path"):
            sub_text += f"   •   🚀 {Path(local['_exe_path']).name}"
        sub = ttk.Label(info, text=sub_text, style="ResultSubtle.TLabel")
        sub.pack(anchor="w", pady=(2, 0))
        right_box = ttk.Frame(row, style="Result.TFrame")
        right_box.pack(side="right", padx=(8, 0))
        if installed:
            tk.Label(right_box, text="  ✅ INSTALLED  ",
                     background="#3ba55d", foreground="#ffffff",
                     font=(self.font_family, 8, "bold"),
                     padx=4, pady=3).pack()
        widgets = [row, info, name_lbl, sub, right_box]
        def on_enter(_e):
            for x in widgets:
                try:
                    if x in (row, info, right_box): x.configure(style="Selected.TFrame")
                    elif x is sub: x.configure(style="SelectedSubtle.TLabel")
                    else: x.configure(style="Selected.TLabel")
                except tk.TclError: pass
        def on_leave(_e):
            for x in widgets:
                try:
                    if x in (row, info, right_box): x.configure(style="Result.TFrame")
                    elif x is sub: x.configure(style="ResultSubtle.TLabel")
                    else: x.configure(style="Result.TLabel")
                except tk.TclError: pass
        for w in widgets:
            w.bind("<Enter>", on_enter); w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", lambda e, r=rec: self.select_mod(r))
        if local and local.get("_preview_path"):
            threading.Thread(target=self._load_local_thumb,
                             args=(local, thumb), daemon=True).start()
        else:
            threading.Thread(target=self._load_thumb, args=(rec, thumb),
                             daemon=True).start()

    def _load_local_thumb(self, local_rec, label):
        p = local_rec.get("_preview_path")
        if not p:
            t = THEMES[self.theme]
            try:
                img = Image.new("RGB", (96, 64), t["preview_bg"])
                def blank():
                    try:
                        if not label.winfo_exists(): return
                        tkimg = ImageTk.PhotoImage(img)
                        self.thumb_refs.append(tkimg)
                        label.config(image=tkimg, width=96, height=64)
                    except tk.TclError: pass
                self.after(0, blank)
            except Exception: pass
            return
        with THUMB_SEM:
            try:
                img = Image.open(p).convert("RGB")
                img.thumbnail((96, 64), Image.LANCZOS)
            except Exception: return
            def apply():
                try:
                    if not label.winfo_exists(): return
                    tkimg = ImageTk.PhotoImage(img)
                    self.thumb_refs.append(tkimg)
                    label.config(image=tkimg, width=img.width, height=img.height)
                except tk.TclError: pass
            self.after(0, apply)

    def _load_thumb(self, rec, label):
        with THUMB_SEM:
            img = None
            if rec.get("_aPreviewMedia"):
                media = rec["_aPreviewMedia"]
                images = media.get("_aImages") or []
                if images:
                    url = (f"{images[0].get('_sBaseUrl','')}/"
                           f"{images[0].get('_sFile','')}")
                    img = fetch_image(url, (96, 64))
            if img is None: return
            def apply():
                try:
                    if not label.winfo_exists(): return
                    tkimg = ImageTk.PhotoImage(img)
                    self.thumb_refs.append(tkimg)
                    label.config(image=tkimg, width=img.width, height=img.height)
                except tk.TclError: pass
            self.after(0, apply)

    # ---------- MODS ROW ----------

    def _build_mod_row(self, rec):
        t = THEMES[self.theme]
        row = ttk.Frame(self.results_frame, style="Result.TFrame", padding=10)
        row.pack(fill="x", padx=2, pady=4)
        th = tk.Frame(row, background=t["panel"])
        th.pack(side="left", padx=(0, 12))
        thumb = tk.Label(th, width=14, height=6, borderwidth=0,
                         background=t["preview_bg"], cursor="hand2")
        thumb.pack()
        info = tk.Frame(row, background=t["panel"])
        info.pack(side="left", fill="both", expand=True)
        name = rec.get("_sName", "?")
        official = name in self.official_mods
        zipped = rec.get("_zipped")
        exe_path = rec.get("_exe_path")
        title_text = name + ("   🌟" if official else "")
        tk.Label(info, text=title_text, background=t["panel"], foreground=t["fg"],
                 font=(self.font_family, 11, "bold"), anchor="w",
                 justify="left", wraplength=460).pack(anchor="w")
        size_txt = human_size(rec.get("_size", 0))
        if zipped:
            meta_text = (f"💾 {size_txt}   •   "
                         f"📦 Zipped (not extracted)")
        elif exe_path:
            meta_text = (f"💾 {size_txt}   •   "
                         f"🚀 {Path(exe_path).name}")
        else:
            meta_text = f"💾 {size_txt}   •   no .exe"
        tk.Label(info, text=meta_text, background=t["panel"],
                 foreground=t["subtle"], font=(self.font_family, 9),
                 anchor="w").pack(anchor="w", pady=(4, 0))
        struct = rec.get("_structure") or {}
        hints = struct.get("hints", [])
        if hints:
            tk.Label(info, text="   •   ".join(hints[:3]),
                     background=t["panel"], foreground=t["subtle"],
                     font=(self.font_family, 8, "italic"), anchor="w").pack(
                anchor="w", pady=(2, 0))
        tk.Label(info, text=f"📁 {Path(rec['_folder']).name}",
                 background=t["panel"], foreground=t["subtle"],
                 font=(self.font_family, 8), anchor="w").pack(anchor="w", pady=(2, 0))
        btns = tk.Frame(row, background=t["panel"])
        btns.pack(side="right", padx=(12, 0))
        def mk_btn(text, cmd, bg=None, fg=None):
            b = FButton(btns, text=text, command=cmd,
                          background=bg or t["bg"], foreground=fg or t["fg"],
                          activebackground=t["hover"], activeforeground=t["fg"],
                          borderwidth=0, padx=12, pady=6, cursor="hand2",
                          font=(self.font_family, 9, "bold" if bg else "normal"),
                          relief="flat")
            b.pack(side="top", fill="x", pady=2)
            return b
        fp = rec.get("_folder")
        if zipped:
            mk_btn("📂  Extract & Install",
                   lambda p=fp, z=rec.get("_zip_path"):
                       self._extract_zipped_mod(p, z),
                   bg=t["accent"], fg=t["accent_fg"])
            mk_btn("📁  Open folder", lambda p=fp: self._open_folder(p))
            mk_btn("🗑  Delete", lambda p=fp, n=name: self._delete_mod(p, n),
                   bg=t["danger"], fg="#ffffff")
        else:
            mk_btn("▶  Run", lambda p=fp: self.launch_mod(p),
                   bg=t["accent"], fg=t["accent_fg"])
            mk_btn("📂  Open folder", lambda p=fp: self._open_folder(p))
            mk_btn("🌟  " + ("Unmark" if official else "Mark official"),
                   lambda n=name: self.toggle_official(n))
            mk_btn("🗑  Delete", lambda p=fp, n=name: self._delete_mod(p, n),
                   bg=t["danger"], fg="#ffffff")
        threading.Thread(target=self._load_mod_thumb, args=(rec, thumb),
                         daemon=True).start()

    def _build_mods_grid(self, records):
        # REMADE grid: always 4 across on desktop, 3/2 as the window shrinks.
        # Premium cards: bigger preview, engine + size + folder path, rounded buttons.
        t = THEMES[self.theme]
        grid = tk.Frame(self.results_frame, background=t["bg"])
        grid.pack(fill="both", expand=True, padx=4, pady=4)
        w = self.winfo_width()
        cols = 4 if w >= 1080 else 3 if w >= 800 else 2
        for i in range(cols):
            grid.columnconfigure(i, weight=1, uniform="card")
        for idx, rec in enumerate(records):
            r = idx // cols; c = idx % cols
            card = self._build_mod_card(grid, rec)
            card.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)

    def _build_mod_card(self, parent, rec):
        t = THEMES[self.theme]
        name = rec.get("_sName", "?")
        official = name in self.official_mods
        zipped = rec.get("_zipped")
        card = tk.Frame(parent, background=t["panel"],
                        highlightbackground=t["border"], highlightthickness=1)
        th = tk.Frame(card, background=t["preview_bg"], height=150)
        th.pack(fill="x"); th.pack_propagate(False)
        thumb = tk.Label(th, background=t["preview_bg"], borderwidth=0,
                         cursor="hand2")
        thumb.pack(expand=True)
        tf = tk.Frame(card, background=t["panel"])
        tf.pack(fill="x", padx=12, pady=(10, 4))
        title_text = name[:34] + ("…" if len(name) > 34 else "")
        tk.Label(tf, text=title_text, background=t["panel"], foreground=t["fg"],
                 font=(self.font_family, 10, "bold"), anchor="w",
                 justify="left", wraplength=220).pack(anchor="w")
        size_txt = human_size(rec.get("_size", 0))
        struct = rec.get("_structure") or {}
        engine = struct.get("engine") or detect_engine(name)
        tk.Label(tf, text=f"⚙ {engine}   •   💾 {size_txt}",
                 background=t["panel"], foreground=t["subtle"],
                 font=(self.font_family, 8), anchor="w").pack(anchor="w", pady=(2, 0))
        try:
            folder_nm = Path(rec.get("_folder", "")).name
            if folder_nm:
                tk.Label(tf, text=f"📁 {folder_nm}", background=t["panel"],
                         foreground=t["subtle"],
                         font=(self.font_family, 8), anchor="w").pack(anchor="w")
        except Exception:
            pass
        if zipped:
            tk.Label(tf, text="📦 Zipped — extract to play", background=t["panel"],
                     foreground=t["zipped"], font=(self.font_family, 8, "bold"),
                     anchor="w").pack(anchor="w")
        if official:
            tk.Label(tf, text="🌟 Official", background=t["panel"],
                     foreground="#f59e0b", font=(self.font_family, 8, "bold"),
                     anchor="w").pack(anchor="w")
        br = tk.Frame(card, background=t["panel"])
        br.pack(fill="x", padx=8, pady=(6, 10))
        fp = rec.get("_folder")
        def mk(txt, cmd, bg=None, fg=None):
            return FButton(br, text=txt, command=cmd,
                             background=bg or t["panel2"], foreground=fg or t["fg"],
                             activebackground=t["hover"], activeforeground=t["fg"],
                             borderwidth=0, padx=10, pady=5, cursor="hand2",
                             radius=12,
                             font=(self.font_family, 8, "bold" if bg else "normal"),
                             relief="flat")
        if zipped:
            mk("📂 Extract", lambda p=fp, z=rec.get("_zip_path"):
               self._extract_zipped_mod(p, z), bg=t["accent"],
               fg=t["accent_fg"]).pack(side="left", padx=1)
            mk("🗑", lambda p=fp, n=name: self._delete_mod(p, n),
               bg=t["danger"], fg="#ffffff").pack(side="left", padx=1)
        else:
            mk("▶", lambda p=fp: self.launch_mod(p), bg=t["accent"],
               fg=t["accent_fg"]).pack(side="left", padx=1)
            mk("📂", lambda p=fp: self._open_folder(p)).pack(side="left", padx=1)
            mk("🌟" if not official else "☆",
               lambda n=name: self.toggle_official(n)).pack(side="left", padx=1)
            mk("🗑", lambda p=fp, n=name: self._delete_mod(p, n),
               bg=t["danger"], fg="#ffffff").pack(side="left", padx=1)
        threading.Thread(target=self._load_mod_card_thumb, args=(rec, thumb),
                         daemon=True).start()
        return card

    def _load_mod_card_thumb(self, rec, label):
        with THUMB_SEM:
            p = rec.get("_preview_path")
            if p:
                try:
                    img = Image.open(p).convert("RGB")
                    img.thumbnail((200, 140), Image.LANCZOS)
                except Exception: img = None
            else:
                img = None
            if img is None:
                t = THEMES[self.theme]
                img = Image.new("RGB", (200, 130), t["preview_bg"])
            def apply():
                try:
                    if not label.winfo_exists(): return
                    tkimg = ImageTk.PhotoImage(img)
                    self.row_thumb_refs.append(tkimg)
                    label.config(image=tkimg, width=img.width, height=img.height)
                except tk.TclError: pass
            self.after(0, apply)

    def _load_mod_thumb(self, rec, label):
        with THUMB_SEM:
            p = rec.get("_preview_path")
            if p:
                try:
                    img = Image.open(p).convert("RGB")
                    img.thumbnail((140, 88), Image.LANCZOS)
                except Exception: img = None
            else:
                img = None
            if img is None:
                t = THEMES[self.theme]
                img = Image.new("RGB", (140, 88), t["preview_bg"])
            def apply():
                try:
                    if not label.winfo_exists(): return
                    tkimg = ImageTk.PhotoImage(img)
                    self.row_thumb_refs.append(tkimg)
                    label.config(image=tkimg, width=img.width, height=img.height)
                except tk.TclError: pass
            self.after(0, apply)

    def _extract_zipped_mod(self, folder_path, zip_path):
        folder = Path(folder_path); zf = Path(zip_path)
        if not zf.is_file():
            self.notify("Extract failed", "Zip file not found."); return
        try:
            self.set_status(f"Extracting {zf.name}…")
            tmp = folder / f"_ff_extract_{int(time.time())}"
            extract_zip_smart(zf, tmp)
            for item in tmp.iterdir():
                tgt = folder / item.name
                if tgt.exists():
                    if tgt.is_dir(): shutil.rmtree(tgt, ignore_errors=True)
                    else: tgt.unlink()
                shutil.move(str(item), str(tgt))
            shutil.rmtree(tmp, ignore_errors=True)
            try: zf.unlink()
            except Exception: pass
            self.notify("Mod extracted", f"✅ {folder.name}")
            self.log_history("install", folder.name, "📥 extracted from zip")
            with self._mod_scan_lock:
                self._mod_scan_cache.pop(str(folder), None)
            self.refresh_local_mods()
        except Exception as e:
            traceback.print_exc(); self.notify("Extract failed", str(e))

    def _delete_mod(self, folder_path, name):
        if not messagebox.askyesno("Delete mod",
                                   f"Permanently delete '{name}'?\n\n"
                                   f"This removes the folder:\n{folder_path}"):
            return
        try: shutil.rmtree(folder_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete:\n{e}"); return
        self.official_mods.discard(name)
        with self._mod_scan_lock:
            self._mod_scan_cache.pop(folder_path, None)
        self._persist()
        self.notify("Mod deleted", f"'{name}' has been removed.")
        self.log_history("delete", name, f"🗑 {folder_path}")
        self.refresh_local_mods()

    # ---------- HISTORY ROW ----------

    def _build_history_row(self, rec):
        t = THEMES[self.theme]
        kind = rec.get("_kind", "info")
        color, icon = HISTORY_STYLES.get(kind, ("#9a9da3", "•"))
        row = ttk.Frame(self.results_frame, style="Result.TFrame", padding=8)
        row.pack(fill="x", padx=2, pady=3)
        tk.Label(row, text=icon, font=(self.font_family, 18),
                 background=t["panel"], foreground=color, width=3).pack(
            side="left", padx=(0, 8))
        info = ttk.Frame(row, style="Result.TFrame")
        info.pack(side="left", fill="x", expand=True)
        ttk.Label(info, text=rec.get("_sName", "?"), style="Result.TLabel",
                  wraplength=600, justify="left").pack(anchor="w")
        ttk.Label(info, text=f"{fmt_ago(rec.get('_tsDateAdded', 0))}   •   {kind}",
                  style="ResultSubtle.TLabel").pack(anchor="w", pady=(2, 0))
        detail = rec.get("_detail", "")
        if detail:
            ttk.Label(info, text=detail, style="ResultSubtle.TLabel",
                      wraplength=600, justify="left").pack(anchor="w")

    # ---------- DETAIL ----------

    def _refresh_badge(self):
        if not self.selected_mod: return
        t = THEMES[self.theme]
        name = self.selected_mod.get("_sName", "")
        parts = []
        if is_official_rec(self.selected_mod, self.official_mods):
            parts.append("🌟 OFFICIAL")
        local = self._local_match(self.selected_mod)
        if self.selected_mod.get("_local") or local is not None:
            parts.append("✅ INSTALLED")
        if parts:
            bg = "#3ba55d" if "INSTALLED" in parts else t["accent"]
            self.badge_label.config(text="  " + "   ".join(parts) + "  ",
                                    background=bg, foreground="#ffffff")
        else:
            self.badge_label.config(text="", background=t["bg"], foreground=t["fg"])

    def select_mod(self, rec):
        self.selected_mod = rec
        name = rec.get("_sName", "Unknown")
        kind = rec.get("_sModelName") or "Mod"
        type_tag = "" if kind == "Mod" else f"{MODEL_ICONS.get(kind, '🧩')} {kind}   •   "
        submitter = (rec.get("_aSubmitter") or {}).get("_sName", "Unknown")
        downloads = rec.get("_nDownloadCount") or 0
        likes = rec.get("_nLikeCount") or 0
        added = fmt_date(rec.get("_tsDateAdded"))
        updated = fmt_date(rec.get("_tsDateModified"))
        self.title_label.config(text=name)
        profile = gb_page_url_rec(rec)
        self.meta_label.config(
            text=(f"{type_tag}👤 {submitter}\n"
                  f"⬇ {downloads:,} downloads   •   ❤ {likes:,} likes\n"
                  f"📅 Added {added}   •   🕒 Updated {updated}"))
        self.desc.config(state="normal")
        self.desc.delete("1.0", "end")
        self.desc.insert("end", f"Loading description…\n\n{profile}")
        self.desc.config(state="disabled")
        self._refresh_badge()
        if self.preview_job:
            try: self.after_cancel(self.preview_job)
            except Exception: pass
            self.preview_job = None
        self.current_previews = []; self.preview_tk = []
        self.thumb_strip_tk = []; self.preview_idx = 0
        t = THEMES[self.theme]
        self.preview_label.config(image="", text="",
                                  fg=t["subtle"], bg=t["preview_bg"])
        for w in self.strip.winfo_children(): w.destroy()
        self._strip_labels = []
        if self.spinner: self.spinner.stop()
        self.spinner = LoadingSpinner(self.preview_label,
                                      bg_color=t["preview_bg"],
                                      fg_color=t["accent"],
                                      size=70, interval=60)
        self.spinner.start()
        local = self._local_match(rec)
        if local and local.get("_preview_path"):
            threading.Thread(target=self._load_local_previews,
                             args=(local,), daemon=True).start()
        else:
            threading.Thread(target=self._load_previews, args=(rec,),
                             daemon=True).start()
        threading.Thread(target=self._load_details, args=(rec,),
                         daemon=True).start()

    def _on_preview_click(self, event):
        """Click → advance with smooth fade."""
        if not self.preview_tk: return
        old = self.preview_idx % len(self.preview_tk)
        new = (old + 1) % len(self.preview_tk)
        if len(self.preview_tk) == 1:
            return
        self._fade_between(old, new)
        self.preview_idx = new

    def _jump_to(self, idx):
        if not self.preview_tk: return
        old = self.preview_idx % len(self.preview_tk)
        if old == idx:
            self._draw_preview(idx); return
        self._fade_between(old, idx)
        self.preview_idx = idx

    def _fade_between(self, old_idx, new_idx):
        """Smooth crossfade between two slides using PIL blend."""
        if not self.current_previews or old_idx >= len(self.current_previews) \
                or new_idx >= len(self.current_previews):
            self._draw_preview(new_idx); return
        def step(s):
            if s > FADE_STEPS:
                self._draw_preview(new_idx); return
            try:
                a = s / FADE_STEPS
                blended = Image.blend(self.current_previews[old_idx],
                                       self.current_previews[new_idx], a)
                tkimg = ImageTk.PhotoImage(blended)
                self._transition_ref = tkimg
                self.preview_label.config(image=tkimg, text="")
                self.after(25, lambda: step(s + 1))
            except Exception:
                self._draw_preview(new_idx)
        step(0)

    def _draw_preview(self, idx):
        if not self.preview_tk: return
        idx = idx % len(self.preview_tk)
        try:
            self.preview_label.config(image=self.preview_tk[idx], text="")
        except tk.TclError:
            return
        t = THEMES[self.theme]
        for i, holder in enumerate(self._strip_labels):
            try:
                if i == idx:
                    holder.configure(highlightbackground=t["accent"])
                else:
                    holder.configure(highlightbackground=t["strip"])
            except tk.TclError: pass

    def _load_local_previews(self, local_rec):
        full, strips = [], []
        p = local_rec.get("_preview_path")
        if p:
            try:
                img = Image.open(p).convert("RGB")
                img.thumbnail(PREVIEW_SIZE, Image.LANCZOS)
                full.append(img)
                thumb = img.copy(); thumb.thumbnail(STRIP_SIZE, Image.LANCZOS)
                strips.append(thumb)
            except Exception: pass
        self.after(0, lambda: self._start_animation(full, strips))

    def _load_previews(self, rec):
        media = rec.get("_aPreviewMedia") or {}
        images = media.get("_aImages") or []
        urls = [f"{i.get('_sBaseUrl','')}/{i.get('_sFile','')}"
                for i in images[:8]]
        full, strips = [], []
        for u in urls:
            img = fetch_image(u, PREVIEW_SIZE)
            if img:
                full.append(img)
                thumb = img.copy(); thumb.thumbnail(STRIP_SIZE, Image.LANCZOS)
                strips.append(thumb)
        self.after(0, lambda: self._start_animation(full, strips))

    def _start_animation(self, imgs, strips):
        if self.spinner: self.spinner.stop(); self.spinner = None
        self.current_previews = imgs
        self.preview_tk = [ImageTk.PhotoImage(i) for i in imgs]
        self.thumb_strip_tk = [ImageTk.PhotoImage(s) for s in strips]
        self.preview_idx = 0
        t = THEMES[self.theme]
        for w in self.strip.winfo_children(): w.destroy()
        self._strip_labels = []
        if not imgs:
            self.preview_label.config(image="", text="No preview images.",
                                      fg=t["subtle"], bg=t["preview_bg"])
            return
        for i, tkimg in enumerate(self.thumb_strip_tk):
            holder = tk.Frame(self.strip, background=t["strip"],
                              highlightthickness=2,
                              highlightbackground=t["strip"], cursor="hand2")
            holder.pack(side="left", padx=3, pady=3)
            lbl = tk.Label(holder, image=tkimg, borderwidth=0,
                           cursor="hand2", background=t["strip"])
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, idx=i: self._jump_to(idx))
            holder.bind("<Button-1>", lambda e, idx=i: self._jump_to(idx))
            self._strip_labels.append(holder)
        self._draw_preview(0)
        # Only start auto-cycle if toggle is ON
        if self.animate_var.get():
            self._schedule_auto_cycle()

    def _schedule_auto_cycle(self):
        if self.preview_job:
            try: self.after_cancel(self.preview_job)
            except Exception: pass
        if self.animate_var.get() and len(self.preview_tk) > 1:
            self.preview_job = self.after(PREVIEW_INTERVAL_MS, self._auto_advance)

    def _auto_advance(self):
        if not self.preview_tk: return
        if not self.animate_var.get(): return
        old = self.preview_idx % len(self.preview_tk)
        new = (old + 1) % len(self.preview_tk)
        self._fade_between(old, new)
        self.preview_idx = new
        self._schedule_auto_cycle()

    def _on_animate_toggle(self):
        if self.animate_var.get():
            self._schedule_auto_cycle()
        else:
            if self.preview_job:
                try: self.after_cancel(self.preview_job)
                except Exception: pass
                self.preview_job = None

    def _load_details(self, rec):
        try:
            mid = rec.get("_idRow")
            if not mid: return
            r = gb_session().get(
                f"{GB_API}/{rec.get('_sModelName') or 'Mod'}/{mid}/ProfilePage",
                timeout=15)
            r.raise_for_status()
            html = r.json().get("_sText", "") or ""
            text = strip_html(html)[:2500] or "(no description)"
            self.after(0, lambda: self._show_desc(text))
        except Exception as e:
            self.after(0, lambda: self._show_desc(f"(failed to load: {e})"))

    def _show_desc(self, text):
        self.desc.config(state="normal")
        self.desc.delete("1.0", "end")
        self.desc.insert("end", text)
        self.desc.config(state="disabled")

    # ---------- DOWNLOAD ----------

    def download_mod(self):
        if not self.selected_mod:
            self.notify("No mod selected", "Pick a mod first."); return
        if self.download_lock.locked():
            self.notify("Download in progress", "Please wait."); return
        mid = self.selected_mod.get("_idRow")
        if not mid: return
        name = safe_name(self.selected_mod.get("_sName", "mod"))
        mod_dir = Path(self.mods_folder) / name
        try: mod_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.notify("Error", f"Can't create folder: {e}"); return
        self.notify("Download started", f"Fetching '{name}'…")
        self.log_history("download", name, "Started from GameBanana")
        model = self.selected_mod.get("_sModelName") or "Mod"
        threading.Thread(target=self._download_worker,
                         args=(mid, name, mod_dir, model), daemon=True).start()

    def _download_worker(self, mid, name, mod_dir, model="Mod"):
        with self.download_lock:
            try:
                self._ui_status(f"Fetching file list for {name}…")
                r = gb_session().get(f"{GB_API}/{model}/{mid}/ProfilePage",
                                     timeout=20)
                r.raise_for_status()
                data = r.json()
                files = data.get("_aFiles") or []
                if not files:
                    self._ui_status("No direct file — opening page.")
                    self.after(0, lambda: webbrowser.open(
                        gb_page_url(model, mid)))
                    self.after(0, lambda: self.notify(
                        "Manual download needed",
                        "Opened GameBanana page in your browser."))
                    return
                fs = sorted(files, key=lambda f: f.get("_nFilesize", 0) or 0, reverse=True)
                target = fs[0]
                fid = target.get("_idRow")
                fname = target.get("_sFile") or f"{name}.zip"
                size = target.get("_nFilesize") or 0
                url = target.get("_sDownloadUrl") or f"https://gamebanana.com/dl/{fid}"
                tmp_dir = Path(tempfile.gettempdir()) / "funkforge_dl"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_zip = tmp_dir / fname
                with requests.get(url, headers=HEADERS, stream=True,
                                  timeout=60, allow_redirects=True) as r2:
                    r2.raise_for_status()
                    total = int(r2.headers.get("content-length", 0)) or size
                    done = 0
                    with open(tmp_zip, "wb") as f:
                        for chunk in r2.iter_content(65536):
                            if not chunk: continue
                            f.write(chunk); done += len(chunk)
                            if total:
                                pct = int(done * 100 / total)
                                self._ui_status(
                                    f"Downloading {fname} — {pct}% "
                                    f"({human_size(done)} / {human_size(total)})")
                self._ui_status("Extracting…")
                if mod_dir.exists():
                    for item in mod_dir.iterdir():
                        if item.is_dir(): shutil.rmtree(item, ignore_errors=True)
                        else: item.unlink()
                extract_zip_smart(tmp_zip, mod_dir)
                if self.auto_zip_backup:
                    try:
                        backups = Path(self.mods_folder) / "_backups"
                        backups.mkdir(exist_ok=True)
                        zip_folder(mod_dir, backups / f"{name}.zip")
                    except Exception: pass
                # Analyze structure for engine detection
                info = analyze_mod_structure(mod_dir)
                exe = info.get("exe")
                write_mod_meta(mod_dir, {
                    "gb_id": mid,
                    "name": self.selected_mod.get("_sName", name)
                            if self.selected_mod else name,
                    "engine": info["engine"],
                    "downloaded_at": int(time.time()),
                    "filename": fname})
                try: tmp_zip.unlink(missing_ok=True)
                except Exception: pass
                extra = f"  •  🚀 {exe.name}" if exe else ""
                self._ui_status(f"✅ Installed '{name}'{extra}")
                self.after(0, lambda: self.notify("Mod installed",
                                                   f"✅ {name}{extra}"))
                self.after(0, lambda: self.log_history(
                    "install", name,
                    f"📥 Installed to {mod_dir.name}"
                    + (f" · 🚀 {exe.name}" if exe else "")))
                with self._mod_scan_lock:
                    self._mod_scan_cache.pop(str(mod_dir), None)
                self.after(0, self.refresh_local_mods)
                self.after(0, self._rerender)
                self.after(0, self._refresh_badge)
            except Exception as e:
                traceback.print_exc()
                self._ui_status(f"Download failed: {e}")
                self.after(0, lambda: self.notify("Download failed", f"{name}: {e}"))
                self.after(0, lambda: self.log_history("download", name,
                                                        f"❌ Failed: {e}"))

    def _ui_status(self, text):
        self.after(0, lambda: self.set_status(text))

    # ---------- LAUNCH / ACTIONS ----------

    def auto_detect_game_exe(self, silent=False):
        """Find the official Friday Night Funkin' install (Steam/itch/common
        folders). Falls back to a known engine build if the official game is
        not found."""
        if not silent:
            self.set_status("Searching for Friday Night Funkin'…")
        path, official = find_official_game()
        if path:
            self.set_game_exe(str(path))
            if official:
                self.notify("Official game found", f"🌟 {path.name}")
                self.set_status(f"🌟 Official game detected: {path}")
            else:
                self.notify("Engine build found",
                            f"⚙ {path.name} (official game not found)")
                self.set_status(f"Using {path.name} — official game not found.")
            self.log_history("official", path.name, f"🎮 auto-detected {path}")
            return str(path)
        if not silent:
            self.notify("Auto-detect failed",
                        "Couldn't find Friday Night Funkin'. Set it in Settings.")
            self.set_status("Couldn't auto-detect the game exe.")
        return None

    def launch_game(self):
        if not self.game_exe or not Path(self.game_exe).exists():
            self.notify("No game exe", "Set a valid game exe in Settings first.")
            return
        try:
            subprocess.Popen([self.game_exe], cwd=str(Path(self.game_exe).parent))
            self.notify("Launching", "🎮 Starting game…")
            self.log_history("launch", Path(self.game_exe).name,
                             f"🚀 {self.game_exe}")
        except Exception as e:
            self.notify("Launch failed", str(e))

    def launch_mod(self, mod_dir):
        exe = find_mod_exe(mod_dir)
        if exe:
            try:
                subprocess.Popen([str(exe)], cwd=str(exe.parent))
                self.notify("Launching mod", f"🎮 {exe.name}")
                self.log_history("launch", Path(mod_dir).name, f"🚀 via {exe.name}")
                return
            except Exception as e:
                self.notify("Launch failed", str(e)); return
        if self.game_exe and Path(self.game_exe).exists():
            self.launch_game()
            self.log_history("launch", Path(mod_dir).name, "🚀 fallback → base game")
        else:
            self.notify("Nothing to launch",
                        "Mod has no .exe and no game exe is set.")

    def _open_folder(self, path):
        try:
            if sys.platform.startswith("win"): os.startfile(str(path))
            elif sys.platform == "darwin": subprocess.Popen(["open", str(path)])
            else: subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.notify("Can't open folder", str(e))

    def open_mods_folder(self):
        try: Path(self.mods_folder).mkdir(parents=True, exist_ok=True)
        except Exception: pass
        self._open_folder(self.mods_folder)

    def add_mod_folder(self):
        src = filedialog.askdirectory()
        if not src: return
        sp = Path(src); name = safe_name(sp.name)
        dest = Path(self.mods_folder) / name
        if dest.exists():
            if not messagebox.askyesno("Overwrite?",
                                       f"'{name}' already exists. Overwrite?"):
                return
            shutil.rmtree(dest, ignore_errors=True)
        try:
            shutil.copytree(sp, dest)
            self.notify("Mod imported", f"✅ {name}")
            self.log_history("import", name, f"➕ from {src}")
            with self._mod_scan_lock:
                self._mod_scan_cache.pop(str(dest), None)
            self.refresh_local_mods()
        except Exception as e:
            self.notify("Import failed", str(e))

    def open_page(self):
        if not self.selected_mod: return
        mid = self.selected_mod.get("_idRow")
        if not mid: return
        webbrowser.open(gb_page_url_rec(self.selected_mod))
        self.set_status("Opened in browser.")

    def add_local_file(self):
        if not self.selected_mod:
            self.notify("No mod selected", "Pick a mod first."); return
        try: Path(self.mods_folder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.notify("Error", f"Can't create mods folder: {e}"); return
        path = filedialog.askopenfilename(
            filetypes=[("Zip archive", "*.zip"), ("All files", "*.*")],
            initialdir=str(Path.home() / "Downloads"))
        if not path: return
        mod_name = safe_name(self.selected_mod.get("_sName", "mod"))
        dest = Path(self.mods_folder) / mod_name
        try:
            if zipfile.is_zipfile(path):
                if dest.exists(): shutil.rmtree(dest, ignore_errors=True)
                extract_zip_smart(path, dest)
                if self.auto_zip_backup:
                    try:
                        backups = Path(self.mods_folder) / "_backups"
                        backups.mkdir(exist_ok=True)
                        shutil.copy(path, backups / f"{mod_name}.zip")
                    except Exception: pass
                info = analyze_mod_structure(dest)
                write_mod_meta(dest, {
                    "gb_id": self.selected_mod.get("_idRow"),
                    "name": self.selected_mod.get("_sName", mod_name),
                    "engine": info["engine"],
                    "downloaded_at": int(time.time())})
                self.notify("Mod installed", f"✅ {mod_name}")
                self.log_history("install", mod_name,
                                 f"📥 from local zip: {Path(path).name}")
            else:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy(path, dest / Path(path).name)
                self.notify("File copied", f"✅ {mod_name}")
                self.log_history("install", mod_name,
                                 f"📥 copied {Path(path).name}")
            with self._mod_scan_lock:
                self._mod_scan_cache.pop(str(dest), None)
            self.refresh_local_mods()
        except Exception as e:
            self.notify("Failed", str(e))

    def toggle_official(self, name):
        if name in self.official_mods:
            self.official_mods.discard(name)
            self.notify("Unmarked", f"🌟 removed from '{name}'")
            self.log_history("official", name, "🌟 unmarked")
        else:
            self.official_mods.add(name)
            self.notify("Marked official", f"🌟 {name}")
            self.log_history("official", name, "🌟 marked official")
        self._persist()
        self._rerender()

    def open_web(self):
        """Launch the browser UI (serves index.html on localhost)."""
        try:
            _, url = serve_web(open_browser=True, silent=True)
            self.notify("Web version", f"Opened {url}")
            self.set_status(f"🌐 Web version running at {url}")
            self.log_history("folder", "Web version", f"🌐 {url}")
        except FileNotFoundError as e:
            messagebox.showwarning(
                "Web version not available",
                f"{e}\n\nPlace index.html next to app.py to enable this button.")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Web version failed", str(e))

    def open_settings(self): SettingsWindow(self)
    def set_status(self, text): self.status.config(text=text)


if __name__ == "__main__":
    _p = argparse.ArgumentParser(description="FunkForge — FNF Mod Browser")
    _p.add_argument("--web", action="store_true",
                    help="Launch the browser-based UI (serves index.html "
                         "on localhost and opens your browser)")
    _p.add_argument("--web-only", action="store_true",
                    help="Only run the web server (no desktop GUI)")
    _p.add_argument("--port", type=int, default=None,
                    help="Port for the web server (default: auto)")
    _p.add_argument("--no-open", action="store_true",
                    help="Don't auto-open the browser")
    _args = _p.parse_args()

    if _args.web_only:
        try:
            httpd, url = serve_web(port=_args.port,
                                   open_browser=not _args.no_open)
            print(f"[FunkForge] Web-only mode — press Ctrl+C to stop.")
            print(f"[FunkForge] Open: {url}")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[FunkForge] Shutting down…")
                httpd.shutdown()
        except FileNotFoundError as e:
            print(f"[FunkForge] Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[FunkForge] Failed: {e}")
            sys.exit(1)
    else:
        try:
            app = FunkForgeBrowser()
            if _args.web and not _args.no_open:
                try:
                    serve_web(port=_args.port, open_browser=True, silent=True)
                except Exception:
                    pass
            app.mainloop()
        except Exception:
            _err = traceback.format_exc()
            try: (Path.home() / ".funkforge_error.log").write_text(_err)
            except Exception: pass
            try: messagebox.showerror("FunkForge crashed", _err[-1500:])
            except Exception: print(_err)
