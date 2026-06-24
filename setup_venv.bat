@echo off
REM Create the .venv and install songstem with dev dependencies (editable).
REM Run from the project root: setup_venv.bat
setlocal

cd /d "%~dp0"

if exist .venv (
    echo .venv already exists. Delete it first to recreate.
    goto :install
)

echo Creating virtual environment in .venv ...
python -m venv .venv
if errorlevel 1 (
    echo Failed to create virtual environment. Is Python on PATH?
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
