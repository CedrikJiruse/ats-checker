# Changelog

All notable changes to the ATS Resume Checker project.

## [Unreleased] - 2025-12-12

### Added - Job Scraping System

#### New Features
- **Multi-Site Job Scraping**: Search for jobs across LinkedIn, Indeed, and Jobs.ie
- **Advanced Filtering**: Filter by keywords, location, job type, remote status, experience level, and date posted
- **Saved Searches**: Save search configurations for quick reuse
- **Search Management**: View, manage, and delete saved searches
- **Results Storage**: Automatically save all search results with timestamps
- **Export to Job Descriptions**: Convert scraped jobs to text files for resume tailoring
- **Interactive Menu**: Comprehensive menu system for all job search operations

#### New Files
- `job_scraper_base.py`: Base classes and data structures
  - `JobPosting`: Data class for job information
  - `SearchFilters`: Data class for search criteria
  - `SavedSearch`: Data class for saved search configurations
  - `BaseJobScraper`: Abstract base class for job site scrapers

- `job_scrapers.py`: Concrete scraper implementations
  - `LinkedInScraper`: Scraper for LinkedIn jobs
  - `IndeedScraper`: Scraper for Indeed jobs
  - `JobsIEScraper`: Scraper for Jobs.ie (Irish market)

- `job_scraper_manager.py`: Coordination and management
  - `JobScraperManager`: Manages all scrapers and coordinates searches
  - `SavedSearchManager`: Handles persistent saved searches

- `README_JOB_SCRAPER.md`: Comprehensive documentation for job scraping features

#### Configuration Changes
- Added `job_search_results_folder` (default: "job_search_results")
- Added `max_job_results_per_search` (default: 50)

#### Menu Updates
- Main menu option 3: "Job Search & Scraping"
- Sub-menu with 6 options:
  1. New job search
  2. Manage saved searches
  3. Run saved search
  4. View saved results
  5. Export jobs to job descriptions folder
  6. Back to main menu

#### Dependencies
- `requests`: HTTP library for web requests
- `beautifulsoup4`: HTML parsing library
- `lxml`: Fast XML/HTML parser

### Fixed

#### Bug Fixes
- **tesseract_cmd Configuration**: Fixed missing `tesseract_cmd` parameter in `Config` initialization (commit: 610ade9)
  - The parameter was defined in the config file but not being passed to the Config object
  - Now properly supports custom Tesseract executable paths

- **Optional Dependencies**: Made web scraping dependencies optional (commit: 63a5d78)
  - Application now runs without scraping dependencies installed
  - Graceful error messages when attempting to use scrapers without dependencies
  - Users are informed to install required packages when needed

### Changed
- Updated main menu numbering (Exit is now option 8 instead of 7)
- Enhanced config.py to support new job scraper settings
- Improved error handling for missing dependencies

## Git Commits

### Job Scraper Implementation
1. `610ade9` - Fix: Add missing tesseract_cmd parameter to Config initialization
2. `8615007` - feat: Add job scraper framework with LinkedIn, Indeed, and Jobs.ie support
3. `565f8aa` - feat: Add dependencies for web scraping
4. `2ca4b28` - feat: Add job scraper configuration options
5. `c7fde19` - feat: Integrate job scraping into main menu
6. `41c5875` - docs: Add comprehensive job scraper documentation
7. `63a5d78` - fix: Make web scraping dependencies optional

## Usage Example

### Quick Start with Job Scraping

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python main.py
   ```

3. **Search for jobs**:
   - Select option 3 (Job Search & Scraping)
   - Select option 1 (New job search)
   - Choose a job site or search all
   - Enter your criteria (keywords, location, etc.)
   - View results

4. **Export jobs for resume tailoring**:
   - From Job Search menu, select option 5
   - Choose a result file
   - Select how many jobs to export
   - Jobs are saved to `job_descriptions/` folder

5. **Process resumes with job descriptions**:
   - Return to main menu
   - Select option 1 (Process resumes)
   - Choose option 2 or 3 to tailor to specific job
   - Select an exported job description
   - Generate tailored resume

## Architecture

### Job Scraper Components

```
job_scraper_base.py
├── JobPosting (dataclass)
├── SearchFilters (dataclass)
├── SavedSearch (dataclass)
└── BaseJobScraper (abstract class)

job_scrapers.py
├── LinkedInScraper
├── IndeedScraper
└── JobsIEScraper

job_scraper_manager.py
├── SavedSearchManager
└── JobScraperManager

main.py
├── job_search_menu()
├── new_job_search()
├── manage_saved_searches()
├── run_saved_search()
├── view_saved_job_results()
└── export_jobs_to_descriptions()
```

### Data Flow

1. User enters search criteria → `SearchFilters` object created
2. Filters passed to scraper → HTTP request to job site
3. HTML parsed → List of `JobPosting` objects
4. Results saved to `job_search_results/` folder
5. User selects jobs to export → Converted to text files
6. Text files saved to `job_descriptions/` folder
7. Job descriptions used to tailor resumes

## Known Limitations

### Web Scraping
- Job sites have anti-scraping measures; results may vary
- Site structure changes can break scrapers
- Rate limiting may affect result counts
- Some sites may block automated requests

### Recommendations
- Use responsibly and respect site terms of service
- Verify job details on original sites
- Keep dependencies updated
- Monitor for site structure changes

## Future Enhancements

Potential features for future releases:
- Add more job sites (Glassdoor, Monster, etc.)
- Implement caching to reduce duplicate requests
- Add proxy support for reliability
- Use headless browsers for JavaScript sites
- Email notifications for new matching jobs
- Advanced filtering (salary ranges, company ratings)
- Job application tracking
- Interview scheduling integration

## Migration Guide

### For Existing Users

No breaking changes. All existing functionality remains unchanged.

To use new job scraping features:

1. Update dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configuration will auto-update with defaults:
   - `job_search_results_folder`: "job_search_results"
   - `max_job_results_per_search`: 50

3. New menu option available: "3. Job Search & Scraping"

### Optional Configuration

Add to `config.json`:
```json
{
  "job_search_results_folder": "job_search_results",
  "max_job_results_per_search": 50
}
```

## Testing

Basic tests included in module `__main__` blocks:
- `job_scraper_base.py`: Tests data structures
- `job_scrapers.py`: Tests scraper initialization
- `job_scraper_manager.py`: Tests manager functionality

To run tests:
```bash
python job_scraper_base.py
python job_scraper_manager.py
```

## Contributors

Changes implemented in this release:
- Job scraping framework
- Multi-site support
- Saved search functionality
- Export capabilities
- Comprehensive documentation
- Bug fixes for existing features

## Support

For issues:
1. Ensure dependencies are installed: `pip install -r requirements.txt`
2. Check `config.json` is valid
3. Review error messages in console
4. Verify internet connectivity
5. Check if job sites are accessible

For web scraping issues:
- Sites may change structure without notice
- Anti-bot measures may block requests
- Consider using official APIs when available
