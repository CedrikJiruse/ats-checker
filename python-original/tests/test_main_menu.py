"""
Comprehensive tests for the interactive CLI menu system in main.py.

Tests cover all menu entries and their sub-options:
- Menu 1: Process resumes
- Menu 2: Convert files
- Menu 3: Job Search & Scraping
- Menu 4: View/Edit settings
- Menu 5: AI Model Configuration
- Menu 6: View available files
- Menu 7: View generated outputs
- Menu 8: Test OCR functionality
- Menu 9: Exit
"""

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

# Import the functions to test
import main


class TestDisplayMenu(unittest.TestCase):
    """Tests for the main menu display."""

    def test_display_menu_shows_all_options(self):
        """Verify display_menu prints all 9 menu options."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            main.display_menu()

        output = buf.getvalue()
        self.assertIn("ATS Resume Checker", output)
        self.assertIn("1. Process resumes", output)
        self.assertIn("2. Convert files to appropriate format", output)
        self.assertIn("3. Job Search & Scraping", output)
        self.assertIn("4. View/Edit settings", output)
        self.assertIn("5. AI Model Configuration", output)
        self.assertIn("6. View available files", output)
        self.assertIn("7. View generated outputs", output)
        self.assertIn("8. Test OCR functionality", output)
        self.assertIn("9. Exit", output)


class TestExtractTextFromFile(unittest.TestCase):
    """Tests for extract_text_from_file function."""

    def test_extract_text_from_txt_file(self):
        """Test extracting text from a .txt file."""
        with TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "test.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("Hello, World!")

            result = main.extract_text_from_file(filepath)
            self.assertEqual(result, "Hello, World!")

    def test_extract_text_from_md_file(self):
        """Test extracting text from a .md file."""
        with TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "test.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("# Heading\n\nSome content")

            result = main.extract_text_from_file(filepath)
            self.assertEqual(result, "# Heading\n\nSome content")

    def test_extract_text_from_tex_file(self):
        """Test extracting text from a .tex file."""
        with TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "test.tex")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}")

            result = main.extract_text_from_file(filepath)
            self.assertIn("\\documentclass", result)

    def test_extract_text_from_unsupported_format_reads_as_text(self):
        """Test that unsupported formats are read as plain text."""
        with TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "test.xyz")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("Unknown format content")

            result = main.extract_text_from_file(filepath)
            self.assertEqual(result, "Unknown format content")

    def test_extract_text_from_nonexistent_file_returns_empty(self):
        """Test that nonexistent file returns empty string."""
        result = main.extract_text_from_file("/nonexistent/path/file.txt")
        self.assertEqual(result, "")

    def test_extract_text_from_pdf_file(self):
        """Test extracting text from a PDF file."""
        with TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "test.pdf")
            # Create a dummy PDF file
            with open(filepath, "wb") as f:
                f.write(b"%PDF-1.4 test content")

            # Mock the PyPDF2 module
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "PDF content"
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]

            mock_pypdf2 = MagicMock()
            mock_pypdf2.PdfReader.return_value = mock_reader

            with patch.dict("sys.modules", {"PyPDF2": mock_pypdf2}):
                # Force re-import of PyPDF2 within the function
                result = main.extract_text_from_file(filepath)
                self.assertIn("PDF content", result)

    def test_extract_text_from_docx_file(self):
        """Test extracting text from a DOCX file."""
        with TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "test.docx")
            with open(filepath, "wb") as f:
                f.write(b"dummy docx content")

            mock_docx2txt = MagicMock()
            mock_docx2txt.process.return_value = "DOCX content"

            with patch.dict("sys.modules", {"docx2txt": mock_docx2txt}):
                result = main.extract_text_from_file(filepath)
                self.assertEqual(result, "DOCX content")


# =============================================================================
# Menu 1: Process Resumes Tests
# =============================================================================


class TestProcessResumesMenu(unittest.TestCase):
    """Tests for the process resumes menu (Menu 1)."""

    @patch("builtins.input")
    def test_process_resumes_menu_back_option(self, mock_input):
        """Test that option 4 exits the process resumes menu."""
        mock_input.return_value = "4"
        config = MagicMock()
        # Should not raise and should exit cleanly
        main.process_resumes_menu(config)
        mock_input.assert_called()

    @patch("builtins.input")
    def test_process_resumes_menu_invalid_choice(self, mock_input):
        """Test invalid choice handling in process resumes menu."""
        mock_input.side_effect = ["5", "invalid", "4"]  # Invalid, then exit
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.process_resumes_menu(config)

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)


class TestProcessAllResumes(unittest.TestCase):
    """Tests for process_all_resumes function (Menu 1, Option 1)."""

    @patch("builtins.input", return_value="")
    @patch("main.ResumeProcessor")
    @patch("main.InputHandler")
    @patch("main.StateManager")
    def test_process_all_resumes_success(
        self, mock_state_manager, mock_input_handler, mock_processor, mock_input
    ):
        """Test successful processing of all resumes."""
        config = self._create_mock_config()
        mock_processor_instance = MagicMock()
        mock_processor.return_value = mock_processor_instance

        main.process_all_resumes(config)

        mock_processor.assert_called_once()
        mock_processor_instance.process_resumes.assert_called_once()

    @patch("builtins.input", return_value="")
    @patch("main.ResumeProcessor")
    @patch("main.StateManager")
    def test_process_all_resumes_handles_exception(
        self, mock_state_manager, mock_processor, mock_input
    ):
        """Test that exceptions are handled gracefully."""
        config = self._create_mock_config()
        mock_processor.side_effect = Exception("Test error")

        # Should not raise
        main.process_all_resumes(config)

    def _create_mock_config(self):
        """Create a mock config object with all required attributes."""
        config = MagicMock()
        config.input_resumes_folder = "workspace/input_resumes"
        config.output_folder = "workspace/output"
        config.job_descriptions_folder = "workspace/job_descriptions"
        config.state_file = "data/state.toml"
        config.model_name = "gemini-pro"
        config.temperature = 0.7
        config.top_p = 0.95
        config.top_k = 40
        config.max_output_tokens = 8192
        config.num_versions_per_job = 1
        config.tesseract_cmd = None
        config.ai_agents = {}
        config.scoring_weights_file = "config/scoring_weights.toml"
        config.structured_output_format = "toml"
        config.iterate_until_score_reached = False
        config.target_score = 80.0
        config.max_iterations = 5
        config.min_score_delta = 0.5
        config.iteration_strategy = "best_of"
        config.iteration_patience = 3
        config.stop_on_regression = False
        config.max_regressions = 3
        config.schema_validation_enabled = False
        config.resume_schema_path = None
        config.schema_validation_max_retries = 3
        config.recommendations_enabled = False
        config.recommendations_max_items = 5
        config.output_subdir_pattern = "{resume_name}/{job_title}/{timestamp}"
        config.write_score_summary_file = True
        config.score_summary_filename = "scores.toml"
        config.write_manifest_file = True
        config.manifest_filename = "manifest.toml"
        config.max_concurrent_requests = 1
        config.score_cache_enabled = False
        return config


class TestProcessResumesWithJobDescription(unittest.TestCase):
    """Tests for process_resumes_with_job_description (Menu 1, Option 2)."""

    @patch("builtins.input")
    @patch("main.ResumeProcessor")
    @patch("main.InputHandler")
    @patch("main.StateManager")
    def test_process_with_job_description_no_jobs_found(
        self, mock_state_manager, mock_input_handler, mock_processor, mock_input
    ):
        """Test handling when no job descriptions are found."""
        mock_input.return_value = ""
        config = self._create_mock_config()

        mock_handler_instance = MagicMock()
        mock_handler_instance.get_job_descriptions.return_value = {}
        mock_input_handler.return_value = mock_handler_instance

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.process_resumes_with_job_description(config)

        output = buf.getvalue()
        self.assertIn("No job descriptions found", output)

    @patch("builtins.input")
    @patch("main.ResumeProcessor")
    @patch("main.InputHandler")
    @patch("main.StateManager")
    def test_process_with_job_description_invalid_choice(
        self, mock_state_manager, mock_input_handler, mock_processor, mock_input
    ):
        """Test handling of invalid job description selection."""
        mock_input.side_effect = ["99", ""]  # Invalid choice, then continue
        config = self._create_mock_config()

        mock_handler_instance = MagicMock()
        mock_handler_instance.get_job_descriptions.return_value = {
            "job1.txt": "Job 1 content"
        }
        mock_input_handler.return_value = mock_handler_instance

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.process_resumes_with_job_description(config)

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)

    @patch("builtins.input")
    @patch("main.ResumeProcessor")
    @patch("main.InputHandler")
    @patch("main.StateManager")
    def test_process_with_job_description_success(
        self, mock_state_manager, mock_input_handler, mock_processor, mock_input
    ):
        """Test successful processing with a job description."""
        mock_input.side_effect = ["1", ""]  # Select first job, then continue
        config = self._create_mock_config()

        mock_handler_instance = MagicMock()
        mock_handler_instance.get_job_descriptions.return_value = {
            "job1.txt": "Job 1 content"
        }
        mock_input_handler.return_value = mock_handler_instance

        mock_processor_instance = MagicMock()
        mock_processor.return_value = mock_processor_instance

        main.process_resumes_with_job_description(config)

        mock_processor_instance.process_resumes.assert_called_once_with(
            job_description_name="job1.txt"
        )

    def _create_mock_config(self):
        """Create a mock config object."""
        config = MagicMock()
        config.input_resumes_folder = "workspace/input_resumes"
        config.output_folder = "workspace/output"
        config.job_descriptions_folder = "workspace/job_descriptions"
        config.state_file = "data/state.toml"
        config.model_name = "gemini-pro"
        config.temperature = 0.7
        config.top_p = 0.95
        config.top_k = 40
        config.max_output_tokens = 8192
        config.num_versions_per_job = 1
        config.tesseract_cmd = None
        config.ai_agents = {}
        config.scoring_weights_file = "config/scoring_weights.toml"
        config.structured_output_format = "toml"
        config.iterate_until_score_reached = False
        config.target_score = 80.0
        config.max_iterations = 5
        config.min_score_delta = 0.5
        config.iteration_strategy = "best_of"
        config.iteration_patience = 3
        config.stop_on_regression = False
        config.max_regressions = 3
        config.schema_validation_enabled = False
        config.resume_schema_path = None
        config.schema_validation_max_retries = 3
        config.recommendations_enabled = False
        config.recommendations_max_items = 5
        config.output_subdir_pattern = "{resume_name}/{job_title}/{timestamp}"
        config.write_score_summary_file = True
        config.score_summary_filename = "scores.toml"
        config.write_manifest_file = True
        config.manifest_filename = "manifest.toml"
        config.max_concurrent_requests = 1
        config.score_cache_enabled = False
        return config


class TestProcessSpecificResumeWithJob(unittest.TestCase):
    """Tests for process_specific_resume_with_job (Menu 1, Option 3)."""

    @patch("builtins.input", return_value="")
    @patch("os.path.exists", return_value=False)
    def test_input_folder_does_not_exist(self, mock_exists, mock_input):
        """Test handling when input folder doesn't exist."""
        config = MagicMock()
        config.input_resumes_folder = "nonexistent/folder"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.process_specific_resume_with_job(config)

        output = buf.getvalue()
        self.assertIn("does not exist", output)

    @patch("builtins.input", return_value="")
    @patch("os.listdir", return_value=[])
    @patch("os.path.exists", return_value=True)
    def test_no_resume_files_found(self, mock_exists, mock_listdir, mock_input):
        """Test handling when no resume files are found."""
        config = MagicMock()
        config.input_resumes_folder = "workspace/input_resumes"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.process_specific_resume_with_job(config)

        output = buf.getvalue()
        self.assertIn("No resume files found", output)

    @patch("builtins.input")
    @patch("os.listdir", return_value=["resume1.txt", "resume2.txt"])
    @patch("os.path.exists", return_value=True)
    def test_invalid_resume_selection(self, mock_exists, mock_listdir, mock_input):
        """Test handling of invalid resume selection."""
        mock_input.side_effect = ["99", ""]  # Invalid choice, continue
        config = MagicMock()
        config.input_resumes_folder = "workspace/input_resumes"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.process_specific_resume_with_job(config)

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)


