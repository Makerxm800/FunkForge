@echo off
REM ===================================================================
REM  FunkForge (Beta) - Windows build script
REM  Produces a real native .exe (PyInstaller, no Electron).
REM  Output: dist\FunkForge (Beta).exe
REM ===================================================================
setlocal enabledelayedexpansion

echo.
echo  === FunkForge (Beta) - Windows build ===
echo.

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo Installing build dependencies...
    python -m pip install --upgrade pip || goto :fail
    python -m pip install -r requirements-build.txt || goto :fail
) else (
    echo pyinstaller found.
)

echo.
echo Building .exe (this takes a few minutes)...
python -m PyInstaller FunkForge.spec --noconfirm --clean
if errorlevel 1 goto :fail

echo.
if exist "dist\FunkForge (Beta).exe" (
    echo  BUILD OK  ^->  "dist\FunkForge (Beta).exe"
    for %%F in ("dist\FunkForge (Beta).exe") do echo  Size: %%~zF bytes
) else (
    echo  Build finished but the .exe was not found.
    goto :fail
)
echo.
exit /b 0

:fail
echo.
echo  BUILD FAILED
exit /b 1
