@echo off
setlocal
cd /d "%~dp0"
echo [labelon-reviewer] setup start

where py >nul 2>nul
if errorlevel 1 goto nopy
py -3.13 -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==64 else 1)" >nul 2>nul
if errorlevel 1 goto nopy

where claude >nul 2>nul
if errorlevel 1 echo [WARN] claude CLI not found on PATH. Install Claude Code and run 'claude' once to log in.

if not exist ".venv\Scripts\python.exe" (
  echo [labelon-reviewer] creating .venv with 64-bit Python 3.13
  py -3.13 -m venv .venv
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -e ".[dev]"
if errorlevel 1 goto fail

if not exist "config.yaml" (
  copy /y config.example.yaml config.yaml >nul
  echo [labelon-reviewer] config.yaml created from config.example.yaml. Review dataset_id, persona, cli.cwd.
)
if not exist "C:\labelon-reviewer-work" mkdir "C:\labelon-reviewer-work"

".venv\Scripts\python.exe" -m pytest -q
echo.
echo [labelon-reviewer] setup done. Run run.bat to start.
pause
exit /b 0

:nopy
echo [ERROR] 64-bit Python 3.13 not found. Install it from python.org, then run setup.bat again.
pause
exit /b 1

:fail
echo [ERROR] setup failed. See messages above.
pause
exit /b 1
