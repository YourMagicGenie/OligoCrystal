@echo off
rem Double-click to open the Gallery Curator.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Setting up the first time, one moment...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)
.venv\Scripts\python.exe -I tools\curate.py
pause
