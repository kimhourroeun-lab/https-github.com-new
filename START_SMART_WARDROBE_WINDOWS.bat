@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  set "PYEXE=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3 is required. Install it from https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set "PYEXE=python"
)
if not exist ".venv\Scripts\python.exe" (
  %PYEXE% -m venv .venv
  if errorlevel 1 (pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause