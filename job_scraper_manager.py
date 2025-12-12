"""
Manager for job scrapers and saved searches.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from job_scraper_base import BaseJobScraper, JobPosting, SavedSearch, SearchFilters
from job_scrapers import IndeedScraper, JobsIEScraper, LinkedInScraper

logger = logging.getLogger(__name__)


class SavedSearchManager:
    """Manages saved job searches."""

    def __init__(self, storage_path: str = "saved_searches.json"):
        """
        Initialize the saved search manager.

        Args:
            storage_path: Path to store saved searches
        """
        self.storage_path = storage_path
        self.searches: Dict[str, SavedSearch] = {}
        self._load_searches()

    def _load_searches(self) -> None:
        """Load saved searches from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for search_data in data:
                        search = SavedSearch.from_dict(search_data)
                        self.searches[search.id] = search
                logger.info(f"Loaded {len(self.searches)} saved searches")
            except Exception as e:
                logger.error(f"Error loading saved searches: {e}", exc_info=True)
        else:
            logger.info("No saved searches file found, starting fresh")

    def _save_searches(self) -> None:
        """Save searches to storage."""
        try:
            data = [search.to_dict() for search in self.searches.values()]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Saved searches to storage")
        except Exception as e:
            logger.error(f"Error saving searches: {e}", exc_info=True)

    def create_search(
        self, name: str, source: str, filters: SearchFilters
    ) -> SavedSearch:
        """
        Create a new saved search.

        Args:
            name: Name for the saved search
            source: Job site source (e.g., "LinkedIn", "Indeed")
            filters: Search filters

        Returns:
            The created SavedSearch object
        """
        search_id = str(uuid.uuid4())
        search = SavedSearch(id=search_id, name=name, source=source, filters=filters)
        self.searches[search_id] = search
        self._save_searches()
        logger.info(f"Created saved search: {name} (ID: {search_id})")
        return search

    def get_search(self, search_id: str) -> Optional[SavedSearch]:
        """Get a saved search by ID."""
        return self.searches.get(search_id)

    def get_all_searches(self) -> List[SavedSearch]:
        """Get all saved searches."""
        return list(self.searches.values())

    def update_search(
        self,
        search_id: str,
        name: Optional[str] = None,
        filters: Optional[SearchFilters] = None,
    ) -> bool:
        """
        Update a saved search.

        Args:
            search_id: ID of the search to update
            name: New name (optional)
            filters: New filters (optional)

        Returns:
            True if updated successfully, False otherwise
        """
        search = self.searches.get(search_id)
        if not search:
            return False

        if name:
            search.name = name
        if filters:
            search.filters = filters

        self._save_searches()
        logger.info(f"Updated saved search: {search_id}")
        return True

    def delete_search(self, search_id: str) -> bool:
        """
        Delete a saved search.

        Args:
            search_id: ID of the search to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if search_id in self.searches:
            del self.searches[search_id]
            self._save_searches()
            logger.info(f"Deleted saved search: {search_id}")
            return True
        return False

    def update_search_stats(self, search_id: str, results_count: int) -> None:
        """
        Update statistics for a search after it's run.

        Args:
            search_id: ID of the search
            results_count: Number of results found
        """
        search = self.searches.get(search_id)
        if search:
            search.last_run = datetime.now().isoformat()
            search.results_count = results_count
            self._save_searches()


class JobScraperManager:
    """Manages multiple job scrapers and coordinates searches."""

    def __init__(self, results_folder: str = "job_search_results"):
        """
        Initialize the job scraper manager.

        Args:
            results_folder: Folder to store search results
        """
        self.results_folder = results_folder
        os.makedirs(results_folder, exist_ok=True)

        # Initialize all available scrapers
        self.scrapers: Dict[str, BaseJobScraper] = {
            "LinkedIn": LinkedInScraper(),
            "Indeed": IndeedScraper(),
            "Jobs.ie": JobsIEScraper(),
        }

        self.saved_search_manager = SavedSearchManager()
        logger.info(f"JobScraperManager initialized with {len(self.scrapers)} scrapers")

    def get_available_sources(self) -> List[str]:
        """Get list of available job sources."""
        return list(self.scrapers.keys())

    def search_jobs(
        self,
        source: str,
        filters: SearchFilters,
        max_results: int = 50,
        save_results: bool = True,
    ) -> List[JobPosting]:
        """
        Search for jobs on a specific source.

        Args:
            source: Job site source (e.g., "LinkedIn", "Indeed")
            filters: Search filters
            max_results: Maximum number of results
            save_results: Whether to save results to file

        Returns:
            List of JobPosting objects
        """
        scraper = self.scrapers.get(source)
        if not scraper:
            logger.error(f"Unknown job source: {source}")
            return []

        logger.info(f"Searching {source} with filters: {filters.to_dict()}")
        jobs = scraper.search_jobs(filters, max_results)

        if save_results and jobs:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{source.lower().replace('.', '_')}_{timestamp}.json"
            filepath = os.path.join(self.results_folder, filename)
            scraper.save_results(jobs, filepath)

        return jobs

    def search_all_sources(
        self, filters: SearchFilters, max_results_per_source: int = 50
    ) -> Dict[str, List[JobPosting]]:
        """
        Search all available job sources.

        Args:
            filters: Search filters
            max_results_per_source: Maximum results per source

        Returns:
            Dictionary mapping source names to lists of JobPosting objects
        """
        all_jobs = {}
        for source in self.scrapers.keys():
            logger.info(f"Searching {source}...")
            jobs = self.search_jobs(source, filters, max_results_per_source)
            all_jobs[source] = jobs
            logger.info(f"Found {len(jobs)} jobs on {source}")

        return all_jobs

    def run_saved_search(
        self, search_id: str, max_results: int = 50
    ) -> List[JobPosting]:
        """
        Run a saved search.

        Args:
            search_id: ID of the saved search
            max_results: Maximum number of results

        Returns:
            List of JobPosting objects
        """
        search = self.saved_search_manager.get_search(search_id)
        if not search:
            logger.error(f"Saved search not found: {search_id}")
            return []

        logger.info(f"Running saved search: {search.name}")
        jobs = self.search_jobs(search.source, search.filters, max_results)

        # Update search statistics
        self.saved_search_manager.update_search_stats(search_id, len(jobs))

        # Save with search name
        if jobs:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = search.name.replace(" ", "_").replace("/", "_")
            filename = f"{safe_name}_{timestamp}.json"
            filepath = os.path.join(self.results_folder, filename)
            self.scrapers[search.source].save_results(jobs, filepath)

        return jobs

    def get_saved_results(self) -> List[str]:
        """Get list of saved result files."""
        if not os.path.exists(self.results_folder):
            return []

        files = [f for f in os.listdir(self.results_folder) if f.endswith(".json")]
        return sorted(files, reverse=True)  # Most recent first

    def load_saved_results(self, filename: str) -> List[JobPosting]:
        """
        Load results from a saved file.

        Args:
            filename: Name of the results file

        Returns:
            List of JobPosting objects
        """
        filepath = os.path.join(self.results_folder, filename)
        return BaseJobScraper.load_results(filepath)

    def export_to_job_descriptions(
        self, jobs: List[JobPosting], job_descriptions_folder: str
    ) -> int:
        """
        Export job postings to the job descriptions folder for resume tailoring.

        Args:
            jobs: List of JobPosting objects to export
            job_descriptions_folder: Path to job descriptions folder

        Returns:
            Number of jobs exported
        """
        os.makedirs(job_descriptions_folder, exist_ok=True)
        exported = 0

        for job in jobs:
            try:
                # Create a safe filename
                safe_title = job.title.replace("/", "_").replace("\\", "_")[:50]
                safe_company = job.company.replace("/", "_").replace("\\", "_")[:30]
                filename = f"{safe_company}_{safe_title}.txt"
                filepath = os.path.join(job_descriptions_folder, filename)

                # Create job description content
                content = f"""Job Title: {job.title}
