"""
Base classes and interfaces for job scraping functionality.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class JobPosting:
    """Represents a single job posting."""

    title: str
    company: str
    location: str
    description: str
    url: str
    source: str  # e.g., "linkedin", "indeed", "jobs.ie"
    posted_date: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None  # e.g., "Full-time", "Part-time", "Contract"
    remote: Optional[bool] = None
    experience_level: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert job posting to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert job posting to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class SearchFilters:
    """Filter options for job searches."""

    keywords: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[List[str]] = None  # ["Full-time", "Part-time", "Contract"]
    remote_only: bool = False
    experience_level: Optional[List[str]] = None  # ["Entry", "Mid", "Senior"]
    salary_min: Optional[int] = None
    date_posted: Optional[str] = None  # "24h", "week", "month"

    def to_dict(self) -> Dict[str, Any]:
        """Convert filters to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchFilters":
        """Create SearchFilters from dictionary."""
        return cls(**data)


@dataclass
class SavedSearch:
    """Represents a saved search configuration."""

    id: str
    name: str
    source: str  # Job site name
    filters: SearchFilters
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    results_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert saved search to dictionary."""
        data = asdict(self)
        data["filters"] = self.filters.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedSearch":
        """Create SavedSearch from dictionary."""
        filters_data = data.pop("filters", {})
        filters = SearchFilters.from_dict(filters_data)
        return cls(filters=filters, **data)


class BaseJobScraper(ABC):
    """Abstract base class for job scrapers."""

    def __init__(self, name: str):
        """
        Initialize the scraper.

        Args:
            name: Name of the job site (e.g., "LinkedIn", "Indeed")
        """
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def search_jobs(
        self, filters: SearchFilters, max_results: int = 50
    ) -> List[JobPosting]:
        """
        Search for jobs based on filters.

        Args:
            filters: SearchFilters object containing search criteria
            max_results: Maximum number of results to return

        Returns:
            List of JobPosting objects
        """
        pass

    @abstractmethod
    def get_job_details(self, job_url: str) -> Optional[JobPosting]:
        """
        Get detailed information for a specific job posting.

        Args:
            job_url: URL of the job posting

        Returns:
            JobPosting object with detailed information, or None if failed
        """
        pass

    def validate_filters(self, filters: SearchFilters) -> bool:
        """
        Validate that the filters are appropriate for this scraper.

        Args:
            filters: SearchFilters to validate

        Returns:
            True if valid, False otherwise
        """
        if not filters.keywords and not filters.location:
            self.logger.warning(
                "At least one of keywords or location should be provided"
            )
            return False
        return True

    def save_results(self, jobs: List[JobPosting], filepath: str) -> None:
        """
        Save job results to a file.

        Args:
            jobs: List of JobPosting objects
            filepath: Path to save the results
        """
        try:
            data = [job.to_dict() for job in jobs]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(jobs)} jobs to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving results to {filepath}: {e}", exc_info=True)
            raise

    @staticmethod
    def load_results(filepath: str) -> List[JobPosting]:
        """
        Load job results from a file.

        Args:
            filepath: Path to load the results from

        Returns:
            List of JobPosting objects
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            jobs = [JobPosting(**job_data) for job_data in data]
            logger.info(f"Loaded {len(jobs)} jobs from {filepath}")
            return jobs
        except Exception as e:
            logger.error(f"Error loading results from {filepath}: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Test data structures
    filters = SearchFilters(
        keywords="software engineer",
        location="Dublin",
        job_type=["Full-time"],
        remote_only=True,
        experience_level=["Mid", "Senior"],
    )

    logger.info("Testing SearchFilters:")
    logger.info(f"Filters: {filters}")
    logger.info(f"Filters dict: {filters.to_dict()}")

    # Test JobPosting
    job = JobPosting(
        title="Senior Software Engineer",
        company="Tech Corp",
        location="Dublin, Ireland",
        description="We are looking for a senior software engineer...",
        url="https://example.com/job/123",
        source="linkedin",
        salary="€80,000 - €100,000",
        job_type="Full-time",
        remote=True,
        experience_level="Senior",
    )

    logger.info("\nTesting JobPosting:")
    logger.info(f"Job: {job.title} at {job.company}")
    logger.info(f"Job dict: {job.to_dict()}")

    # Test SavedSearch
    saved_search = SavedSearch(
        id="search_001",
        name="Dublin Software Engineer Jobs",
        source="linkedin",
        filters=filters,
    )

    logger.info("\nTesting SavedSearch:")
    logger.info(f"Saved search: {saved_search.name}")
    logger.info(f"Saved search dict: {saved_search.to_dict()}")
