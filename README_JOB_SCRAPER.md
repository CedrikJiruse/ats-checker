# Job Scraper Feature

## Overview

The ATS Resume Checker now includes comprehensive job scraping functionality that allows you to search for jobs across multiple job sites, save searches for reuse, and export job descriptions for resume tailoring.

## Supported Job Sites

- **LinkedIn**: Professional networking and job search
- **Indeed**: Leading job search engine
- **Jobs.ie**: Irish job market specialist

## Features

### 1. New Job Search
Search for jobs with comprehensive filtering options:
- **Keywords**: Job title, skills, or keywords
- **Location**: City, region, or "Remote"
- **Job Type**: Full-time, Part-time, Contract, Internship
- **Remote Only**: Filter for remote positions
- **Experience Level**: Entry, Mid, Senior, Director, Executive
- **Date Posted**: Last 24 hours, week, month, or any time

### 2. Saved Searches
- Save your search configurations for quick reuse
- View search history and last run statistics
- Edit or delete saved searches
- Run saved searches with one click

### 3. Search Results Management
- Automatically save all search results with timestamps
- View previously saved results
- Browse job listings with full details
- Track search statistics (number of results, last run date)

### 4. Export to Job Descriptions
- Export scraped jobs to the job descriptions folder
- Automatically format job postings as text files
- Use exported jobs to tailor your resumes
- Select specific jobs or export all results

## Installation

### Install Required Dependencies

```bash
pip install -r requirements.txt
```

The new dependencies include:
- `requests`: For making HTTP requests
- `beautifulsoup4`: For parsing HTML
- `lxml`: For faster HTML parsing

### Configure Settings

The following settings are available in `config.json`:

```json
{
  "job_search_results_folder": "job_search_results",
  "max_job_results_per_search": 50
}
```

- `job_search_results_folder`: Where to save search results (default: "job_search_results")
- `max_job_results_per_search`: Maximum results per search (default: 50)

## Usage

### Access the Job Search Menu

1. Run the ATS Resume Checker: `python main.py`
2. Select option **3. Job Search & Scraping**

### Perform a New Search

1. Choose "1. New job search"
2. Select a job site or search all sites
3. Enter your search criteria:
   - Keywords (e.g., "software engineer python")
   - Location (e.g., "Dublin", "Remote")
   - Job type (Full-time, Part-time, etc.)
   - Remote only filter
   - Experience level
   - Date posted filter
4. Optionally save the search for later
5. View results

### Save and Reuse Searches

1. When performing a new search, choose "y" when asked to save
2. Give your search a descriptive name
3. Later, use "3. Run saved search" to quickly rerun it
4. Manage saved searches with "2. Manage saved searches"

### Export Jobs for Resume Tailoring

1. Go to "4. View saved results"
2. Select a result file to view
3. Then use "5. Export jobs to job descriptions folder"
4. Select a result file and specify how many jobs to export
5. The jobs will be saved to your `job_descriptions_folder`
6. Use these job descriptions when processing resumes

## Data Storage

### Search Results
Search results are stored in JSON format in the `job_search_results_folder`:
- Filename format: `{source}_{timestamp}.json` or `{search_name}_{timestamp}.json`
- Contains full job details: title, company, location, description, URL, etc.

### Saved Searches
Saved search configurations are stored in `saved_searches.json`:
- Search name and source
- Filter criteria
- Creation date and last run statistics

## Important Notes

### Web Scraping Considerations

1. **Rate Limiting**: The scrapers include basic rate limiting, but be mindful of making too many requests
2. **Terms of Service**: Ensure your use complies with each site's terms of service
3. **Anti-Scraping**: LinkedIn and Indeed have anti-scraping measures; results may vary
4. **Accuracy**: Web scraping is fragile and may break if sites change their HTML structure

### Best Practices

1. **Use Responsibly**: Don't hammer job sites with too many requests
2. **Verify Results**: Always verify job details on the original site
3. **Keep Updated**: Site structures change; scrapers may need updates
4. **Legal Compliance**: Only use for personal job searching purposes

### Limitations

- Scrapers may not work if job sites change their HTML structure
- Some sites may block automated requests
- Results may be limited compared to manual browsing
- Detailed job descriptions may not always be available

## Architecture

### Core Classes

**JobPosting**: Represents a single job listing
- title, company, location, description
- url, source, posted_date
- salary, job_type, remote, experience_level

**SearchFilters**: Search criteria
- keywords, location
- job_type, remote_only
- experience_level, salary_min, date_posted

**SavedSearch**: Persistent search configuration
- name, source, filters
- created_at, last_run, results_count

**BaseJobScraper**: Abstract base for scrapers
- search_jobs(): Perform a search
- get_job_details(): Get detailed job info
- save_results(): Save to file
- load_results(): Load from file

**JobScraperManager**: Coordinates multiple scrapers
- Manages all available scrapers
- Handles saved searches
- Exports to job descriptions

### Extensibility

To add a new job site:

1. Create a new class inheriting from `BaseJobScraper`
2. Implement `search_jobs()` and `get_job_details()`
3. Add the scraper to `JobScraperManager.__init__()`

Example:

```python
class NewSiteScraper(BaseJobScraper):
    def __init__(self):
        super().__init__("NewSite")

    def search_jobs(self, filters, max_results=50):
        # Implementation
        pass

    def get_job_details(self, job_url):
        # Implementation
        pass
```

## Workflow Example

1. **Search for Jobs**:
   - Search for "software engineer" in "Dublin"
   - Filter for "Full-time" and "Remote"
   - Save search as "Dublin Software Jobs"

2. **Review Results**:
   - View the jobs found
   - Results saved automatically

3. **Export for Resume Tailoring**:
   - Export top 5 jobs to job descriptions folder
   - Jobs appear as text files in `job_descriptions/`

4. **Process Resumes**:
   - Use "1. Process resumes" from main menu
   - Select one of the exported job descriptions
   - Generate tailored resume

5. **Rerun Periodically**:
   - Use "3. Run saved search" to check for new jobs
   - Export new interesting positions
   - Continue tailoring resumes

## Troubleshooting

### No Results Found
- Try broader keywords
- Check your internet connection
- The job site may have changed its structure
- Try a different job site

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version compatibility

### Slow Performance
- Reduce `max_job_results_per_search` in config
- Search one site at a time instead of all sites
- Some sites are naturally slower to scrape

## Future Enhancements

Potential improvements:
- Add more job sites (Glassdoor, Monster, etc.)
- Implement caching to avoid duplicate requests
- Add proxy support for better reliability
- Implement headless browser for JavaScript-heavy sites
- Add email notifications for new jobs
- Implement advanced filtering (salary ranges, company size, etc.)
- Add job application tracking
- Integrate with calendar for interview scheduling

## Support

For issues or questions:
1. Check that all dependencies are installed
2. Verify your configuration in `config.json`
3. Review the logs for error messages
4. Check if the job site's structure has changed

## License

This feature is part of the ATS Resume Checker and follows the same license.
