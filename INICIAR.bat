@echo off
chcp 65001 >nul
title Control Presupuestario - Ensena por Bolivia
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 iniciar.py
  goto fin
)
where python >nul 2>nul
if %errorlevel%==0 (
  python iniciar.py
  goto fin
)
echo.
echo [ERROR] No se encontro Python en esta computadora.
echo         Instale Python 3.11 o superior desde https://www.python.org/downloads/
echo         y marque la casilla "Add python.exe to PATH" durante la instalacion.
start "" https://www.python.org/downloads/
:fin
echo.
pause
