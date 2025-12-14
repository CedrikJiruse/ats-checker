"""
Tests for job scraper functionality, including the is_remote boolean fix.
"""

import unittest
from unittest.mock import MagicMock, call, patch

from job_scraper_base import JobPosting, SavedSearch, SearchFilters
from job_scrapers_improved import (
    GlassdoorJobSpyScraper,
    GoogleJobSpyScraper,
    IndeedJobSpyScraper,
    JobSpyScraper,
    LinkedInJobSpyScraper,
    ZipRecruiterJobSpyScraper,
)


class FakeRow(dict):
    """
    Lightweight stand-in for a pandas Series.
    Job scrapers access rows via `row.get(...)` and `'key' in row`.
    """

    pass


class FakeDataFrame:
    """
    Lightweight stand-in for a pandas DataFrame.
    Job scrapers access `.empty` and iterate via `.iterrows()`.
    """

    def __init__(self, rows=None):
        self._rows = list(rows or [])

    @property
    def empty(self):
        return len(self._rows) == 0

    def iterrows(self):
        for idx, row in enumerate(self._rows):
            yield idx, FakeRow(row)


class TestSearchFilters(unittest.TestCase):
    """Tests for SearchFilters data class."""

    def test_create_basic_filters(self):
        """Test creating basic search filters."""
        filters = SearchFilters(keywords="software engineer", location="Dublin")
        self.assertEqual(filters.keywords, "software engineer")
        self.assertEqual(filters.location, "Dublin")
        self.assertFalse(filters.remote_only)

    def test_create_filters_with_remote(self):
        """Test creating filters with remote_only set to True."""
        filters = SearchFilters(
            keywords="python developer", location="Remote", remote_only=True
        )
        self.assertTrue(filters.remote_only)

    def test_filters_to_dict(self):
        """Test converting filters to dictionary."""
        filters = SearchFilters(
            keywords="data scientist",
            location="Ireland",
            job_type=["Full-time"],
            remote_only=False,
            experience_level=["Entry", "Mid"],
        )
        filters_dict = filters.to_dict()
        self.assertEqual(filters_dict["keywords"], "data scientist")
        self.assertEqual(filters_dict["location"], "Ireland")
        self.assertFalse(filters_dict["remote_only"])

    def test_filters_from_dict(self):
        """Test creating filters from dictionary."""
        data = {
            "keywords": "electrical engineer",
            "location": "Dublin",
            "job_type": ["Full-time"],
            "remote_only": False,
            "experience_level": ["Entry"],
            "salary_min": None,
            "date_posted": "week",
        }
        filters = SearchFilters.from_dict(data)
        self.assertEqual(filters.keywords, "electrical engineer")
        self.assertFalse(filters.remote_only)
        self.assertEqual(filters.date_posted, "week")


class TestJobPosting(unittest.TestCase):
    """Tests for JobPosting data class."""

    def test_create_job_posting(self):
        """Test creating a job posting."""
        job = JobPosting(
            title="Software Engineer",
            company="Tech Corp",
            location="Dublin",
            description="Great job opportunity",
            url="https://example.com/job/123",
            source="linkedin",
            remote=True,
        )
        self.assertEqual(job.title, "Software Engineer")
        self.assertTrue(job.remote)
        self.assertIsNotNone(job.scraped_at)

    def test_job_posting_to_dict(self):
        """Test converting job posting to dictionary."""
        job = JobPosting(
            title="Data Analyst",
            company="Data Inc",
            location="Remote",
            description="Analyze data",
            url="https://example.com/job/456",
            source="indeed",
            salary="€50,000 - €70,000",
            job_type="Full-time",
            remote=True,
        )
        job_dict = job.to_dict()
        self.assertEqual(job_dict["title"], "Data Analyst")
        self.assertTrue(job_dict["remote"])
        self.assertEqual(job_dict["salary"], "€50,000 - €70,000")


