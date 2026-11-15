#!/usr/bin/env bash
# ===================================================================
#  FunkForge (Beta) - Linux build script
#  Output: dist/"FunkForge (Beta)"/FunkForge (Beta)
# ===================================================================
set -euo pipefail

cd "$(dirname "$0")"
echo "=== FunkForge (Beta) - Linux build ==="

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "Installing build dependencies..."
  python3 -m pip install --upgrade pip
  python3 -m pip install -r requirements-build.txt
fi

echo "Building..."
python3 -m PyInstaller FunkForge.spec --noconfirm --clean

echo
echo "  BUILD OK  ->  dist/FunkForge (Beta)/"
