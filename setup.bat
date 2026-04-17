@echo off
REM Medicus Dictate — one-time setup.
REM Creates a Python virtual environment and installs dependencies.
setlocal
set "ROOT=%~dp0"
set "APP=%ROOT%medicus-dictate"
set "VENV=%ROOT%.venv"

echo.
echo ========================================
echo   Medicus Dictate - first-time setup
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found.
    echo.
    echo Please install Python 3.10 or newer from:
    echo     https://www.python.org/downloads/
    echo.
    echo When the installer runs, make sure to tick
    echo     [x] Add Python to PATH
    echo.
    echo Then close this window and run setup.bat again.
    echo.
    pause
    exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
    echo Creating a Python environment in .venv ...
    python -m venv "%VENV%"
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
echo The first launch downloads a speech model ^(about 470 MB^) — one-off.
echo.
pause