# =============================================================================
# Menu 2: Convert Files Tests
# =============================================================================


class TestConvertFilesMenu(unittest.TestCase):
    """Tests for the convert files menu (Menu 2)."""

    @patch("builtins.input")
    def test_convert_files_menu_back_option(self, mock_input):
        """Test that option 3 exits the convert files menu."""
        mock_input.return_value = "3"
        config = MagicMock()
        main.convert_files_menu(config)
        mock_input.assert_called()

    @patch("builtins.input")
    def test_convert_files_menu_invalid_choice(self, mock_input):
        """Test invalid choice handling in convert files menu."""
        mock_input.side_effect = ["5", "3"]  # Invalid, then exit
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.convert_files_menu(config)

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)


class TestConvertResumeFiles(unittest.TestCase):
    """Tests for convert_resume_files function (Menu 2, Option 1)."""

    @patch("builtins.input")
    @patch("os.path.exists", return_value=False)
    def test_source_folder_does_not_exist(self, mock_exists, mock_input):
        """Test handling when source folder doesn't exist."""
        mock_input.side_effect = ["nonexistent/path", ""]
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.convert_resume_files(config)

        output = buf.getvalue()
        self.assertIn("does not exist", output)

    @patch("builtins.input")
    @patch("os.walk", return_value=[(".", [], [])])
    @patch("os.path.exists", return_value=True)
    def test_no_supported_files_found(self, mock_exists, mock_walk, mock_input):
        """Test handling when no supported files are found."""
        mock_input.side_effect = [".", ""]
        config = MagicMock()
        config.input_resumes_folder = "workspace/input_resumes"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.convert_resume_files(config)

        output = buf.getvalue()
        self.assertIn("No supported files found", output)

    @patch("builtins.input")
    @patch("os.makedirs")
    @patch("os.walk")
    @patch("os.path.exists", return_value=True)
    def test_user_cancels_conversion(self, mock_exists, mock_walk, mock_makedirs, mock_input):
        """Test that conversion is cancelled when user says no."""
        mock_walk.return_value = [(".", [], ["test.txt"])]
        mock_input.side_effect = [".", "n", ""]  # Source folder, decline, continue
        config = MagicMock()
        config.input_resumes_folder = "workspace/input_resumes"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.convert_resume_files(config)

        output = buf.getvalue()
        self.assertIn("Conversion cancelled", output)

    @patch("builtins.input")
    @patch("os.makedirs")
    @patch("os.walk")
    @patch("os.path.exists")
    @patch("main.extract_text_from_file", return_value="Test content")
    @patch("builtins.open", create=True)
    def test_successful_conversion(
        self, mock_open, mock_extract, mock_exists, mock_walk, mock_makedirs, mock_input
    ):
        """Test successful file conversion."""
        with TemporaryDirectory() as tmp:
            mock_walk.return_value = [(tmp, [], ["test.txt"])]
            mock_exists.return_value = True
            mock_input.side_effect = [tmp, "y", ""]  # Source, confirm, continue

            config = MagicMock()
            config.input_resumes_folder = os.path.join(tmp, "input_resumes")

            buf = io.StringIO()
            with redirect_stdout(buf):
                main.convert_resume_files(config)

            output = buf.getvalue()
            self.assertIn("Successfully converted", output)


