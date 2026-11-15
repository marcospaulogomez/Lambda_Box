@echo off
setlocal
chcp 65001 >nul
title Prova de conversao da suite
cd /d "%~dp0"
if not defined LIBREOFFICE_PATH (
    if exist "%~dp0laboratory\engine\program\soffice.com" (
        set "LIBREOFFICE_PATH=%~dp0laboratory\engine\program\soffice.com"
    )
)
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0validate_conversion.py" %*
) else if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" "%~dp0validate_conversion.py" %*
) else (
    python "%~dp0validate_conversion.py" %*
)
set "conversionResult=%ERRORLEVEL%"
echo.
pause
exit /b %conversionResult%
