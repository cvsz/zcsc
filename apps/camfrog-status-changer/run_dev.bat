@echo off
setlocal
cd /d "%~dp0"
py -m pip install -r requirements.txt pytest
if errorlevel 1 exit /b 1
py -m pytest -q
if errorlevel 1 exit /b 1
py self_test.py
if errorlevel 1 exit /b 1
py app.py