class TestConvertJobDescriptionFiles(unittest.TestCase):
    """Tests for convert_job_description_files (Menu 2, Option 2)."""

    @patch("builtins.input")
    @patch("os.path.exists", return_value=False)
    def test_source_folder_does_not_exist(self, mock_exists, mock_input):
        """Test handling when source folder doesn't exist."""
        mock_input.side_effect = ["nonexistent/path", ""]
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.convert_job_description_files(config)

        output = buf.getvalue()
        self.assertIn("does not exist", output)


# =============================================================================
# Menu 3: Job Search & Scraping Tests
# =============================================================================


class TestJobSearchMenu(unittest.TestCase):
    """Tests for the job search menu (Menu 3)."""

    @patch("builtins.input")
    def test_job_search_menu_back_option(self, mock_input):
        """Test that option 6 exits the job search menu."""
        mock_input.return_value = "6"
        config = MagicMock()
        job_scraper_manager = MagicMock()
        main.job_search_menu(config, job_scraper_manager)
        mock_input.assert_called()

    @patch("builtins.input")
    def test_job_search_menu_invalid_choice(self, mock_input):
        """Test invalid choice handling."""
        mock_input.side_effect = ["99", "6"]  # Invalid, then exit
        config = MagicMock()
        job_scraper_manager = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.job_search_menu(config, job_scraper_manager)

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)


class TestNewJobSearch(unittest.TestCase):
    """Tests for new_job_search function (Menu 3, Option 1)."""

    @patch("builtins.input")
    def test_invalid_source_selection(self, mock_input):
        """Test handling of invalid source selection."""
        mock_input.side_effect = ["99", ""]  # Invalid source, continue
        config = MagicMock()
        config.job_search_defaults = {}

        job_scraper_manager = MagicMock()
        job_scraper_manager.get_available_sources.return_value = ["LinkedIn", "Indeed"]

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.new_job_search(config, job_scraper_manager)

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)

    @patch("builtins.input")
    def test_single_source_search(self, mock_input):
        """Test searching a single job site."""
        mock_input.side_effect = [
            "1",  # Select first source
            "python developer",  # Keywords
            "Dublin",  # Location
            "",  # Job types (none)
            "n",  # Remote only: no
            "",  # Experience levels (none)
            "4",  # Date posted: any time
            "n",  # Don't save search
            "",  # Press Enter to continue
        ]
        config = MagicMock()
        config.job_search_defaults = {}
        config.max_job_results_per_search = 25

        job_scraper_manager = MagicMock()
        job_scraper_manager.get_available_sources.return_value = ["LinkedIn"]
        job_scraper_manager.search_jobs.return_value = []

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.new_job_search(config, job_scraper_manager)

        job_scraper_manager.search_jobs.assert_called_once()

    @patch("builtins.input")
    def test_search_all_sources(self, mock_input):
        """Test searching all job sites."""
        mock_input.side_effect = [
            "3",  # Search all sites (assuming 2 sources)
            "software engineer",  # Keywords
            "",  # Location (none)
            "1",  # Job type: Full-time
            "y",  # Remote only: yes
            "2,3",  # Experience: Mid, Senior
            "2",  # Date posted: Last week
            "n",  # Don't save search
            "",  # Press Enter to continue
        ]
        config = MagicMock()
        config.job_search_defaults = {}
        config.max_job_results_per_search = 25

        job_scraper_manager = MagicMock()
        job_scraper_manager.get_available_sources.return_value = ["LinkedIn", "Indeed"]
        job_scraper_manager.search_all_sources.return_value = {"LinkedIn": [], "Indeed": []}

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.new_job_search(config, job_scraper_manager)

        job_scraper_manager.search_all_sources.assert_called_once()

    @patch("builtins.input")
    def test_search_with_defaults(self, mock_input):
        """Test search using config defaults."""
        mock_input.side_effect = [
            "1",  # Select first source
            "",  # Use default keywords
            "",  # Use default location
            "",  # Job types (none)
            "",  # Use default remote setting
            "",  # Experience levels (none)
            "",  # Use default date posted
            "n",  # Don't save search
            "",  # Press Enter to continue
        ]
        config = MagicMock()
        config.job_search_defaults = {
            "keywords": "python",
            "location": "Remote",
            "remote_only": True,
            "date_posted": "week",
        }
        config.max_job_results_per_search = 25

        job_scraper_manager = MagicMock()
        job_scraper_manager.get_available_sources.return_value = ["LinkedIn"]
        job_scraper_manager.search_jobs.return_value = []

        main.new_job_search(config, job_scraper_manager)

        job_scraper_manager.search_jobs.assert_called_once()

    @patch("builtins.input")
    def test_save_search(self, mock_input):
        """Test saving a search configuration."""
        mock_input.side_effect = [
            "1",  # Select first source
            "python developer",  # Keywords
            "Dublin",  # Location
            "",  # Job types
            "n",  # Remote only
            "",  # Experience levels
            "4",  # Date posted
            "y",  # Save search
            "My Python Search",  # Search name
            "",  # Press Enter to continue
        ]
        config = MagicMock()
        config.job_search_defaults = {}
        config.max_job_results_per_search = 25

        job_scraper_manager = MagicMock()
        job_scraper_manager.get_available_sources.return_value = ["LinkedIn"]
        job_scraper_manager.search_jobs.return_value = []

        main.new_job_search(config, job_scraper_manager)

        job_scraper_manager.saved_search_manager.create_search.assert_called_once()


