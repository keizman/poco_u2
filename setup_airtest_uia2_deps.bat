@echo off
setlocal
set SCRIPT_DIR=%~dp0
echo Poco root: %SCRIPT_DIR%
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%setup_airtest_uia2_deps.ps1" -PocoRoot "%SCRIPT_DIR%"
echo.
echo If successful, restart AirtestIDE and try again.
pause