Company: {job.company}
Location: {job.location}
Source: {job.source}
URL: {job.url}

{job.description}

Salary: {job.salary or "Not specified"}
Job Type: {job.job_type or "Not specified"}
Remote: {"Yes" if job.remote else "No" if job.remote is not None else "Not specified"}
Experience Level: {job.experience_level or "Not specified"}
Posted: {job.posted_date or "Not specified"}
"""

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

                exported += 1
                logger.debug(f"Exported job to: {filepath}")

            except Exception as e:
                logger.error(f"Error exporting job {job.title}: {e}")

        logger.info(f"Exported {exported} jobs to {job_descriptions_folder}")
        return exported


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Test the manager
    manager = JobScraperManager()

    logger.info(f"Available sources: {manager.get_available_sources()}")

    # Create a test search
    filters = SearchFilters(
        keywords="python developer",
        location="Dublin",
        job_type=["Full-time"],
        remote_only=False,
    )

    # Save the search
    saved_search = manager.saved_search_manager.create_search(
        name="Dublin Python Jobs", source="Indeed", filters=filters
    )

    logger.info(f"Created saved search: {saved_search.name}")

    # Test searching (commented out to avoid actual web requests in test)
    # jobs = manager.search_jobs("Indeed", filters, max_results=5)
    # logger.info(f"Found {len(jobs)} jobs")

    # List saved searches
    all_searches = manager.saved_search_manager.get_all_searches()
    logger.info(f"Total saved searches: {len(all_searches)}")
    for search in all_searches:
        logger.info(f"  - {search.name} ({search.source})")
