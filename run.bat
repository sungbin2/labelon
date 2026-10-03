@echo off
rem labelon-reviewer launcher. Keep this file small and stable: it may be updated by the git pull below
rem while cmd is still reading it. All real logic lives in scripts\start.bat, which is loaded after the pull.
setlocal
cd /d "%~dp0"
if "%~1"=="--no-update" goto start
if not exist ".git" goto start
where git >nul 2>nul
if errorlevel 1 goto start
echo [labelon-reviewer] checking for updates - git pull...
git pull --ff-only > "%TEMP%\labelon_pull.txt" 2>&1
if errorlevel 1 goto pullfail
findstr /C:"Already up to date" "%TEMP%\labelon_pull.txt" >nul
if errorlevel 1 goto reinstall
echo [labelon-reviewer] already up to date.
goto start

:reinstall
echo [labelon-reviewer] updated. Reinstalling package...
if exist ".venv\Scripts\python.exe" ".venv\Scripts\python.exe" -m pip install -q -e . >nul 2>&1
goto start

:pullfail
echo [labelon-reviewer] update skipped - network or conflict. Running current version.
type "%TEMP%\labelon_pull.txt"
goto start

:start
call "%~dp0scripts\start.bat" %*
endlocal & exit /b %ERRORLEVEL%
