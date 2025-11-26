@echo off
chcp 65001 > nul
title Dawn of Stellar - Game Launcher

REM Check for embedded Python first
if exist "python\python.exe" (
    set "PYTHON_EXE=%~dp0python\python.exe"
    echo Using embedded Python
    goto RunLauncher
)

REM Check for virtual environment second
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
    echo Using virtual environment Python
    goto RunLauncher
)

REM Fallback to system Python search
set "PYTHON_EXE="
if exist "python.exe" (
    set "PYTHON_EXE=python.exe"
) else (
    REM Try to find Python in common locations
    if exist "C:\Python*\python.exe" (
        for /d %%i in ("C:\Python*") do if exist "%%i\python.exe" set "PYTHON_EXE=%%i\python.exe"
    )
    if exist "%PROGRAMFILES%\Python*\python.exe" (
        for /d %%i in ("%PROGRAMFILES%\Python*") do if exist "%%i\python.exe" set "PYTHON_EXE=%%i\python.exe"
    )
    if exist "%PROGRAMFILES(x86)%\Python*\python.exe" (
        for /d %%i in ("%PROGRAMFILES(x86)%\Python*") do if exist "%%i\python.exe" set "PYTHON_EXE=%%i\python.exe"
    )
)

REM Check if Python is found
if "%PYTHON_EXE%"=="" (
    REM Last resort: try python command
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Error: Python is not found.
        echo Please ensure Python 3.10+ is installed.
        echo.
        echo You can download it from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    ) else (
        set "PYTHON_EXE=python"
    )
)

:RunLauncher
echo Using Python: %PYTHON_EXE%
echo Starting game launcher...
echo.

REM 게임 런처 실행
"%PYTHON_EXE%" main.py

REM 오류 발생 시 대기
if errorlevel 1 (
    echo.
    echo Error occurred while running the launcher.
    echo This might be due to missing dependencies or configuration issues.
    echo.
    echo Try running the following commands manually:
    echo   "%PYTHON_EXE%" -m pip install -r requirements.txt
    echo   "%PYTHON_EXE%" main.py
    echo.
    pause
)
