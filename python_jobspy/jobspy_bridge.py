#!/usr/bin/env python3
"""
JobSpy Bridge - Python wrapper for JobSpy library

This script provides a JSON interface to JobSpy for use by the Rust ATS program.
It reads search parameters from stdin as JSON and outputs results as JSON.

Usage:
    python jobspy_bridge.py < search_params.json
    
Input JSON format:
    {
        "source": "linkedin",  # or "indeed", "glassdoor", "google", "zip_recruiter"
        "keywords": "software engineer",
        "location": "San Francisco, CA",
        "max_results": 50,
        "remote_only": false,
        "date_posted": "24h"  # optional: "24h", "3d", "7d", "30d"
    }

Output JSON format:
    {
        "success": true,
        "jobs": [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "location": "San Francisco, CA",
                "description": "Job description...",
                "url": "https://...",
                "source": "linkedin",
                "salary": "$100k-$150k",
                "posted_date": "2024-01-15"
            }
        ],
        "count": 1
    }
"""

import json
import sys
from typing import Dict, List, Any, Optional

try:
    from jobspy import scrape_jobs
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "JobSpy not installed. Run: pip install python-jobspy"
    }), file=sys.stderr)
    sys.exit(1)


def search_jobs(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for jobs using JobSpy.
    
    Args:
        params: Dictionary containing search parameters
        
    Returns:
        Dictionary with success status and job results
    """
    try:
        source = params.get("source", "linkedin")
        keywords = params.get("keywords", "")
        location = params.get("location", "")
        max_results = params.get("max_results", 50)
        remote_only = params.get("remote_only", False)
        date_posted = params.get("date_posted")
        
        # Map our source names to JobSpy site names
        site_map = {
            "linkedin": "linkedin",
            "indeed": "indeed",
            "glassdoor": "glassdoor",
            "google": "google",
            "zip_recruiter": "zip_recruiter"
        }
        
        site = site_map.get(source, "linkedin")
        
        # Build JobSpy parameters
        jobspy_params = {
            "site_name": [site],
            "search_term": keywords,
            "location": location,
            "results_wanted": max_results,
            "is_remote": remote_only
        }
        
        # Only add hours_old if specified
        hours = get_hours_old(date_posted)
        if hours is not None:
            jobspy_params["hours_old"] = hours
        
        # Call JobSpy
        jobs_df = scrape_jobs(**jobspy_params)
        
        # Convert DataFrame to list of dictionaries
        jobs = []
        for _, row in jobs_df.iterrows():
            job = {
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "location": str(row.get("location", "")),
                "description": str(row.get("description", "")),
                "url": str(row.get("job_url", "")),
                "source": source,
                "salary": str(row.get("salary", "")),
                "posted_date": str(row.get("date_posted", ""))
            }
            jobs.append(job)
        
        return {
            "success": True,
            "jobs": jobs,
            "count": len(jobs)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_hours_old(date_posted: Optional[str]) -> Optional[int]:
    """Convert date_posted string to hours."""
    if not date_posted:
        return None
    
    mapping = {
        "24h": 24,
        "3d": 72,
        "7d": 168,
        "30d": 720
    }
    return mapping.get(date_posted)


def main():
    """Main entry point."""
    try:
        # Read JSON from stdin
        input_data = sys.stdin.read()
        params = json.loads(input_data)
        
        # Search for jobs
        result = search_jobs(params)
        
        # Output JSON to stdout
        print(json.dumps(result, indent=2))
        
    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "error": f"Invalid JSON input: {e}"
        }), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Unexpected error: {e}"
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
