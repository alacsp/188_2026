@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\inditas\inditas.ps1" -Telepites %*
if errorlevel 1 (pause) else (echo A telepites sikeres. & pause)
