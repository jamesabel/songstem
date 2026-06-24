@echo off
REM Create the .venv and install songstem with dev dependencies (editable).
REM Run from the project root: setup_venv.bat
REM
REM Uses Python 3.13 explicitly: PySide6 6.11 crashes (0xC0000409 in Qt6Core.dll) on
REM Python 3.14, which is not yet a supported target. Do NOT create the venv with a bare
REM "python" (which may resolve to 3.14).
setlocal

cd /d "%~dp0"

if exist .venv (
    echo .venv already exists. Delete it first to recreate.
    goto :install
)

echo Creating virtual environment in .venv (Python 3.13) ...
py -3.13 -m venv .venv
if errorlevel 1 (
    echo Failed to create virtual environment with Python 3.13.
    echo Install Python 3.13 from https://www.python.org/downloads/ and retry.
    exit /b 1
)

:install
echo Upgrading pip ...
call .venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo Installing songstem with dev extras ...
call .venv\Scripts\python.exe -m pip install -e ".[dev]"
if errorlevel 1 exit /b 1

echo.
echo Done. Activate with:  .venv\Scripts\activate.bat
endlocal
