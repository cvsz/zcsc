@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title Camfrog Status Changer - Production Candidate Build
set "APP=CamfrogStatusChanger"
set "OLD_DIST=%CD%\dist"
set "NEW_DIST=%CD%\.tmp\CamfrogStatusChanger-dist"
set "WORK=%CD%\build\CamfrogStatusChanger-work"
set "SPEC_DIR=%CD%\.tmp\CamfrogStatusChanger-spec"

echo ==================================================
echo Camfrog Status Changer - Production Candidate Build
echo ==================================================
where py >nul 2>&1 || (echo [ERROR] Python launcher not found.& exit /b 1)

echo [1/6] Installing pinned build dependencies...
py -m pip install -r requirements.txt pytest pyinstaller==6.22.3
if errorlevel 1 goto :failed

echo [2/6] Running regression tests...
set "PYTHONPATH=%CD%"
py -m pytest -q
if errorlevel 1 goto :failed

echo [3/6] Running source compile check...
py -m compileall -q app.py automation camfrog system ui version.py self_test.py
if errorlevel 1 goto :failed

echo [4/6] Cleaning isolated staging directories...
if exist "%NEW_DIST%" rmdir /S /Q "%NEW_DIST%"
if exist "%WORK%" rmdir /S /Q "%WORK%"
if exist "%SPEC_DIR%" rmdir /S /Q "%SPEC_DIR%"
mkdir "%NEW_DIST%" >nul 2>&1
mkdir "%SPEC_DIR%" >nul 2>&1

echo [5/6] Building windowed one-file EXE...
py -m PyInstaller --clean --noconfirm --onefile --windowed --exclude-module PIL._avif --name "%APP%" --icon "%CD%\app.ico" --add-data "%CD%\bad_word_starters.json;." --add-data "%CD%\app.ico;." --distpath "%NEW_DIST%" --workpath "%WORK%" --specpath "%SPEC_DIR%" app.py
if errorlevel 1 goto :failed
if not exist "%NEW_DIST%\%APP%.exe" (echo [ERROR] Expected EXE not generated.& goto :failed)

echo [6/6] Publishing artifact after tests and build pass...
if not exist "%OLD_DIST%" mkdir "%OLD_DIST%"
copy /Y "%NEW_DIST%\%APP%.exe" "%OLD_DIST%\%APP%.exe" >nul
if errorlevel 1 goto :failed
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\release_manifest.ps1"
if errorlevel 1 goto :failed

echo Cleaning isolated staging output...
rmdir /S /Q "%NEW_DIST%" >nul 2>&1
rmdir /S /Q "%WORK%" >nul 2>&1
rmdir /S /Q "%SPEC_DIR%" >nul 2>&1

echo.
echo BUILD SUCCESS
echo EXE:      "%OLD_DIST%\%APP%.exe"
echo Manifest: "%OLD_DIST%\release-manifest.json"
exit /b 0

:failed
echo.
echo BUILD FAILED - inspect staged logs and verify the published EXE and manifest before use.
exit /b 1
