@echo off
cd /d "%~dp0"
py -3 server.py --open %*
if errorlevel 1 (
  echo.
  echo Comprueba que Python 3.10+ este instalado y que molly_lab este al lado de molly.py y demo.py
  pause
)
