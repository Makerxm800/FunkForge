#!/usr/bin/env python3
"""Package the PyInstaller output into a distributable .zip.

Why Python instead of `zip`: GitHub's Windows runners have no `zip` binary,
so shelling out to it fails there with exit 127. Python is guaranteed to
exist on every runner, so this works identically everywhere.

Usage:
    python tools/package_release.py <artifact-basename>

Produces:
    dist_pkg/<artifact-basename>.zip
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "FunkForge (Beta)"
DIST = ROOT / "dist"
STAGING = ROOT / "build" / "staging"
OUT = ROOT / "dist_pkg"

# Docs that ship alongside the binary.
EXTRA_DOCS = ("README.md", "License", "requirements.txt")


def _reset_dir(p: Path) -> Path:
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)
    return p


def _zip_dir(src: Path, dest: Path) -> None:
    """Zip `src`'s contents (not the folder itself) into `dest`."""
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(src.rglob("*")):
            if f.is_dir():
                continue
            if f.name == ".DS_Store":
                continue
            z.write(f, f.relative_to(src))
            # Preserve the executable bit on POSIX (bundled macOS binaries).
            if hasattr(f, "chmod"):
                info = z.getinfo(str(f.relative_to(src)))
                info.external_attr = (f.stat().st_mode & 0o777) << 16


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    basename = argv[1]

    if sys.platform.startswith("win"):
        target = DIST / f"{APP_NAME}.exe"
        kind = "exe"
    elif sys.platform == "darwin":
        target = DIST / f"{APP_NAME}.app"
        kind = "app"
    else:
        target = DIST / APP_NAME
        kind = "dir"

    if not target.exists():
        print(f"[package] ERROR: expected build output not found: {target}")
        if DIST.exists():
            print("[package] dist/ contains:")
            for p in sorted(DIST.iterdir()):
                print(f"  - {p.name}")
        return 1

    staging = _reset_dir(STAGING)
    OUT.mkdir(parents=True, exist_ok=True)

    if kind == "exe":
        shutil.copy2(target, staging / target.name)
        for doc in EXTRA_DOCS:
            src = ROOT / doc
            if src.exists():
                shutil.copy2(src, staging / doc)
        size = target.stat().st_size
    elif kind == "app":
        # Zip the .app folder itself so macOS metadata/symlinks survive.
        shutil.copytree(target, staging / target.name, symlinks=True)
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    else:
        shutil.copytree(target, staging / target.name, symlinks=True)
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())

    out_zip = OUT / f"{basename}.zip"
    if out_zip.exists():
        out_zip.unlink()
    _zip_dir(staging, out_zip)

    mb = out_zip.stat().st_size / (1024 * 1024)
    print(f"[package] {target.name}  ({size / (1024*1024):.1f} MB)")
    print(f"[package] wrote {out_zip}  ({mb:.1f} MB)")

    # Surface the path to later CI steps.
    gh_out = __import__("os").environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"zip_path={out_zip}\n")
            fh.write(f"zip_name={out_zip.name}\n")

    shutil.rmtree(staging, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
