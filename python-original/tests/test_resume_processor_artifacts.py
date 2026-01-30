import json
import os
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

import resume_processor
from resume_processor import ResumeProcessor


class _FakeGeminiAPIIntegrator:
    def __init__(self, *args, **kwargs):
        pass

    def enhance_resume(self, resume_content: str, job_description=None) -> str:
        # Minimal structured resume payload; ResumeProcessor will enrich with _meta/_scoring.
        resume_obj = {
            "personal_info": {"name": "Alice Example", "email": "alice@example.com"},
            "summary": "Test summary",
            "experience": [],
            "education": [],
            "skills": ["Python"],
            "projects": [],
        }
        return json.dumps(resume_obj, ensure_ascii=False)

    def revise_resume(self, *args, **kwargs) -> str:
        raise AssertionError("revise_resume should not be called in this test")


class _FakeInputHandler:
    def __init__(self, *args, **kwargs):
        self._resumes = kwargs.get("_resumes", [])

    def get_resumes_to_process(self, input_folder: str):
        return list(self._resumes)

    def get_job_descriptions(self):
        return {}


class TestResumeProcessorArtifacts(unittest.TestCase):
    def test_writes_manifest_and_scores_toml_files(self):
        with TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            output_dir = os.path.join(tmp, "output")
            os.makedirs(input_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            # Create a real file path for stable naming; content isn't read because InputHandler is mocked.
            resume_path = os.path.join(input_dir, "alice.txt")
            with open(resume_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("Raw resume content")

            state_path = os.path.join(tmp, "state.toml")

            fake_resumes = [
                {
                    "filepath": resume_path,
                    "content": "Raw resume content",
                    "hash": "hash-alice-123",
                }
            ]

            fake_input_handler = _FakeInputHandler(_resumes=fake_resumes)

            # Patch constructors used by ResumeProcessor to avoid external calls.
            with (
                patch.object(
                    resume_processor,
                    "GeminiAPIIntegrator",
                    return_value=_FakeGeminiAPIIntegrator(),
                ),
                patch.object(
                    resume_processor, "InputHandler", return_value=fake_input_handler
                ),
            ):
                processor = ResumeProcessor(
                    input_folder=input_dir,
                    output_folder=output_dir,
                    model_name="gemini-pro",
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=1024,
                    num_versions_per_job=1,
                    job_description_folder=None,
                    tesseract_cmd=None,
                    structured_output_format="toml",
                    output_subdir_pattern="{resume_name}/{job_title}/{timestamp}",
                    write_score_summary_file=True,
                    score_summary_filename="scores.toml",
                    write_manifest_file=True,
                    manifest_filename="manifest.toml",
                    max_concurrent_requests=1,
                    score_cache_enabled=True,
                    state_filepath=state_path,
                    # Keep schema validation/recommendations off to minimize moving parts in this artifact test.
                    schema_validation_enabled=False,
                    recommendations_enabled=False,
                )

                processor.process_resumes(job_description_name=None)

            # Find the output bundle directory by searching for manifest.toml
            manifest_path = None
            scores_path = None
            structured_path = None
            text_path = None

            for root, _dirs, files in os.walk(output_dir):
                if "manifest.toml" in files:
                    manifest_path = os.path.join(root, "manifest.toml")
                if "scores.toml" in files:
                    scores_path = os.path.join(root, "scores.toml")
                for fn in files:
                    if fn.endswith("_generic_enhanced.toml"):
                        structured_path = os.path.join(root, fn)
                    if fn.endswith("_generic_enhanced.txt"):
                        text_path = os.path.join(root, fn)

            self.assertIsNotNone(manifest_path, "manifest.toml was not created")
            self.assertIsNotNone(scores_path, "scores.toml was not created")
            self.assertIsNotNone(
                structured_path, "structured resume TOML was not created"
            )
            self.assertIsNotNone(text_path, "text resume output was not created")

            # Ensure they live in the same bundle directory
            bundle_dir = os.path.dirname(manifest_path)
            self.assertEqual(os.path.dirname(scores_path), bundle_dir)
            self.assertEqual(os.path.dirname(structured_path), bundle_dir)
            self.assertEqual(os.path.dirname(text_path), bundle_dir)

            # Parse TOML files (Python 3.11+)
            import tomllib

            with open(manifest_path, "rb") as f:
                manifest = tomllib.load(f)

            with open(scores_path, "rb") as f:
                scores = tomllib.load(f)

            self.assertIsInstance(manifest, dict)
            self.assertIsInstance(scores, dict)

            # Manifest basic structure
            self.assertIn("meta", manifest)
            self.assertIn("outputs", manifest)
            self.assertIn("scoring", manifest)

            outputs = manifest.get("outputs", {})
            self.assertIsInstance(outputs, dict)
            self.assertTrue(outputs.get("structured_output_path"))
            self.assertTrue(outputs.get("text_output_path"))
            # scores.toml path may be empty if writing failed; in this test it should exist.
            self.assertTrue(outputs.get("score_summary_path"))

            meta = manifest.get("meta", {})
            self.assertIsInstance(meta, dict)
            self.assertEqual(meta.get("resume_filename"), "alice.txt")
            self.assertEqual(meta.get("job_title"), "generic")

            # Scores file should have an iteration_score and a mode
            self.assertIn("iteration_score", scores)
            self.assertIsInstance(scores.get("iteration_score"), (int, float))
            self.assertIn("mode", scores)

            # Structured resume output should contain _scoring and _meta (best-effort)
            with open(structured_path, "rb") as f:
                structured_doc = tomllib.load(f)

            self.assertIsInstance(structured_doc, dict)
            self.assertIn("_scoring", structured_doc)
            self.assertIn("_meta", structured_doc)
            self.assertIsInstance(structured_doc["_scoring"], dict)
            self.assertIn("iteration_score", structured_doc["_scoring"])
            self.assertIsInstance(structured_doc["_meta"], dict)
            self.assertIn("timestamp", structured_doc["_meta"])


if __name__ == "__main__":
    unittest.main()