class TestJobSpyScraperIsRemote(unittest.TestCase):
    """Tests specifically for the is_remote parameter fix."""

    def setUp(self):
        """Set up test fixtures."""
        self.scraper = JobSpyScraper("linkedin")

    @patch("job_scrapers_improved._lazy_load_jobspy")
    def test_remote_only_true_passes_is_remote(self, mock_lazy_load_jobspy):
        """Test that remote_only=True correctly passes is_remote=True to JobSpy."""
        # Setup mock
        mock_scrape_fn = MagicMock(return_value=FakeDataFrame())
        mock_lazy_load_jobspy.return_value = mock_scrape_fn

        # Create filters with remote_only=True
        filters = SearchFilters(
            keywords="software engineer", location="Dublin", remote_only=True
        )

        # Execute search
        self.scraper.search_jobs(filters, max_results=50)

        # Verify scrape_jobs was called with is_remote=True
        mock_scrape_fn.assert_called_once()
        call_kwargs = mock_scrape_fn.call_args[1]
        self.assertIn("is_remote", call_kwargs)
        self.assertTrue(call_kwargs["is_remote"])

    @patch("job_scrapers_improved._lazy_load_jobspy")
    def test_remote_only_false_omits_is_remote(self, mock_lazy_load_jobspy):
        """Test that remote_only=False does NOT pass is_remote to JobSpy."""
        # Setup mock
        mock_scrape_fn = MagicMock(return_value=FakeDataFrame())
        mock_lazy_load_jobspy.return_value = mock_scrape_fn

        # Create filters with remote_only=False
        filters = SearchFilters(
            keywords="electrical engineer", location="Dublin", remote_only=False
        )

        # Execute search
        self.scraper.search_jobs(filters, max_results=50)

        # Verify scrape_jobs was called WITHOUT is_remote parameter
        mock_scrape_fn.assert_called_once()
        call_kwargs = mock_scrape_fn.call_args[1]
        self.assertNotIn("is_remote", call_kwargs)

    @patch("job_scrapers_improved._lazy_load_jobspy")
    def test_remote_only_none_omits_is_remote(self, mock_lazy_load_jobspy):
        """Test that remote_only not set (None/default False) does NOT pass is_remote."""
        # Setup mock
        mock_scrape_fn = MagicMock(return_value=FakeDataFrame())
        mock_lazy_load_jobspy.return_value = mock_scrape_fn

        # Create filters without setting remote_only (defaults to False)
        filters = SearchFilters(keywords="data scientist", location="Ireland")

        # Execute search
        self.scraper.search_jobs(filters, max_results=50)

        # Verify scrape_jobs was called WITHOUT is_remote parameter
        mock_scrape_fn.assert_called_once()
        call_kwargs = mock_scrape_fn.call_args[1]
        self.assertNotIn("is_remote", call_kwargs)


