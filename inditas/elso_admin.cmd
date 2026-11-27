@echo off
call "%~dp0szerver_inditas.cmd" --elso-admin
if not errorlevel 1 pause
