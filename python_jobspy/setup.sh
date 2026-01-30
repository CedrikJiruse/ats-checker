#!/bin/bash
set -e

echo "Setting up JobSpy Bridge for ATS Resume Checker"
echo "================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "Found Python installation:"
python3 --version
echo ""

# Install dependencies
echo "Installing JobSpy and dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Setup completed successfully!"
echo ""
echo "You can now use job scraping in the ATS Resume Checker."
echo "Make sure to set your API keys if needed:"
echo "  - LinkedIn: May require authentication for heavy usage"
echo "  - Indeed: Generally works without API key"
echo "  - Glassdoor: May have rate limiting"