class TestManageSavedSearches(unittest.TestCase):
    """Tests for manage_saved_searches function (Menu 3, Option 2)."""

    @patch("builtins.input", return_value="")
    def test_no_saved_searches(self, mock_input):
        """Test handling when no saved searches exist."""
        config = MagicMock()
        job_scraper_manager = MagicMock()
        job_scraper_manager.saved_search_manager.get_all_searches.return_value = []

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.manage_saved_searches(config, job_scraper_manager)

        output = buf.getvalue()
        self.assertIn("No saved searches found", output)

    @patch("builtins.input")
    def test_view_search_details(self, mock_input):
        """Test viewing details of a saved search."""
        mock_input.side_effect = ["1", "", "3"]  # View first, continue, exit

        config = MagicMock()

        # Create a mock saved search
        mock_search = MagicMock()
        mock_search.name = "Test Search"
        mock_search.source = "LinkedIn"
        mock_search.created_at = "2024-01-01"
        mock_search.last_run = "2024-01-02"
        mock_search.results_count = 10
        mock_search.filters = MagicMock()
        mock_search.filters.keywords = "python"
        mock_search.filters.location = "Dublin"
        mock_search.filters.job_type = ["Full-time"]
        mock_search.filters.remote_only = True
        mock_search.filters.experience_level = ["Mid"]

        job_scraper_manager = MagicMock()
        job_scraper_manager.saved_search_manager.get_all_searches.return_value = [mock_search]

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.manage_saved_searches(config, job_scraper_manager)

        output = buf.getvalue()
        self.assertIn("Test Search", output)

    @patch("builtins.input")
    def test_delete_saved_search(self, mock_input):
        """Test deleting a saved search."""
        mock_input.side_effect = ["2", "1", "y", "3"]  # Delete option, select search, confirm, exit

        config = MagicMock()

        mock_search = MagicMock()
        mock_search.id = "search_001"
        mock_search.name = "Test Search"
        mock_search.source = "LinkedIn"
        mock_search.last_run = None
        mock_search.results_count = 0

        job_scraper_manager = MagicMock()
        job_scraper_manager.saved_search_manager.get_all_searches.return_value = [mock_search]

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.manage_saved_searches(config, job_scraper_manager)

        job_scraper_manager.saved_search_manager.delete_search.assert_called_once_with("search_001")


class TestRunSavedSearch(unittest.TestCase):
    """Tests for run_saved_search function (Menu 3, Option 3)."""

    @patch("builtins.input", return_value="")
    def test_no_saved_searches(self, mock_input):
        """Test handling when no saved searches exist."""
        config = MagicMock()
        job_scraper_manager = MagicMock()
        job_scraper_manager.saved_search_manager.get_all_searches.return_value = []

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.run_saved_search(config, job_scraper_manager)

        output = buf.getvalue()
        self.assertIn("No saved searches found", output)

    @patch("builtins.input")
    def test_cancel_run_search(self, mock_input):
        """Test cancelling a search run."""
        mock_input.side_effect = ["0", ""]

        config = MagicMock()

        mock_search = MagicMock()
        mock_search.name = "Test Search"
        mock_search.source = "LinkedIn"
        mock_search.last_run = None

        job_scraper_manager = MagicMock()
        job_scraper_manager.saved_search_manager.get_all_searches.return_value = [mock_search]

        main.run_saved_search(config, job_scraper_manager)

        job_scraper_manager.run_saved_search.assert_not_called()

    @patch("builtins.input")
    def test_run_search_successfully(self, mock_input):
        """Test running a saved search successfully."""
        mock_input.side_effect = ["1", ""]  # Select first search, continue

        config = MagicMock()
        config.max_job_results_per_search = 25

        mock_search = MagicMock()
        mock_search.id = "search_001"
        mock_search.name = "Test Search"
        mock_search.source = "LinkedIn"
        mock_search.last_run = None

        job_scraper_manager = MagicMock()
        job_scraper_manager.saved_search_manager.get_all_searches.return_value = [mock_search]
        job_scraper_manager.run_saved_search.return_value = []

        main.run_saved_search(config, job_scraper_manager)

        job_scraper_manager.run_saved_search.assert_called_once_with("search_001", 25)


class TestViewSavedJobResults(unittest.TestCase):
    """Tests for view_saved_job_results function (Menu 3, Option 4)."""

    @patch("builtins.input", return_value="")
    def test_no_saved_results(self, mock_input):
        """Test handling when no saved results exist."""
        config = MagicMock()
        job_scraper_manager = MagicMock()
        job_scraper_manager.get_saved_results.return_value = []

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_saved_job_results(config, job_scraper_manager)

        output = buf.getvalue()
        self.assertIn("No saved results found", output)

    @patch("builtins.input")
    def test_cancel_view_results(self, mock_input):
        """Test cancelling results view."""
        mock_input.side_effect = ["0"]

        config = MagicMock()
        job_scraper_manager = MagicMock()
        job_scraper_manager.get_saved_results.return_value = ["results_001.toml"]

        main.view_saved_job_results(config, job_scraper_manager)

        job_scraper_manager.load_saved_results.assert_not_called()


class TestExportJobsToDescriptions(unittest.TestCase):
    """Tests for export_jobs_to_descriptions function (Menu 3, Option 5)."""

    @patch("builtins.input", return_value="")
    def test_no_saved_results(self, mock_input):
        """Test handling when no saved results exist."""
        config = MagicMock()
        job_scraper_manager = MagicMock()
        job_scraper_manager.get_saved_results.return_value = []

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.export_jobs_to_descriptions(config, job_scraper_manager)

        output = buf.getvalue()
        self.assertIn("No saved results found", output)

    @patch("builtins.input")
    def test_cancel_export(self, mock_input):
        """Test cancelling export."""
        mock_input.side_effect = ["0"]

        config = MagicMock()
        job_scraper_manager = MagicMock()
        job_scraper_manager.get_saved_results.return_value = ["results.toml"]

        main.export_jobs_to_descriptions(config, job_scraper_manager)

        job_scraper_manager.export_to_job_descriptions.assert_not_called()


# =============================================================================
# Menu 4: View/Edit Settings Tests
# =============================================================================


