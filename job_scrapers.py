"""
Concrete implementations of job scrapers for various job sites.
"""

import logging
import re
import time
from typing import List, Optional
from urllib.parse import quote_plus, urlencode

import requests
from bs4 import BeautifulSoup

from job_scraper_base import BaseJobScraper, JobPosting, SearchFilters

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseJobScraper):
    """Scraper for LinkedIn job postings."""

    BASE_URL = "https://www.linkedin.com"
    SEARCH_URL = f"{BASE_URL}/jobs/search"

    def __init__(self):
        super().__init__("LinkedIn")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def search_jobs(
        self, filters: SearchFilters, max_results: int = 50
    ) -> List[JobPosting]:
        """Search for jobs on LinkedIn."""
        if not self.validate_filters(filters):
            return []

        jobs = []
        try:
            # Build query parameters
            params = {}
            if filters.keywords:
                params["keywords"] = filters.keywords
            if filters.location:
                params["location"] = filters.location
            if filters.job_type:
                # LinkedIn uses f_JT parameter for job type
                job_type_map = {
                    "Full-time": "F",
                    "Part-time": "P",
                    "Contract": "C",
                    "Internship": "I",
                }
                params["f_JT"] = ",".join(
                    [
                        job_type_map.get(jt, "")
                        for jt in filters.job_type
                        if jt in job_type_map
                    ]
                )

            if filters.remote_only:
                params["f_WT"] = "2"  # Remote only

            if filters.experience_level:
                # LinkedIn experience levels
                level_map = {
                    "Entry": "2",
                    "Mid": "3",
                    "Senior": "4",
                    "Director": "5",
                    "Executive": "6",
                }
                params["f_E"] = ",".join(
                    [
                        level_map.get(level, "")
                        for level in filters.experience_level
                        if level in level_map
                    ]
                )

            if filters.date_posted:
                # LinkedIn time filters
                date_map = {"24h": "r86400", "week": "r604800", "month": "r2592000"}
                params["f_TPR"] = date_map.get(filters.date_posted, "")

            url = f"{self.SEARCH_URL}?{urlencode(params)}"
            self.logger.info(f"Searching LinkedIn with URL: {url}")

            # Note: LinkedIn has strong anti-scraping measures
            # This is a simplified implementation that may need cookies/authentication
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # LinkedIn's structure may vary, this is a basic approach
            job_cards = soup.find_all("div", class_=re.compile(r"job.*card|base-card"))

            for card in job_cards[:max_results]:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    self.logger.warning(f"Error parsing job card: {e}")
                    continue

            self.logger.info(f"Found {len(jobs)} jobs on LinkedIn")

        except requests.RequestException as e:
            self.logger.error(f"Error fetching LinkedIn jobs: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error during LinkedIn search: {e}", exc_info=True
            )

        return jobs

    def _parse_job_card(self, card) -> Optional[JobPosting]:
        """Parse a LinkedIn job card element."""
        try:
            # This is a simplified parser - actual LinkedIn structure may vary
            title_elem = card.find("h3", class_=re.compile(r"title|job-title"))
            company_elem = card.find("h4", class_=re.compile(r"company|subtitle"))
            location_elem = card.find("span", class_=re.compile(r"location"))
            link_elem = card.find("a", href=re.compile(r"/jobs/view/"))

            if not all([title_elem, company_elem, link_elem]):
                return None

            title = title_elem.get_text(strip=True)
            company = company_elem.get_text(strip=True)
            location = (
                location_elem.get_text(strip=True) if location_elem else "Not specified"
            )
            url = link_elem.get("href", "")
            if not url.startswith("http"):
                url = self.BASE_URL + url

            # Extract job ID from URL for description placeholder
            job_id = re.search(r"/jobs/view/(\d+)", url)
            job_id = job_id.group(1) if job_id else "unknown"

            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=f"Job ID: {job_id}. Full details available at job URL.",
                url=url,
                source="LinkedIn",
            )
        except Exception as e:
            self.logger.warning(f"Error parsing job card: {e}")
            return None

    def get_job_details(self, job_url: str) -> Optional[JobPosting]:
        """Get detailed job information from LinkedIn."""
        try:
            response = requests.get(job_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Parse job details (simplified)
            title_elem = soup.find("h1", class_=re.compile(r"job.*title"))
            company_elem = soup.find("a", class_=re.compile(r"company"))
            description_elem = soup.find("div", class_=re.compile(r"description"))

            if not title_elem:
                return None

            return JobPosting(
                title=title_elem.get_text(strip=True),
                company=company_elem.get_text(strip=True)
                if company_elem
                else "Unknown",
                location="See job page",
                description=description_elem.get_text(strip=True)
                if description_elem
                else "",
                url=job_url,
                source="LinkedIn",
            )
        except Exception as e:
            self.logger.error(f"Error fetching job details from {job_url}: {e}")
            return None


class IndeedScraper(BaseJobScraper):
    """Scraper for Indeed job postings."""

    BASE_URL = "https://www.indeed.com"
    SEARCH_URL = f"{BASE_URL}/jobs"

    def __init__(self):
        super().__init__("Indeed")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def search_jobs(
        self, filters: SearchFilters, max_results: int = 50
    ) -> List[JobPosting]:
        """Search for jobs on Indeed."""
        if not self.validate_filters(filters):
            return []

        jobs = []
        try:
            # Build query parameters
            params = {
                "q": filters.keywords or "",
                "l": filters.location or "",
            }

            if filters.job_type:
                # Indeed job type parameter
                jt_map = {
                    "Full-time": "fulltime",
                    "Part-time": "parttime",
                    "Contract": "contract",
                    "Internship": "internship",
                }
                params["jt"] = ",".join(
                    [jt_map.get(jt, "") for jt in filters.job_type if jt in jt_map]
                )

            if filters.remote_only:
                params["remotejob"] = "1"

            if filters.date_posted:
                date_map = {"24h": "1", "week": "7", "month": "30"}
                params["fromage"] = date_map.get(filters.date_posted, "")

            if filters.salary_min:
                params["salary"] = f"${filters.salary_min}+"

            url = f"{self.SEARCH_URL}?{urlencode(params)}"
            self.logger.info(f"Searching Indeed with URL: {url}")

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Indeed uses various card structures
            job_cards = soup.find_all(
                "div", class_=re.compile(r"job_seen_beacon|jobsearch-SerpJobCard")
            )

            for card in job_cards[:max_results]:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    self.logger.warning(f"Error parsing job card: {e}")
                    continue

            self.logger.info(f"Found {len(jobs)} jobs on Indeed")

        except requests.RequestException as e:
            self.logger.error(f"Error fetching Indeed jobs: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error during Indeed search: {e}", exc_info=True
            )

        return jobs

    def _parse_job_card(self, card) -> Optional[JobPosting]:
        """Parse an Indeed job card element."""
        try:
            title_elem = card.find("h2", class_=re.compile(r"jobTitle"))
            if not title_elem:
                title_elem = card.find("a", class_=re.compile(r"jcs-JobTitle"))

            company_elem = card.find("span", class_=re.compile(r"companyName"))
            location_elem = card.find("div", class_=re.compile(r"companyLocation"))
            snippet_elem = card.find("div", class_=re.compile(r"job-snippet"))
            link_elem = title_elem.find("a") if title_elem else None

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            location = (
                location_elem.get_text(strip=True) if location_elem else "Not specified"
            )
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            url = ""
            if link_elem:
                url = link_elem.get("href", "")
                if url and not url.startswith("http"):
                    url = self.BASE_URL + url

            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=snippet,
                url=url,
                source="Indeed",
            )
        except Exception as e:
            self.logger.warning(f"Error parsing job card: {e}")
            return None

    def get_job_details(self, job_url: str) -> Optional[JobPosting]:
        """Get detailed job information from Indeed."""
        try:
            response = requests.get(job_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            title_elem = soup.find(
                "h1", class_=re.compile(r"jobsearch-JobInfoHeader-title")
            )
            company_elem = soup.find(
                "div", class_=re.compile(r"jobsearch-InlineCompanyRating")
            )
            description_elem = soup.find("div", id="jobDescriptionText")

            if not title_elem:
                return None

            return JobPosting(
                title=title_elem.get_text(strip=True),
                company=company_elem.get_text(strip=True)
                if company_elem
                else "Unknown",
                location="See job page",
                description=description_elem.get_text(strip=True)
                if description_elem
                else "",
                url=job_url,
                source="Indeed",
            )
        except Exception as e:
            self.logger.error(f"Error fetching job details from {job_url}: {e}")
            return None


class JobsIEScraper(BaseJobScraper):
    """Scraper for Jobs.ie (Irish job site)."""

    BASE_URL = "https://www.jobs.ie"
    SEARCH_URL = f"{BASE_URL}/ApplyForJob.aspx"

    def __init__(self):
        super().__init__("Jobs.ie")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def search_jobs(
        self, filters: SearchFilters, max_results: int = 50
    ) -> List[JobPosting]:
        """Search for jobs on Jobs.ie."""
        if not self.validate_filters(filters):
            return []

        jobs = []
        try:
            # Build query parameters for Jobs.ie
            params = {}
            if filters.keywords:
                params["Keywords"] = filters.keywords
            if filters.location:
                params["Location"] = filters.location

            url = f"{self.SEARCH_URL}?{urlencode(params)}"
            self.logger.info(f"Searching Jobs.ie with URL: {url}")

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Jobs.ie structure - may need adjustment based on actual site
            job_cards = soup.find_all(
                "div", class_=re.compile(r"job.*listing|job.*card")
            )
            if not job_cards:
                # Try alternative selectors
                job_cards = soup.find_all("article", class_=re.compile(r"job"))

            for card in job_cards[:max_results]:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    self.logger.warning(f"Error parsing job card: {e}")
                    continue

            self.logger.info(f"Found {len(jobs)} jobs on Jobs.ie")

        except requests.RequestException as e:
            self.logger.error(f"Error fetching Jobs.ie jobs: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error during Jobs.ie search: {e}", exc_info=True
            )

        return jobs

    def _parse_job_card(self, card) -> Optional[JobPosting]:
        """Parse a Jobs.ie job card element."""
        try:
            # This is a generalized parser that may need adjustment
            title_elem = card.find(["h2", "h3"], class_=re.compile(r"job.*title"))
            if not title_elem:
                title_elem = card.find("a", class_=re.compile(r"job.*link"))

            company_elem = card.find(["span", "div"], class_=re.compile(r"company"))
            location_elem = card.find(["span", "div"], class_=re.compile(r"location"))
            description_elem = card.find(
                ["p", "div"], class_=re.compile(r"description|summary")
            )

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            location = (
                location_elem.get_text(strip=True) if location_elem else "Ireland"
            )
            description = (
                description_elem.get_text(strip=True) if description_elem else ""
            )

            # Get URL
            link_elem = card.find("a")
            url = ""
            if link_elem:
                url = link_elem.get("href", "")
                if url and not url.startswith("http"):
                    url = self.BASE_URL + url

            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                source="Jobs.ie",
            )
        except Exception as e:
            self.logger.warning(f"Error parsing job card: {e}")
            return None

    def get_job_details(self, job_url: str) -> Optional[JobPosting]:
        """Get detailed job information from Jobs.ie."""
        try:
            response = requests.get(job_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            title_elem = soup.find("h1")
            company_elem = soup.find("span", class_=re.compile(r"company"))
            description_elem = soup.find("div", class_=re.compile(r"job.*description"))

            if not title_elem:
                return None

            return JobPosting(
                title=title_elem.get_text(strip=True),
                company=company_elem.get_text(strip=True)
                if company_elem
                else "Unknown",
                location="Ireland",
                description=description_elem.get_text(strip=True)
                if description_elem
                else "",
                url=job_url,
                source="Jobs.ie",
            )
        except Exception as e:
            self.logger.error(f"Error fetching job details from {job_url}: {e}")
            return None


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Test scrapers with sample filters
    filters = SearchFilters(
        keywords="software engineer",
        location="Dublin",
        job_type=["Full-time"],
        remote_only=False,
    )

    logger.info("Testing LinkedIn scraper:")
    linkedin_scraper = LinkedInScraper()
    linkedin_jobs = linkedin_scraper.search_jobs(filters, max_results=5)
    logger.info(f"Found {len(linkedin_jobs)} LinkedIn jobs")

    logger.info("\nTesting Indeed scraper:")
    indeed_scraper = IndeedScraper()
    indeed_jobs = indeed_scraper.search_jobs(filters, max_results=5)
    logger.info(f"Found {len(indeed_jobs)} Indeed jobs")

    logger.info("\nTesting Jobs.ie scraper:")
    jobsie_scraper = JobsIEScraper()
    jobsie_jobs = jobsie_scraper.search_jobs(filters, max_results=5)
    logger.info(f"Found {len(jobsie_jobs)} Jobs.ie jobs")
