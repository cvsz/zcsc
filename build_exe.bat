@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python Launcher ^(py.exe^) was not found.
  echo Install 64-bit CPython 3.12 and retry.
  exit /b 1
)

py -3.12 -c "import struct,sys; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] CamfrogStatusChanger release builds require 64-bit CPython 3.12.
  echo The generic "py -3" command may select Python 3.14/3.14t, which is not supported by the locked Windows audit/build toolchain.
  echo Install Python 3.12 x64, then verify with: py -3.12 --version
  exit /b 1
)

py -3.12 "%~dp0scripts\build_windows.py"
exit /b %ERRORLEVEL%
