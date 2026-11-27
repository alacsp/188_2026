@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0adatbazis_telepites.ps1" %*
if errorlevel 1 (pause) else (echo A muvelet sikeres. & pause)
