@echo off
rem Starts the labelon-reviewer server. Called by run.bat after the update step.
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" goto novenv
if not exist "config.yaml" goto noconfig
if "%~1"=="--no-update" shift
".venv\Scripts\python.exe" -m labelon_reviewer --config config.yaml %1 %2 %3 %4 %5
set RC=%ERRORLEVEL%
if "%RC%"=="0" goto done
echo [labelon-reviewer] exited with code %RC%. See logs\app.log
pause
:done
endlocal & exit /b %RC%

:novenv
echo [labelon-reviewer] .venv not found. Run setup.bat first - see README.md.
pause
exit /b 1

:noconfig
echo [labelon-reviewer] config.yaml not found. Copy config.example.yaml to config.yaml and edit it.
pause
exit /b 1
