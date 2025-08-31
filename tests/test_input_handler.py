import unittest
import os
import json
from unittest.mock import MagicMock, patch
from input_handler import InputHandler
from state_manager import StateManager

class TestInputHandler(unittest.TestCase):

    def setUp(self):
        self.test_input_folder = "test_input_handler_resumes"
        self.test_schema_filepath = "test_resume_schema.json"
        self.test_state_filepath = "test_state_input_handler.json"

        os.makedirs(self.test_input_folder, exist_ok=True)

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

        self.state_manager = StateManager(self.test_state_filepath)
        self.input_handler = InputHandler(self.state_manager, self.test_schema_filepath)

    def tearDown(self):
        # Clean up test files and folders
        for root, _, files in os.walk(self.test_input_folder):
            for f in files:
                os.remove(os.path.join(root, f))
        if os.path.exists(self.test_input_folder):
            os.rmdir(self.test_input_folder)
        if os.path.exists(self.test_schema_filepath):
            os.remove(self.test_schema_filepath)
        if os.path.exists(self.test_state_filepath):
            os.remove(self.test_state_filepath)

    def _create_resume_file(self, filename: str, content: dict) -> str:
        filepath = os.path.join(self.test_input_folder, filename)
        with open(filepath, "w") as f:
            json.dump(content, f)
        return filepath

    def test_get_resumes_to_process_valid_new_resume(self):
        """Test processing a valid, new resume."""
        valid_resume_content = {
            "personal_info": {"name": "John Doe", "email": "john.doe@example.com"},
            "experience": [], "education": [], "skills": []
        }
        self._create_resume_file("valid_new.json", valid_resume_content)

        resumes = self.input_handler.get_resumes_to_process(self.test_input_folder)
        self.assertEqual(len(resumes), 1)
        self.assertEqual(resumes["content"], valid_resume_content)
        self.assertIn("hash", resumes)

    def test_get_resumes_to_process_invalid_resume_schema(self):
        """Test skipping an invalid resume due to schema validation."""
        invalid_resume_content = {
            "personal_info": {"name": "Jane Doe"}, # Missing email
            "experience": [], "education": [], "skills": []
        }
        self._create_resume_file("invalid_schema.json", invalid_resume_content)

        resumes = self.input_handler.get_resumes_to_process(self.test_input_folder)
        self.assertEqual(len(resumes), 0)

    def test_get_resumes_to_process_already_processed_resume(self):
        """Test skipping a resume that has already been processed."""
        valid_resume_content = {
            "personal_info": {"name": "Alice", "email": "alice@example.com"},
            "experience": [], "education": [], "skills": []
        }
        filepath = self._create_resume_file("already_processed.json", valid_resume_content)
        file_hash = self.input_handler.calculate_file_hash(filepath) # Use the actual hash calculation
        self.state_manager.update_resume_state(file_hash, "output/alice.pdf")

        resumes = self.input_handler.get_resumes_to_process(self.test_input_folder)
        self.assertEqual(len(resumes), 0)

    def test_get_resumes_to_process_mixed_files(self):
        """Test processing a mix of valid, invalid, and processed resumes."""
        valid_resume_content1 = {
            "personal_info": {"name": "Bob", "email": "bob@example.com"},
            "experience": [], "education": [], "skills": []
        }
        filepath1 = self._create_resume_file("bob.json", valid_resume_content1)
        file_hash1 = self.input_handler.calculate_file_hash(filepath1)
        self.state_manager.update_resume_state(file_hash1, "output/bob.pdf") # Bob is processed

        valid_resume_content2 = {
            "personal_info": {"name": "Charlie", "email": "charlie@example.com"},
            "experience": [], "education": [], "skills": []
        }
        self._create_resume_file("charlie.json", valid_resume_content2) # Charlie is new

        invalid_resume_content = {
            "personal_info": {"name": "David"}, # Missing email
            "experience": [], "education": [], "skills": []
        }
        self._create_resume_file("david.json", invalid_resume_content) # David is invalid

        resumes = self.input_handler.get_resumes_to_process(self.test_input_folder)
        self.assertEqual(len(resumes), 1)
        self.assertEqual(resumes["content"]["personal_info"]["name"], "Charlie")

    def test_get_resumes_to_process_non_existent_folder(self):
        """Test handling a non-existent input folder."""
        resumes = self.input_handler.get_resumes_to_process("non_existent_folder")
        self.assertEqual(len(resumes), 0)

    def test_get_resumes_to_process_malformed_json(self):
        """Test skipping a malformed JSON file."""
        filepath = os.path.join(self.test_input_folder, "malformed.json")
        with open(filepath, "w") as f:
            f.write("{'personal_info': {'name': 'Frank', 'email': 'frank@example.com'}}") # Invalid JSON syntax

        resumes = self.input_handler.get_resumes_to_process(self.test_input_folder)
        self.assertEqual(len(resumes), 0)

    @patch('input_handler.calculate_file_hash')
    def test_input_handler_uses_calculate_file_hash(self, mock_calculate_file_hash):
        """Test that InputHandler calls calculate_file_hash."""
        mock_calculate_file_hash.return_value = "mock_hash"
        valid_resume_content = {
            "personal_info": {"name": "Grace", "email": "grace@example.com"},
            "experience": [], "education": [], "skills": []
        }
        self._create_resume_file("grace.json", valid_resume_content)

        self.input_handler.get_resumes_to_process(self.test_input_folder)
        mock_calculate_file_hash.assert_called_once()

if __name__ == '__main__':
    unittest.main()