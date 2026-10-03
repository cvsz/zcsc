@echo off
setlocal
py -3 "%~dp0scripts\build_windows.py"
exit /b %ERRORLEVEL%
