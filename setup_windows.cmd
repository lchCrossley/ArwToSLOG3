@echo off
setlocal
pushd "%~dp0" || exit /b 1

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Python 3.11 or newer was not found as the 'python' command.
    echo Check your Python installation, then run this file again.
    set "result=1"
    goto finish
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating this project's private Python environment...
    python -m venv ".venv"
    if errorlevel 1 (
        echo Could not create .venv. Check that Python includes the venv module.
        set "result=1"
        goto finish
    )
)

echo Installing the project and required libraries. Internet access is needed the first time.
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
    echo Installation failed. Check the error above and your Internet connection.
    set "result=1"
    goto finish
)

echo Setup complete. Drag one .ARW file onto convert_windows.cmd.
set "result=0"

:finish
echo.
pause
popd
exit /b %result%
