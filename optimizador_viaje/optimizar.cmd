@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Error: no se encontro Python en "%PYTHON_EXE%". 1>&2
  exit /b 1
)

"%PYTHON_EXE%" "%~dp0optimizar.py" %*
