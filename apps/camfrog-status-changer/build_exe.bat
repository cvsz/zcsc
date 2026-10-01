@echo off
setlocal
cd /d "%~dp0"
title Camfrog Status Changer - Windows Builder

where py >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python launcher not found. Install Python 3.12+.
  pause
  exit /b 1
)

py -m pip install --upgrade pip
if errorlevel 1 goto :error
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist CamfrogStatusChanger.spec del /q CamfrogStatusChanger.spec

set "ICON_ARG="
if exist "%CD%\app.ico" set "ICON_ARG=--icon=%CD%\app.ico"

py -m PyInstaller --clean --noconfirm --onefile --windowed --noconsole --name CamfrogStatusChanger %ICON_ARG% app.py
if errorlevel 1 goto :error

if not exist "dist\CamfrogStatusChanger.exe" goto :error

echo.
echo BUILD SUCCESS:
echo %CD%\dist\CamfrogStatusChanger.exe
explorer "%CD%\dist"
pause
exit /b 0

:error
echo.
echo BUILD FAILED. Review the error output above.
pause
exit /b 1
