@echo off
REM Create the .venv and install songstem with dev dependencies (editable).
REM Run from the project root: setup_venv.bat
REM
REM Uses regular Python 3.14 explicitly. Do NOT use the free-threaded "3.14t" (no-GIL)
REM build or a bare "python" that may resolve to it — torch/PySide6/numba have no
REM free-threaded wheels.
setlocal

cd /d "%~dp0"

if exist .venv (
    echo .venv already exists. Delete it first to recreate.
    goto :install
)

echo Creating virtual environment in .venv (Python 3.14) ...
py -3.14 -m venv .venv
if errorlevel 1 (
    echo Failed to create virtual environment with Python 3.14.
    echo Install Python 3.14 (regular, not free-threaded) and retry.
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
