@echo off
setlocal
chcp 65001 >nul
title Suite de documentos
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Prepare o ambiente seguindo o README.md: python -m venv .venv
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -c "import fastapi, uvicorn, multipart, jinja2, pypdf" >nul 2>&1
if errorlevel 1 (
    echo Instale as dependencias com:
    echo .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0start_suite.py" %*
set "suiteResult=%ERRORLEVEL%"
echo.
pause
exit /b %suiteResult%
