@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Labelmate build
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Create the virtual environment first: python -m venv .venv
  exit /b 1
)

if not exist "labelmate.spec" (
  echo ERROR: Missing labelmate.spec
  exit /b 1
)

if not exist "assets\kick_logo_1024-1.webp" (
  echo ERROR: Missing assets\kick_logo_1024-1.webp
  exit /b 1
)

tasklist /FI "IMAGENAME eq Labelmate.exe" 2>nul | findstr /I /C:"Labelmate.exe" >nul
if not errorlevel 1 (
  echo ERROR: Close Labelmate.exe before rebuilding
  exit /b 1
)

echo [1/3] Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-build.txt -q
if errorlevel 1 (
  echo ERROR: pip install failed
  exit /b 1
)

echo [2/3] Building with PyInstaller...
".venv\Scripts\pyinstaller.exe" labelmate.spec --noconfirm
if errorlevel 1 (
  echo ERROR: PyInstaller build failed
  exit /b 1
)

echo [3/3] Verifying output...
if not exist "dist\Labelmate\Labelmate.exe" (
  echo ERROR: dist\Labelmate\Labelmate.exe was not created
  exit /b 1
)

set "LOGO_OK=0"
if exist "dist\Labelmate\assets\kick_logo_1024-1.webp" set "LOGO_OK=1"
if exist "dist\Labelmate\_internal\assets\kick_logo_1024-1.webp" set "LOGO_OK=1"
if "%LOGO_OK%"=="0" (
  echo ERROR: Kick logo missing from build output
  exit /b 1
)

echo.
echo Build OK: dist\Labelmate\Labelmate.exe
echo Kick logo bundled.
echo Runtime data: %%APPDATA%%\Labelmate
echo.
echo Next step: package_release.bat
