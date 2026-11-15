#!/usr/bin/env python3
"""Generate the platform icon files electron-builder needs.

    assets/logo.png  ->  build/icon.ico   (Windows: 16..256, multi-resolution)
                        build/icon.icns  (macOS icon bundle)
                        build/icon.png   (Linux: 512x512)

Uses Apple's `iconutil` on macOS when available (the most compatible .icns),
otherwise falls back to Pillow, which works on every platform.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "logo.png"
OUT = ROOT / "build"

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ICONSET = [
    (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
]


def load_master() -> Image.Image:
    if not SRC.is_file():
        sys.exit(f"[icons] missing source logo: {SRC}")
    im = Image.open(SRC)
    im.load()
    return im.convert("RGBA")


def make_ico(im: Image.Image) -> None:
    p = OUT / "icon.ico"
    im.save(p, "ICO", sizes=ICO_SIZES, bitmap_format="bmp")
    print(f"[icons] build/icon.ico  ({len(ICO_SIZES)} sizes, {p.stat().st_size // 1024} KB)")


def make_png(im: Image.Image) -> None:
    p = OUT / "icon.png"
    im.resize((512, 512), Image.LANCZOS).save(p, "PNG", optimize=True)
    print(f"[icons] build/icon.png  (512x512, {p.stat().st_size // 1024} KB)")


def make_icns(im: Image.Image) -> None:
    p = OUT / "icon.icns"
    if sys.platform == "darwin" and shutil.which("iconutil"):
        tmp = Path(tempfile.mkdtemp())
        iconset = tmp / "icon.iconset"
        iconset.mkdir()
        for size, name in ICONSET:
            im.resize((size, size), Image.LANCZOS).save(iconset / name, "PNG")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(p)],
                       check=True)
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[icons] build/icon.icns (iconutil, {p.stat().st_size // 1024} KB)")
    else:
        im.save(p, "ICNS",
                sizes=[(s, s) for s in (16, 32, 64, 128, 256, 512, 1024)])
        print(f"[icons] build/icon.icns (Pillow, {p.stat().st_size // 1024} KB)")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    master = load_master()
    make_ico(master)
    make_png(master)
    make_icns(master)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
