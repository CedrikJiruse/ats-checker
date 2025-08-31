import unittest
import os
import json
from unittest.mock import MagicMock, patch
from input_handler import InputHandler
from resume_processor import ResumeProcessor
from state_manager import StateManager
from config import load_config
import argparse

class TestJobDescriptionIntegration(unittest.TestCase):

    def setUp(self):
        self.test_input_folder = "test_input_resumes_jd"
        self.test_output_folder = "test_output_jd"
        self.test_job_description_folder = "test_job_descriptions_jd"
        self.test_schema_filepath = "test_resume_schema_jd.json"
        self.test_state_filepath = "test_state_jd.json"
        self.test_config_filepath = "test_config_jd.json"

        os.makedirs(self.test_input_folder, exist_ok=True)
        os.makedirs(self.test_output_folder, exist_ok=True)
        os.makedirs(self.test_job_description_folder, exist_ok=True)

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
                "experience": {"type": "array", "items": {"type": "object"}},
                "education": {"type": "array", "items": {"type": "object"}},
                "skills": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["personal_info", "experience", "education", "skills"]
        }
        with open(self.test_schema_filepath, "w") as f:
            json.dump(self.valid_schema, f)

        # Create a dummy config file
        self.test_config_content = {
            "output_folder": self.test_output_folder,
            "num_versions_per_job": 1,
            "model_name": "gemini-pro",
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "input_resumes_folder": self.test_input_folder,
            "resume_schema_path": self.test_schema_filepath,
            "job_descriptions_folder": self.test_job_description_folder
        }
        with open(self.test_config_filepath, "w") as f:
            json.dump(self.test_config_content, f)

        self.state_manager = StateManager(self.test_state_filepath)
        self.input_handler = InputHandler(self.state_manager, self.test_schema_filepath, self.test_job_description_folder)

    def tearDown(self):
        # Clean up test files and folders
        for folder in [self.test_input_folder, self.test_output_folder, self.test_job_description_folder]:
            if os.path.exists(folder):
                for root, _, files in os.walk(folder):
                    for f in files:
                        os.remove(os.path.join(root, f))
                os.rmdir(folder)
        
        for f in [self.test_schema_filepath, self.test_state_filepath, self.test_config_filepath]:
            if os.path.exists(f):
                os.remove(f)

    def _create_resume_file(self, filename: str, content: dict) -> str:
        filepath = os.path.join(self.test_input_folder, filename)
        with open(filepath, "w") as f:
            json.dump(content, f)
        return filepath

    def _create_job_description_file(self, filename: str, content: str) -> str:
        filepath = os.path.join(self.test_job_description_folder, filename)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def test_get_job_descriptions(self):
        """Test that InputHandler correctly reads job descriptions."""
        self._create_job_description_file("software_engineer.txt", "Looking for a software engineer.")
        self._create_job_description_file("data_scientist.md", "Data scientist with machine learning experience.")

        job_descriptions = self.input_handler.get_job_descriptions()
        self.assertIn("software_engineer.txt", job_descriptions)
        self.assertIn("data_scientist.md", job_descriptions)
        self.assertEqual(job_descriptions["software_engineer.txt"], "Looking for a software engineer.")
        self.assertEqual(job_descriptions["data_scientist.md"], "Data scientist with machine learning experience.")

    @patch('gemini_integrator.GeminiAPIIntegrator.enhance_resume')
    @patch('output_generator.OutputGenerator.generate_pdf')
    def test_process_resumes_with_job_description(self, mock_generate_pdf, mock_enhance_resume):
        """Test processing resumes with a specific job description."""
        mock_enhance_resume.return_value = {"enhanced": "resume"}
        mock_generate_pdf.return_value = "path/to/pdf"

        valid_resume_content = {
            "personal_info": {"name": "John Doe", "email": "john.doe@example.com"},
            "experience": [], "education": [], "skills": []
        }
        self._create_resume_file("john_doe.json", valid_resume_content)
        self._create_job_description_file("software_engineer.txt", "Looking for a software engineer.")

        config = load_config(self.test_config_filepath)
        processor = ResumeProcessor(
            input_folder=config.input_resumes_folder,
            output_folder=config.output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_output_tokens,
            resume_schema_path=config.resume_schema_path,
            num_versions_per_job=config.num_versions_per_job,
            job_description_folder=config.job_descriptions_folder
        )
        processor.process_resumes(job_description_name="software_engineer.txt")

        mock_enhance_resume.assert_called_once_with(valid_resume_content, job_description="Looking for a software engineer.")
        mock_generate_pdf.assert_called_once()
        self.assertTrue(self.state_manager.is_processed(self.input_handler.calculate_file_hash(os.path.join(self.test_input_folder, "john_doe.json"))))

    @patch('gemini_integrator.GeminiAPIIntegrator.enhance_resume')
    @patch('output_generator.OutputGenerator.generate_pdf')
    def test_process_resumes_without_job_description(self, mock_generate_pdf, mock_enhance_resume):
        """Test processing resumes without a job description."""
        mock_enhance_resume.return_value = {"enhanced": "resume"}
        mock_generate_pdf.return_value = "path/to/pdf"

        valid_resume_content = {
            "personal_info": {"name": "Jane Doe", "email": "jane.doe@example.com"},
            "experience": [], "education": [], "skills": []
        }
        self._create_resume_file("jane_doe.json", valid_resume_content)

        config = load_config(self.test_config_filepath)
        processor = ResumeProcessor(
            input_folder=config.input_resumes_folder,
            output_folder=config.output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_output_tokens,
            resume_schema_path=config.resume_schema_path,
            num_versions_per_job=config.num_versions_per_job,
            job_description_folder=config.job_descriptions_folder
        )
        processor.process_resumes()

        mock_enhance_resume.assert_called_once_with(valid_resume_content, job_description=None)
        mock_generate_pdf.assert_called_once()
        self.assertTrue(self.state_manager.is_processed(self.input_handler.calculate_file_hash(os.path.join(self.test_input_folder, "jane_doe.json"))))

    @patch('sys.argv', ['main.py', '--config_file', 'test_config_jd.json', '--job_description', 'software_engineer.txt'])
    @patch('main.main') # Patch main.main to prevent it from running fully
    def test_main_with_job_description_argument(self, mock_main_func):
        """Test that main.py correctly parses job description argument."""
        # This test primarily checks argument parsing. The actual processing logic is mocked.
        # We need to re-import main to pick up the sys.argv change
        import main as main_module
        with patch('main.ResumeProcessor') as MockResumeProcessor:
            with patch('main.InputHandler') as MockInputHandler:
                mock_input_handler_instance = MockInputHandler.return_value
                mock_input_handler_instance.get_job_descriptions.return_value = {"software_engineer.txt": "JD Content"}
                
                main_module.main()
                
                MockResumeProcessor.assert_called_once()
                # Assert that process_resumes was called with the job description
                MockResumeProcessor.return_value.process_resumes.assert_called_once_with(job_description_name="software_engineer.txt")

    @patch('sys.argv', ['main.py', '--config_file', 'test_config_jd.json'])
    @patch('main.main') # Patch main.main to prevent it from running fully
    def test_main_without_job_description_argument(self, mock_main_func):
        """Test that main.py correctly handles no job description argument."""
        import main as main_module
        with patch('main.ResumeProcessor') as MockResumeProcessor:
            main_module.main()
            MockResumeProcessor.assert_called_once()
            MockResumeProcessor.return_value.process_resumes.assert_called_once_with(job_description_name=None)


if __name__ == '__main__':
    unittest.main()