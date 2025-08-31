import unittest
import os
import json
from unittest.mock import MagicMock, patch
from gemini_integrator import GeminiAPIIntegrator

class TestGeminiAPIIntegrator(unittest.TestCase):

    def setUp(self):
        self.test_schema_filepath = "test_resume_schema.json"
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
                "summary": {"type": "string"}
            },
            "required": ["personal_info"]
        }
        with open(self.test_schema_filepath, "w") as f:
            json.dump(self.valid_schema, f)

        # Mock the genai.configure to prevent actual API key configuration
        patcher = patch('google.generativeai.configure')
        self.mock_genai_configure = patcher.start()
        self.addCleanup(patcher.stop)

        # Set a dummy API key for initialization
        os.environ["GEMINI_API_KEY"] = "dummy_api_key"
        self.integrator = GeminiAPIIntegrator(model_name="mock-model")

    def tearDown(self):
        if os.path.exists(self.test_schema_filepath):
            os.remove(self.test_schema_filepath)
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

    @patch('google.generativeai.GenerativeModel')
    def test_enhance_resume_success(self, MockGenerativeModel):
        """Test successful resume enhancement with mocked Gemini API."""
        mock_model_instance = MockGenerativeModel.return_value
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "personal_info": {"name": "John Doe", "email": "john.doe@example.com"},
            "summary": "Enhanced software engineer summary."
        })
        mock_model_instance.generate_content.return_value = mock_response

        sample_resume_data = {
            "personal_info": {"name": "John Doe", "email": "john.doe@example.com"},
            "summary": "Software engineer."
        }

        enhanced_data = self.integrator.enhance_resume(sample_resume_data)
        self.assertIn("Enhanced software engineer summary.", enhanced_data["summary"])
        mock_model_instance.generate_content.assert_called_once()

    @patch('google.generativeai.GenerativeModel')
    def test_enhance_resume_api_error(self, MockGenerativeModel):
        """Test handling of Gemini API errors."""
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.side_effect = Exception("API call failed")

        sample_resume_data = {
            "personal_info": {"name": "John Doe", "email": "john.doe@example.com"},
            "summary": "Software engineer."
        }

        with self.assertRaises(Exception) as cm:
            self.integrator.enhance_resume(sample_resume_data)
        self.assertIn("API call failed", str(cm.exception))

    @patch('google.generativeai.GenerativeModel')
    def test_enhance_resume_invalid_json_response(self, MockGenerativeModel):
        """Test handling of invalid JSON response from Gemini API."""
        mock_model_instance = MockGenerativeModel.return_value
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
        mock_model_instance.generate_content.return_value = mock_response

        sample_resume_data = {
            "personal_info": {"name": "John Doe", "email": "john.doe@example.com"},
            "summary": "Software engineer."
        }

        with self.assertRaises(Exception) as cm:
            self.integrator.enhance_resume(sample_resume_data)
        self.assertIn("JSONDecodeError", str(cm.exception))

    def test_api_key_not_provided(self):
        """Test that an error is raised if API key is not provided."""
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        with self.assertRaises(ValueError) as cm:
            GeminiAPIIntegrator()
        self.assertIn("GEMINI_API_KEY not found", str(cm.exception))

if __name__ == '__main__':
    unittest.main()