@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Labelmate release package
echo.

if not exist "dist\Labelmate\Labelmate.exe" (
  echo ERROR: Run build_exe.bat first.
  exit /b 1
)

set "LOGO_OK=0"
if exist "dist\Labelmate\assets\kick_logo_1024-1.webp" set "LOGO_OK=1"
if exist "dist\Labelmate\_internal\assets\kick_logo_1024-1.webp" set "LOGO_OK=1"
if "%LOGO_OK%"=="0" (
  echo ERROR: Kick logo missing from dist\Labelmate - rebuild with build_exe.bat
  exit /b 1
)

set "OUT=dist\Labelmate-windows.zip"
if exist "%OUT%" del "%OUT%"

echo Creating %OUT% ...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Labelmate\*' -DestinationPath '%OUT%' -Force"
if errorlevel 1 (
  echo ERROR: Failed to create zip.
  exit /b 1
)

for %%A in ("%OUT%") do set "SIZE=%%~zA"
set /a SIZE_MB=%SIZE% / 1048576

echo.
echo Created: %OUT% (~%SIZE_MB% MB)
echo.
echo Upload options:
echo   GitHub Actions: Actions -^> Build Windows release -^> Run workflow
echo   Or tag a release:  git tag v0.0.2 ^&^& git push origin v0.0.2
echo   Manual upload:     gh release upload ^<tag^> "%OUT%"
