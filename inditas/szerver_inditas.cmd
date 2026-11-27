@echo off
if "%~1"=="--elso-admin" (
 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0inditas.ps1" -Kiszolgalo -ElsoAdmin
) else (
 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0inditas.ps1" -Kiszolgalo %*
)
if errorlevel 1 pause
