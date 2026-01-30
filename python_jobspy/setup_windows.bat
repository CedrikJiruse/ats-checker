@echo off
echo Setting up JobSpy Bridge for ATS Resume Checker
echo =================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    exit /b 1
)

echo Found Python installation:
python --version
echo.

REM Install dependencies
echo Installing JobSpy and dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo You can now use job scraping in the ATS Resume Checker.
echo Make sure to set your API keys if needed:
echo   - LinkedIn: May require authentication for heavy usage
echo   - Indeed: Generally works without API key
echo   - Glassdoor: May have rate limiting
echo.
pause
