@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo   OmniLink Universal IoT Platform - Bootstrapper
echo =======================================================
echo [1/4] Checking Python runtime environment...

where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [!] Python was not found in PATH. Attempting winget install...
        winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        if %errorlevel% neq 0 (
            echo [X] Could not auto-install Python. Please install Python 3.10+ from python.org.
            pause
            exit /b 1
        )
    )
)

:: Find python executable
set "PYTHON_EXE=python"
where %PYTHON_EXE% >nul 2>nul
if %errorlevel% neq 0 (
    set "PYTHON_EXE=py"
)

echo [2/4] Setting up isolated virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    echo [*] Creating fresh .venv...
    %PYTHON_EXE% -m venv .venv
    if %errorlevel% neq 0 (
        echo [X] Failed to create virtualenv. Exiting.
        pause
        exit /b 1
    )
)

echo [3/4] Quietly installing and updating project dependencies...
.\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
if %errorlevel% neq 0 (
    echo [X] Dependency installation encountered an issue.
    pause
    exit /b 1
)

echo [4/4] Preparing directories and launching OmniLink Monolith on http://localhost:8000...
if not exist "uploads\avatars" mkdir uploads\avatars

start "" "http://localhost:8000"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
