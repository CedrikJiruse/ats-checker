import unittest
import os
from output_generator import OutputGenerator
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from typing import Dict, Any, List

class TestOutputGenerator(unittest.TestCase):

    def setUp(self):
        self.test_output_folder = "test_output_pdfs"
        self.output_generator = OutputGenerator(output_folder=self.test_output_folder)
        self.sample_resume_data = {
            "personal_info": {
                "name": "Test User",
                "email": "test.user@example.com",
                "phone": "111-222-3333",
                "linkedin": "https://linkedin.com/in/testuser",
                "github": "https://github.com/testuser"
            },
            "summary": "A highly skilled and motivated individual with expertise in various technologies.",
            "experience": [
                {
                    "title": "Software Engineer",
                    "company": "Test Corp",
                    "location": "Test City, TC",
                    "start_date": "2020-01-01",
                    "end_date": "2023-12-31",
                    "description": [
                        "Developed and maintained software applications.",
                        "Collaborated with team members on projects."
                    ]
                }
            ],
            "education": [
                {
                    "degree": "B.Sc. Computer Science",
                    "institution": "Test University",
                    "location": "University Town, UT",
                    "graduation_date": "2019-05-01",
                    "gpa": "3.5/4.0"
                }
            ],
            "skills": ["Python", "Java", "Testing"],
            "projects": [
                {
                    "name": "Test Project",
                    "description": "A project to test PDF generation.",
                    "link": "https://github.com/testuser/testproject"
                }
            ]
        }

    def tearDown(self):
        # Clean up generated PDF files and the output folder
        for root, _, files in os.walk(self.test_output_folder):
            for f in files:
                os.remove(os.path.join(root, f))
        if os.path.exists(self.test_output_folder):
            os.rmdir(self.test_output_folder)

    def test_generate_pdf_creates_file(self):
        """Test that generate_pdf creates a PDF file."""
        output_filename = "test_resume.pdf"
        filepath = self.output_generator.generate_pdf(self.sample_resume_data, output_filename)
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(os.path.isfile(filepath))
        self.assertTrue(filepath.endswith(".pdf"))

    def test_generate_pdf_returns_correct_filepath(self):
        """Test that generate_pdf returns the correct file path."""
        output_filename = "another_test_resume.pdf"
        expected_filepath = os.path.join(self.test_output_folder, output_filename)
        actual_filepath = self.output_generator.generate_pdf(self.sample_resume_data, output_filename)
        self.assertEqual(actual_filepath, expected_filepath)

    def test_generate_pdf_with_minimal_data(self):
        """Test PDF generation with minimal required resume data."""
        minimal_resume_data = {
            "personal_info": {
                "name": "Minimal User",
                "email": "minimal.user@example.com"
            },
            "experience": [],
            "education": [],
            "skills": []
        }
        output_filename = "minimal_resume.pdf"
        filepath = self.output_generator.generate_pdf(minimal_resume_data, output_filename)
        self.assertTrue(os.path.exists(filepath))

    def test_output_folder_creation(self):
        """Test that the output folder is created if it doesn't exist."""
        # Remove the folder if it exists from previous tests
        if os.path.exists(self.test_output_folder):
            os.rmdir(self.test_output_folder)

        # Re-initialize to trigger folder creation
        new_output_generator = OutputGenerator(output_folder=self.test_output_folder)
        self.assertTrue(os.path.exists(self.test_output_folder))
        self.assertTrue(os.path.isdir(self.test_output_folder))

if __name__ == '__main__':
    unittest.main()