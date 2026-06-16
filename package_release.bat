@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\Labelmate\Labelmate.exe" (
  echo Build the app first: build_exe.bat
  exit /b 1
)

set OUT=dist\Labelmate-windows.zip
if exist "%OUT%" del "%OUT%"

powershell -NoProfile -Command ^
  "Compress-Archive -Path 'dist\Labelmate\*' -DestinationPath '%OUT%' -Force"

if errorlevel 1 (
  echo Failed to create zip.
  exit /b 1
)

echo.
echo Created: %OUT%
echo Upload this file to GitHub Releases.
