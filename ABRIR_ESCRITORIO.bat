@echo off
setlocal
cd /d "%~dp0"
title Preparar Acceso Residencial - Escritorio
where py >nul 2>nul
if errorlevel 1 goto usar_python
py -X utf8 preparar.py --desktop
goto resultado
:usar_python
where python >nul 2>nul
if errorlevel 1 goto sin_python
python -X utf8 preparar.py --desktop
:resultado
if errorlevel 1 goto fallo
exit /b 0
:sin_python
echo Instala Python 3.12 de 64 bits:
echo https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
:fallo
echo No se pudo preparar el escritorio. Copia el mensaje de arriba.
pause
