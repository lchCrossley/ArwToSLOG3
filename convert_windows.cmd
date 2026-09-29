@echo off
setlocal
pushd "%~dp0" || exit /b 1

if not exist ".venv\Scripts\python.exe" (
    echo Environment not found. Run setup_windows.cmd first.
    set "result=1"
    goto finish
)
if "%~1"=="" (
    echo Drag one .ARW file onto convert_windows.cmd.
    set "result=1"
    goto finish
)
if not "%~2"=="" (
    echo Please drag only one .ARW file at a time.
    set "result=1"
    goto finish
)
if /i not "%~x1"==".arw" (
    echo Input must be an .ARW file.
    set "result=1"
    goto finish
)
if not exist "%~f1" (
    echo Input file was not found.
    set "result=1"
    goto finish
)

set "output=%~dpn1_SLog3.tif"
".venv\Scripts\python.exe" "arw_to_slog3.py" "%~f1" "%output%"
set "result=%errorlevel%"
if "%result%"=="0" echo Saved: "%output%"

:finish
echo.
pause
popd
exit /b %result%
