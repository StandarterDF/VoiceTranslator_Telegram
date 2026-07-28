@echo off
chcp 65001 >nul
call "%~dp0venv\Scripts\activate"
python "%~dp0VoiceTranslator.py"
pause
