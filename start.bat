@echo off
chcp 65001 >nul
echo.
echo ======================================
echo   VoiceTranslator Telegram Bot
echo ======================================
echo.
echo Select launch mode:
echo  1 - TUI interface (recommended)
echo  2 - Classic console mode
set /p choice=">>> "

if "%choice%"=="2" (
    echo Starting in classic mode...
    "%~dp0venv\Scripts\python.exe" "%~dp0VoiceTranslator.py"
    pause
) else (
    echo Starting TUI interface...
    "%~dp0venv\Scripts\python.exe" "%~dp0tui_app.py"
    if errorlevel 1 (
        echo Error. Try: pip install textual
        pause
    )
)
