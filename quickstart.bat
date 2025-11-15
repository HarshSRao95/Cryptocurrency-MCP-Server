@echo off
REM MCP Crypto Server - Quick Start Setup Script for Windows
REM This script automates the setup process

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  MCP Crypto Server - Quick Start Setup
echo ========================================
echo.

REM Step 1: Check Python
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.9 or higher from https://www.python.org
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Found Python %PYTHON_VERSION%

REM Step 2: Check pip
echo [INFO] Checking pip installation...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed!
    echo Please run: python -m ensurepip
    pause
    exit /b 1
)
echo [OK] pip is installed

REM Step 3: Create virtual environment
echo.
echo ========================================
echo  Setting up Virtual Environment
echo ========================================
echo.

if exist venv (
    echo [WARNING] Virtual environment already exists
    set /p RECREATE="Do you want to recreate it? (y/n): "
    if /i "!RECREATE!"=="y" (
        echo [INFO] Removing old virtual environment...
        rmdir /s /q venv
    ) else (
        echo [INFO] Using existing virtual environment
        goto :activate
    )
)

echo [INFO] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment created

:activate
REM Step 4: Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated

REM Step 5: Upgrade pip
echo.
echo ========================================
echo  Upgrading pip
echo ========================================
echo.
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded

REM Step 6: Install dependencies
echo.
echo ========================================
echo  Installing Dependencies
echo ========================================
echo.

if not exist requirements.txt (
    echo [ERROR] requirements.txt not found!
    pause
    exit /b 1
)

echo [INFO] Installing packages (this may take a few minutes)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] All dependencies installed

REM Step 7: Verify installation
echo.
echo ========================================
echo  Verifying Installation
echo ========================================
echo.

echo [INFO] Checking ccxt...
python -c "import ccxt; print('ccxt', ccxt.__version__)" 2>nul
if errorlevel 1 (
    echo [ERROR] ccxt verification failed
) else (
    echo [OK] ccxt OK
)

echo [INFO] Checking pydantic...
python -c "import pydantic; print('pydantic', pydantic.__version__)" 2>nul
if errorlevel 1 (
    echo [ERROR] pydantic verification failed
) else (
    echo [OK] pydantic OK
)

echo [INFO] Checking pytest...
python -c "import pytest; print('pytest', pytest.__version__)" 2>nul
if errorlevel 1 (
    echo [ERROR] pytest verification failed
) else (
    echo [OK] pytest OK
)

REM Step 8: Run tests
echo.
echo ========================================
echo  Running Tests
echo ========================================
echo.

if exist test_mcp_crypto_server.py (
    echo [INFO] Running test suite...
    pytest test_mcp_crypto_server.py -v --tb=short
    if errorlevel 1 (
        echo [WARNING] Some tests failed, but installation is complete
    ) else (
        echo [OK] All tests passed!
    )
) else (
    echo [WARNING] Test file not found, skipping tests
)

REM Step 9: Create .env file
echo.
echo ========================================
echo  Configuration
echo ========================================
echo.

if exist .env.example (
    if not exist .env (
        echo [INFO] Creating .env file from template...
        copy .env.example .env >nul
        echo [OK] .env file created (customize as needed)
    )
)

REM Step 10: Test run
echo.
echo ========================================
echo  Test Run
echo ========================================
echo.

if exist mcp_crypto_server.py (
    echo [INFO] Running a quick test...
    python -c "import asyncio; from mcp_crypto_server import CryptoMCPServer, MarketDataRequest, Exchange; asyncio.run((lambda: CryptoMCPServer().get_ticker(MarketDataRequest(symbol='BTC/USDT', exchange=Exchange.BINANCE)))())"
    if errorlevel 1 (
        echo [WARNING] Server test failed, but installation is complete
    ) else (
        echo [OK] Server is working!
    )
)

REM Final message
echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Your MCP Crypto Server is ready to use!
echo.
echo Next steps:
echo   1. Activate the virtual environment:
echo      venv\Scripts\activate
echo.
echo   2. Run the main application:
echo      python mcp_crypto_server.py
echo.
echo   3. Try the examples:
echo      python examples.py
echo.
echo   4. Run tests:
echo      pytest test_mcp_crypto_server.py -v
echo.
echo   5. View documentation:
echo      type README.md
echo.
echo Happy coding!
echo.
pause