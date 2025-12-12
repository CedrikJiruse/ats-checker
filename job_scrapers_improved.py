"""
Improved job scrapers using JobSpy library for reliable scraping.
"""

import logging
from typing import List, Optional

from job_scraper_base import BaseJobScraper, JobPosting, SearchFilters

logger = logging.getLogger(__name__)

# Try to import JobSpy library
try:
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    logger.warning("JobSpy not available. Install with: pip install python-jobspy")


class JobSpyScraper(BaseJobScraper):
    """
    Universal scraper using JobSpy library.
    Supports LinkedIn, Indeed, Glassdoor, Google Jobs, and ZipRecruiter.
    """

    def __init__(self, site_name: str = "all"):
        """
        Initialize JobSpy scraper.

        Args:
            site_name: Site to scrape - "linkedin", "indeed", "glassdoor", "google", "zip_recruiter", or "all"
        """
        super().__init__(f"JobSpy-{site_name}")
        self.site_name = site_name.lower()

        # Map our site names to JobSpy's expected names
        self.site_map = {
            "all": ["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"],
            "linkedin": ["linkedin"],
            "indeed": ["indeed"],
            "glassdoor": ["glassdoor"],
            "google": ["google"],
            "ziprecruiter": ["zip_recruiter"],
            "zip_recruiter": ["zip_recruiter"],
        }

    def search_jobs(
        self, filters: SearchFilters, max_results: int = 50
    ) -> List[JobPosting]:
        """
        Search for jobs using JobSpy library.

        Args:
            filters: SearchFilters object with search criteria
            max_results: Maximum number of results to return

        Returns:
            List of JobPosting objects
        """
        if not JOBSPY_AVAILABLE:
            self.logger.error(
                "JobSpy library not available. Install with: pip install python-jobspy"
            )
            return []

        if not self.validate_filters(filters):
            return []

        jobs = []
        try:
            # Map our filters to JobSpy parameters
            search_term = filters.keywords or ""
            location = filters.location or ""

            # Map job type
            job_type = None
            if filters.job_type:
                # JobSpy expects: fulltime, parttime, contract, internship
                type_map = {
                    "Full-time": "fulltime",
                    "Part-time": "parttime",
                    "Contract": "contract",
                    "Internship": "internship",
                }
                mapped_types = [
                    type_map.get(jt) for jt in filters.job_type if jt in type_map
                ]
                if mapped_types:
                    job_type = mapped_types[0]  # JobSpy takes single value

            # Map date posted
            hours_old = None
            if filters.date_posted:
                date_map = {
                    "24h": 24,
                    "week": 168,  # 7 days
                    "month": 720,  # 30 days
                }
                hours_old = date_map.get(filters.date_posted)

            # Get sites to search
            sites = self.site_map.get(self.site_name, ["linkedin", "indeed"])

            self.logger.info(f"Searching {sites} for '{search_term}' in '{location}'")

            # Call JobSpy
            df = scrape_jobs(
                site_name=sites,
                search_term=search_term,
                location=location,
                results_wanted=max_results,
                hours_old=hours_old,
                country_indeed="USA",  # Can be made configurable
                is_remote=filters.remote_only if filters.remote_only else None,
                job_type=job_type,
            )

            if df is not None and not df.empty:
                # Convert DataFrame to JobPosting objects
                for _, row in df.iterrows():
                    try:
                        job = JobPosting(
                            title=str(row.get("title", "Unknown")),
                            company=str(row.get("company", "Unknown")),
                            location=str(row.get("location", "Unknown")),
                            description=str(row.get("description", "")),
                            url=str(row.get("job_url", "")),
                            source=str(row.get("site", self.site_name)),
                            posted_date=str(row.get("date_posted", "")),
                            salary=self._format_salary(row),
                            job_type=str(row.get("job_type", "")),
                            remote=self._is_remote(row),
                            experience_level=str(row.get("job_level", ""))
                            if "job_level" in row
                            else None,
                        )
                        jobs.append(job)
                    except Exception as e:
                        self.logger.warning(f"Error converting row to JobPosting: {e}")
                        continue

                self.logger.info(f"Successfully scraped {len(jobs)} jobs")
            else:
                self.logger.info("No jobs found")

        except Exception as e:
            self.logger.error(f"Error during JobSpy scraping: {e}", exc_info=True)

        return jobs

    def _format_salary(self, row) -> Optional[str]:
        """Format salary information from JobSpy data."""
        try:
            min_amount = row.get("min_amount")
            max_amount = row.get("max_amount")
            interval = row.get("interval", "yearly")
            currency = row.get("currency", "USD")

            if min_amount or max_amount:
                parts = []
                if currency:
                    parts.append(currency)
                if min_amount and max_amount:
                    parts.append(f"{min_amount:,.0f} - {max_amount:,.0f}")
                elif min_amount:
                    parts.append(f"{min_amount:,.0f}+")
                elif max_amount:
                    parts.append(f"Up to {max_amount:,.0f}")
                if interval:
                    parts.append(f"per {interval}")
                return " ".join(parts)
        except:
            pass
        return None

    def _is_remote(self, row) -> Optional[bool]:
        """Determine if job is remote from JobSpy data."""
        try:
            is_remote = row.get("is_remote")
            if is_remote is not None:
                return bool(is_remote)

            # Fallback: check location string
            location = str(row.get("location", "")).lower()
            if "remote" in location:
                return True
        except:
            pass
        return None

    def get_job_details(self, job_url: str) -> Optional[JobPosting]:
        """
        Get detailed job information.

        Note: JobSpy already provides detailed information in search results.
        This method is mainly for consistency with the base class.
        """
        self.logger.info(
            "JobSpy provides detailed info in search results. Use search_jobs() instead."
        )
        return None


class LinkedInJobSpyScraper(JobSpyScraper):
    """LinkedIn-specific scraper using JobSpy."""

    def __init__(self):
        super().__init__("linkedin")


class IndeedJobSpyScraper(JobSpyScraper):
    """Indeed-specific scraper using JobSpy."""

    def __init__(self):
        super().__init__("indeed")


class GlassdoorJobSpyScraper(JobSpyScraper):
    """Glassdoor-specific scraper using JobSpy."""

    def __init__(self):
        super().__init__("glassdoor")


class GoogleJobSpyScraper(JobSpyScraper):
    """Google Jobs-specific scraper using JobSpy."""

    def __init__(self):
        super().__init__("google")


class ZipRecruiterJobSpyScraper(JobSpyScraper):
    """ZipRecruiter-specific scraper using JobSpy."""

    def __init__(self):
        super().__init__("ziprecruiter")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    if not JOBSPY_AVAILABLE:
        logger.error("JobSpy not installed. Install with: pip install python-jobspy")
        logger.info("This library is much more reliable than basic HTML scraping!")
    else:
        # Test the scraper
        from job_scraper_base import SearchFilters

        filters = SearchFilters(
            keywords="software engineer python",
            location="Dublin",
            job_type=["Full-time"],
            remote_only=False,
        )

        logger.info("Testing JobSpy scraper with LinkedIn...")
        scraper = LinkedInJobSpyScraper()
        jobs = scraper.search_jobs(filters, max_results=5)

        logger.info(f"\nFound {len(jobs)} jobs:")
        for i, job in enumerate(jobs, 1):
            logger.info(f"\n{i}. {job.title}")
            logger.info(f"   Company: {job.company}")
            logger.info(f"   Location: {job.location}")
            logger.info(f"   Salary: {job.salary}")
            logger.info(f"   URL: {job.url[:80]}...")
