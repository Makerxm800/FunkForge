#!/usr/bin/env python3
"""Build the platform icon files from assets/logo.png.

Produces:
  assets/logo.ico   - multi-resolution Windows icon (16..256)
  assets/logo.icns  - macOS icon bundle
  assets/logo_1024.png - normalized 1024x1024 master

Run:  python tools/make_icons.py
Cross-platform (no macOS or Windows needed) thanks to Pillow.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "logo.png"
OUT = ROOT / "assets"

# Windows .ico: classic shell sizes (Pillow embeds each one).
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
             (128, 128), (256, 256)]

# macOS .icns: Pillow writes these; 512x512@2x == 1024x1024.
ICNS_SIZES = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256),
              (512, 512), (1024, 1024)]


def load_master() -> Image.Image:
    if not SRC.is_file():
        sys.exit(f"[make_icons] Missing source logo: {SRC}")
    im = Image.open(SRC)
    im.load()
    # .ico/.icns want an alpha channel so the tile can have rounded corners.
    return im.convert("RGBA")


def make_png_master(im: Image.Image) -> Path:
    p = OUT / "logo_1024.png"
    im.resize((1024, 1024), Image.LANCZOS).save(p, "PNG", optimize=True)
    print(f"[make_icons] wrote {p.relative_to(ROOT)}")
    return p


def make_ico(im: Image.Image) -> Path:
    p = OUT / "logo.ico"
    im.save(
        p,
        "ICO",
        sizes=ICO_SIZES,
        # Bitmap-format entries keep older Windows shells happy.
        bitmap_format="bmp",
    )
    print(f"[make_icons] wrote {p.relative_to(ROOT)} ({len(ICO_SIZES)} sizes)")
    return p


def make_icns(im: Image.Image) -> Path:
    p = OUT / "logo.icns"
    im.save(p, "ICNS", sizes=ICNS_SIZES)
    print(f"[make_icons] wrote {p.relative_to(ROOT)} ({len(ICNS_SIZES)} sizes)")
    return p


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    master = load_master()
    make_png_master(master)
    make_ico(master)
    try:
        make_icns(master)
    except Exception as exc:  # non-fatal: Windows/Linux builds don't need it
        print(f"[make_icons] note: could not write .icns ({exc}). "
              f"macOS builds will fall back to the .ico.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
