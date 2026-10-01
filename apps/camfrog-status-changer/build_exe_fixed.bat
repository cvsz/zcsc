@echo off
setlocal
cd /d "%~dp0"

taskkill /F /IM CamfrogStatusChanger.exe >nul 2>&1

py -m pip install -r requirements.txt pytest pyinstaller
if errorlevel 1 exit /b 1
py -m pytest -q
if errorlevel 1 exit /b 1
py -m compileall -q .
if errorlevel 1 exit /b 1

if exist dist-new rmdir /s /q dist-new
set "ICON_ARGS="
if exist app.ico set "ICON_ARGS=--icon app.ico --add-data app.ico;."

py -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name CamfrogStatusChanger ^
  --distpath dist-new ^
  --hidden-import pystray._win32 ^
  --exclude-module Xlib ^
  --exclude-module gi ^
  --exclude-module objc ^
  --exclude-module AppKit ^
  --exclude-module Foundation ^
  --exclude-module PyQt5 ^
  --exclude-module qtpy ^
  %ICON_ARGS% ^
  app.py
if errorlevel 1 exit /b 1

if not exist dist mkdir dist
copy /y dist-new\CamfrogStatusChanger.exe dist\CamfrogStatusChanger.exe >nul
powershell -ExecutionPolicy Bypass -File release_manifest.ps1
if errorlevel 1 exit /b 1

echo BUILD SUCCESS:
echo %CD%\dist\CamfrogStatusChanger.exe
