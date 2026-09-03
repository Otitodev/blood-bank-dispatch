@echo off
rem Blood Bank Dispatch server launcher.
rem Foreground:  serve.cmd            (Ctrl+C stops it)
rem Background:  scripts/start_server.ps1
cd /d "%~dp0"
".\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2> uvicorn.err.log
