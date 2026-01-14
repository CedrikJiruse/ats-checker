"""
Manager for JobSpy-based job scrapers and saved searches.

Changes in this version:
- Removes all non-JobSpy scrapers (no fallback to basic HTML scrapers).
- Switches saved searches storage from JSON -> TOML.
- Switches job search results storage from JSON -> TOML.
- Restores the legacy `JobScraperManager` API surface that `main.py` expects:
  - `run_saved_search(...)`
  - `get_saved_results()`
  - `load_saved_results(filename)`
  - `export_to_job_descriptions(...)`

TOML formats:

Saved searches file (default: data/saved_searches.toml)
-----------------------------------------------
[searches.<id>]
id = "<id>"
name = "My search"
source = "LinkedIn"
created_at = "2025-12-13T12:34:56.123456"
last_run = "2025-12-13T12:40:00.000000"
results_count = 42

[searches.<id>.filters]
keywords = "software engineer"
location = "Dublin"
remote_only = true
job_type = ["Full-time"]
experience_level = ["Mid"]
salary_min = 80000
date_posted = "week"

Results file example (default: job_search_results/<source>_<timestamp>.toml)
---------------------------------------------------------------------------
source = "LinkedIn"
timestamp = "20251213_124000"

[filters]
keywords = "software engineer"
location = "Dublin"
remote_only = false

[jobs.0]
title = "Software Engineer"
company = "Tech Corp"
location = "Dublin"
description = "..."
url = "https://example.com/job/1"
source = "linkedin"
posted_date = "2025-12-01"
salary = "EUR 60,000 - 80,000 per yearly"
job_type = "fulltime"
remote = false
experience_level = "Mid"
scraped_at = "2025-12-13T12:40:00.000000"
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from job_scraper_base import BaseJobScraper, JobPosting, SavedSearch, SearchFilters
from job_scrapers_improved import (
    GlassdoorJobSpyScraper,
    GoogleJobSpyScraper,
    IndeedJobSpyScraper,
    LinkedInJobSpyScraper,
    ZipRecruiterJobSpyScraper,
)
from scoring import score_job

logger = logging.getLogger(__name__)

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None


# ---------------------------
# TOML read/write (best-effort)
# ---------------------------


def _toml_load_file(path: str) -> Dict[str, Any]:
    """
    Load TOML with stdlib `tomllib` when available, otherwise fallback to local `toml_io`.
    """
    if tomllib is not None:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        if not isinstance(data, dict):
            return {}
        return data

    # Fallback for older Python (or environments lacking tomllib)
    import toml_io  # type: ignore

    data = toml_io.load(path)
    if not isinstance(data, dict):
        return {}
    return data


def _toml_dump_file(path: str, data: Dict[str, Any]) -> None:
    """
    Write TOML using local `toml_io` if available, otherwise use a minimal serializer.
    """
    try:
        import toml_io  # type: ignore

        toml_io.dump(data, path)
        return
    except Exception:
        text = _toml_dumps_minimal(data)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)


def _toml_dumps_minimal(data: Dict[str, Any]) -> str:
    """
    Minimal TOML serializer (nested dict tables + lists + scalar values).
    TOML has no null, so None values are omitted.
    """
    if not isinstance(data, dict):
        raise ValueError("TOML root must be a dict")

    lines: List[str] = []
    _emit_toml_table(lines, data, path=())
    return ("\n".join(lines)).rstrip() + "\n"


def _emit_toml_table(
    lines: List[str], table: Dict[str, Any], path: Tuple[str, ...]
) -> None:
    primitives: Dict[str, Any] = {}
    subtables: Dict[str, Dict[str, Any]] = {}

    for k, v in table.items():
        if v is None:
            continue
        if isinstance(v, dict):
            subtables[k] = v
        else:
            primitives[k] = v

    if path:
        lines.append(f"[{'.'.join(path)}]")

    for k in sorted(primitives.keys()):
        lines.append(f"{k} = {_toml_format_value(primitives[k])}")

    if primitives and subtables:
        lines.append("")

    for k in sorted(subtables.keys()):
        _emit_toml_table(lines, subtables[k], path=path + (k,))
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()


def _toml_format_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        return _toml_quote(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_format_value(x) for x in v) + "]"
    raise ValueError(f"Unsupported TOML value type: {type(v).__name__}")


def _toml_quote(s: str) -> str:
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return f'"{s}"'


# ---------------------------
# Saved searches (TOML)
# ---------------------------


class SavedSearchManager:
    """Manages saved job searches (stored in TOML)."""

    def __init__(self, storage_path: str = "data/saved_searches.toml"):
        """
        Args:
            storage_path: Path to store saved searches as TOML.
        """
        self.storage_path = storage_path
        self.searches: Dict[str, SavedSearch] = {}
        self._load_searches()

    def _load_searches(self) -> None:
        if not os.path.exists(self.storage_path):
            # Backward compatibility: migrate legacy JSON -> TOML if TOML is missing.
            legacy_candidates = [
                os.path.splitext(self.storage_path)[0] + ".json",
                "data/saved_searches.json",
                "saved_searches.json",
            ]
            legacy_json_path = next(
                (p for p in legacy_candidates if os.path.exists(p)), None
            )

            if legacy_json_path:
                try:
                    with open(legacy_json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if not isinstance(data, list):
                        logger.warning(
                            "Legacy saved searches file %s is not a list; skipping migration",
                            legacy_json_path,
                        )
                        return

                    migrated = 0
                    for search_data in data:
                        if not isinstance(search_data, dict):
                            continue
                        search = SavedSearch.from_dict(search_data)
                        self.searches[search.id] = search
                        migrated += 1

                    # Persist migrated searches to TOML (best-effort).
                    self._save_searches()
                    logger.info(
                        "Migrated %d saved searches from %s to %s",
                        migrated,
                        legacy_json_path,
                        self.storage_path,
                    )
                    return
                except Exception as e:
                    logger.error(
                        "Error migrating legacy saved searches from %s: %s",
                        legacy_json_path,
                        e,
                        exc_info=True,
                    )
                    return

            logger.info(
                "No saved searches file found at %s, starting fresh", self.storage_path
            )
            return

        try:
            doc = _toml_load_file(self.storage_path)
            searches_tbl = doc.get("searches", {})
            if not isinstance(searches_tbl, dict):
                logger.warning(
                    "Invalid saved searches schema in %s; expected [searches.*] tables",
                    self.storage_path,
                )
                return

            loaded = 0
            for search_id, search_data in searches_tbl.items():
                if not isinstance(search_id, str) or not isinstance(search_data, dict):
                    continue

                # Normalize: ensure 'id' exists (SavedSearch.from_dict requires it)
                if "id" not in search_data:
                    search_data = dict(search_data)
                    search_data["id"] = search_id

                # Filters are stored as a nested dict
                filters_data = search_data.get("filters", {})
                if not isinstance(filters_data, dict):
                    filters_data = {}

                # SavedSearch.from_dict expects filters as a dict under "filters"
                # and other fields at the top-level.
                normalized = dict(search_data)
                normalized["filters"] = filters_data

                search = SavedSearch.from_dict(normalized)
                self.searches[search.id] = search
                loaded += 1

            logger.info("Loaded %d saved searches from %s", loaded, self.storage_path)
        except Exception as e:
            logger.error(
                "Error loading saved searches from %s: %s",
                self.storage_path,
                e,
                exc_info=True,
            )

    def _save_searches(self) -> None:
        try:
            os.makedirs(
                os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True
            )
        except Exception:
            pass

        try:
            doc: Dict[str, Any] = {"searches": {}}
            for search in self.searches.values():
                doc["searches"][search.id] = search.to_dict()
            _toml_dump_file(self.storage_path, doc)
            logger.debug("Saved searches to %s", self.storage_path)
        except Exception as e:
            logger.error(
                "Error saving searches to %s: %s", self.storage_path, e, exc_info=True
            )

    def create_search(
        self, name: str, source: str, filters: SearchFilters
    ) -> SavedSearch:
        search_id = str(uuid.uuid4())
        search = SavedSearch(id=search_id, name=name, source=source, filters=filters)
        self.searches[search_id] = search
        self._save_searches()
        logger.info("Created saved search: %s (ID: %s)", name, search_id)
        return search

    def get_search(self, search_id: str) -> Optional[SavedSearch]:
        return self.searches.get(search_id)

    def get_all_searches(self) -> List[SavedSearch]:
        return list(self.searches.values())

    def update_search(
        self,
        search_id: str,
        name: Optional[str] = None,
        filters: Optional[SearchFilters] = None,
    ) -> bool:
        search = self.searches.get(search_id)
        if not search:
            return False

        if name:
            search.name = name
        if filters:
            search.filters = filters

        self._save_searches()
        logger.info("Updated saved search: %s", search_id)
        return True

    def delete_search(self, search_id: str) -> bool:
        if search_id in self.searches:
            del self.searches[search_id]
            self._save_searches()
            logger.info("Deleted saved search: %s", search_id)
            return True
        return False

    def update_search_stats(self, search_id: str, results_count: int) -> None:
        search = self.searches.get(search_id)
        if search:
            search.last_run = datetime.now().isoformat()
            search.results_count = results_count
            self._save_searches()


# ---------------------------
# Job scrapers (JobSpy only)
# ---------------------------


class JobScraperManager:
    """Manages JobSpy-based job scrapers and coordinates searches."""

    # Default portal mappings (portal_id -> (display_name, scraper_class))
    PORTAL_SCRAPERS = {
        "linkedin": ("LinkedIn", LinkedInJobSpyScraper),
        "indeed": ("Indeed", IndeedJobSpyScraper),
        "glassdoor": ("Glassdoor", GlassdoorJobSpyScraper),
        "google": ("Google Jobs", GoogleJobSpyScraper),
        "ziprecruiter": ("ZipRecruiter", ZipRecruiterJobSpyScraper),
    }

    def __init__(
        self,
        results_folder: str = "job_search_results",
        saved_searches_path: str = "data/saved_searches.toml",
        portals_config: Optional[Dict[str, Dict[str, Any]]] = None,
        jobspy_config: Optional[Dict[str, Any]] = None,
        search_defaults: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            results_folder: Folder to store search results as TOML files.
            saved_searches_path: Path for saved searches TOML file.
            portals_config: Dict of portal configs (enable/disable, display names).
            jobspy_config: Global JobSpy settings (e.g., country_indeed).
            search_defaults: Default filter values for job searches.
        """
        self.results_folder = results_folder
        os.makedirs(self.results_folder, exist_ok=True)

        # Store configs for use in searches
        self.search_defaults = search_defaults or {}
        self.jobspy_config = jobspy_config or {}

        # Build scrapers from config, filtering disabled portals
        self.scrapers = self._build_scrapers(portals_config)

        self.saved_search_manager = SavedSearchManager(storage_path=saved_searches_path)
        logger.info(
            "JobScraperManager initialized with %d JobSpy scrapers", len(self.scrapers)
        )

    def _build_scrapers(
        self, portals_config: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, BaseJobScraper]:
        """
        Build scraper instances from portal configuration.

        Args:
            portals_config: Dict from config.job_search_portals

        Returns:
            Dict[display_name, scraper_instance]
        """
        scrapers: Dict[str, BaseJobScraper] = {}

        for portal_id, (default_name, scraper_class) in self.PORTAL_SCRAPERS.items():
            cfg = (portals_config or {}).get(portal_id, {"enabled": True})
            if not cfg.get("enabled", True):
                logger.debug("Portal %s is disabled, skipping", portal_id)
                continue

            display_name = cfg.get("display_name", default_name)
            scrapers[display_name] = scraper_class()

        return scrapers

    def get_available_sources(self) -> List[str]:
        return list(self.scrapers.keys())

    def search_jobs(
        self,
        source: str,
        filters: SearchFilters,
        max_results: int = 50,
        save_results: bool = True,
    ) -> List[JobPosting]:
        scraper = self.scrapers.get(source)
        if not scraper:
            logger.error("Unknown job source: %s", source)
            return []

        logger.info("Searching %s with filters: %s", source, filters.to_dict())

        # Get country_indeed from jobspy config
        country_indeed = self.jobspy_config.get("country_indeed", "USA")
        jobs = scraper.search_jobs(filters, max_results, country_indeed=country_indeed)

        if save_results:
            self._save_results_toml(source=source, filters=filters, jobs=jobs)

        return jobs

    def search_all_sources(
        self,
        filters: SearchFilters,
        max_results_per_source: int = 50,
        save_results: bool = True,
    ) -> Dict[str, List[JobPosting]]:
        all_jobs: Dict[str, List[JobPosting]] = {}
        for source in self.scrapers.keys():
            logger.info("Searching %s...", source)
            jobs = self.search_jobs(
                source, filters, max_results_per_source, save_results=save_results
            )
            all_jobs[source] = jobs
            logger.info("Found %d jobs on %s", len(jobs), source)
        return all_jobs

    # ---------------------------
    # Results storage (TOML)
    # ---------------------------

    def _save_results_toml(
        self, source: str, filters: SearchFilters, jobs: List[JobPosting]
    ) -> Optional[str]:
        """
        Save results to TOML even if no jobs found (still useful metadata).
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{source.lower().replace('.', '_')}_{timestamp}.toml"
            filepath = os.path.join(self.results_folder, filename)

            doc: Dict[str, Any] = {
                "source": source,
                "timestamp": timestamp,
                "filters": filters.to_dict(),
                "jobs": {},
            }

            # Store jobs as tables: [jobs.0], [jobs.1], ...
            # Also attach job scoring so result files can be ranked and filtered later.
            for i, job in enumerate(jobs or []):
                job_dict = job.to_dict()
                try:
                    job_report = score_job(job_dict)
                    job_dict["job_score"] = float(job_report.total)
                    job_dict["job_score_report"] = job_report.as_dict()
                except Exception:
                    # Scoring is best-effort; never fail saving due to scoring issues.
                    pass

                doc["jobs"][str(i)] = job_dict

            _toml_dump_file(filepath, doc)
            logger.info("Saved %d jobs to %s", len(jobs or []), filepath)
            return filepath
        except Exception as e:
            logger.error("Error saving results to TOML: %s", e, exc_info=True)
            return None

    def list_result_files(self) -> List[str]:
        """
        List result files in the results folder (TOML + legacy JSON).
        """
        if not os.path.isdir(self.results_folder):
            return []

        files = []
        for name in os.listdir(self.results_folder):
            if name.lower().endswith((".toml", ".json")):
                files.append(os.path.join(self.results_folder, name))
        files.sort()
        return files

    def load_results_file(self, filepath: str) -> List[JobPosting]:
        """
        Load results from a TOML results file (preferred) or legacy JSON results file.
        """
        _, ext = os.path.splitext(filepath.lower())
        if ext == ".json":
            return self._load_results_json(filepath)
        return self._load_results_toml(filepath)

    def load_results_file_raw(self, filepath: str) -> Dict[str, Any]:
        """
        Load a results file and return the raw document structure.

        TOML format:
            {
              "source": "...",
              "timestamp": "...",
              "filters": {...},
              "jobs": {"0": {...}, "1": {...}, ...}
            }

        Legacy JSON format:
            [ {job_dict}, {job_dict}, ... ]

        For JSON, this method wraps the list into a TOML-like dict shape:
            {"source": "", "timestamp": "", "filters": {}, "jobs": {"0": {...}, ...}}
        """
        _, ext = os.path.splitext(filepath.lower())
        if ext == ".json":
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    return {"source": "", "timestamp": "", "filters": {}, "jobs": {}}
                jobs_tbl: Dict[str, Any] = {}
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        jobs_tbl[str(i)] = item
                return {"source": "", "timestamp": "", "filters": {}, "jobs": jobs_tbl}
            except Exception as e:
                logger.error(
                    "Error loading legacy JSON results (raw) from %s: %s",
                    filepath,
                    e,
                    exc_info=True,
                )
                return {"source": "", "timestamp": "", "filters": {}, "jobs": {}}

        try:
            doc = _toml_load_file(filepath)
            return doc if isinstance(doc, dict) else {}
        except Exception as e:
            logger.error(
                "Error loading TOML results (raw) from %s: %s",
                filepath,
                e,
                exc_info=True,
            )
            return {}

    def rank_jobs_in_results(
        self,
        filepath: str,
        top_n: int = 20,
        recompute_missing_scores: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Rank jobs in a saved results file by `job_score` descending.

        If `job_score` is missing and `recompute_missing_scores=True`, it will be computed
        using `score_job(job_dict)` and attached in-memory to the returned entries.

        Returns:
            [
              {
                "rank": 1,
                "index": "0",
                "job_score": 87.5,
                "job": {... raw job dict ...}
              },
              ...
            ]
        """
        doc = self.load_results_file_raw(filepath)
        jobs_tbl = doc.get("jobs", {})
        if not isinstance(jobs_tbl, dict):
            return []

        ranked: List[Dict[str, Any]] = []

        for idx, job_data in jobs_tbl.items():
            if not isinstance(job_data, dict):
                continue

            job_dict = dict(job_data)

            score_val = job_dict.get("job_score")
            job_score: Optional[float] = None
            if isinstance(score_val, (int, float)):
                job_score = float(score_val)

            if job_score is None and recompute_missing_scores:
                try:
                    report = score_job(job_dict)
                    job_score = float(report.total)
                    job_dict["job_score"] = job_score
                    job_dict["job_score_report"] = report.as_dict()
                except Exception:
                    job_score = None

            ranked.append(
                {
                    "rank": None,
                    "index": str(idx),
                    "job_score": job_score if job_score is not None else float("-inf"),
                    "job": job_dict,
                }
            )

        ranked.sort(key=lambda x: x.get("job_score", float("-inf")), reverse=True)

        if isinstance(top_n, int) and top_n > 0:
            ranked = ranked[:top_n]

        for i, entry in enumerate(ranked, start=1):
            entry["rank"] = i

        return ranked

    def _load_results_toml(self, filepath: str) -> List[JobPosting]:
        doc = _toml_load_file(filepath)
        jobs_tbl = doc.get("jobs", {})
        if not isinstance(jobs_tbl, dict):
            return []

        # jobs are stored under numeric string keys
        jobs: List[JobPosting] = []
        for _, job_data in sorted(
            jobs_tbl.items(),
            key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 10**9,
        ):
            if isinstance(job_data, dict):
                try:
                    # Tolerate extra fields (e.g., job_score, job_score_report) by filtering
                    # to the dataclass fields JobPosting accepts.
                    allowed = set(JobPosting.__dataclass_fields__.keys())
                    filtered = {k: v for k, v in job_data.items() if k in allowed}
                    jobs.append(JobPosting(**filtered))
                except Exception:
                    # Be permissive: skip malformed entries
                    continue
        return jobs

    def _load_results_json(self, filepath: str) -> List[JobPosting]:
        """
        Legacy JSON format written by older versions:
            [ {job_dict}, {job_dict}, ... ]
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            jobs = []
            for item in data:
                if isinstance(item, dict):
                    try:
                        # Tolerate extra fields (e.g., job_score) from newer result formats.
                        allowed = set(JobPosting.__dataclass_fields__.keys())
                        filtered = {k: v for k, v in item.items() if k in allowed}
                        jobs.append(JobPosting(**filtered))
                    except Exception:
                        continue
            return jobs
        except Exception as e:
            logger.error(
                "Error loading legacy JSON results from %s: %s",
                filepath,
                e,
                exc_info=True,
            )
            return []

    # ---------------------------
    # Legacy API surface (main.py)
    # ---------------------------

    def run_saved_search(
        self, search_id: str, max_results: int = 50
    ) -> List[JobPosting]:
        """
        Run a saved search by id.

        This restores the legacy method used by `main.py`, while keeping:
        - JobSpy-only scraping
        - TOML-based persistence for saved searches and results
        """
        search = self.saved_search_manager.get_search(search_id)
        if not search:
            logger.error("Saved search not found: %s", search_id)
            return []

        logger.info("Running saved search: %s", search.name)

        # Run the search
        jobs = self.search_jobs(
            search.source, search.filters, max_results, save_results=True
        )

        # Update saved-search stats
        self.saved_search_manager.update_search_stats(search_id, len(jobs))

        # Also save a copy with the search name (nice UX parity with the old behavior)
        if jobs:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = (
                    search.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                )
                filename = f"{safe_name}_{timestamp}.toml"
                filepath = os.path.join(self.results_folder, filename)

                doc: Dict[str, Any] = {
                    "source": search.source,
                    "timestamp": timestamp,
                    "filters": search.filters.to_dict(),
                    "jobs": {},
                }
                for i, job in enumerate(jobs):
                    job_dict = job.to_dict()
                    try:
                        job_report = score_job(job_dict)
                        job_dict["job_score"] = float(job_report.total)
                        job_dict["job_score_report"] = job_report.as_dict()
                    except Exception:
                        pass
                    doc["jobs"][str(i)] = job_dict

                _toml_dump_file(filepath, doc)
                logger.info("Saved %d jobs to %s", len(jobs), filepath)
            except Exception as e:
                logger.error("Error saving named results file: %s", e, exc_info=True)

        return jobs

    def get_saved_results(self) -> List[str]:
        """
        Legacy method used by `main.py`.

        Returns:
            List of filenames (not full paths), newest first.
        """
        if not os.path.isdir(self.results_folder):
            return []

        files = [
            f
            for f in os.listdir(self.results_folder)
            if f.lower().endswith((".toml", ".json"))
        ]
        files.sort(reverse=True)
        return files

    def load_saved_results(self, filename: str) -> List[JobPosting]:
        """
        Legacy method used by `main.py`.

        Loads either:
        - TOML results files produced by this version
        - Legacy JSON result files produced by older versions
        """
        filepath = os.path.join(self.results_folder, filename)
        return self.load_results_file(filepath)

    def export_to_job_descriptions(
        self, jobs: List[JobPosting], job_descriptions_folder: str
    ) -> int:
        """
        Legacy method used by `main.py`.

        Export job postings to `job_descriptions_folder` as `.txt` files so they can be
        used for resume tailoring.

        Returns:
            Number of jobs exported successfully.
        """
        os.makedirs(job_descriptions_folder, exist_ok=True)
        exported = 0

        for job in jobs:
            try:
                safe_title = job.title.replace("/", "_").replace("\\", "_")[:50]
                safe_company = job.company.replace("/", "_").replace("\\", "_")[:30]
                filename = f"{safe_company}_{safe_title}.txt"
                filepath = os.path.join(job_descriptions_folder, filename)

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
                logger.debug("Exported job to: %s", filepath)
            except Exception as e:
                logger.error("Error exporting job %s: %s", job.title, e, exc_info=True)

        logger.info("Exported %d jobs to %s", exported, job_descriptions_folder)
        return exported
