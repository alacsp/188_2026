@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0inditas.ps1" %*
if errorlevel 1 pause
