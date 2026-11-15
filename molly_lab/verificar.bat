@echo off
cd /d "%~dp0"
py -3 verificar.py
if errorlevel 1 goto fin
py -3 test_studio.py
:fin
pause