class TestJobSpyScraperSearchJobs(unittest.TestCase):
    """Tests for JobSpyScraper search_jobs method."""

    def setUp(self):
        """Set up test fixtures."""
        self.scraper = LinkedInJobSpyScraper()

    @patch("job_scrapers_improved._lazy_load_jobspy")
    def test_search_jobs_with_results(self, mock_lazy_load_jobspy):
        """Test searching jobs with results returned."""
        # Create mock DataFrame with sample job data
        mock_df = FakeDataFrame(
            [
                {
                    "title": "Software Engineer",
                    "company": "Tech Corp",
                    "location": "Dublin, Ireland",
                    "description": "Great opportunity",
                    "job_url": "https://example.com/job/1",
                    "site": "linkedin",
                    "date_posted": "2025-12-01",
                    "job_type": "fulltime",
                    "is_remote": False,
                    "min_amount": 60000,
                    "max_amount": 80000,
                    "currency": "EUR",
                    "interval": "yearly",
                },
                {
                    "title": "Senior Developer",
                    "company": "Dev Inc",
                    "location": "Remote",
                    "description": "Remote position",
                    "job_url": "https://example.com/job/2",
                    "site": "linkedin",
                    "date_posted": "2025-12-02",
                    "job_type": "fulltime",
                    "is_remote": True,
                    "min_amount": None,
                    "max_amount": None,
                    "currency": None,
                    "interval": None,
                },
            ]
        )
        mock_scrape_fn = MagicMock(return_value=mock_df)
        mock_lazy_load_jobspy.return_value = mock_scrape_fn

        # Create filters
        filters = SearchFilters(keywords="software engineer", location="Dublin")

        # Execute search
        jobs = self.scraper.search_jobs(filters, max_results=10)

        # Assertions
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].title, "Software Engineer")
        self.assertEqual(jobs[0].company, "Tech Corp")
        self.assertFalse(jobs[0].remote)
        self.assertEqual(jobs[0].salary, "EUR 60,000 - 80,000 per yearly")
        self.assertTrue(jobs[1].remote)
        self.assertIsNone(jobs[1].salary)

    @patch("job_scrapers_improved._lazy_load_jobspy")
    def test_search_jobs_with_no_results(self, mock_lazy_load_jobspy):
        """Test searching jobs with no results."""
        # Mock empty DataFrame
        mock_scrape_fn = MagicMock(return_value=FakeDataFrame())
        mock_lazy_load_jobspy.return_value = mock_scrape_fn

        filters = SearchFilters(keywords="rare skill", location="Middle of nowhere")

        jobs = self.scraper.search_jobs(filters, max_results=10)

        self.assertEqual(len(jobs), 0)

    @patch("job_scrapers_improved._lazy_load_jobspy")
    def test_search_jobs_with_job_type_filter(self, mock_lazy_load_jobspy):
        """Test that job_type filter is properly mapped."""
        mock_scrape_fn = MagicMock(return_value=FakeDataFrame())
        mock_lazy_load_jobspy.return_value = mock_scrape_fn

        filters = SearchFilters(
            keywords="engineer", location="Dublin", job_type=["Full-time"]
        )

        self.scraper.search_jobs(filters, max_results=50)

        # Verify job_type was mapped to "fulltime"
        call_kwargs = mock_scrape_fn.call_args[1]
        self.assertEqual(call_kwargs["job_type"], "fulltime")

    @patch("job_scrapers_improved._lazy_load_jobspy")
    def test_search_jobs_with_date_posted_filter(self, mock_lazy_load_jobspy):
        """Test that date_posted filter is properly mapped."""
        mock_scrape_fn = MagicMock(return_value=FakeDataFrame())
        mock_lazy_load_jobspy.return_value = mock_scrape_fn

        filters = SearchFilters(
            keywords="engineer", location="Dublin", date_posted="week"
        )

        self.scraper.search_jobs(filters, max_results=50)

        # Verify date_posted was mapped to hours_old=168
        call_kwargs = mock_scrape_fn.call_args[1]
        self.assertEqual(call_kwargs["hours_old"], 168)

    @patch("job_scrapers_improved._lazy_load_jobspy")
    def test_search_jobs_exception_handling(self, mock_lazy_load_jobspy):
        """Test that exceptions during scraping are handled gracefully."""
        # Mock scrape_jobs to raise an exception
        mock_scrape_fn = MagicMock(side_effect=Exception("Scraping failed"))
        mock_lazy_load_jobspy.return_value = mock_scrape_fn

        filters = SearchFilters(keywords="engineer", location="Dublin")

        # Should not raise exception, but return empty list
        jobs = self.scraper.search_jobs(filters, max_results=50)

        self.assertEqual(len(jobs), 0)


