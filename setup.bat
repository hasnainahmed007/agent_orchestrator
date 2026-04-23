@echo off
REM Setup script for Agent Orchestrator on Windows

echo ========================================
echo 🤖 Agent Orchestrator Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    exit /b 1
)

echo ✅ Python found
echo.

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies
    exit /b 1
)

echo ✅ Dependencies installed
echo.

REM Create .env if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Edit .env file and add your API keys!
    echo.
    echo You need to set:
    echo   - OPENAI_API_KEY
    echo   - TELEGRAM_BOT_TOKEN
    echo   - TELEGRAM_ALLOWED_USERS
    echo.
) else (
    echo ✅ .env file already exists
)

echo.
echo ========================================
echo 🎉 Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file with your API keys
echo 2. Run: venv\Scripts\activate
echo 3. Run: python main.py --mode cli
echo.
echo To start Telegram bot:
echo   python main.py --mode telegram
echo.
echo For help:
echo   python main.py --help
echo.

pause