@echo off
REM UV-based Windows build script for PyQt5 application

echo ================================
echo Building PyQt5 App with UV
echo ================================

REM Check if UV is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo UV is not installed. Installing UV...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    REM Add UV to PATH for this session
    set PATH=%USERPROFILE%\.cargo\bin;%PATH%
)

echo UV version:
uv --version

REM Setup virtual environment with UV
echo.
echo Setting up virtual environment with UV...
uv venv

REM Install dependencies with UV
echo.
echo Installing dependencies with UV...
call .venv\Scripts\activate.bat
uv sync

REM Build executable
echo.
echo Building executable...
python build_dist.py --name brillouinview --entry-point ..\src\main.py 

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ================================
echo Build Complete!
echo Executable location: dist\brillouinview.exe
echo ================================

pause