class TestJobSpyScraperHelperMethods(unittest.TestCase):
    """Tests for JobSpyScraper helper methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.scraper = JobSpyScraper("linkedin")

    def test_format_salary_with_min_and_max(self):
        """Test salary formatting with both min and max amounts."""
        row = FakeRow(
            {
                "min_amount": 50000,
                "max_amount": 70000,
                "currency": "EUR",
                "interval": "yearly",
            }
        )
        salary = self.scraper._format_salary(row)
        self.assertEqual(salary, "EUR 50,000 - 70,000 per yearly")

    def test_format_salary_with_min_only(self):
        """Test salary formatting with only min amount."""
        row = FakeRow(
            {
                "min_amount": 60000,
                "max_amount": None,
                "currency": "USD",
                "interval": "yearly",
            }
        )
        salary = self.scraper._format_salary(row)
        self.assertEqual(salary, "USD 60,000+ per yearly")

    def test_format_salary_with_max_only(self):
        """Test salary formatting with only max amount."""
        row = FakeRow(
            {
                "min_amount": None,
                "max_amount": 80000,
                "currency": "GBP",
                "interval": "yearly",
            }
        )
        salary = self.scraper._format_salary(row)
        self.assertEqual(salary, "GBP Up to 80,000 per yearly")

    def test_format_salary_with_no_amounts(self):
        """Test salary formatting with no amounts."""
        row = FakeRow(
            {
                "min_amount": None,
                "max_amount": None,
                "currency": "EUR",
                "interval": "yearly",
            }
        )
        salary = self.scraper._format_salary(row)
        self.assertIsNone(salary)

    def test_is_remote_from_field(self):
        """Test determining remote status from is_remote field."""
        row = FakeRow({"is_remote": True, "location": "Dublin"})
        is_remote = self.scraper._is_remote(row)
        self.assertTrue(is_remote)

        row = FakeRow({"is_remote": False, "location": "Dublin"})
        is_remote = self.scraper._is_remote(row)
        self.assertFalse(is_remote)

    def test_is_remote_from_location(self):
        """Test determining remote status from location string."""
        row = FakeRow({"is_remote": None, "location": "Remote"})
        is_remote = self.scraper._is_remote(row)
        self.assertTrue(is_remote)

        row = FakeRow({"is_remote": None, "location": "Work from Home"})
        is_remote = self.scraper._is_remote(row)
        self.assertTrue(is_remote)

    def test_is_remote_not_remote(self):
        """Test determining remote status when not remote."""
        row = FakeRow({"is_remote": None, "location": "Dublin, Ireland"})
        is_remote = self.scraper._is_remote(row)
        self.assertIsNone(is_remote)


class TestSpecificScrapers(unittest.TestCase):
    """Tests for specific job site scrapers."""

    def test_linkedin_scraper_initialization(self):
        """Test LinkedIn scraper initialization."""
        scraper = LinkedInJobSpyScraper()
        self.assertEqual(scraper.site_name, "linkedin")
        self.assertIn("linkedin", scraper.site_map[scraper.site_name])

    def test_indeed_scraper_initialization(self):
        """Test Indeed scraper initialization."""
        scraper = IndeedJobSpyScraper()
        self.assertEqual(scraper.site_name, "indeed")
        self.assertIn("indeed", scraper.site_map[scraper.site_name])

    def test_glassdoor_scraper_initialization(self):
        """Test Glassdoor scraper initialization."""
        scraper = GlassdoorJobSpyScraper()
        self.assertEqual(scraper.site_name, "glassdoor")
        self.assertIn("glassdoor", scraper.site_map[scraper.site_name])

    def test_google_scraper_initialization(self):
        """Test Google Jobs scraper initialization."""
        scraper = GoogleJobSpyScraper()
        self.assertEqual(scraper.site_name, "google")
        self.assertIn("google", scraper.site_map[scraper.site_name])

    def test_ziprecruiter_scraper_initialization(self):
        """Test ZipRecruiter scraper initialization."""
        scraper = ZipRecruiterJobSpyScraper()
        self.assertEqual(scraper.site_name, "ziprecruiter")
        self.assertIn("zip_recruiter", scraper.site_map[scraper.site_name])


class TestSavedSearch(unittest.TestCase):
    """Tests for SavedSearch data class."""

    def test_create_saved_search(self):
        """Test creating a saved search."""
        filters = SearchFilters(
            keywords="software engineer", location="Dublin", remote_only=True
        )
        saved_search = SavedSearch(
            id="test_001",
            name="Dublin Software Jobs",
            source="linkedin",
            filters=filters,
        )
        self.assertEqual(saved_search.name, "Dublin Software Jobs")
        self.assertEqual(saved_search.source, "linkedin")
        self.assertTrue(saved_search.filters.remote_only)

    def test_saved_search_to_dict(self):
        """Test converting saved search to dictionary."""
        filters = SearchFilters(keywords="data scientist", location="Remote")
        saved_search = SavedSearch(
            id="test_002", name="Remote Data Science", source="indeed", filters=filters
        )
        search_dict = saved_search.to_dict()
        self.assertEqual(search_dict["id"], "test_002")
        self.assertEqual(search_dict["filters"]["keywords"], "data scientist")

    def test_saved_search_from_dict(self):
        """Test creating saved search from dictionary."""
        data = {
            "id": "test_003",
            "name": "Engineering Jobs",
            "source": "linkedin",
            "filters": {
                "keywords": "engineer",
                "location": "Dublin",
                "job_type": ["Full-time"],
                "remote_only": False,
                "experience_level": ["Entry"],
                "salary_min": None,
                "date_posted": "week",
            },
            "created_at": "2025-12-13T00:00:00",
            "last_run": None,
            "results_count": 0,
        }
        saved_search = SavedSearch.from_dict(data)
        self.assertEqual(saved_search.name, "Engineering Jobs")
        self.assertEqual(saved_search.filters.keywords, "engineer")
        self.assertFalse(saved_search.filters.remote_only)


if __name__ == "__main__":
    unittest.main()
