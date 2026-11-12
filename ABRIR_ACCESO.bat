@echo off
setlocal
cd /d "%~dp0"
title Acceso Residencial - Piloto local
where py >nul 2>nul
if errorlevel 1 goto usar_python
py -X utf8 preparar.py
goto fin
:usar_python
where python >nul 2>nul
if errorlevel 1 goto sin_python
python -X utf8 preparar.py
goto fin
:sin_python
echo Instala Python 3.12 de 64 bits y vuelve a abrir este archivo.
echo https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
:fin
pause
