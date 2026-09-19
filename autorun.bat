@echo off
title Naissance
echo [Naissance HGIS] Ensuring dependencies are up-to-date.
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not installed or not in your PATH.
    echo Please install Node.js from https://nodejs.org/en/download
    pause
    exit /b
)
if not exist "node_modules\" (
    echo [Naissance HGIS] node_modules not found. Installing dependencies...
    call npm install
)
echo [Naissance HGIS] Auto-run is starting ..
echo [Naissance HGIS] Depending on your system, this may take a while.

call npm start

if %ERRORLEVEL% neq 0 (
    echo [Naissance HGIS] Application exited with error code %ERRORLEVEL%.
    pause
)