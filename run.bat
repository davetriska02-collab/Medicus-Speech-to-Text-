@echo off
REM Medicus Dictate — day-to-day launcher.
setlocal
set "ROOT=%~dp0"
set "APP=%ROOT%medicus-dictate"
set "VENV=%ROOT%.venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo The Python environment is missing.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

call "%VENV%\Scripts\activate.bat"
cd /d "%APP%"
python -m src
