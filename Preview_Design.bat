@echo off
title Previa visual da suite
if not exist "%~dp0outputs\design-preview.html" (
    echo Nao foi encontrado o arquivo outputs\design-preview.html.
    pause
    exit /b 1
)
start "" "%~dp0outputs\design-preview.html"
