@echo off
REM Medicus Dictate - one-time setup.
REM Creates a Python virtual environment and installs dependencies.
REM Works without admin rights if a portable Python (e.g. WinPython) is
REM placed next to this script.
setlocal
set "ROOT=%~dp0"
set "APP=%ROOT%medicus-dictate"
set "VENV=%ROOT%.venv"
set "PY="

echo.
echo ========================================
echo   Medicus Dictate - first-time setup
echo ========================================
echo.

REM 1. Prefer a bundled portable Python (folder named "python" next to us).
if exist "%ROOT%python\python.exe" (
    set "PY=%ROOT%python\python.exe"
    goto found_py
)

REM 2. Auto-detect a WinPython extract next to us.
for /d %%D in ("%ROOT%WinPython*") do (
    for /d %%P in ("%%D\python-*") do (
        if exist "%%P\python.exe" (
            set "PY=%%P\python.exe"
            goto found_py
        )
    )
)

REM 3. Fall back to system Python on PATH.
where python >nul 2>nul
if not errorlevel 1 (
    set "PY=python"
    goto found_py
)

REM 4. Nothing found.  Explain both admin and no-admin routes.
echo Python was not found on this PC.
echo.
echo If you have admin rights:
echo     Install Python 3.10 or newer from
echo         https://www.python.org/downloads/
echo     When the installer runs, tick [x] "Add Python to PATH".
echo.
echo If you do NOT have admin rights (NHS, corporate, locked-down):
echo     1. Go to https://winpython.github.io/ and download the latest
echo        "WinPython64" ZIP.
echo     2. Extract the ZIP anywhere.
echo     3. Inside the extracted folder you will see a folder called
echo        something like "python-3.11.4.amd64".  Rename that folder
echo        to just "python".
echo     4. Move that "python" folder next to this setup.bat file.
echo     5. Run setup.bat again - it will use the portable Python
echo        with no admin rights needed.
echo.
pause
exit /b 1

:found_py
echo Using Python: %PY%
echo.

if not exist "%VENV%\Scripts\python.exe" (
    echo Creating a Python environment in .venv ...
    "%PY%" -m venv "%VENV%"
    if errorlevel 1 (
        echo.
        echo Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

call "%VENV%\Scripts\activate.bat"

echo Installing dependencies ^(this can take a few minutes the first time^)...
python -m pip install --upgrade pip >nul
pip install -r "%APP%\requirements.txt"
if errorlevel 1 (
    echo.
    echo Dependency install failed. Scroll up for the error.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Setup complete.
echo ========================================
echo.
echo Next: double-click run.bat to start Medicus Dictate.
echo The first launch downloads a speech model ^(about 470 MB^) - one-off.
echo.
pause
