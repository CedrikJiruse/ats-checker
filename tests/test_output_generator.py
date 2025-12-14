import json
import os
import unittest
from tempfile import TemporaryDirectory

from output_generator import OutputGenerator


class TestOutputGenerator(unittest.TestCase):
    def test_initialization_creates_output_folder(self):
        with TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "nested", "out")
            self.assertFalse(os.path.exists(out_dir))

            gen = OutputGenerator(output_folder=out_dir)

            self.assertTrue(os.path.isdir(gen.output_folder))
            # OutputGenerator stores an absolute path internally
            self.assertTrue(os.path.isabs(gen.output_folder))

    def test_generate_json_output_creates_file_and_preserves_content(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(output_folder=tmp)

            resume_data = {
                "personal_info": {
                    "name": "Test User",
                    "email": "test@example.com",
                },
                "summary": "Résumé with non-ascii: José",
                "skills": ["Python", "Testing"],
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)
            resume_filename = "my_resume.txt"
            job_title = "Software_Engineer"

            out_path = gen.generate_json_output(
                resume_data_str, resume_filename, job_title
            )

            self.assertTrue(os.path.isfile(out_path))
            self.assertTrue(
                out_path.endswith("my_resume_Software_Engineer_enhanced.json")
            )

            with open(out_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            self.assertEqual(loaded["personal_info"]["name"], "Test User")
            self.assertEqual(loaded["summary"], "Résumé with non-ascii: José")
            self.assertEqual(loaded["skills"], ["Python", "Testing"])

    def test_generate_text_output_creates_file_and_includes_expected_sections(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(output_folder=tmp)

            resume_data = {
                "personal_info": {
                    "name": "Alice Wonderland",
                    "email": "alice.w@example.com",
                    "phone": "987-654-3210",
                    "linkedin": "https://linkedin.com/in/alicew",
                    "github": "https://github.com/alicew",
                    "portfolio": "https://alice.example.com",
                },
                "summary": "Highly motivated engineer.",
                "experience": [
                    {
                        "title": "Software Engineer",
                        "company": "Tech Corp",
                        "location": "Dublin, Ireland",
                        "start_date": "2023-01-01",
                        "end_date": "Present",
                        "description": [
                            "Built features",
                            "Wrote tests",
                        ],
                    }
                ],
                "education": [
                    {
                        "degree": "B.Sc. Computer Science",
                        "institution": "University of Example",
                        "location": "Dublin",
                        "graduation_date": "2022",
                        "gpa": "3.9/4.0",
                    }
                ],
                "skills": ["Python", "PyTest"],
                "projects": [
                    {
                        "name": "ATS Checker",
                        "description": "Improved resume parsing.",
                        "link": "https://github.com/example/ats-checker",
                    }
                ],
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)
            resume_filename = "Alice_Resume.txt"
            job_title = "Data_Scientist"

            out_path = gen.generate_text_output(
                resume_data_str, resume_filename, job_title
            )

            self.assertTrue(os.path.isfile(out_path))
            self.assertTrue(
                out_path.endswith("Alice_Resume_Data_Scientist_enhanced.txt")
            )

            with open(out_path, "r", encoding="utf-8") as f:
                text = f.read()

            # Personal info
            self.assertIn("Name: Alice Wonderland", text)
            self.assertIn("Email: alice.w@example.com", text)
            self.assertIn("Phone: 987-654-3210", text)
            self.assertIn("LinkedIn: https://linkedin.com/in/alicew", text)
            self.assertIn("GitHub: https://github.com/alicew", text)
            self.assertIn("Portfolio: https://alice.example.com", text)

            # Sections
            self.assertIn("Summary:", text)
            self.assertIn("Highly motivated engineer.", text)

            self.assertIn("Experience:", text)
            self.assertIn("Software Engineer - Tech Corp", text)
            self.assertIn("2023-01-01 - Present | Dublin, Ireland", text)
            self.assertIn("• Built features", text)
            self.assertIn("• Wrote tests", text)

            self.assertIn("Education:", text)
            self.assertIn("B.Sc. Computer Science", text)
            self.assertIn("University of Example, Dublin", text)
            self.assertIn("Graduation: 2022 | GPA: 3.9/4.0", text)

            self.assertIn("Skills:", text)
            self.assertIn("Python, PyTest", text)

            self.assertIn("Projects:", text)
            self.assertIn("ATS Checker", text)
            self.assertIn("Improved resume parsing.", text)
            self.assertIn("Link: https://github.com/example/ats-checker", text)

    def test_generate_text_output_missing_optional_fields_uses_defaults(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(output_folder=tmp)

            # Intentionally omit personal_info, experience, education, projects, etc.
            resume_data = {
                "skills": ["Python"],
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)

            out_path = gen.generate_text_output(
                resume_data_str, "resume.txt", "generic"
            )
            self.assertTrue(os.path.isfile(out_path))

            with open(out_path, "r", encoding="utf-8") as f:
                text = f.read()

            # Defaults
            self.assertIn("Name: N/A", text)
            self.assertIn("Email: N/A", text)
            # Skills still printed
            self.assertIn("Skills:", text)
            self.assertIn("Python", text)

    def test_generate_text_output_includes_scores_when_scoring_metadata_present(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(output_folder=tmp)

            resume_data = {
                "personal_info": {
                    "name": "Score User",
                    "email": "score@example.com",
                },
                "skills": ["Python"],
                "_scoring": {
                    "iteration_score": 87.5,
                    "resume_report": {
                        "total": 80.0,
                        "categories": [
                            {"name": "completeness", "score": 90.0, "weight": 0.3},
                        ],
                    },
                    "match_report": {
                        "total": 92.0,
                        "categories": [
                            {"name": "keyword_overlap", "score": 95.0, "weight": 0.45},
                        ],
                    },
                },
            }
            resume_data_str = json.dumps(resume_data, ensure_ascii=False)

            out_path = gen.generate_text_output(
                resume_data_str, "resume.txt", "generic"
            )
            self.assertTrue(os.path.isfile(out_path))

            with open(out_path, "r", encoding="utf-8") as f:
                text = f.read()

            self.assertIn("Scores:", text)
            self.assertIn("Overall: 87.5", text)

            # The score renderer may format floats slightly differently across versions,
            # but these labels must exist when resume_report/match_report are present.
            self.assertIn("Resume:", text)
            self.assertIn("Match:", text)

            # Category lines should be present; don't overfit to weight/float formatting.
            self.assertIn("- completeness: 90.0", text)
            self.assertIn("- keyword_overlap: 95.0", text)

    def test_generate_json_output_invalid_json_raises(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(output_folder=tmp)

            with self.assertRaises(json.JSONDecodeError):
                gen.generate_json_output("{not valid json", "resume.txt", "generic")

    def test_generate_text_output_invalid_json_raises(self):
        with TemporaryDirectory() as tmp:
            gen = OutputGenerator(output_folder=tmp)

            with self.assertRaises(json.JSONDecodeError):
                gen.generate_text_output("{not valid json", "resume.txt", "generic")


if __name__ == "__main__":
    unittest.main()
