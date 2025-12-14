# Test Suite for ATS Resume Checker

## Overview
This directory contains comprehensive tests for the ATS Resume Checker application, with a focus on the job scraping functionality.

## Test Files

### test_job_scrapers.py
Comprehensive unit tests for the job scraper module, including:
- **SearchFilters tests**: Creating, converting, and loading search filters
- **JobPosting tests**: Creating and serializing job postings
- **is_remote fix tests**: Critical tests verifying the boolean validation fix
- **JobSpyScraper tests**: Full integration tests with mocked JobSpy library
- **Helper method tests**: Testing salary formatting and remote detection
- **Scraper initialization tests**: Testing all job site scrapers (LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter)
- **SavedSearch tests**: Testing saved search functionality

### Other Test Files
- `test_output_generator.py`: Tests for output generation
- `test_resume_processor.py`: Tests for resume processing orchestration (uses mocks)
- `test_state_manager.py`: Tests for state management
- `test_utils.py`: Tests for utility functions

## Running Tests

### Using pytest (Recommended)
```bash
python -m pytest -q
```

### Manual check (is_remote parameter generation)
```bash
python tools/manual_test_is_remote_fix.py
```

### Using unittest (alternative)
```bash
# Run all job scraper tests
python -m unittest tests.test_job_scrapers -v

# Run specific test class
python -m unittest tests.test_job_scrapers.TestJobSpyScraperIsRemote -v

# Run specific test
python -m unittest tests.test_job_scrapers.TestJobSpyScraperIsRemote.test_remote_only_true_passes_is_remote -v
```

## The is_remote Boolean Fix

### Problem
JobSpy's pydantic validation requires the `is_remote` parameter to be a boolean, but the code was passing `None` when `remote_only=False`, causing:
```
ValidationError: 1 validation error for ScraperInput
is_remote
  Input should be a valid boolean [type=bool_type, input_value=None, input_type=NoneType]
```

### Solution
Modified `job_scrapers_improved.py` to only include the `is_remote` parameter when `remote_only=True`:

```python
scrape_params = {
    "site_name": sites,
    "search_term": search_term,
    "location": location,
    "results_wanted": max_results,
    "hours_old": hours_old,
    "country_indeed": "USA",
    "job_type": job_type,
}

# Only add is_remote if explicitly set to True
if filters.remote_only:
    scrape_params["is_remote"] = True

df = scrape_jobs(**scrape_params)
```

### Test Coverage
The `TestJobSpyScraperIsRemote` class contains three critical tests:
1. `test_remote_only_true_passes_is_remote`: Verifies `is_remote=True` is passed when `remote_only=True`
2. `test_remote_only_false_omits_is_remote`: Verifies `is_remote` is omitted when `remote_only=False`
3. `test_remote_only_none_omits_is_remote`: Verifies `is_remote` is omitted when `remote_only` defaults to `False`

## Test Statistics
- **Total Test Classes**: 8
- **Total Test Methods**: 20+
- **Key Test Areas**:
  - Data structure validation
  - Boolean parameter handling (is_remote fix)
  - Scraper initialization
  - Search functionality with mocked responses
  - Helper method behavior
  - Error handling

## Dependencies
- `pytest`: Test runner
- `unittest`: Standard library testing framework (used by some tests)
- `unittest.mock`: For mocking external dependencies

## Known Issues
- If you install `python-jobspy`, it may pull in heavy dependencies (e.g., numpy/pandas). The unit tests are designed to avoid importing those during test collection by using mocks and lightweight fakes.

## Contributing
When adding new scraper functionality:
1. Add corresponding tests to `test_job_scrapers.py`
2. Ensure tests cover both success and failure cases
3. Mock external dependencies (JobSpy, HTTP requests)
4. Run the test suite before committing changes