class TestViewEditSettings(unittest.TestCase):
    """Tests for view/edit settings menu (Menu 4)."""

    @patch("builtins.input")
    def test_settings_menu_back_option(self, mock_input):
        """Test that option 11 exits the settings menu."""
        mock_input.return_value = "11"
        config = self._create_mock_config()
        main.view_edit_settings(config, "config/config.toml")
        mock_input.assert_called()

    @patch("builtins.input")
    def test_settings_menu_displays_current_values(self, mock_input):
        """Test that current settings are displayed."""
        mock_input.return_value = "11"  # Exit immediately
        config = self._create_mock_config()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_edit_settings(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("Output folder:", output)
        self.assertIn("Model name:", output)
        self.assertIn("Temperature:", output)

    @patch("builtins.input")
    def test_settings_menu_invalid_choice(self, mock_input):
        """Test invalid choice handling."""
        mock_input.side_effect = ["99", "11"]  # Invalid, then exit
        config = self._create_mock_config()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_edit_settings(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)

    def _create_mock_config(self):
        """Create a mock config object."""
        config = MagicMock()
        config.output_folder = "workspace/output"
        config.num_versions_per_job = 1
        config.model_name = "gemini-pro"
        config.temperature = 0.7
        config.top_p = 0.95
        config.top_k = 40
        config.max_output_tokens = 8192
        config.input_resumes_folder = "workspace/input_resumes"
        config.job_descriptions_folder = "workspace/job_descriptions"
        config.tesseract_cmd = None
        return config


class TestEditSetting(unittest.TestCase):
    """Tests for edit_setting function."""

    @patch("builtins.input")
    @patch("config.save_config_toml")
    def test_edit_output_folder(self, mock_save, mock_input):
        """Test editing the output folder setting."""
        mock_input.side_effect = ["new/output/path", ""]
        config = MagicMock()
        config.output_folder = "old/path"

        main.edit_setting(config, "config/config.toml", "1")

        self.assertEqual(config.output_folder, "new/output/path")
        mock_save.assert_called_once()

    @patch("builtins.input")
    @patch("config.save_config_toml")
    def test_edit_num_versions_valid_integer(self, mock_save, mock_input):
        """Test editing num_versions_per_job with valid integer."""
        mock_input.side_effect = ["3", ""]
        config = MagicMock()
        config.num_versions_per_job = 1

        main.edit_setting(config, "config/config.toml", "2")

        self.assertEqual(config.num_versions_per_job, 3)

    @patch("builtins.input")
    def test_edit_num_versions_invalid_integer(self, mock_input):
        """Test editing num_versions_per_job with invalid input."""
        mock_input.side_effect = ["not_a_number", ""]
        config = MagicMock()
        config.num_versions_per_job = 1

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.edit_setting(config, "config/config.toml", "2")

        output = buf.getvalue()
        self.assertIn("Invalid integer value", output)

    @patch("builtins.input")
    def test_edit_num_versions_out_of_bounds(self, mock_input):
        """Test editing num_versions_per_job with out-of-bounds value."""
        mock_input.side_effect = ["99", ""]  # Max is 20
        config = MagicMock()
        config.num_versions_per_job = 1

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.edit_setting(config, "config/config.toml", "2")

        output = buf.getvalue()
        self.assertIn("must be between 1 and 20", output)

    @patch("builtins.input")
    @patch("config.save_config_toml")
    def test_edit_temperature_valid_float(self, mock_save, mock_input):
        """Test editing temperature with valid float."""
        mock_input.side_effect = ["0.5", ""]
        config = MagicMock()
        config.temperature = 0.7

        main.edit_setting(config, "config/config.toml", "4")

        self.assertEqual(config.temperature, 0.5)

    @patch("builtins.input")
    def test_edit_temperature_invalid_float(self, mock_input):
        """Test editing temperature with invalid input."""
        mock_input.side_effect = ["not_a_float", ""]
        config = MagicMock()
        config.temperature = 0.7

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.edit_setting(config, "config/config.toml", "4")

        output = buf.getvalue()
        self.assertIn("Invalid float value", output)

    @patch("builtins.input")
    def test_edit_temperature_out_of_bounds(self, mock_input):
        """Test editing temperature with out-of-bounds value."""
        mock_input.side_effect = ["1.5", ""]  # Must be 0.0-1.0
        config = MagicMock()
        config.temperature = 0.7

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.edit_setting(config, "config/config.toml", "4")

        output = buf.getvalue()
        self.assertIn("must be between 0.0 and 1.0", output)

    @patch("builtins.input")
    @patch("config.save_config_toml")
    def test_edit_tesseract_cmd_allows_empty(self, mock_save, mock_input):
        """Test that tesseract_cmd can be set to empty (None)."""
        mock_input.side_effect = ["", ""]  # Empty input
        config = MagicMock()
        config.tesseract_cmd = "/usr/bin/tesseract"

        main.edit_setting(config, "config/config.toml", "10")

        self.assertIsNone(config.tesseract_cmd)

    @patch("builtins.input")
    def test_edit_top_k_out_of_bounds(self, mock_input):
        """Test editing top_k with out-of-bounds value."""
        mock_input.side_effect = ["150", ""]  # Max is 100
        config = MagicMock()
        config.top_k = 40

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.edit_setting(config, "config/config.toml", "6")

        output = buf.getvalue()
        self.assertIn("must be between 1 and 100", output)

    @patch("builtins.input")
    def test_edit_max_output_tokens_out_of_bounds(self, mock_input):
        """Test editing max_output_tokens with out-of-bounds value."""
        mock_input.side_effect = ["100", ""]  # Min is 256
        config = MagicMock()
        config.max_output_tokens = 8192

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.edit_setting(config, "config/config.toml", "7")

        output = buf.getvalue()
        self.assertIn("must be between 256 and 8192", output)

    @patch("builtins.input")
    def test_edit_invalid_setting_choice(self, mock_input):
        """Test handling of invalid setting choice."""
        mock_input.return_value = ""
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.edit_setting(config, "config/config.toml", "99")

        output = buf.getvalue()
        self.assertIn("Invalid setting choice", output)

    @patch("builtins.input")
    def test_edit_no_changes_made(self, mock_input):
        """Test when user doesn't provide new value."""
        mock_input.side_effect = ["", ""]  # Empty input for non-tesseract field
        config = MagicMock()
        config.model_name = "gemini-pro"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.edit_setting(config, "config/config.toml", "3")

        output = buf.getvalue()
        self.assertIn("No changes made", output)


# =============================================================================
# Menu 5: AI Model Configuration Tests
# =============================================================================


class TestAIModelConfigurationMenu(unittest.TestCase):
    """Tests for AI model configuration menu (Menu 5)."""

    @patch("builtins.input")
    def test_ai_config_menu_back_option(self, mock_input):
        """Test that option 5 exits the AI config menu."""
        mock_input.return_value = "5"
        config = MagicMock()
        config.ai_agents = {"enhancer": {"provider": "gemini", "model_name": "gemini-pro"}}
        main.ai_model_configuration_menu(config, "config/config.toml")
        mock_input.assert_called()

    @patch("builtins.input")
    def test_ai_config_menu_invalid_choice(self, mock_input):
        """Test invalid choice handling."""
        mock_input.side_effect = ["99", "5"]  # Invalid, then exit
        config = MagicMock()
        config.ai_agents = {"enhancer": {"provider": "gemini", "model_name": "gemini-pro"}}

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.ai_model_configuration_menu(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)


class TestViewCurrentConfiguration(unittest.TestCase):
    """Tests for view_current_configuration function."""

    def test_displays_all_agents(self):
        """Test that all configured agents are displayed."""
        config = MagicMock()
        config.ai_agents = {
            "enhancer": {"provider": "gemini", "model_name": "gemini-pro"},
            "scorer": {"provider": "openai", "model_name": "gpt-4o"},
        }

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_current_configuration(config)

        output = buf.getvalue()
        self.assertIn("enhancer", output)
        self.assertIn("gemini/gemini-pro", output)
        self.assertIn("scorer", output)
        self.assertIn("openai/gpt-4o", output)


class TestChangeAgentModel(unittest.TestCase):
    """Tests for change_agent_model function."""

    @patch("builtins.input")
    def test_invalid_agent_selection(self, mock_input):
        """Test handling of invalid agent selection."""
        mock_input.side_effect = ["99", ""]
        config = MagicMock()
        config.ai_agents = {"enhancer": {"provider": "gemini", "model_name": "gemini-pro"}}

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.change_agent_model(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)

    @patch("builtins.input")
    def test_invalid_provider_selection(self, mock_input):
        """Test handling of invalid provider selection."""
        mock_input.side_effect = ["1", "99", ""]  # Valid agent, invalid provider
        config = MagicMock()
        config.ai_agents = {"enhancer": {"provider": "gemini", "model_name": "gemini-pro"}}

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.change_agent_model(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)


class TestGetAvailableModelsForProvider(unittest.TestCase):
    """Tests for get_available_models_for_provider function."""

    def test_gemini_models(self):
        """Test that Gemini models are returned."""
        models = main.get_available_models_for_provider("gemini")
        self.assertIn("gemini-2.0-flash-exp", models)
        self.assertIn("gemini-1.5-pro", models)

    def test_openai_models(self):
        """Test that OpenAI models are returned."""
        models = main.get_available_models_for_provider("openai")
        self.assertIn("gpt-4o", models)
        self.assertIn("gpt-4o-mini", models)

    def test_anthropic_models(self):
        """Test that Anthropic models are returned."""
        models = main.get_available_models_for_provider("anthropic")
        self.assertIn("claude-3-5-sonnet-20241022", models)

    def test_llama_models(self):
        """Test that Llama models are returned."""
        models = main.get_available_models_for_provider("llama")
        self.assertIn("meta-llama/Llama-3.3-70B-Instruct", models)

    def test_unknown_provider_returns_empty(self):
        """Test that unknown provider returns empty list."""
        models = main.get_available_models_for_provider("unknown")
        self.assertEqual(models, [])


class TestLoadProviderProfile(unittest.TestCase):
    """Tests for load_provider_profile function."""

    @patch("builtins.input")
    def test_invalid_profile_choice(self, mock_input):
        """Test handling of invalid profile choice."""
        mock_input.side_effect = ["99", ""]
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.load_provider_profile(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)

    @patch("builtins.input")
    @patch("os.path.exists", return_value=False)
    def test_profile_file_not_found(self, mock_exists, mock_input):
        """Test handling when profile file doesn't exist."""
        mock_input.side_effect = ["1", ""]  # Select Budget profile
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.load_provider_profile(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("not found", output)


class TestTestAIConfiguration(unittest.TestCase):
    """Tests for test_ai_configuration function."""

    @patch("builtins.input", return_value="")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=False)
    def test_api_key_found(self, mock_input):
        """Test when API key is found in environment."""
        config = MagicMock()
        config.ai_agents = {"enhancer": {"provider": "gemini", "model_name": "gemini-pro"}}

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.test_ai_configuration(config)

        output = buf.getvalue()
        self.assertIn("API key found", output)

    @patch("builtins.input", return_value="")
    @patch.dict(os.environ, {}, clear=True)
    def test_api_key_missing(self, mock_input):
        """Test when API key is missing from environment."""
        config = MagicMock()
        config.ai_agents = {"enhancer": {"provider": "gemini", "model_name": "gemini-pro"}}

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.test_ai_configuration(config)

        output = buf.getvalue()
        self.assertIn("Missing", output)


class TestViewAvailableModels(unittest.TestCase):
    """Tests for view_available_models function."""

    @patch("builtins.input", return_value="")
    def test_displays_all_providers(self, mock_input):
        """Test that all providers and models are displayed."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_available_models()

        output = buf.getvalue()
        self.assertIn("Gemini", output)
        self.assertIn("OpenAI", output)
        self.assertIn("Anthropic", output)
        self.assertIn("Llama", output)
        self.assertIn("Recommendations", output)


# =============================================================================
# Menu 6: View Available Files Tests
# =============================================================================


class TestViewAvailableFiles(unittest.TestCase):
    """Tests for view available files menu (Menu 6)."""

    @patch("builtins.input")
    def test_view_files_menu_back_option(self, mock_input):
        """Test that option 3 exits the view files menu."""
        mock_input.return_value = "3"
        config = MagicMock()
        main.view_available_files(config)
        mock_input.assert_called()

    @patch("builtins.input")
    def test_view_files_menu_invalid_choice(self, mock_input):
        """Test invalid choice handling."""
        mock_input.side_effect = ["99", "3"]  # Invalid, then exit
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_available_files(config)

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)


class TestViewInputResumes(unittest.TestCase):
    """Tests for view_input_resumes function (Menu 6, Option 1)."""

    @patch("builtins.input", return_value="")
    @patch("os.path.exists", return_value=False)
    def test_folder_does_not_exist(self, mock_exists, mock_input):
        """Test handling when input folder doesn't exist."""
        config = MagicMock()
        config.input_resumes_folder = "nonexistent/folder"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_input_resumes(config)

        output = buf.getvalue()
        self.assertIn("does not exist", output)

    @patch("builtins.input", return_value="")
    @patch("os.listdir", return_value=[])
    @patch("os.path.exists", return_value=True)
    def test_no_resume_files(self, mock_exists, mock_listdir, mock_input):
        """Test handling when no resume files are found."""
        config = MagicMock()
        config.input_resumes_folder = "workspace/input_resumes"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_input_resumes(config)

        output = buf.getvalue()
        self.assertIn("No resume files found", output)

    @patch("builtins.input", return_value="")
    @patch("os.listdir", return_value=["resume1.txt", "resume2.md", "resume3.png"])
    @patch("os.path.exists", return_value=True)
    def test_lists_resume_files(self, mock_exists, mock_listdir, mock_input):
        """Test that resume files are listed."""
        config = MagicMock()
        config.input_resumes_folder = "workspace/input_resumes"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_input_resumes(config)

        output = buf.getvalue()
        self.assertIn("resume1.txt", output)
        self.assertIn("resume2.md", output)
        self.assertIn("resume3.png", output)


class TestViewJobDescriptions(unittest.TestCase):
    """Tests for view_job_descriptions function (Menu 6, Option 2)."""

    @patch("builtins.input", return_value="")
    @patch("os.path.exists", return_value=False)
    def test_folder_does_not_exist(self, mock_exists, mock_input):
        """Test handling when job descriptions folder doesn't exist."""
        config = MagicMock()
        config.job_descriptions_folder = "nonexistent/folder"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_job_descriptions(config)

        output = buf.getvalue()
        self.assertIn("does not exist", output)

    @patch("builtins.input", return_value="")
    @patch("main.InputHandler")
    @patch("main.StateManager")
    @patch("os.path.exists", return_value=True)
    def test_no_job_descriptions(self, mock_exists, mock_state, mock_handler, mock_input):
        """Test handling when no job descriptions are found."""
        config = MagicMock()
        config.job_descriptions_folder = "workspace/job_descriptions"
        config.state_file = "data/state.toml"

        mock_handler_instance = MagicMock()
        mock_handler_instance.get_job_descriptions.return_value = {}
        mock_handler.return_value = mock_handler_instance

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_job_descriptions(config)

        output = buf.getvalue()
        self.assertIn("No job descriptions found", output)

    @patch("builtins.input", return_value="")
    @patch("main.InputHandler")
    @patch("main.StateManager")
    @patch("os.path.exists", return_value=True)
    def test_lists_job_descriptions(self, mock_exists, mock_state, mock_handler, mock_input):
        """Test that job descriptions are listed."""
        config = MagicMock()
        config.job_descriptions_folder = "workspace/job_descriptions"
        config.state_file = "data/state.toml"

        mock_handler_instance = MagicMock()
        mock_handler_instance.get_job_descriptions.return_value = {
            "job1.txt": "Content 1",
            "job2.txt": "Content 2",
        }
        mock_handler.return_value = mock_handler_instance

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_job_descriptions(config)

        output = buf.getvalue()
        self.assertIn("job1.txt", output)
        self.assertIn("job2.txt", output)


# =============================================================================
# Menu 7: View Generated Outputs Tests
# =============================================================================


class TestViewGeneratedOutputs(unittest.TestCase):
    """Tests for view_generated_outputs function (Menu 7)."""

    @patch("builtins.input", return_value="")
    @patch("os.path.exists", return_value=False)
    def test_output_folder_does_not_exist(self, mock_exists, mock_input):
        """Test handling when output folder doesn't exist."""
        config = MagicMock()
        config.output_folder = "nonexistent/folder"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_generated_outputs(config)

        output = buf.getvalue()
        self.assertIn("does not exist", output)

    @patch("builtins.input", return_value="")
    @patch("os.listdir", return_value=[])
    @patch("os.path.exists", return_value=True)
    def test_no_output_files(self, mock_exists, mock_listdir, mock_input):
        """Test handling when no output files are found."""
        config = MagicMock()
        config.output_folder = "workspace/output"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_generated_outputs(config)

        output = buf.getvalue()
        self.assertIn("No output files found", output)

    @patch("builtins.input")
    @patch("os.listdir", return_value=["output1.txt", "output2.txt"])
    @patch("os.path.exists", return_value=True)
    def test_cancel_view(self, mock_exists, mock_listdir, mock_input):
        """Test cancelling file view."""
        mock_input.side_effect = ["0"]
        config = MagicMock()
        config.output_folder = "workspace/output"

        main.view_generated_outputs(config)

    @patch("builtins.input")
    @patch("os.listdir", return_value=["output1.txt"])
    @patch("os.path.exists", return_value=True)
    def test_invalid_file_selection(self, mock_exists, mock_listdir, mock_input):
        """Test handling of invalid file selection."""
        mock_input.side_effect = ["99", ""]
        config = MagicMock()
        config.output_folder = "workspace/output"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_generated_outputs(config)

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)

    @patch("builtins.input")
    @patch("builtins.open", create=True)
    @patch("os.listdir", return_value=["output1.txt"])
    @patch("os.path.exists", return_value=True)
    def test_view_file_content(self, mock_exists, mock_listdir, mock_open, mock_input):
        """Test viewing file content."""
        mock_input.side_effect = ["1", ""]

        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "File content here"
        mock_open.return_value = mock_file

        config = MagicMock()
        config.output_folder = "workspace/output"

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.view_generated_outputs(config)

        output = buf.getvalue()
        self.assertIn("Content of", output)


