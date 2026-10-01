@echo off
setlocal
cd /d "%~dp0"
taskkill /F /IM CamfrogStatusChanger.exe >nul 2>&1
py -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
py -m pytest -q
if errorlevel 1 exit /b 1
py -m compileall -q .
if errorlevel 1 exit /b 1
if exist dist-new rmdir /s /q dist-new
py -m PyInstaller --clean --noconfirm --onefile --windowed --name CamfrogStatusChanger --distpath dist-new --icon app.ico --add-data "app.ico;." app.py
if errorlevel 1 exit /b 1
if not exist dist mkdir dist
copy /y dist-new\CamfrogStatusChanger.exe dist\CamfrogStatusChanger.exe >nul
powershell -ExecutionPolicy Bypass -File release_manifest.ps1
echo Build complete: dist\CamfrogStatusChanger.exe
