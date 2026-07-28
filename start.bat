@echo off
chcp 65001 >nul
"%~dp0venv\Scripts\python.exe" "%~dp0VoiceTranslator.py"
pause
