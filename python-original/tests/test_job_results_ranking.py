import json
import os
import unittest
from tempfile import TemporaryDirectory

from job_scraper_base import JobPosting
from job_scraper_manager import JobScraperManager


class TestJobResultsRankingAndRawLoading(unittest.TestCase):
    def _make_manager(
        self, results_folder: str, saved_searches_path: str
    ) -> JobScraperManager:
        # SavedSearchManager will load/migrate on init; point it at a temp path.
        return JobScraperManager(
            results_folder=results_folder,
            saved_searches_path=saved_searches_path,
        )

    def test_load_results_file_raw_toml_returns_dict_shape(self):
        with TemporaryDirectory() as tmp:
            results_dir = os.path.join(tmp, "results")
            os.makedirs(results_dir, exist_ok=True)

            saved_searches = os.path.join(tmp, "saved_searches.toml")
            mgr = self._make_manager(results_dir, saved_searches)

            # Create a minimal TOML results file
            toml_path = os.path.join(results_dir, "linkedin_20250101_120000.toml")
            toml_text = "\n".join(
                [
                    'source = "LinkedIn"',
                    'timestamp = "20250101_120000"',
                    "",
                    "[filters]",
                    'keywords = "python"',
                    'location = "Dublin"',
                    "remote_only = false",
                    "",
                    "[jobs.0]",
                    'title = "Software Engineer"',
                    'company = "Tech Corp"',
                    'location = "Dublin"',
                    'description = "A"'.ljust(220, "A")[:220].replace("\n", " "),
                    'url = "https://example.com/1"',
                    'source = "linkedin"',
                    "",
                    "[jobs.1]",
                    'title = "Data Engineer"',
                    'company = "Data Inc"',
                    'location = "Remote"',
                    'description = "B"'.ljust(220, "B")[:220].replace("\n", " "),
                    'url = "https://example.com/2"',
                    'source = "linkedin"',
                ]
            )

            # The description lines above are intentionally simplistic; ensure TOML remains valid.
            # Re-write with valid quoted strings.
            toml_text = "\n".join(
                [
                    'source = "LinkedIn"',
                    'timestamp = "20250101_120000"',
                    "",
                    "[filters]",
                    'keywords = "python"',
                    'location = "Dublin"',
                    "remote_only = false",
                    "",
                    "[jobs.0]",
                    'title = "Software Engineer"',
                    'company = "Tech Corp"',
                    'location = "Dublin"',
                    'description = "A role with responsibilities and requirements."',
                    'url = "https://example.com/1"',
                    'source = "linkedin"',
                    "",
                    "[jobs.1]",
                    'title = "Data Engineer"',
                    'company = "Data Inc"',
                    'location = "Remote"',
                    'description = "Another role with qualifications and benefits."',
                    'url = "https://example.com/2"',
                    'source = "linkedin"',
                ]
            )

            with open(toml_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(toml_text + "\n")

            raw = mgr.load_results_file_raw(toml_path)

            self.assertIsInstance(raw, dict)
            self.assertEqual(raw.get("source"), "LinkedIn")
            self.assertEqual(raw.get("timestamp"), "20250101_120000")

            self.assertIn("filters", raw)
            self.assertIsInstance(raw.get("filters"), dict)

            self.assertIn("jobs", raw)
            self.assertIsInstance(raw.get("jobs"), dict)
            self.assertIn("0", raw["jobs"])
            self.assertIn("1", raw["jobs"])
            self.assertEqual(raw["jobs"]["0"]["title"], "Software Engineer")
            self.assertEqual(raw["jobs"]["1"]["title"], "Data Engineer")

    def test_load_results_file_raw_json_wraps_to_toml_like_dict(self):
        with TemporaryDirectory() as tmp:
            results_dir = os.path.join(tmp, "results")
            os.makedirs(results_dir, exist_ok=True)

            saved_searches = os.path.join(tmp, "saved_searches.toml")
            mgr = self._make_manager(results_dir, saved_searches)

            json_path = os.path.join(results_dir, "legacy_results.json")
            payload = [
                {
                    "title": "Role A",
                    "company": "Co A",
                    "location": "Dublin",
                    "description": "desc",
                    "url": "https://example.com/a",
                    "source": "linkedin",
                },
                {
                    "title": "Role B",
                    "company": "Co B",
                    "location": "Remote",
                    "description": "desc2",
                    "url": "https://example.com/b",
                    "source": "indeed",
                },
            ]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            raw = mgr.load_results_file_raw(json_path)

            self.assertIsInstance(raw, dict)
            self.assertIn("jobs", raw)
            self.assertIsInstance(raw["jobs"], dict)
            self.assertEqual(raw["jobs"]["0"]["title"], "Role A")
            self.assertEqual(raw["jobs"]["1"]["title"], "Role B")

    def test_rank_jobs_in_results_sorts_by_job_score_desc(self):
        with TemporaryDirectory() as tmp:
            results_dir = os.path.join(tmp, "results")
            os.makedirs(results_dir, exist_ok=True)

            saved_searches = os.path.join(tmp, "saved_searches.toml")
            mgr = self._make_manager(results_dir, saved_searches)

            toml_path = os.path.join(results_dir, "scored_results.toml")
            toml_text = "\n".join(
                [
                    'source = "LinkedIn"',
                    'timestamp = "20250101_120000"',
                    "",
                    "[jobs.0]",
                    'title = "Low Score Job"',
                    'company = "Co Low"',
                    'location = "Dublin"',
                    'description = "short desc"',
                    'url = "https://example.com/low"',
                    'source = "linkedin"',
                    "job_score = 10.0",
                    "",
                    "[jobs.1]",
                    'title = "High Score Job"',
                    'company = "Co High"',
                    'location = "Remote"',
                    'description = "longer description that looks more like a real posting. requirements responsibilities benefits."',
                    'url = "https://example.com/high"',
                    'source = "linkedin"',
                    "job_score = 90.0",
                    "",
                    "[jobs.2]",
                    'title = "Mid Score Job"',
                    'company = "Co Mid"',
                    'location = "Dublin"',
                    'description = "some description"',
                    'url = "https://example.com/mid"',
                    'source = "linkedin"',
                    "job_score = 50.0",
                ]
            )
            with open(toml_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(toml_text + "\n")

            ranked = mgr.rank_jobs_in_results(
                toml_path, top_n=10, recompute_missing_scores=False
            )

            self.assertEqual(len(ranked), 3)
            self.assertEqual(ranked[0]["rank"], 1)
            self.assertEqual(ranked[0]["job"]["title"], "High Score Job")
            self.assertAlmostEqual(ranked[0]["job_score"], 90.0)

            self.assertEqual(ranked[1]["rank"], 2)
            self.assertEqual(ranked[1]["job"]["title"], "Mid Score Job")
            self.assertAlmostEqual(ranked[1]["job_score"], 50.0)

            self.assertEqual(ranked[2]["rank"], 3)
            self.assertEqual(ranked[2]["job"]["title"], "Low Score Job")
            self.assertAlmostEqual(ranked[2]["job_score"], 10.0)

    def test_rank_jobs_in_results_missing_score_goes_last_when_no_recompute(self):
        with TemporaryDirectory() as tmp:
            results_dir = os.path.join(tmp, "results")
            os.makedirs(results_dir, exist_ok=True)

            saved_searches = os.path.join(tmp, "saved_searches.toml")
            mgr = self._make_manager(results_dir, saved_searches)

            toml_path = os.path.join(results_dir, "missing_score.toml")
            toml_text = "\n".join(
                [
                    'source = "LinkedIn"',
                    'timestamp = "20250101_120000"',
                    "",
                    "[jobs.0]",
                    'title = "Scored"',
                    'company = "Co"',
                    'location = "Dublin"',
                    'description = "desc"',
                    'url = "https://example.com/a"',
                    'source = "linkedin"',
                    "job_score = 42.0",
                    "",
                    "[jobs.1]",
                    'title = "Unscored"',
                    'company = "Co2"',
                    'location = "Remote"',
                    'description = "desc2"',
                    'url = "https://example.com/b"',
                    'source = "linkedin"',
                ]
            )
            with open(toml_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(toml_text + "\n")

            ranked = mgr.rank_jobs_in_results(
                toml_path, top_n=10, recompute_missing_scores=False
            )

            self.assertEqual(len(ranked), 2)
            self.assertEqual(ranked[0]["job"]["title"], "Scored")
            self.assertEqual(ranked[1]["job"]["title"], "Unscored")

    def test_rank_jobs_in_results_recomputes_missing_score_when_enabled(self):
        with TemporaryDirectory() as tmp:
            results_dir = os.path.join(tmp, "results")
            os.makedirs(results_dir, exist_ok=True)

            saved_searches = os.path.join(tmp, "saved_searches.toml")
            mgr = self._make_manager(results_dir, saved_searches)

            toml_path = os.path.join(results_dir, "recompute_score.toml")
            toml_text = "\n".join(
                [
                    'source = "LinkedIn"',
                    'timestamp = "20250101_120000"',
                    "",
                    "[jobs.0]",
                    'title = "Unscored but Realistic"',
                    'company = "Co"',
                    'location = "Dublin"',
                    # Long description helps job scoring heuristics be non-trivial
                    'description = "Responsibilities: build systems. Requirements: python. Benefits: health. "',
                    'url = "https://example.com/a"',
                    'source = "linkedin"',
                    "",
                    "[jobs.1]",
                    'title = "Already scored"',
                    'company = "Co2"',
                    'location = "Remote"',
                    'description = "short desc"',
                    'url = "https://example.com/b"',
                    'source = "linkedin"',
                    "job_score = 1.0",
                ]
            )
            with open(toml_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(toml_text + "\n")

            ranked = mgr.rank_jobs_in_results(
                toml_path, top_n=10, recompute_missing_scores=True
            )

            self.assertEqual(len(ranked), 2)

            # Ensure the previously-unscored job now has a numeric score and a report attached.
            entry0 = next(
                e for e in ranked if e["job"]["title"] == "Unscored but Realistic"
            )
            self.assertIsInstance(entry0.get("job_score"), (int, float))
            self.assertIn("job_score", entry0["job"])
            self.assertIn("job_score_report", entry0["job"])
            self.assertIsInstance(entry0["job"]["job_score_report"], dict)

    def test_load_results_file_filters_extra_fields_into_jobposting(self):
        with TemporaryDirectory() as tmp:
            results_dir = os.path.join(tmp, "results")
            os.makedirs(results_dir, exist_ok=True)

            saved_searches = os.path.join(tmp, "saved_searches.toml")
            mgr = self._make_manager(results_dir, saved_searches)

            toml_path = os.path.join(results_dir, "with_extras.toml")
            toml_text = "\n".join(
                [
                    'source = "LinkedIn"',
                    'timestamp = "20250101_120000"',
                    "",
                    "[jobs.0]",
                    'title = "Software Engineer"',
                    'company = "Tech Corp"',
                    'location = "Dublin"',
                    'description = "A real job description."',
                    'url = "https://example.com/1"',
                    'source = "linkedin"',
                    "job_score = 77.0",
                    "",
                    "[jobs.0.job_score_report]",
                    'kind = "job"',
                    "total = 77.0",
                ]
            )
            with open(toml_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(toml_text + "\n")

            jobs = mgr.load_results_file(toml_path)

            self.assertEqual(len(jobs), 1)
            self.assertIsInstance(jobs[0], JobPosting)
            self.assertEqual(jobs[0].title, "Software Engineer")
            self.assertEqual(jobs[0].company, "Tech Corp")


if __name__ == "__main__":
    unittest.main()
