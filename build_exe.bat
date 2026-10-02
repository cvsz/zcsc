@echo off
setlocal
cd /d "%~dp0"
call "%~dp0build_exe_fixed.bat"
exit /b %ERRORLEVEL%
