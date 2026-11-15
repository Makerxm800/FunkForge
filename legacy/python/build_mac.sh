#!/usr/bin/env bash
# ===================================================================
#  FunkForge (Beta) - macOS build script
#  Produces a real native .app bundle (PyInstaller, no Electron).
#  Output: dist/FunkForge (Beta).app
# ===================================================================
set -euo pipefail

APP_NAME="FunkForge (Beta)"
cd "$(dirname "$0")"

echo "=== FunkForge (Beta) - macOS build ==="

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "Installing build dependencies..."
  python3 -m pip install --upgrade pip
  python3 -m pip install -r requirements-build.txt
fi

echo "Building .app (this takes a few minutes)..."
python3 -m PyInstaller FunkForge.spec --noconfirm --clean

APP_PATH="dist/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "BUILD FAILED: $APP_PATH not found" >&2
  exit 1
fi

# Ad-hoc sign so macOS doesn't immediately flag the bundle as damaged.
# (Distribution-signed builds need an Apple Developer certificate.)
echo "Ad-hoc signing..."
codesign --force --deep --sign - "$APP_PATH" \
  || echo "  (codesign skipped - the app will still run locally)"

echo
echo "  BUILD OK  ->  $APP_PATH"
du -sh "$APP_PATH"
