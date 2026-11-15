@echo off
title Previa visual da suite
if not exist "%~dp0outputs\testar-visual.html" (
    echo Nao foi encontrado o arquivo outputs\testar-visual.html.
    pause
    exit /b 1
)
start "" "%~dp0outputs\testar-visual.html"
