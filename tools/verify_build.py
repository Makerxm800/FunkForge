#!/usr/bin/env python3
"""Verify that a PyInstaller build produced a real, launchable binary.

A green "Build with PyInstaller" step only proves the command exited 0. This
checks the bytes on disk actually are what we claim to ship:

  Windows -> a real PE/COFF .exe  (and a GUI-subsystem one, so no console
             window pops up behind the app)
  macOS   -> a real .app bundle: Contents/MacOS/<bin>, Info.plist, Resources,
             and a Mach-O executable
  Linux   -> a real ELF executable

Usage: python tools/verify_build.py
Exits non-zero if anything is wrong.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "FunkForge (Beta)"
DIST = ROOT / "dist"

MIN_SIZE = 5 * 1024 * 1024   # a real frozen Python app is well over 5 MB

ok = True


def fail(msg: str) -> None:
    global ok
    ok = False
    print(f"  FAIL: {msg}")


def good(msg: str) -> None:
    print(f"  ok:   {msg}")


def verify_windows(exe: Path) -> None:
    data = exe.read_bytes()
    if data[:2] != b"MZ":
        return fail("missing 'MZ' DOS header -- not a Windows executable")
    good("DOS header present")

    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_off:pe_off + 4] != b"PE\0\0":
        return fail("missing 'PE\\0\\0' signature at the COFF header")
    good("PE signature present")

    machine = struct.unpack_from("<H", data, pe_off + 4)[0]
    arch = {0x8664: "x86-64", 0x014C: "x86", 0xAA64: "ARM64"}.get(machine)
    if arch:
        good(f"machine type = {arch}")
    else:
        fail(f"unexpected machine type 0x{machine:X}")

    # Optional header starts right after the 20-byte COFF header.
    opt = pe_off + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x20B:
        good("PE32+ (64-bit)")
    elif magic == 0x10B:
        good("PE32 (32-bit)")
    else:
        fail(f"unknown optional header magic 0x{magic:X}")

    subsystem = struct.unpack_from("<H", data, opt + 68)[0]
    if subsystem == 2:
        good("subsystem = GUI (no console window)")
    else:
        fail(f"subsystem is {subsystem}, expected 2 (GUI)")

    if len(data) < MIN_SIZE:
        fail(f"suspiciously small ({len(data)} bytes) -- bundle likely broken")
    else:
        good(f"size {len(data) / (1024 * 1024):.1f} MB")


def verify_macos(app: Path) -> None:
    for rel in ("Contents/MacOS", "Contents/Info.plist", "Contents/Resources"):
        if not (app / rel).exists():
            fail(f"missing {rel} -- not a valid .app bundle")
        else:
            good(f"{rel} present")

    plist = app / "Contents" / "Info.plist"
    if plist.exists():
        text = plist.read_text(encoding="utf-8", errors="ignore")
        for key in ("CFBundleName", "CFBundleIdentifier",
                    "CFBundleShortVersionString"):
            if key in text:
                good(f"Info.plist has {key}")
            else:
                fail(f"Info.plist missing {key}")
        if "FunkForge" in text:
            good("Info.plist names FunkForge")

    macos = app / "Contents" / "MacOS"
    bins = [p for p in macos.iterdir()] if macos.is_dir() else []
    if not bins:
        return fail("no executable inside Contents/MacOS")
    main_bin = bins[0]
    if not (main_bin.stat().st_mode & 0o111):
        fail(f"{main_bin.name} is not executable")
    else:
        good(f"executable: {main_bin.name} (mode {oct(main_bin.stat().st_mode & 0o777)})")

    magic = main_bin.read_bytes()[:4]
    if magic in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe",
                 b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
        good(f"Mach-O binary (magic {magic.hex()})")
    else:
        fail(f"not a Mach-O binary (magic {magic.hex()})")


def verify_linux(folder: Path) -> None:
    bins = [p for p in folder.iterdir() if p.is_file() and p.stat().st_mode & 0o111]
    if not bins:
        return fail("no executable found in the build folder")
    b = bins[0]
    if b.read_bytes()[:4] != b"\x7fELF":
        fail(f"{b.name} is not an ELF executable")
    else:
        good(f"ELF executable: {b.name}")


def main() -> int:
    print(f"[verify] FunkForge (Beta) build check on {sys.platform}")

    if sys.platform.startswith("win"):
        exe = DIST / f"{APP_NAME}.exe"
        if not exe.is_file():
            print(f"  FAIL: {exe} not found")
            return 1
        verify_windows(exe)
    elif sys.platform == "darwin":
        app = DIST / f"{APP_NAME}.app"
        if not app.is_dir():
            print(f"  FAIL: {app} not found")
            return 1
        verify_macos(app)
    else:
        folder = DIST / APP_NAME
        if not folder.is_dir():
            print(f"  FAIL: {folder} not found")
            return 1
        verify_linux(folder)

    print("[verify] " + ("PASS - genuine native binary" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
