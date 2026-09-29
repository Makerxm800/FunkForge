# app.py
# FunkForge - FNF Mod Manager
# MIT License

import os
import json
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

PROGRAM_NAME = "FunkForge"
VERSION = "0.1.0"
AUTHOR = "Your Name"

CONFIG_PATH = Path.home() / ".funkforge.json"
DISABLED_SUFFIX = ".disabled"


# ---------------- CONFIG ----------------

def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return {"mods_path": "", "game_path": ""}


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


# ---------------- MOD LOGIC ----------------

def list_mods(mods_path):
    """Return list of (display_name, actual_folder_name, enabled_bool)."""
    mods = []
    p = Path(mods_path)
    if not p.is_dir():
        return mods
    for entry in sorted(p.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.endswith(DISABLED_SUFFIX):
            mods.append((name[: -len(DISABLED_SUFFIX)], name, False))
        else:
            mods.append((name, name, True))
    return mods


def toggle_mod(mods_path, folder_name, enable):
    p = Path(mods_path) / folder_name
    if not p.exists():
        return False
    if enable and folder_name.endswith(DISABLED_SUFFIX):
        new = p.with_name(folder_name[: -len(DISABLED_SUFFIX)])
        p.rename(new)
        return True
    if not enable and not folder_name.endswith(DISABLED_SUFFIX):
        new = p.with_name(folder_name + DISABLED_SUFFIX)
        p.rename(new)
        return True
    return False


def launch_game(game_path):
    if not game_path or not Path(game_path).exists():
        return False, "Game path not set or invalid."
    try:
        subprocess.Popen([game_path], cwd=str(Path(game_path).parent))
        return True, "Game launched."
    except Exception as e:
        return False, str(e)


# ---------------- GUI ----------------

class FunkForge(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{PROGRAM_NAME} v{VERSION}")
        self.geometry("640x480")
        self.minsize(520, 400)

        self.cfg = load_config()
        self.mod_rows = {}  # folder_name -> BooleanVar

        self._build_ui()
        self.refresh_mods()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Mods folder:").pack(side="left")
        self.mods_var = tk.StringVar(value=self.cfg.get("mods_path", ""))
        ttk.Entry(top, textvariable=self.mods_var).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(top, text="Browse", command=self.pick_mods).pack(side="left")

        top2 = ttk.Frame(self, padding=(8, 0, 8, 8))
        top2.pack(fill="x")

        ttk.Label(top2, text="Game exe:").pack(side="left")
        self.game_var = tk.StringVar(value=self.cfg.get("game_path", ""))
        ttk.Entry(top2, textvariable=self.game_var).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(top2, text="Browse", command=self.pick_game).pack(side="left")

        mid = ttk.Frame(self, padding=(8, 0, 8, 0))
        mid.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(mid, highlightthickness=0)
        scrollbar = ttk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill="x")

        ttk.Button(bottom, text="Refresh", command=self.refresh_mods).pack(side="left")
        ttk.Button(bottom, text="Save", command=self.save).pack(side="left", padx=6)
        ttk.Button(bottom, text="Launch Game", command=self.launch).pack(side="right")

        self.status = ttk.Label(self, text="Ready.", padding=(8, 2))
        self.status.pack(fill="x")

    def pick_mods(self):
        d = filedialog.askdirectory(title="Select your FNF mods folder")
        if d:
            self.mods_var.set(d)
            self.refresh_mods()

    def pick_game(self):
        f = filedialog.askopenfilename(
            title="Select FNF executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if f:
            self.game_var.set(f)

    def refresh_mods(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.mod_rows.clear()

        path = self.mods_var.get().strip()
        if not path:
            ttk.Label(self.scroll_frame, text="Set a mods folder above.").pack(
                anchor="w", padx=4, pady=4
            )
            return

        mods = list_mods(path)
        if not mods:
            ttk.Label(self.scroll_frame, text="No mods found.").pack(
                anchor="w", padx=4, pady=4
            )
            return

        for display, folder, enabled in mods:
            var = tk.BooleanVar(value=enabled)
            cb = ttk.Checkbutton(
                self.scroll_frame,
                text=display,
                variable=var,
                command=lambda f=folder, v=var: self.on_toggle(f, v),
            )
            cb.pack(anchor="w", padx=4, pady=2)
            self.mod_rows[folder] = var

    def on_toggle(self, folder_name, var):
        path = self.mods_var.get().strip()
        enable = var.get()
        ok = toggle_mod(path, folder_name, enable)
        if ok:
            self.set_status(f"{'Enabled' if enable else 'Disabled'}: {folder_name}")
            # re-map the key since folder name changed
            self.after(50, self.refresh_mods)
        else:
            self.set_status("Toggle failed.")

    def save(self):
        self.cfg["mods_path"] = self.mods_var.get().strip()
        self.cfg["game_path"] = self.game_var.get().strip()
        save_config(self.cfg)
        self.set_status(f"Saved to {CONFIG_PATH}")

    def launch(self):
        self.save()
        ok, msg = launch_game(self.cfg.get("game_path", ""))
        self.set_status(msg)
        if not ok:
            messagebox.showerror(PROGRAM_NAME, msg)

    def set_status(self, text):
        self.status.config(text=text)


if __name__ == "__main__":
    app = FunkForge()
    app.mainloop()
