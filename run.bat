@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto novenv

if "%~1"=="--no-update" goto run
if not exist ".git" goto run
where git >nul 2>nul
if errorlevel 1 goto run
echo [labelon-reviewer] checking for updates (git pull)...
git pull --ff-only > "%TEMP%\labelon_pull.txt" 2>&1
if errorlevel 1 (
  echo [labelon-reviewer] update skipped (network/conflict). Running current version.
  type "%TEMP%\labelon_pull.txt"
  goto run
)
findstr /C:"Already up to date" "%TEMP%\labelon_pull.txt" >nul
if errorlevel 1 (
  echo [labelon-reviewer] updated. Reinstalling package...
  ".venv\Scripts\python.exe" -m pip install -q -e . >nul 2>&1
) else (
  echo [labelon-reviewer] already up to date.
)

:run
if not exist "config.yaml" goto noconfig
if "%~1"=="--no-update" shift
".venv\Scripts\python.exe" -m labelon_reviewer --config config.yaml %1 %2 %3 %4 %5
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo [labelon-reviewer] exited with code %RC%. See logs\app.log
  pause
)
endlocal & exit /b %RC%

:novenv
echo [labelon-reviewer] .venv not found. Run setup.bat first (see README.md).
pause
exit /b 1

:noconfig
echo [labelon-reviewer] config.yaml not found. Copy config.example.yaml to config.yaml and edit it.
pause
exit /b 1
