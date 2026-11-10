@echo off
rem Run the CUP checker from any directory, preferring the project venv.
cd /d "%~dp0"
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" main.py %*
