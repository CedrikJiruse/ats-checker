import json
import os
import unittest
from tempfile import TemporaryDirectory

from output_generator import OutputGenerator


class TestOutputGeneratorLayout(unittest.TestCase):
    def test_output_subdir_pattern_creates_nested_output_dir(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(
                output_folder=tmp,
                structured_output_format="json",
                output_subdir_pattern="{resume_name}/{job_title}/{timestamp}",
            )

            resume_data = {
                "personal_info": {"name": "Alice", "email": "alice@example.com"},
                "skills": ["Python"],
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)
            resume_filename = "Alice Resume.txt"
            job_title = "software_engineer"

            structured_path = gen.generate_structured_output(
                resume_data_str, resume_filename, job_title
            )

            self.assertTrue(os.path.isfile(structured_path))

            # Expect: <tmp>/<resume_name>/<job_title>/<timestamp>/<file>
            # resume_name should be "Alice Resume" (spaces are ok)
            # job_title should be "software_engineer"
            rel = os.path.relpath(structured_path, tmp)
            parts = rel.split(os.sep)

            self.assertGreaterEqual(len(parts), 4)
            self.assertEqual(parts[0], "Alice Resume")
            self.assertEqual(parts[1], "software_engineer")
            # parts[2] is timestamp, do not hardcode its value here
            self.assertTrue(parts[2])
            self.assertTrue(parts[-1].endswith("_enhanced.json"))

    def test_bundle_timestamp_shared_between_structured_and_text_outputs(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(
                output_folder=tmp,
                structured_output_format="json",
                output_subdir_pattern="{resume_name}/{job_title}/{timestamp}",
            )

            resume_data = {
                "personal_info": {"name": "Score User", "email": "score@example.com"},
                "skills": ["Python"],
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)
            resume_filename = "resume.txt"
            job_title = "generic"

            structured_path = gen.generate_structured_output(
                resume_data_str, resume_filename, job_title
            )
            text_path = gen.generate_text_output(
                resume_data_str, resume_filename, job_title
            )

            self.assertTrue(os.path.isfile(structured_path))
            self.assertTrue(os.path.isfile(text_path))

            structured_dir = os.path.dirname(structured_path)
            text_dir = os.path.dirname(text_path)

            # Same bundle => same timestamped output directory
            self.assertEqual(structured_dir, text_dir)

            # Structured output should embed _meta.timestamp matching the directory name
            ts_dir = os.path.basename(structured_dir)
            with open(structured_path, "r", encoding="utf-8") as f:
                obj = json.load(f)

            self.assertIsInstance(obj, dict)
            meta = obj.get("_meta")
            self.assertIsInstance(meta, dict)
            self.assertEqual(meta.get("timestamp"), ts_dir)

    def test_explicit_timestamp_forces_output_dir_and_is_reused_by_bundle(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(
                output_folder=tmp,
                structured_output_format="json",
                output_subdir_pattern="{resume_name}/{job_title}/{timestamp}",
            )

            resume_data = {
                "personal_info": {"name": "Bob", "email": "bob@example.com"},
                "skills": ["Python"],
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)
            resume_filename = "bob.txt"
            job_title = "generic"

            forced_ts = "20250101_010203"

            # Start bundle with an explicit timestamp via text output
            text_path = gen.generate_text_output(
                resume_data_str, resume_filename, job_title, timestamp=forced_ts
            )
            self.assertTrue(os.path.isfile(text_path))
            self.assertEqual(os.path.basename(os.path.dirname(text_path)), forced_ts)

            # Next structured output should reuse the bundle timestamp when timestamp=None
            structured_path = gen.generate_structured_output(
                resume_data_str, resume_filename, job_title
            )
            self.assertTrue(os.path.isfile(structured_path))
            self.assertEqual(
                os.path.basename(os.path.dirname(structured_path)), forced_ts
            )

            with open(structured_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            meta = obj.get("_meta")
            self.assertIsInstance(meta, dict)
            self.assertEqual(meta.get("timestamp"), forced_ts)

    def test_different_job_titles_do_not_share_bundle_timestamp(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(
                output_folder=tmp,
                structured_output_format="json",
                output_subdir_pattern="{resume_name}/{job_title}/{timestamp}",
            )

            resume_data = {
                "personal_info": {"name": "Carol", "email": "carol@example.com"},
                "skills": ["Python"],
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)
            resume_filename = "carol.txt"

            # Use explicit timestamps to avoid flakiness due to time resolution
            path_a = gen.generate_structured_output(
                resume_data_str, resume_filename, "job_a", timestamp="TS_A"
            )
            path_b = gen.generate_structured_output(
                resume_data_str, resume_filename, "job_b", timestamp="TS_B"
            )

            self.assertTrue(os.path.isfile(path_a))
            self.assertTrue(os.path.isfile(path_b))

            dir_a = os.path.dirname(path_a)
            dir_b = os.path.dirname(path_b)

            self.assertNotEqual(dir_a, dir_b)
            self.assertEqual(os.path.basename(dir_a), "TS_A")
            self.assertEqual(os.path.basename(dir_b), "TS_B")

    def test_output_subdir_pattern_with_backslashes_is_normalized(self):
        with TemporaryDirectory() as tmp:
            # Intentionally use backslashes in the pattern; OutputGenerator should normalize it.
            gen = OutputGenerator(
                output_folder=tmp,
                structured_output_format="json",
                output_subdir_pattern="{resume_name}\\{job_title}\\{timestamp}",
            )

            resume_data = {
                "personal_info": {"name": "Dana", "email": "dana@example.com"},
                "skills": ["Python"],
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)

            structured_path = gen.generate_structured_output(
                resume_data_str, "dana.txt", "generic", timestamp="TS"
            )
            self.assertTrue(os.path.isfile(structured_path))

            rel = os.path.relpath(structured_path, tmp)
            parts = rel.split(os.sep)
            self.assertGreaterEqual(len(parts), 4)
            self.assertEqual(parts[0], "dana")
            self.assertEqual(parts[1], "generic")
            self.assertEqual(parts[2], "TS")


if __name__ == "__main__":
    unittest.main()