# =============================================================================
# Menu 8: Test OCR Functionality Tests
# =============================================================================


class TestOCRFunctionality(unittest.TestCase):
    """Tests for test_ocr_functionality function (Menu 8)."""

    @patch("builtins.input", return_value="")
    @patch("main.pytesseract", create=True)
    def test_tesseract_not_available(self, mock_pytesseract, mock_input):
        """Test handling when Tesseract is not available."""
        mock_pytesseract.get_tesseract_version.side_effect = Exception("Not found")
        config = MagicMock()

        buf = io.StringIO()
        with redirect_stdout(buf):
            # Import will fail, handled in the function
            try:
                main.test_ocr_functionality(config)
            except (ImportError, Exception):
                pass

    @patch("builtins.input", return_value="")
    @patch("os.path.exists", return_value=False)
    def test_input_folder_does_not_exist(self, mock_exists, mock_input):
        """Test handling when input folder doesn't exist."""
        # Need to mock pytesseract import
        with patch.dict("sys.modules", {"pytesseract": MagicMock()}):
            config = MagicMock()
            config.input_resumes_folder = "nonexistent/folder"

            buf = io.StringIO()
            with redirect_stdout(buf):
                main.test_ocr_functionality(config)

            output = buf.getvalue()
            self.assertIn("does not exist", output)

    @patch("builtins.input", return_value="")
    @patch("os.listdir", return_value=[])
    @patch("os.path.exists", return_value=True)
    def test_no_image_files(self, mock_exists, mock_listdir, mock_input):
        """Test handling when no image files are found."""
        with patch.dict("sys.modules", {"pytesseract": MagicMock()}):
            config = MagicMock()
            config.input_resumes_folder = "workspace/input_resumes"

            buf = io.StringIO()
            with redirect_stdout(buf):
                main.test_ocr_functionality(config)

            output = buf.getvalue()
            self.assertIn("No image files found", output)

    @patch("builtins.input")
    @patch("os.listdir", return_value=["resume.png", "resume.jpg"])
    @patch("os.path.exists", return_value=True)
    def test_cancel_ocr_test(self, mock_exists, mock_listdir, mock_input):
        """Test cancelling OCR test."""
        mock_input.side_effect = ["0"]
        with patch.dict("sys.modules", {"pytesseract": MagicMock()}):
            config = MagicMock()
            config.input_resumes_folder = "workspace/input_resumes"

            main.test_ocr_functionality(config)

    @patch("builtins.input")
    @patch("os.listdir", return_value=["resume.png"])
    @patch("os.path.exists", return_value=True)
    def test_invalid_image_selection(self, mock_exists, mock_listdir, mock_input):
        """Test handling of invalid image selection."""
        mock_input.side_effect = ["99", ""]
        with patch.dict("sys.modules", {"pytesseract": MagicMock()}):
            config = MagicMock()
            config.input_resumes_folder = "workspace/input_resumes"

            buf = io.StringIO()
            with redirect_stdout(buf):
                main.test_ocr_functionality(config)

            output = buf.getvalue()
            self.assertIn("Invalid choice", output)


