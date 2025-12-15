import io
import json
import os
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import cli_commands


@dataclass
class FakeReport:
    total: float
    categories: list | None = None
    kind: str = "resume"

    def as_dict(self):
        # Keep it TOML-writable if needed (no arrays-of-tables)
        # For CLI output tests, categories are optional.
        return {
            "kind": self.kind,
            "total": float(self.total),
            "categories": self.categories if self.categories is not None else [],
            "meta": {},
        }


class TestCliCommands(unittest.TestCase):
    def _write_resume_json(self, path: str) -> None:
        resume_obj = {
            "personal_info": {"name": "Test User", "email": "test@example.com"},
            "summary": "Summary",
            "experience": [],
            "education": [],
            "skills": ["Python"],
            "projects": [],
        }
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(resume_obj, f, ensure_ascii=False, indent=2)

    def _write_job_desc_txt(self, path: str) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("We want a Python engineer with AWS and Docker experience.\n")

    def test_build_parser_has_expected_subcommands(self):
        parser = cli_commands.build_parser()

        args = parser.parse_args(["score-resume", "--resume", "x.toml"])
        self.assertEqual(args.command, "score-resume")
        self.assertTrue(callable(args.func))

        args = parser.parse_args(
            ["score-match", "--resume", "x.toml", "--job", "j.txt"]
        )
        self.assertEqual(args.command, "score-match")
        self.assertTrue(callable(args.func))

        args = parser.parse_args(["rank-jobs", "--results", "r.toml"])
        self.assertEqual(args.command, "rank-jobs")
        self.assertTrue(callable(args.func))

    @patch.object(cli_commands, "load_config")
    @patch.object(cli_commands, "score_resume")
    def test_cmd_score_resume_json_output(self, mock_score_resume, mock_load_config):
        with TemporaryDirectory() as tmp:
            resume_path = os.path.join(tmp, "resume.json")
            self._write_resume_json(resume_path)

            mock_load_config.return_value = SimpleNamespace(
                scoring_weights_file=os.path.join(tmp, "weights.toml")
            )
            mock_score_resume.return_value = FakeReport(total=88.0)

            args = SimpleNamespace(
                config_file="config/config.toml",
                resume=resume_path,
                weights=None,
                write_back=False,
                json=True,
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_commands.cmd_score_resume(args)

            self.assertEqual(rc, 0)

            out = buf.getvalue().strip()
            payload = json.loads(out)
            self.assertEqual(payload["mode"], "resume_only")
            self.assertAlmostEqual(payload["iteration_score"], 88.0, places=6)
            self.assertIn("resume_report", payload)

            # File should be untouched
            with open(resume_path, "r", encoding="utf-8") as f:
                resume_obj = json.load(f)
            self.assertNotIn("_scoring", resume_obj)

    @patch.object(cli_commands, "load_config")
    @patch.object(cli_commands, "score_resume")
    def test_cmd_score_resume_write_back_updates_resume_file(
        self, mock_score_resume, mock_load_config
    ):
        with TemporaryDirectory() as tmp:
            resume_path = os.path.join(tmp, "resume.json")
            self._write_resume_json(resume_path)

            mock_load_config.return_value = SimpleNamespace(
                scoring_weights_file=os.path.join(tmp, "weights.toml")
            )
            mock_score_resume.return_value = FakeReport(total=91.25)

            args = SimpleNamespace(
                config_file="config/config.toml",
                resume=resume_path,
                weights=None,
                write_back=True,
                json=False,
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_commands.cmd_score_resume(args)

            self.assertEqual(rc, 0)
            self.assertIn("Wrote _scoring into:", buf.getvalue())

            with open(resume_path, "r", encoding="utf-8") as f:
                resume_obj = json.load(f)

            self.assertIn("_scoring", resume_obj)
            self.assertEqual(resume_obj["_scoring"]["mode"], "resume_only")
            self.assertAlmostEqual(
                resume_obj["_scoring"]["iteration_score"], 91.25, places=6
            )

    @patch.object(cli_commands, "load_config")
    @patch.object(cli_commands, "compute_iteration_score")
    @patch.object(cli_commands, "score_match")
    @patch.object(cli_commands, "score_resume")
    def test_cmd_score_match_prints_keyword_samples(
        self,
        mock_score_resume,
        mock_score_match,
        mock_compute_iteration_score,
        mock_load_config,
    ):
        with TemporaryDirectory() as tmp:
            resume_path = os.path.join(tmp, "resume.json")
            job_path = os.path.join(tmp, "job.txt")
            self._write_resume_json(resume_path)
            self._write_job_desc_txt(job_path)

            mock_load_config.return_value = SimpleNamespace(
                scoring_weights_file=os.path.join(tmp, "weights.toml")
            )

            mock_score_resume.return_value = FakeReport(total=70.0, kind="resume")
            mock_score_match.return_value = FakeReport(
                total=90.0,
                kind="match",
                categories=[
                    {
                        "name": "keyword_overlap",
                        "score": 80.0,
                        "weight": 0.45,
                        "details": {
                            "sample_overlap": ["python", "docker"],
                            "sample_missing": ["aws"],
                        },
                    }
                ],
            )
            mock_compute_iteration_score.return_value = (
                82.5,
                {
                    "resume_total": 70.0,
                    "match_total": 90.0,
                    "weights": {"resume": 0.5, "match": 0.5},
                },
            )

            args = SimpleNamespace(
                config_file="config/config.toml",
                resume=resume_path,
                job=job_path,
                weights=None,
                write_back=False,
                json=False,
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_commands.cmd_score_match(args)

            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("Overall iteration score: 82.50", out)
            self.assertIn("Matched keywords", out)
            self.assertIn("python", out.lower())
            self.assertIn("Missing keywords", out)
            self.assertIn("aws", out.lower())

    @patch.object(cli_commands, "load_config")
    @patch.object(cli_commands, "JobScraperManager")
    def test_cmd_rank_jobs_displays_and_exports_top(
        self, mock_manager_cls, mock_load_config
    ):
        with TemporaryDirectory() as tmp:
            results_path = os.path.join(tmp, "results.toml")
            # Create a placeholder results file so path existence checks pass
            with open(results_path, "w", encoding="utf-8", newline="\n") as f:
                f.write('source = "LinkedIn"\n')

            mock_load_config.return_value = SimpleNamespace(
                job_search_results_folder=os.path.join(tmp, "job_search_results"),
                saved_searches_file=os.path.join(tmp, "saved_searches.toml"),
                job_descriptions_folder=os.path.join(tmp, "job_descriptions"),
                scoring_weights_file=os.path.join(tmp, "weights.toml"),
            )

            mgr = MagicMock()
            mgr.rank_jobs_in_results.return_value = [
                {
                    "rank": 1,
                    "index": "0",
                    "job_score": 95.0,
                    "job": {
                        "title": "Senior Python Engineer",
                        "company": "ACME",
                        "location": "Remote",
                        "description": "desc",
                        "url": "https://example.com/1",
                        "source": "linkedin",
                    },
                },
                {
                    "rank": 2,
                    "index": "1",
                    "job_score": 80.0,
                    "job": {
                        "title": "Python Developer",
                        "company": "ExampleCo",
                        "location": "Dublin",
                        "description": "desc",
                        "url": "https://example.com/2",
                        "source": "linkedin",
                    },
                },
            ]
            mgr.export_to_job_descriptions.return_value = 2
            mock_manager_cls.return_value = mgr

            args = SimpleNamespace(
                config_file="config/config.toml",
                results=results_path,
                top=20,
                no_recompute=False,
                export_top=2,
                json=False,
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_commands.cmd_rank_jobs(args)

            self.assertEqual(rc, 0)
            out = buf.getvalue()

            self.assertIn("Showing top", out)
            self.assertIn("Senior Python Engineer", out)
            self.assertIn("score:", out.lower())

            mgr.rank_jobs_in_results.assert_called_once()
            mgr.export_to_job_descriptions.assert_called_once()

    @patch.object(cli_commands, "load_config")
    @patch.object(cli_commands, "score_resume")
    def test_cmd_score_resume_uses_explicit_weights_override(
        self, mock_score_resume, mock_load_config
    ):
        with TemporaryDirectory() as tmp:
            resume_path = os.path.join(tmp, "resume.json")
            self._write_resume_json(resume_path)

            cfg_weights = os.path.join(tmp, "cfg_weights.toml")
            arg_weights = os.path.join(tmp, "override_weights.toml")

            mock_load_config.return_value = SimpleNamespace(
                scoring_weights_file=cfg_weights
            )
            mock_score_resume.return_value = FakeReport(total=50.0)

            args = SimpleNamespace(
                config_file="config/config.toml",
                resume=resume_path,
                weights=arg_weights,
                write_back=False,
                json=True,
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_commands.cmd_score_resume(args)

            self.assertEqual(rc, 0)
            # Ensure score_resume was called using the override weights path
            _, kwargs = mock_score_resume.call_args
            self.assertEqual(kwargs.get("weights_toml_path"), arg_weights)


if __name__ == "__main__":
    unittest.main()
