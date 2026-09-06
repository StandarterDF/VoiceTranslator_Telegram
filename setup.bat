@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo ======================================
echo   VoiceTranslator - Setup
echo ======================================
echo.

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in PATH. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)
echo [1/3] Python found:
python --version
echo.

:: Create virtual environment if not exists
if exist "%~dp0venv\Scripts\python.exe" (
    echo [2/3] Virtual environment already exists, skipping creation.
) else (
    echo [2/3] Creating virtual environment...
    python -m venv "%~dp0venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
)
echo.

:: Install dependencies
echo [3/3] Upgrading pip and installing dependencies...
"%~dp0venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 (
    echo [WARNING] pip upgrade failed, continuing anyway.
)
"%~dp0venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed.
echo.

:: Copy .env.example to .env if .env does not exist
if not exist "%~dp0.env" (
    echo Copying .env.example to .env (you need to edit it with your BOT_TOKEN).
    copy "%~dp0.env.example" "%~dp0.env" >nul
    echo.
) else (
    echo .env already exists, skipping.
    echo.
)

echo ======================================
echo   Setup complete!
echo   Edit .env with your BOT_TOKEN,
echo   then run start.bat
echo ======================================
pause
