# JobSpy Setup Guide

## Why JobSpy?

The original scrapers I implemented used basic HTML parsing with BeautifulSoup and requests. While this works in theory, modern job sites have several challenges:

1. **JavaScript Rendering**: Many sites use React/Vue and don't render content in raw HTML
2. **Anti-Bot Protection**: Sites like LinkedIn have sophisticated bot detection
3. **Frequent Changes**: Job sites change their HTML structure regularly
4. **Rate Limiting**: Sites will block IPs that make too many requests

**JobSpy solves all of these problems** by using battle-tested scraping logic maintained by the community.

## Installation

### Step 1: Install JobSpy

```bash
pip install python-jobspy
```

This will also install all required dependencies:
- `requests`
- `beautifulsoup4`
- `pandas`
- `tls-client` (for better bot detection avoidance)

### Step 2: Verify Installation

```bash
python -c "from jobspy import scrape_jobs; print('JobSpy installed successfully!')"
```

### Step 3: Run the Application

```bash
python main.py
```

The application will automatically detect JobSpy and use it for scraping.

## Supported Job Sites

With JobSpy, you now have access to:

1. **LinkedIn** - Professional networking
2. **Indeed** - Most popular job board
3. **Glassdoor** - Reviews and salary data
4. **Google Jobs** - Aggregated from multiple sources
5. **ZipRecruiter** - Large job database

## How It Works

### Automatic Detection

The application automatically detects if JobSpy is installed:

- ✅ **If JobSpy is installed**: Uses improved scrapers with better success rates
- ⚠️ **If JobSpy is NOT installed**: Falls back to basic scrapers (not recommended)

### Usage is Identical

You don't need to change how you use the application. The menu and interface remain the same:

1. Go to "3. Job Search & Scraping"
2. Select "1. New job search"
3. Enter your criteria
4. Get results!

The difference is that JobSpy will:
- Return actual, real results
- Handle JavaScript-rendered content
- Bypass bot detection
- Work with current site structures

## Example: Testing JobSpy

### Quick Test

```python
from jobspy import scrape_jobs

# Search for Python jobs in Dublin
jobs_df = scrape_jobs(
    site_name=["indeed", "linkedin"],
    search_term="python developer",
    location="Dublin",
    results_wanted=10,
    hours_old=72,  # Jobs posted in last 3 days
    country_indeed="Ireland"
)

print(f"Found {len(jobs_df)} jobs")
print(jobs_df[['title', 'company', 'location']].head())
```

### Through the Application

1. Run `python main.py`
2. Select "3. Job Search & Scraping"
3. Select "1. New job search"
4. Choose "Indeed" (or any site)
5. Enter:
   - Keywords: `python developer`
   - Location: `Dublin`
   - Job types: `1` (Full-time)
   - Remote only: `n`
   - Date posted: `2` (Last week)
6. View real results!

## What You Get

JobSpy returns rich data for each job:

- **Basic Info**: Title, company, location
- **Details**: Full job description
- **Salary**: Min/max amounts, currency, interval
- **Metadata**: Date posted, job type, is_remote
- **Links**: Direct URL to apply
- **Emails**: Company emails (when available)
- **Benefits**: Listed benefits (when available)

## Configuration

### Country-Specific Searching

For Indeed, you can search specific countries:

```python
# Edit job_scrapers_improved.py line with country_indeed
country_indeed="Ireland"  # or "USA", "UK", "Canada", etc.
```

### Proxy Support (Optional)

If you're making many requests, consider using proxies:

```python
# In job_scrapers_improved.py, add to scrape_jobs call:
proxies=["http://proxy1.com:8080", "http://proxy2.com:8080"]
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'jobspy'"

**Solution**: Install JobSpy
```bash
pip install python-jobspy
```

### Issue: "Using basic scrapers" warning

**Solution**: This means JobSpy isn't installed. Install it:
```bash
pip install python-jobspy
```

Then restart the application.

### Issue: No results returned

**Possible causes**:
1. **Too specific search**: Try broader keywords
2. **Location issues**: Try different location formats
3. **Site down**: The job site might be temporarily unavailable
4. **Rate limiting**: Wait a few minutes and try again

**Solutions**:
- Broaden your search terms
- Try a different job site
- Wait 5-10 minutes between searches
- Use max_results=10 for testing instead of 50

### Issue: Slow performance

**Cause**: JobSpy fetches real data from live sites

**Solutions**:
- Reduce `max_job_results_per_search` in config.json
- Search one site at a time instead of all sites
- Use saved searches to avoid re-running

### Issue: Results in wrong location

**For Indeed**: Make sure country is set correctly

Edit `job_scrapers_improved.py` and change:
```python
country_indeed="Ireland"  # Change to your country
```

## Advanced: Custom Scraper Configuration

You can customize the JobSpy scrapers by editing `job_scrapers_improved.py`:

### Change Default Countries

```python
# Line ~78 in job_scrapers_improved.py
country_indeed="USA",  # Change this
```

### Add More Sites

```python
# In __init__ method, add more sites to site_map
self.site_map = {
    "all": ["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"],
    "custom": ["linkedin", "indeed"],  # Add custom combinations
}
```

### Adjust Timeouts

JobSpy handles this internally, but you can configure retries in the library itself.

## Performance Comparison

### Basic Scrapers (BeautifulSoup)
- ❌ LinkedIn: Usually 0 results (blocked)
- ❌ Indeed: 0-2 results (incomplete rendering)
- ❌ Jobs.ie: Maybe 1-3 results

### JobSpy Scrapers
- ✅ LinkedIn: 10-50+ results
- ✅ Indeed: 10-50+ results
- ✅ Glassdoor: 10-50+ results
- ✅ Google: 10-50+ results
- ✅ ZipRecruiter: 10-50+ results

## Best Practices

### 1. Be Respectful
- Don't spam requests
- Wait 30-60 seconds between searches
- Use reasonable result limits (10-50)

### 2. Use Saved Searches
- Save your common searches
- Reuse them instead of creating new ones
- This reduces the number of requests

### 3. Export Strategically
- Don't export all results
- Choose the top 5-10 most relevant jobs
- This keeps your job_descriptions folder manageable

### 4. Refine Your Search
- Start with broader terms
- Narrow down based on results
- Use location filters effectively

## Next Steps

Now that JobSpy is set up:

1. **Test it**: Run a simple search to verify it works
2. **Save searches**: Create 2-3 saved searches for jobs you're interested in
3. **Run regularly**: Check for new jobs weekly
4. **Export jobs**: Export interesting positions to job descriptions
5. **Tailor resumes**: Use the exported jobs to customize your resumes

## Need Help?

### JobSpy Documentation
- GitHub: https://github.com/Bunsly/JobSpy
- Issues: Report problems on GitHub

### This Application
- Check `README_JOB_SCRAPER.md` for general job scraper usage
- Check `CHANGELOG.md` for recent changes
- Review code in `job_scrapers_improved.py`

## Summary

✅ **JobSpy provides**:
- Real, working job scraping
- Multiple major job sites
- Rich job data
- Active maintenance
- Community support

🚀 **You get**:
- Actual job listings
- Current openings
- Detailed information
- Direct application links
- Reliable daily use

Install it now: `pip install python-jobspy`
