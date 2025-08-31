import unittest
import os
import json
from unittest.mock import MagicMock, patch
from resume_processor import ResumeProcessor
from state_manager import StateManager
from input_handler import InputHandler
from gemini_integrator import GeminiAPIIntegrator
from output_generator import OutputGenerator

class TestResumeProcessor(unittest.TestCase):

    def setUp(self):
        self.input_folder = "test_input_processor"
        self.output_folder = "test_output_processor"
        os.makedirs(self.input_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

        # Mock dependencies
        self.mock_state_manager = MagicMock(spec=StateManager)
        self.mock_input_handler = MagicMock(spec=InputHandler)
        self.mock_gemini_integrator = MagicMock(spec=GeminiAPIIntegrator)
        self.mock_output_generator = MagicMock(spec=OutputGenerator)

        # Patch the classes in resume_processor to return our mocks
        self.patcher_state = patch('resume_processor.StateManager', return_value=self.mock_state_manager)
        self.patcher_input = patch('resume_processor.InputHandler', return_value=self.mock_input_handler)
        self.patcher_gemini = patch('resume_processor.GeminiAPIIntegrator', return_value=self.mock_gemini_integrator)
        self.patcher_output = patch('resume_processor.OutputGenerator', return_value=self.mock_output_generator)

        self.patcher_state.start()
        self.patcher_input.start()
        self.patcher_gemini.start()
        self.patcher_output.start()

        self.processor = ResumeProcessor(self.input_folder, self.output_folder, api_key="dummy_key")

    def tearDown(self):
        self.patcher_state.stop()
        self.patcher_input.stop()
        self.patcher_gemini.stop()
        self.patcher_output.stop()

        for root, _, files in os.walk(self.input_folder):
            for f in files:
                os.remove(os.path.join(root, f))
        if os.path.exists(self.input_folder):
            os.rmdir(self.input_folder)
        for root, _, files in os.walk(self.output_folder):
            for f in files:
                os.remove(os.path.join(root, f))
        if os.path.exists(self.output_folder):
            os.rmdir(self.output_folder)

    def test_process_resumes_no_new_resumes(self):
        """Test when no new or modified resumes are found."""
        self.mock_input_handler.get_resumes_to_process.return_value = []
        self.processor.process_resumes()
        self.mock_input_handler.get_resumes_to_process.assert_called_once_with(self.input_folder)
        self.mock_gemini_integrator.enhance_resume.assert_not_called()
        self.mock_output_generator.generate_pdf.assert_not_called()
        self.mock_state_manager.update_resume_state.assert_not_called()

    def test_process_resumes_one_new_resume_success(self):
        """Test processing one new resume successfully."""
        sample_resume = {
            "filepath": os.path.join(self.input_folder, "resume1.json"),
            "content": {"personal_info": {"name": "Test1"}},
            "hash": "hash1"
        }
        self.mock_input_handler.get_resumes_to_process.return_value = [sample_resume]
        self.mock_gemini_integrator.enhance_resume.return_value = {"personal_info": {"name": "Test1 Enhanced"}}
        self.mock_output_generator.generate_pdf.return_value = os.path.join(self.output_folder, "resume1_enhanced.pdf")

        self.processor.process_resumes()

        self.mock_input_handler.get_resumes_to_process.assert_called_once_with(self.input_folder)
        self.mock_gemini_integrator.enhance_resume.assert_called_once_with(sample_resume["content"])
        self.mock_output_generator.generate_pdf.assert_called_once()
        self.mock_state_manager.update_resume_state.assert_called_once_with(
            sample_resume["hash"], os.path.join(self.output_folder, "resume1_enhanced.pdf")
        )

    def test_process_resumes_multiple_resumes_mixed_results(self):
        """Test processing multiple resumes with some failures."""
        sample_resume1 = {
            "filepath": os.path.join(self.input_folder, "resume1.json"),
            "content": {"personal_info": {"name": "Test1"}},
            "hash": "hash1"
        }
        sample_resume2 = {
            "filepath": os.path.join(self.input_folder, "resume2.json"),
            "content": {"personal_info": {"name": "Test2"}},
            "hash": "hash2"
        }
        self.mock_input_handler.get_resumes_to_process.return_value = [sample_resume1, sample_resume2]

        # Simulate success for resume1, failure for resume2
        self.mock_gemini_integrator.enhance_resume.side_effect = [
            {"personal_info": {"name": "Test1 Enhanced"}},
            Exception("Gemini API error for Test2")
        ]
        self.mock_output_generator.generate_pdf.return_value = os.path.join(self.output_folder, "resume1_enhanced.pdf")

        self.processor.process_resumes()

        self.mock_input_handler.get_resumes_to_process.assert_called_once_with(self.input_folder)
        self.assertEqual(self.mock_gemini_integrator.enhance_resume.call_count, 2)
        self.mock_output_generator.generate_pdf.assert_called_once() # Only called for the successful resume
        self.mock_state_manager.update_resume_state.assert_called_once_with(
            sample_resume1["hash"], os.path.join(self.output_folder, "resume1_enhanced.pdf")
        )

    def test_process_resumes_gemini_api_error_handling(self):
        """Test error handling when Gemini API fails."""
        sample_resume = {
            "filepath": os.path.join(self.input_folder, "resume_error.json"),
            "content": {"personal_info": {"name": "ErrorUser"}},
            "hash": "hash_error"
        }
        self.mock_input_handler.get_resumes_to_process.return_value = [sample_resume]
        self.mock_gemini_integrator.enhance_resume.side_effect = Exception("Gemini API is down")

        self.processor.process_resumes()

        self.mock_gemini_integrator.enhance_resume.assert_called_once_with(sample_resume["content"])
        self.mock_output_generator.generate_pdf.assert_not_called()
        self.mock_state_manager.update_resume_state.assert_not_called()

    def test_process_resumes_pdf_generation_error_handling(self):
        """Test error handling when PDF generation fails."""
        sample_resume = {
            "filepath": os.path.join(self.input_folder, "resume_pdf_error.json"),
            "content": {"personal_info": {"name": "PDFErrorUser"}},
            "hash": "hash_pdf_error"
        }
        self.mock_input_handler.get_resumes_to_process.return_value = [sample_resume]
        self.mock_gemini_integrator.enhance_resume.return_value = {"personal_info": {"name": "PDFErrorUser Enhanced"}}
        self.mock_output_generator.generate_pdf.side_effect = Exception("PDF generation failed")

        self.processor.process_resumes()

        self.mock_gemini_integrator.enhance_resume.assert_called_once_with(sample_resume["content"])
        self.mock_output_generator.generate_pdf.assert_called_once()
        self.mock_state_manager.update_resume_state.assert_not_called()

if __name__ == '__main__':
    unittest.main()