@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Create the virtual environment first: python -m venv .venv
  exit /b 1
)

echo Installing build dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-build.txt -q
if errorlevel 1 exit /b 1

echo Building Labelmate.exe...
".venv\Scripts\pyinstaller.exe" labelmate.spec --noconfirm
if errorlevel 1 exit /b 1

echo.
echo Done. Run: dist\Labelmate\Labelmate.exe
echo User data will be stored in %%APPDATA%%\Labelmate
