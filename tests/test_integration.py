import unittest
import os
import json
import subprocess
from unittest.mock import patch, MagicMock
from state_manager import StateManager
from utils import calculate_file_hash

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.test_input_folder = "integration_test_input"
        self.test_output_folder = "integration_test_output"
        self.test_state_filepath = "processed_resumes_state.json"
        self.test_schema_filepath = "resume_schema.json"

        os.makedirs(self.test_input_folder, exist_ok=True)
        os.makedirs(self.test_output_folder, exist_ok=True)

        # Create a dummy schema file
        self.valid_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Resume",
            "type": "object",
            "properties": {
                "personal_info": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"}
                    },
                    "required": ["name", "email"]
                },
                "summary": {"type": "string"},
                "experience": {"type": "array", "items": {"type": "object"}},
                "education": {"type": "array", "items": {"type": "object"}},
                "skills": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["personal_info", "experience", "education", "skills"]
        }
        with open(self.test_schema_filepath, "w") as f:
            json.dump(self.valid_schema, f)

        # Create a sample valid resume
        self.sample_resume_content = {
            "personal_info": {
                "name": "Integration Test User",
                "email": "integration.test@example.com"
            },
            "summary": "A highly capable individual for integration testing.",
            "experience": [],
            "education": [],
            "skills": ["Python", "Integration Testing"]
        }
        self.sample_resume_filename = "integration_resume.json"
        self.sample_resume_filepath = os.path.join(self.test_input_folder, self.sample_resume_filename)
        with open(self.sample_resume_filepath, "w") as f:
            json.dump(self.sample_resume_content, f, indent=4)

        self.sample_resume_hash = calculate_file_hash(self.sample_resume_filepath)
        self.expected_output_pdf = os.path.join(self.test_output_folder, "integration_resume_enhanced.pdf")

    def tearDown(self):
        # Clean up all test files and folders
        if os.path.exists(self.sample_resume_filepath):
            os.remove(self.sample_resume_filepath)
        if os.path.exists(self.test_input_folder):
            os.rmdir(self.test_input_folder)
        if os.path.exists(self.expected_output_pdf):
            os.remove(self.expected_output_pdf)
        if os.path.exists(self.test_output_folder):
            os.rmdir(self.test_output_folder)
        if os.path.exists(self.test_state_filepath):
            os.remove(self.test_state_filepath)
        if os.path.exists(self.test_schema_filepath):
            os.remove(self.test_schema_filepath)

    @patch('gemini_integrator.GeminiAPIIntegrator.enhance_resume')
    def test_full_workflow_new_resume(self, mock_enhance_resume):
        """Test the full workflow for a new resume."""
        # Mock the Gemini API response
        mock_enhance_resume.return_value = {
            "personal_info": {
                "name": "Integration Test User",
                "email": "integration.test@example.com"
            },
            "summary": "An expertly enhanced summary for integration testing.",
            "experience": [],
            "education": [],
            "skills": ["Python", "Integration Testing", "Enhanced Skill"]
        }

        # Run the main script
        result = subprocess.run(
            ["python", "main.py",
             "--input_folder", self.test_input_folder,
             "--output_folder", self.test_output_folder,
             "--api_key", "dummy_api_key"], # Provide a dummy API key, it will be mocked
            capture_output=True, text=True, check=False
        )

        # Assertions
        self.assertEqual(result.returncode, 0, f"Script failed with error: {result.stderr}")
        self.assertTrue(os.path.exists(self.expected_output_pdf))

        state_manager = StateManager(self.test_state_filepath)
        self.assertTrue(state_manager.is_processed(self.sample_resume_hash))
        self.assertEqual(state_manager.get_resume_state(self.sample_resume_hash)["output_path"], self.expected_output_pdf)
        mock_enhance_resume.assert_called_once()

    @patch('gemini_integrator.GeminiAPIIntegrator.enhance_resume')
    def test_full_workflow_already_processed_resume(self, mock_enhance_resume):
        """Test that an already processed resume is skipped."""
        # Pre-process the resume and update state
        state_manager = StateManager(self.test_state_filepath)
        state_manager.update_resume_state(self.sample_resume_hash, self.expected_output_pdf)

        # Run the main script
        result = subprocess.run(
            ["python", "main.py",
             "--input_folder", self.test_input_folder,
             "--output_folder", self.test_output_folder,
             "--api_key", "dummy_api_key"],
            capture_output=True, text=True, check=False
        )

        # Assertions
        self.assertEqual(result.returncode, 0, f"Script failed with error: {result.stderr}")
        self.assertIn(f"Skipping already processed resume: {self.sample_resume_filepath}", result.stdout)
        self.assertFalse(mock_enhance_resume.called) # Gemini API should not be called

    @patch('gemini_integrator.GeminiAPIIntegrator.enhance_resume')
    def test_full_workflow_modified_resume(self, mock_enhance_resume):
        """Test that a modified resume is re-processed."""
        # Process the resume once
        state_manager = StateManager(self.test_state_filepath)
        state_manager.update_resume_state(self.sample_resume_hash, self.expected_output_pdf)

        # Modify the resume file
        modified_content = self.sample_resume_content.copy()
        modified_content["summary"] = "A significantly modified summary for re-processing."
        with open(self.sample_resume_filepath, "w") as f:
            json.dump(modified_content, f, indent=4)

        new_hash = calculate_file_hash(self.sample_resume_filepath)
        self.assertNotEqual(self.sample_resume_hash, new_hash) # Ensure hash changed

        # Mock the Gemini API response for the modified content
        mock_enhance_resume.return_value = {
            "personal_info": {
                "name": "Integration Test User",
                "email": "integration.test@example.com"
            },
            "summary": "A significantly modified summary for re-processing - enhanced.",
            "experience": [],
            "education": [],
            "skills": ["Python", "Integration Testing", "Enhanced Skill"]
        }

        # Run the main script again
        result = subprocess.run(
            ["python", "main.py",
             "--input_folder", self.test_input_folder,
             "--output_folder", self.test_output_folder,
             "--api_key", "dummy_api_key"],
            capture_output=True, text=True, check=False
        )

        # Assertions
        self.assertEqual(result.returncode, 0, f"Script failed with error: {result.stderr}")
        self.assertTrue(os.path.exists(self.expected_output_pdf)) # PDF should be overwritten or new one created
        self.assertTrue(state_manager.is_processed(new_hash))
        self.assertEqual(state_manager.get_resume_state(new_hash)["output_path"], self.expected_output_pdf)
        mock_enhance_resume.assert_called_once() # Should be called for the modified resume

if __name__ == '__main__':
    unittest.main()