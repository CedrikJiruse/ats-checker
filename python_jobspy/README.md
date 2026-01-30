# JobSpy Python Bridge

This directory contains a Python bridge that allows the Rust ATS Resume Checker to use the JobSpy library for job scraping.

## Overview

Since JobSpy is a Python library, this bridge provides a JSON-based interface between the Rust application and Python. The Rust code calls the Python bridge script with search parameters via stdin, and receives job results as JSON via stdout.

## Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Quick Setup

**Windows:**
```batch
python_jobspy\setup_windows.bat
```

**Linux/Mac:**
```bash
cd python_jobspy
./setup.sh
```

### Manual Setup

If the setup scripts don't work, you can manually install:

```bash
cd python_jobspy
pip install -r requirements.txt
```

Or install directly:

```bash
pip install python-jobspy pandas
```

## How It Works

1. **Rust Side**: The `JobSpyScraper` in Rust creates a subprocess running `jobspy_bridge.py`
2. **Communication**: Search parameters are sent as JSON to the Python script via stdin
3. **Python Side**: The bridge script uses JobSpy to scrape jobs from various sources
4. **Results**: Jobs are returned as JSON to Rust via stdout

### Input Format (JSON sent to Python)

```json
{
    "source": "linkedin",
    "keywords": "software engineer",
    "location": "San Francisco, CA",
    "max_results": 50,
    "remote_only": false,
    "date_posted": "24h"
}
```

### Output Format (JSON returned from Python)

```json
{
    "success": true,
    "jobs": [
        {
            "title": "Senior Software Engineer",
            "company": "Tech Corp",
            "location": "San Francisco, CA",
            "description": "We are looking for a senior software engineer...",
            "url": "https://linkedin.com/jobs/view/123456",
            "source": "linkedin",
            "salary": "$120k-$180k",
            "posted_date": "2024-01-20"
        }
    ],
    "count": 1
}
```

## Supported Job Sources

- **LinkedIn** (`linkedin`) - Professional networking jobs
- **Indeed** (`indeed`) - General job board
- **Glassdoor** (`glassdoor`) - Company reviews and jobs
- **Google Jobs** (`google`) - Aggregated from various sources
- **ZipRecruiter** (`zip_recruiter`) - General job board

## Testing

You can test the bridge manually:

```bash
echo '{"source": "linkedin", "keywords": "software engineer", "location": "San Francisco", "max_results": 5}' | python python_jobspy/jobspy_bridge.py
```

## Troubleshooting

### "Python not found"

Make sure Python is installed and in your PATH:
- Windows: Download from https://python.org
- Linux: `sudo apt-get install python3 python3-pip`
- Mac: `brew install python3`

### "JobSpy not installed"

Run the setup script or manually install:
```bash
pip install python-jobspy pandas
```

### "No jobs found"

- Try different keywords
- Check your internet connection
- Some sources may require authentication for heavy usage
- LinkedIn and Glassdoor may have rate limiting

### Rate Limiting

If you see errors about rate limiting:
- Reduce the number of requests
- Add delays between searches
- Use different job sources
- Some sources (LinkedIn) may require authentication

## Files

- `jobspy_bridge.py` - Main Python bridge script
- `requirements.txt` - Python dependencies
- `setup_windows.bat` - Windows setup script
- `setup.sh` - Linux/Mac setup script

## License

This bridge uses the JobSpy library which has its own license. Please respect the terms of service of the job sites you're scraping.
