@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo.
echo ======================================
echo   VoiceTranslator Telegram Bot
echo ======================================
echo.
echo Select launch mode:
echo  1 - TUI interface (recommended)
echo  2 - Run via CMD (select model in console)
set /p choice=">>> "

if "%choice%"=="1" (
    echo Starting TUI interface...
    "%~dp0venv\Scripts\python.exe" "%~dp0tui_app.py"
    if errorlevel 1 (
        echo Error. Try: pip install textual
        pause
    )
) else if "%choice%"=="2" (
    echo.
    echo Select STT provider:
    echo  1 - Vosk (local, low quality)
    echo  2 - Google Speech (online, + punctuation)
    echo  3 - Whisper tiny  (~75 MB)
    echo  4 - Whisper base  (~150 MB)
    echo  5 - Whisper small (~500 MB)
    echo  6 - Whisper large-v3-turbo (~1.2 GB, best)
    echo  Enter - use default (from .env)
    set /p prov_choice=">>> "

    set "PROVIDER="
    set "SIZE="
    if "%prov_choice%"=="1" set PROVIDER=vosk
    if "%prov_choice%"=="2" set PROVIDER=google
    if "%prov_choice%"=="3" set PROVIDER=faster_whisper& set SIZE=tiny
    if "%prov_choice%"=="4" set PROVIDER=faster_whisper& set SIZE=base
    if "%prov_choice%"=="5" set PROVIDER=faster_whisper& set SIZE=small
    if "%prov_choice%"=="6" set PROVIDER=faster_whisper& set SIZE=large-v3-turbo

    echo.
    echo Enable LLM post-processing (punctuation correction)? [y/n]
    set /p llm_choice=">>> "

    set "LLM_ARG="
    if /i "%llm_choice%"=="y" set LLM_ARG=--llm on
    if /i "%llm_choice%"=="д" set LLM_ARG=--llm on

    echo.
    echo Starting via CMD...
    if defined PROVIDER (
        if defined SIZE (
            "%~dp0venv\Scripts\python.exe" "%~dp0run.py" --provider !PROVIDER! --size !SIZE! !LLM_ARG!
        ) else (
            "%~dp0venv\Scripts\python.exe" "%~dp0run.py" --provider !PROVIDER! !LLM_ARG!
        )
    ) else (
        "%~dp0venv\Scripts\python.exe" "%~dp0run.py" !LLM_ARG!
    )
    pause
) else (
    echo Invalid choice.
    pause
)