# =============================================================================
# Menu 9: Exit and Main Menu Loop Tests
# =============================================================================


class TestMainMenuLoop(unittest.TestCase):
    """Tests for main_menu function and exit behavior."""

    @patch("builtins.input")
    @patch("main.JobScraperManager")
    def test_exit_menu(self, mock_scraper_manager, mock_input):
        """Test that option 9 exits the main menu."""
        mock_input.return_value = "9"
        config = self._create_mock_config()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.main_menu(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("Thank you for using ATS Resume Checker", output)

    @patch("builtins.input")
    @patch("main.JobScraperManager")
    def test_invalid_main_menu_choice(self, mock_scraper_manager, mock_input):
        """Test invalid choice handling in main menu."""
        mock_input.side_effect = ["99", "invalid", "9"]  # Invalid choices, then exit
        config = self._create_mock_config()

        buf = io.StringIO()
        with redirect_stdout(buf):
            main.main_menu(config, "config/config.toml")

        output = buf.getvalue()
        self.assertIn("Invalid choice", output)

    @patch("builtins.input")
    @patch("main.process_resumes_menu")
    @patch("main.JobScraperManager")
    def test_menu_option_1_calls_process_resumes_menu(
        self, mock_scraper_manager, mock_process_menu, mock_input
    ):
        """Test that option 1 calls process_resumes_menu."""
        mock_input.side_effect = ["1", "9"]  # Select option 1, then exit
        config = self._create_mock_config()

        main.main_menu(config, "config/config.toml")

        mock_process_menu.assert_called_once_with(config)

    @patch("builtins.input")
    @patch("main.convert_files_menu")
    @patch("main.JobScraperManager")
    def test_menu_option_2_calls_convert_files_menu(
        self, mock_scraper_manager, mock_convert_menu, mock_input
    ):
        """Test that option 2 calls convert_files_menu."""
        mock_input.side_effect = ["2", "9"]
        config = self._create_mock_config()

        main.main_menu(config, "config/config.toml")

        mock_convert_menu.assert_called_once_with(config)

    @patch("builtins.input")
    @patch("main.job_search_menu")
    @patch("main.JobScraperManager")
    def test_menu_option_3_calls_job_search_menu(
        self, mock_scraper_manager, mock_job_menu, mock_input
    ):
        """Test that option 3 calls job_search_menu."""
        mock_input.side_effect = ["3", "9"]
        config = self._create_mock_config()

        main.main_menu(config, "config/config.toml")

        mock_job_menu.assert_called_once()

    @patch("builtins.input")
    @patch("main.view_edit_settings")
    @patch("main.JobScraperManager")
    def test_menu_option_4_calls_view_edit_settings(
        self, mock_scraper_manager, mock_settings, mock_input
    ):
        """Test that option 4 calls view_edit_settings."""
        mock_input.side_effect = ["4", "9"]
        config = self._create_mock_config()

        main.main_menu(config, "config/config.toml")

        mock_settings.assert_called_once_with(config, "config/config.toml")

    @patch("builtins.input")
    @patch("main.ai_model_configuration_menu")
    @patch("main.JobScraperManager")
    def test_menu_option_5_calls_ai_model_config(
        self, mock_scraper_manager, mock_ai_config, mock_input
    ):
        """Test that option 5 calls ai_model_configuration_menu."""
        mock_input.side_effect = ["5", "9"]
        config = self._create_mock_config()

        main.main_menu(config, "config/config.toml")

        mock_ai_config.assert_called_once_with(config, "config/config.toml")

    @patch("builtins.input")
    @patch("main.view_available_files")
    @patch("main.JobScraperManager")
    def test_menu_option_6_calls_view_available_files(
        self, mock_scraper_manager, mock_view_files, mock_input
    ):
        """Test that option 6 calls view_available_files."""
        mock_input.side_effect = ["6", "9"]
        config = self._create_mock_config()

        main.main_menu(config, "config/config.toml")

        mock_view_files.assert_called_once_with(config)

    @patch("builtins.input")
    @patch("main.view_generated_outputs")
    @patch("main.JobScraperManager")
    def test_menu_option_7_calls_view_generated_outputs(
        self, mock_scraper_manager, mock_view_outputs, mock_input
    ):
        """Test that option 7 calls view_generated_outputs."""
        mock_input.side_effect = ["7", "9"]
        config = self._create_mock_config()

        main.main_menu(config, "config/config.toml")

        mock_view_outputs.assert_called_once_with(config)

    @patch("builtins.input")
    @patch("main.test_ocr_functionality")
    @patch("main.JobScraperManager")
    def test_menu_option_8_calls_test_ocr(
        self, mock_scraper_manager, mock_ocr, mock_input
    ):
        """Test that option 8 calls test_ocr_functionality."""
        mock_input.side_effect = ["8", "9"]
        config = self._create_mock_config()

        main.main_menu(config, "config/config.toml")

        mock_ocr.assert_called_once_with(config)

    def _create_mock_config(self):
        """Create a mock config object."""
        config = MagicMock()
        config.job_search_results_folder = "workspace/job_search_results"
        config.saved_searches_file = "data/saved_searches.toml"
        config.job_search_portals = {}
        config.job_search_jobspy = {}
        config.job_search_defaults = {}
        return config


# =============================================================================
# Main Entry Point Tests
# =============================================================================


class TestMainEntryPoint(unittest.TestCase):
    """Tests for the main() function entry point."""

    @patch("main.main_menu")
    @patch("main.load_config")
    @patch("os.makedirs")
    @patch("sys.argv", ["main.py"])
    def test_main_interactive_mode(self, mock_makedirs, mock_load_config, mock_main_menu):
        """Test main() runs in interactive mode when no job description provided."""
        mock_config = MagicMock()
        mock_config.output_folder = "workspace/output"
        mock_load_config.return_value = mock_config

        main.main()

        mock_main_menu.assert_called_once()

    @patch("main.ResumeProcessor")
    @patch("main.InputHandler")
    @patch("main.StateManager")
    @patch("main.load_config")
    @patch("os.makedirs")
    @patch("sys.argv", ["main.py", "--job_description", "test_job.txt"])
    def test_main_cli_mode_with_job_description(
        self, mock_makedirs, mock_load_config, mock_state, mock_handler, mock_processor
    ):
        """Test main() runs in CLI mode when job description is provided."""
        mock_config = MagicMock()
        mock_config.output_folder = "workspace/output"
        mock_config.job_descriptions_folder = "workspace/job_descriptions"
        mock_config.state_file = "data/state.toml"
        mock_config.input_resumes_folder = "workspace/input_resumes"
        mock_config.model_name = "gemini-pro"
        mock_config.temperature = 0.7
        mock_config.top_p = 0.95
        mock_config.top_k = 40
        mock_config.max_output_tokens = 8192
        mock_config.num_versions_per_job = 1
        mock_config.tesseract_cmd = None
        mock_config.ai_agents = {}
        mock_config.scoring_weights_file = "config/scoring_weights.toml"
        mock_config.structured_output_format = "toml"
        mock_config.iterate_until_score_reached = False
        mock_config.target_score = 80.0
        mock_config.max_iterations = 5
        mock_config.min_score_delta = 0.5
        mock_config.iteration_strategy = "best_of"
        mock_config.iteration_patience = 3
        mock_config.stop_on_regression = False
        mock_config.max_regressions = 3
        mock_config.schema_validation_enabled = False
        mock_config.resume_schema_path = None
        mock_config.schema_validation_max_retries = 3
        mock_config.recommendations_enabled = False
        mock_config.recommendations_max_items = 5
        mock_config.output_subdir_pattern = "{resume_name}/{job_title}/{timestamp}"
        mock_config.write_score_summary_file = True
        mock_config.score_summary_filename = "scores.toml"
        mock_config.write_manifest_file = True
        mock_config.manifest_filename = "manifest.toml"
        mock_config.max_concurrent_requests = 1
        mock_config.score_cache_enabled = False
        mock_load_config.return_value = mock_config

        mock_handler_instance = MagicMock()
        mock_handler_instance.get_job_descriptions.return_value = {
            "test_job.txt": "Job content"
        }
        mock_handler.return_value = mock_handler_instance

        mock_processor_instance = MagicMock()
        mock_processor.return_value = mock_processor_instance

        main.main()

        mock_processor_instance.process_resumes.assert_called_once_with(
            job_description_name="test_job.txt"
        )

    @patch("main.cli_commands.main")
    @patch("sys.argv", ["main.py", "score-resume", "--resume", "test.json"])
    def test_main_cli_subcommand(self, mock_cli_main):
        """Test main() delegates to CLI subcommands."""
        mock_cli_main.return_value = 0

        with self.assertRaises(SystemExit) as context:
            main.main()

        self.assertEqual(context.exception.code, 0)
        mock_cli_main.assert_called_once()


if __name__ == "__main__":
    unittest.main()
