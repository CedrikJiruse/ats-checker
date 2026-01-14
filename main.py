import argparse
import json
import logging
import os
import sys
import warnings

# Suppress NumPy MINGW-W64 warnings on Windows
warnings.filterwarnings("ignore", category=RuntimeWarning, module="numpy")

from config import Config, load_config
from input_handler import InputHandler  # Import InputHandler
from job_scraper_base import JobPosting, SearchFilters
from job_scraper_manager import JobScraperManager
from resume_processor import ResumeProcessor
from scoring import compute_iteration_score, score_match, score_resume
from state_manager import StateManager  # Import StateManager
from utils import calculate_file_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def display_menu():
    """Display the main menu options"""
    print("\n" + "=" * 50)
    print("           ATS Resume Checker")
    print("=" * 50)
    print("1. Process resumes")
    print("2. Convert files to appropriate format")
    print("3. Job Search & Scraping")
    print("4. View/Edit settings")
    print("5. AI Model Configuration")
    print("6. View available files")
    print("7. View generated outputs")
    print("8. Test OCR functionality")
    print("9. Exit")


def extract_text_from_file(filepath):
    """
    Extract text content from various file formats.

    Args:
        filepath (str): Path to the file to extract text from

    Returns:
        str: Extracted text content or empty string if extraction fails
    """
    import os

    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()

    try:
        if ext == ".txt":
            # Plain text file
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".md":
            # Markdown file
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".pdf":
            # PDF file - try to extract text
            try:
                import PyPDF2

                with open(filepath, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                print(
                    "PyPDF2 not installed. Please install it with: pip install PyPDF2"
                )
                return ""
        elif ext in [".docx", ".doc"]:
            # Word document - try to extract text
            try:
                import docx2txt

                return docx2txt.process(filepath)
            except ImportError:
                print(
                    "docx2txt not installed. Please install it with: pip install docx2txt"
                )
                return ""
        elif ext == ".rtf":
            # RTF file - basic handling
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple RTF stripping - in a real implementation, you might want to use a proper RTF parser
                import re

                # Remove RTF formatting tags
                content = re.sub(r"\{\\[^}]*\}", "", content)
                content = re.sub(r"\\[a-z]+", "", content)
                return content
        elif ext == ".tex":
            # LaTeX file - return as is
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        else:
            # For unsupported formats, try to read as text
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}")
        return ""


def convert_files_menu(config):
    """Handle file conversion options"""
    while True:
        print("\n--- Convert Files ---")
        print("1. Convert resume files to standard format")
        print("2. Convert job description files to standard format")
        print("3. Back to main menu")

        choice = input("Enter your choice (1-3): ").strip()

        if choice == "1":
            convert_resume_files(config)
        elif choice == "2":
            convert_job_description_files(config)
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please try again.")


def convert_resume_files(config):
    """Convert resume files to standard format and place them in the input_resumes_folder"""
    print(f"\n--- Converting Resume Files ---")

    # Get source folder from user
    source_folder = input(
        f"Enter the source folder path for resumes (or press Enter for current directory): "
    ).strip()
    if not source_folder:
        source_folder = "."

    if not os.path.exists(source_folder):
        print(f"Source folder '{source_folder}' does not exist.")
        input("\nPress Enter to continue...")
        return

    # Ensure input_resumes_folder exists
    os.makedirs(config.input_resumes_folder, exist_ok=True)

    # Supported file extensions for conversion
    supported_extensions = [".docx", ".doc", ".pdf", ".txt", ".md", ".rtf", ".tex"]

    # Find files to convert
    files_to_convert = []
    for root, _, files in os.walk(source_folder):
        for filename in files:
            if any(filename.lower().endswith(ext) for ext in supported_extensions):
                files_to_convert.append(os.path.join(root, filename))

    if not files_to_convert:
        print("No supported files found for conversion.")
        input("\nPress Enter to continue...")
        return

    print(f"Found {len(files_to_convert)} files to convert:")
    for i, filepath in enumerate(files_to_convert, 1):
        print(f"{i}. {filepath}")

    # Ask for confirmation
    confirm = input("\nDo you want to convert all these files? (y/n): ").strip().lower()
    if confirm != "y":
        print("Conversion cancelled.")
        input("\nPress Enter to continue...")
        return

    # Convert files
    converted_count = 0
    for filepath in files_to_convert:
        try:
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)

            # Convert to .txt format
            txt_filename = f"{name}.txt"
            destination_path = os.path.join(config.input_resumes_folder, txt_filename)

            # If file already exists, add a number to the filename
            counter = 1
            while os.path.exists(destination_path):
                txt_filename = f"{name}_{counter}.txt"
                destination_path = os.path.join(
                    config.input_resumes_folder, txt_filename
                )
                counter += 1

            # Extract text content based on file type
            text_content = extract_text_from_file(filepath)

            if text_content:
                # Write text content to destination
                with open(destination_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                print(f"Converted: {filepath} -> {destination_path}")
                converted_count += 1
            else:
                print(f"Failed to extract text from: {filepath}")
        except Exception as e:
            print(f"Error converting {filepath}: {e}")

    print(f"\nSuccessfully converted {converted_count} files.")
    input("\nPress Enter to continue...")


def convert_job_description_files(config):
    """Convert job description files to standard format and place them in the job_descriptions_folder"""
    print(f"\n--- Converting Job Description Files ---")

    # Get source folder from user
    source_folder = input(
        f"Enter the source folder path for job descriptions (or press Enter for current directory): "
    ).strip()
    if not source_folder:
        source_folder = "."

    if not os.path.exists(source_folder):
        print(f"Source folder '{source_folder}' does not exist.")
        input("\nPress Enter to continue...")
        return

    # Ensure job_descriptions_folder exists
    os.makedirs(config.job_descriptions_folder, exist_ok=True)

    # Supported file extensions for conversion
    supported_extensions = [".docx", ".doc", ".pdf", ".txt", ".md", ".rtf", ".tex"]

    # Find files to convert
    files_to_convert = []
    for root, _, files in os.walk(source_folder):
        for filename in files:
            if any(filename.lower().endswith(ext) for ext in supported_extensions):
                files_to_convert.append(os.path.join(root, filename))

    if not files_to_convert:
        print("No supported files found for conversion.")
        input("\nPress Enter to continue...")
        return

    print(f"Found {len(files_to_convert)} files to convert:")
    for i, filepath in enumerate(files_to_convert, 1):
        print(f"{i}. {filepath}")

    # Ask for confirmation
    confirm = input("\nDo you want to convert all these files? (y/n): ").strip().lower()
    if confirm != "y":
        print("Conversion cancelled.")
        input("\nPress Enter to continue...")
        return

    # Convert files
    converted_count = 0
    for filepath in files_to_convert:
        try:
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)

            # Convert to .txt format
            txt_filename = f"{name}.txt"
            destination_path = os.path.join(
                config.job_descriptions_folder, txt_filename
            )

            # If file already exists, add a number to the filename
            counter = 1
            while os.path.exists(destination_path):
                txt_filename = f"{name}_{counter}.txt"
                destination_path = os.path.join(
                    config.job_descriptions_folder, txt_filename
                )
                counter += 1

            # Extract text content based on file type
            text_content = extract_text_from_file(filepath)

            if text_content:
                # Write text content to destination
                with open(destination_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                print(f"Converted: {filepath} -> {destination_path}")
                converted_count += 1
            else:
                print(f"Failed to extract text from: {filepath}")
        except Exception as e:
            print(f"Error converting {filepath}: {e}")

    print(f"\nSuccessfully converted {converted_count} files.")
    input("\nPress Enter to continue...")
    print("=" * 50)


def process_resumes_menu(config):
    """Handle resume processing options"""
    while True:
        print("\n--- Process Resumes ---")
        print("1. Process all resumes without tailoring")
        print("2. Process resumes tailored to a job description")
        print("3. Process a specific resume with a job description")
        print("4. Back to main menu")

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            process_all_resumes(config)
        elif choice == "2":
            process_resumes_with_job_description(config)
        elif choice == "3":
            process_specific_resume_with_job(config)
        elif choice == "4":
            break
        else:
            print("Invalid choice. Please try again.")


def process_all_resumes(config):
    """Process all resumes without tailoring"""
    try:
        state_manager = StateManager(config.state_file)
        input_handler = InputHandler(
            state_manager, job_description_folder=config.job_descriptions_folder
        )

        logging.info(
            f"Starting resume processing for input folder: {config.input_resumes_folder}"
        )
        processor = ResumeProcessor(
            input_folder=config.input_resumes_folder,
            output_folder=config.output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_output_tokens,
            num_versions_per_job=config.num_versions_per_job,
            job_description_folder=config.job_descriptions_folder,
            tesseract_cmd=config.tesseract_cmd,
            ai_agents=config.ai_agents,
            scoring_weights_file=config.scoring_weights_file,
            structured_output_format=config.structured_output_format,
            iterate_until_score_reached=config.iterate_until_score_reached,
            target_score=config.target_score,
            max_iterations=config.max_iterations,
            min_score_delta=config.min_score_delta,
            iteration_strategy=config.iteration_strategy,
            iteration_patience=config.iteration_patience,
            stop_on_regression=config.stop_on_regression,
            max_regressions=config.max_regressions,
            state_filepath=config.state_file,
            schema_validation_enabled=config.schema_validation_enabled,
            resume_schema_path=config.resume_schema_path,
            schema_validation_max_retries=config.schema_validation_max_retries,
            recommendations_enabled=config.recommendations_enabled,
            recommendations_max_items=config.recommendations_max_items,
            output_subdir_pattern=config.output_subdir_pattern,
            write_score_summary_file=config.write_score_summary_file,
            score_summary_filename=config.score_summary_filename,
            write_manifest_file=config.write_manifest_file,
            manifest_filename=config.manifest_filename,
            max_concurrent_requests=config.max_concurrent_requests,
            score_cache_enabled=config.score_cache_enabled,
        )
        processor.process_resumes()
        logging.info("Resume processing completed successfully.")
        input("\nPress Enter to continue...")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        input("\nPress Enter to continue...")


def process_resumes_with_job_description(config):
    """Process resumes tailored to a specific job description"""
    # Get available job descriptions
    try:
        state_manager = StateManager(config.state_file)
        input_handler = InputHandler(
            state_manager, job_description_folder=config.job_descriptions_folder
        )
        job_descriptions = input_handler.get_job_descriptions()

        if not job_descriptions:
            print("No job descriptions found.")
            input("\nPress Enter to continue...")
            return

        print("\nAvailable job descriptions:")
        job_desc_list = list(job_descriptions.keys())
        for i, jd in enumerate(job_desc_list, 1):
            print(f"{i}. {jd}")

        choice = input("\nEnter the number of the job description to use: ").strip()
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(job_desc_list):
            print(f"Invalid choice. Please enter 1-{len(job_desc_list)}.")
            input("\nPress Enter to continue...")
            return

        selected_jd = job_desc_list[int(choice) - 1]

        logging.info(f"Starting resume processing tailored to: {selected_jd}")
        processor = ResumeProcessor(
            input_folder=config.input_resumes_folder,
            output_folder=config.output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_output_tokens,
            num_versions_per_job=config.num_versions_per_job,
            job_description_folder=config.job_descriptions_folder,
            tesseract_cmd=config.tesseract_cmd,
            ai_agents=config.ai_agents,
            scoring_weights_file=config.scoring_weights_file,
            structured_output_format=config.structured_output_format,
            iterate_until_score_reached=config.iterate_until_score_reached,
            target_score=config.target_score,
            max_iterations=config.max_iterations,
            min_score_delta=config.min_score_delta,
            iteration_strategy=config.iteration_strategy,
            iteration_patience=config.iteration_patience,
            stop_on_regression=config.stop_on_regression,
            max_regressions=config.max_regressions,
            state_filepath=config.state_file,
            schema_validation_enabled=config.schema_validation_enabled,
            resume_schema_path=config.resume_schema_path,
            schema_validation_max_retries=config.schema_validation_max_retries,
            recommendations_enabled=config.recommendations_enabled,
            recommendations_max_items=config.recommendations_max_items,
            output_subdir_pattern=config.output_subdir_pattern,
            write_score_summary_file=config.write_score_summary_file,
            score_summary_filename=config.score_summary_filename,
            write_manifest_file=config.write_manifest_file,
            manifest_filename=config.manifest_filename,
            max_concurrent_requests=config.max_concurrent_requests,
            score_cache_enabled=config.score_cache_enabled,
        )
        processor.process_resumes(job_description_name=selected_jd)
        logging.info("Resume processing completed successfully.")
        input("\nPress Enter to continue...")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        input("\nPress Enter to continue...")


def process_specific_resume_with_job(config):
    """Process a specific resume with a specific job description"""
    try:
        # Get available resumes
        if not os.path.exists(config.input_resumes_folder):
            print(f"Input folder '{config.input_resumes_folder}' does not exist.")
            input("\nPress Enter to continue...")
            return

        resume_files = [
            f
            for f in os.listdir(config.input_resumes_folder)
            if f.endswith(
                (".txt", ".md", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")
            )
        ]
        if not resume_files:
            print("No resume files found.")
            input("\nPress Enter to continue...")
            return

        print("\nAvailable resumes:")
        for i, resume in enumerate(resume_files, 1):
            print(f"{i}. {resume}")

        choice = input("\nEnter the number of the resume to process: ").strip()
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(resume_files):
            print(f"Invalid choice. Please enter 1-{len(resume_files)}.")
            input("\nPress Enter to continue...")
            return

        selected_resume = resume_files[int(choice) - 1]
        resume_path = os.path.join(config.input_resumes_folder, selected_resume)

        # Create state manager (used for job description loading, OCR and processing state)
        state_manager = StateManager(config.state_file)

        # Get available job descriptions
        input_handler = InputHandler(
            state_manager, job_description_folder=config.job_descriptions_folder
        )
        job_descriptions = input_handler.get_job_descriptions()

        if not job_descriptions:
            print("No job descriptions found.")
            input("\nPress Enter to continue...")
            return

        print("\nAvailable job descriptions:")
        job_desc_list = list(job_descriptions.keys())
        for i, jd in enumerate(job_desc_list, 1):
            print(f"{i}. {jd}")

        jd_choice = input("\nEnter the number of the job description to use: ").strip()
        if (
            not jd_choice.isdigit()
            or int(jd_choice) < 1
            or int(jd_choice) > len(job_desc_list)
        ):
            print(f"Invalid choice. Please enter 1-{len(job_desc_list)}.")
            input("\nPress Enter to continue...")
            return

        selected_jd = job_desc_list[int(jd_choice) - 1]

        # Process the specific resume
        logging.info(
            f"Processing resume '{selected_resume}' tailored to: {selected_jd}"
        )

        # Extract the resume content (supports text/markdown + OCR for images)
        _, ext = os.path.splitext(resume_path)
        ext = ext.lower()

        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"):
            ocr_handler = InputHandler(
                state_manager, tesseract_cmd=config.tesseract_cmd
            )
            resume_content = ocr_handler.extract_text_from_image(resume_path)
            if not resume_content:
                print(f"Failed to extract text from image: {resume_path}")
                input("\nPress Enter to continue...")
                return
        else:
            resume_content = extract_text_from_file(resume_path)

        # Track processing state by content hash (TOML-backed StateManager)
        file_hash = calculate_file_hash(resume_path)

        # Create a temporary processor for this single resume
        processor = ResumeProcessor(
            input_folder=config.input_resumes_folder,
            output_folder=config.output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_output_tokens,
            num_versions_per_job=config.num_versions_per_job,
            job_description_folder=config.job_descriptions_folder,
            tesseract_cmd=config.tesseract_cmd,
            ai_agents=config.ai_agents,
            scoring_weights_file=config.scoring_weights_file,
            structured_output_format=config.structured_output_format,
            iterate_until_score_reached=config.iterate_until_score_reached,
            target_score=config.target_score,
            max_iterations=config.max_iterations,
            min_score_delta=config.min_score_delta,
            iteration_strategy=config.iteration_strategy,
            iteration_patience=config.iteration_patience,
            stop_on_regression=config.stop_on_regression,
            max_regressions=config.max_regressions,
            state_filepath=config.state_file,
            schema_validation_enabled=config.schema_validation_enabled,
            resume_schema_path=config.resume_schema_path,
            schema_validation_max_retries=config.schema_validation_max_retries,
            recommendations_enabled=config.recommendations_enabled,
            recommendations_max_items=config.recommendations_max_items,
            output_subdir_pattern=config.output_subdir_pattern,
            write_score_summary_file=config.write_score_summary_file,
            score_summary_filename=config.score_summary_filename,
            write_manifest_file=config.write_manifest_file,
            manifest_filename=config.manifest_filename,
            max_concurrent_requests=config.max_concurrent_requests,
            score_cache_enabled=config.score_cache_enabled,
        )

        # Process just this one resume
        try:
            job_description_content = job_descriptions[selected_jd]
            for i in range(1, config.num_versions_per_job + 1):
                job_title_for_filename = selected_jd.replace(".txt", "").replace(
                    ".md", ""
                )

                logging.info(
                    f"Enhancing resume '{selected_resume}' with job description '{selected_jd}' (Version {i})."
                )

                enhanced_resume_data = processor.gemini_integrator.enhance_resume(
                    resume_content, job_description=job_description_content
                )
                logging.info(
                    f"Resume '{selected_resume}' enhanced by Gemini API (Version {i})."
                )

                enhanced_resume_json = enhanced_resume_data

                # Optional iterative loop: revise until target score reached
                if config.iterate_until_score_reached:

                    def score_fn(resume_json_str: str) -> float:
                        resume_obj = json.loads(resume_json_str)
                        if not isinstance(resume_obj, dict):
                            return 0.0

                        resume_report = score_resume(
                            resume_obj, weights_toml_path=config.scoring_weights_file
                        )

                        # If no JD content, optimize resume quality only
                        if not job_description_content:
                            return float(resume_report.total)

                        job_obj = {
                            "title": job_title_for_filename,
                            "company": "",
                            "location": "",
                            "description": job_description_content,
                            "url": "",
                            "source": "job_description",
                        }
                        match_report = score_match(
                            resume_obj,
                            job_obj,
                            weights_toml_path=config.scoring_weights_file,
                        )
                        combined, _details = compute_iteration_score(
                            resume_report=resume_report,
                            match_report=match_report,
                            weights_toml_path=config.scoring_weights_file,
                        )
                        return float(combined)

                    iter_result = (
                        processor.gemini_integrator.revise_resume_until_score_reached(
                            enhanced_resume_json=enhanced_resume_json,
                            score_fn=score_fn,
                            job_description=job_description_content,
                            target_score=config.target_score,
                            max_iterations=config.max_iterations,
                            min_score_delta=config.min_score_delta,
                        )
                    )
                    enhanced_resume_json = iter_result["best_resume_json"]
                    logging.info(
                        f"Iteration finished for '{selected_resume}' (Version {i}): best_score={iter_result['best_score']:.2f} stopped_reason={iter_result['stopped_reason']}"
                    )

                # Structured output (TOML preferred via OutputGenerator config)
                structured_output_path = (
                    processor.output_generator.generate_structured_output(
                        enhanced_resume_json, selected_resume, job_title_for_filename
                    )
                )
                logging.info(
                    f"Generated structured output for '{selected_resume}' at: {structured_output_path}"
                )

                # Always generate TXT output as well
                text_output_path = processor.output_generator.generate_text_output(
                    enhanced_resume_json, selected_resume, job_title_for_filename
                )
                logging.info(
                    f"Generated TXT for '{selected_resume}' at: {text_output_path}"
                )

                # Update processing state to avoid re-processing unchanged resumes
                state_manager.update_resume_state(file_hash, structured_output_path)

            logging.info("Resume processing completed successfully.")
        except Exception as e:
            logging.error(
                f"Failed to process resume '{selected_resume}': {e}", exc_info=True
            )

        input("\nPress Enter to continue...")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        input("\nPress Enter to continue...")


def view_edit_settings(config, config_file_path):
    """View and edit application settings"""
    while True:
        print("\n--- Settings ---")
        print("Current configuration:")
        print(f"1. Output folder: {config.output_folder}")
        print(f"2. Number of versions per job: {config.num_versions_per_job}")
        print(f"3. Model name: {config.model_name}")
        print(f"4. Temperature: {config.temperature}")
        print(f"5. Top-p: {config.top_p}")
        print(f"6. Top-k: {config.top_k}")
        print(f"7. Max output tokens: {config.max_output_tokens}")
        print(f"8. Input resumes folder: {config.input_resumes_folder}")
        print(f"9. Job descriptions folder: {config.job_descriptions_folder}")
        print(
            f"10. Tesseract executable path: {config.tesseract_cmd or 'Not set (using system default)'}"
        )
        print("11. Back to main menu")

        choice = input("\nEnter the number of the setting to edit (1-11): ").strip()

        if choice == "11":
            break
        elif choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
            edit_setting(config, config_file_path, choice)
        else:
            print("Invalid choice. Please try again.")


def edit_setting(config, config_file_path, setting_choice):
    """Edit a specific setting"""
    setting_map = {
        "1": ("output_folder", "Output folder"),
        "2": ("num_versions_per_job", "Number of versions per job"),
        "3": ("model_name", "Model name"),
        "4": ("temperature", "Temperature"),
        "5": ("top_p", "Top-p"),
        "6": ("top_k", "Top-k"),
        "7": ("max_output_tokens", "Max output tokens"),
        "8": ("input_resumes_folder", "Input resumes folder"),
        "9": ("job_descriptions_folder", "Job descriptions folder"),
        "10": ("tesseract_cmd", "Tesseract executable path"),
    }

    if setting_choice in setting_map:
        key, name = setting_map[setting_choice]
        current_value = getattr(config, key)

        # Special handling for tesseract_cmd to allow empty values
        if key == "tesseract_cmd":
            prompt_value = current_value or "Not set (using system default)"
            new_value = input(
                f"Enter new value for {name} (current: {prompt_value}): "
            ).strip()
            # Allow empty string to represent "not set"
            if new_value == "":
                new_value = None
        else:
            new_value = input(
                f"Enter new value for {name} (current: {current_value}): "
            ).strip()

        # Update config object
        if new_value or (key == "tesseract_cmd" and new_value is None):
            # Update config object
            if key in ["num_versions_per_job", "top_k", "max_output_tokens"]:
                try:
                    new_value = int(new_value)
                except ValueError:
                    print("Invalid integer value.")
                    input("\nPress Enter to continue...")
                    return

                # Bounds checking
                if key == "num_versions_per_job" and not (1 <= new_value <= 20):
                    print("num_versions_per_job must be between 1 and 20.")
                    input("\nPress Enter to continue...")
                    return
                elif key == "top_k" and not (1 <= new_value <= 100):
                    print("top_k must be between 1 and 100.")
                    input("\nPress Enter to continue...")
                    return
                elif key == "max_output_tokens" and not (256 <= new_value <= 8192):
                    print("max_output_tokens must be between 256 and 8192.")
                    input("\nPress Enter to continue...")
                    return

            elif key in ["temperature", "top_p"]:
                try:
                    new_value = float(new_value)
                except ValueError:
                    print("Invalid float value.")
                    input("\nPress Enter to continue...")
                    return

                # Bounds checking
                if not (0.0 <= new_value <= 1.0):
                    print(f"{key} must be between 0.0 and 1.0.")
                    input("\nPress Enter to continue...")
                    return

            setattr(config, key, new_value)

            # Persist configuration to TOML (preferred).
            # If the user provided a legacy .json config path, write a sibling .toml file instead.
            try:
                from config import save_config_toml

                toml_path = config_file_path
                if toml_path.lower().endswith(".json"):
                    toml_path = toml_path[:-5] + ".toml"

                save_config_toml(config, toml_path)
                print(f"Setting '{name}' updated successfully.")
                print(f"Configuration saved to: {toml_path}")
            except Exception as e:
                print(f"Setting '{name}' updated successfully.")
                print(f"Warning: failed to save configuration to TOML: {e}")
        else:
            print("No changes made.")
    else:
        print("Invalid setting choice.")

    input("\nPress Enter to continue...")


def view_available_files(config):
    """View available input resumes and job descriptions"""
    while True:
        print("\n--- Available Files ---")
        print("1. View input resumes")
        print("2. View job descriptions")
        print("3. Back to main menu")

        choice = input("Enter your choice (1-3): ").strip()

        if choice == "1":
            view_input_resumes(config)
        elif choice == "2":
            view_job_descriptions(config)
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please try again.")


def view_input_resumes(config):
    """Display available input resumes"""
    print(f"\n--- Input Resumes (in {config.input_resumes_folder}) ---")
    if not os.path.exists(config.input_resumes_folder):
        print(f"Folder '{config.input_resumes_folder}' does not exist.")
    else:
        resume_files = [
            f
            for f in os.listdir(config.input_resumes_folder)
            if f.endswith(
                (".txt", ".md", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")
            )
        ]
        if not resume_files:
            print("No resume files found.")
        else:
            for i, resume in enumerate(resume_files, 1):
                print(f"{i}. {resume}")
    input("\nPress Enter to continue...")


def view_job_descriptions(config):
    """Display available job descriptions"""
    print(f"\n--- Job Descriptions (in {config.job_descriptions_folder}) ---")
    if not os.path.exists(config.job_descriptions_folder):
        print(f"Folder '{config.job_descriptions_folder}' does not exist.")
    else:
        try:
            state_manager = StateManager(config.state_file)
            input_handler = InputHandler(
                state_manager, job_description_folder=config.job_descriptions_folder
            )
            job_descriptions = input_handler.get_job_descriptions()
            if not job_descriptions:
                print("No job descriptions found.")
            else:
                for i, jd in enumerate(job_descriptions.keys(), 1):
                    print(f"{i}. {jd}")
        except Exception as e:
            print(f"Error reading job descriptions: {e}")
    input("\nPress Enter to continue...")


def test_ocr_functionality(config):
    """Test OCR functionality on image files"""
    print("\n--- OCR Functionality Test ---")

    # Check if Tesseract is available
    try:
        import pytesseract

        from input_handler import InputHandler
        from state_manager import StateManager

        # Try to get Tesseract version to verify it's installed
        try:
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract OCR is available. Version: {version}")
        except Exception as version_error:
            print(f"Could not get Tesseract version: {version_error}")
            print("\nError: Tesseract OCR not properly configured.")
            print("  1. Install Tesseract:")
            print("     - Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print("     - macOS: brew install tesseract")
            print("     - Linux: sudo apt-get install tesseract-ocr")
            print("  2. Add Tesseract to PATH or set TESSERACT_CMD in config")
            print("  3. Verify installation: tesseract --version")
            input("\nPress Enter to continue...")
            return
    except ImportError as e:
        print(f"OCR functionality is not available: {e}")
        print("Please install the required dependencies:")
        print("  pip install pytesseract Pillow")
        print("Also ensure Tesseract OCR is installed and added to your system PATH.")
        input("\nPress Enter to continue...")
        return
    except Exception as e:
        print(f"Unexpected error when importing OCR libraries: {e}")
        input("\nPress Enter to continue...")
        return

    # Get available image files
    if not os.path.exists(config.input_resumes_folder):
        print(f"Input folder '{config.input_resumes_folder}' does not exist.")
        input("\nPress Enter to continue...")
        return

    image_files = [
        f
        for f in os.listdir(config.input_resumes_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"))
    ]

    if not image_files:
        print("No image files found in the input folder.")
        input("\nPress Enter to continue...")
        return

    print("Available image files:")
    for i, image_file in enumerate(image_files, 1):
        print(f"{i}. {image_file}")

    choice = input(
        "\nEnter the number of the image file to test OCR on (or 0 to go back): "
    ).strip()
    if choice == "0":
        return
    elif choice.isdigit() and 1 <= int(choice) <= len(image_files):
        selected_file = image_files[int(choice) - 1]
        file_path = os.path.join(config.input_resumes_folder, selected_file)

        try:
            # Use InputHandler to extract text from image
            state_manager = StateManager(config.state_file)
            input_handler = InputHandler(
                state_manager, tesseract_cmd=config.tesseract_cmd
            )
            extracted_text = input_handler.extract_text_from_image(file_path)

            if extracted_text and extracted_text.strip():
                print(f"\n--- OCR Results for {selected_file} ---")
                print(extracted_text)
                print("\n--- End of OCR Results ---")
            else:
                print(f"Could not extract text from {selected_file}.")
                print(
                    "The image may be empty, unreadable, or Tesseract might not be properly configured."
                )
                print("Please ensure:")
                print("1. Tesseract OCR is installed and added to your system PATH")
                print("2. The image file is a clear scan of a document")
                print("3. The image is not corrupted")
        except Exception as e:
            print(f"Error processing image file: {e}")
            print("Please check:")
            print("1. Tesseract OCR is properly installed and configured")
            print("2. The image file is not corrupted")
            print("3. You have read permissions for the file")
    else:
        print("Invalid choice.")

    input("\nPress Enter to continue...")


def view_generated_outputs(config):
    """View generated output files"""
    print(f"\n--- Generated Outputs (in {config.output_folder}) ---")
    if not os.path.exists(config.output_folder):
        print(f"Folder '{config.output_folder}' does not exist.")
        input("\nPress Enter to continue...")
        return

    output_files = [f for f in os.listdir(config.output_folder) if f.endswith(".txt")]
    if not output_files:
        print("No output files found.")
        input("\nPress Enter to continue...")
        return

    print("Available output files:")
    for i, output_file in enumerate(output_files, 1):
        print(f"{i}. {output_file}")

    choice = input("\nEnter the number of the file to view (or 0 to go back): ").strip()
    if choice == "0":
        return
    elif choice.isdigit() and 1 <= int(choice) <= len(output_files):
        selected_file = output_files[int(choice) - 1]
        file_path = os.path.join(config.output_folder, selected_file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"\n--- Content of {selected_file} ---")
            print(content)
            print("\n--- End of file ---")
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print("Invalid choice.")

    input("\nPress Enter to continue...")


def job_search_menu(config, job_scraper_manager):
    """Handle job search and scraping options"""
    while True:
        print("\n--- Job Search & Scraping ---")
        print("1. New job search")
        print("2. Manage saved searches")
        print("3. Run saved search")
        print("4. View saved results")
        print("5. Export jobs to job descriptions folder")
        print("6. Back to main menu")

        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            new_job_search(config, job_scraper_manager)
        elif choice == "2":
            manage_saved_searches(config, job_scraper_manager)
        elif choice == "3":
            run_saved_search(config, job_scraper_manager)
        elif choice == "4":
            view_saved_job_results(config, job_scraper_manager)
        elif choice == "5":
            export_jobs_to_descriptions(config, job_scraper_manager)
        elif choice == "6":
            break
        else:
            print("Invalid choice. Please try again.")


def new_job_search(config, job_scraper_manager):
    """Perform a new job search"""
    print("\n--- New Job Search ---")

    # Display available sources
    sources = job_scraper_manager.get_available_sources()
    print("Available job sites:")
    for i, source in enumerate(sources, 1):
        print(f"{i}. {source}")
    print(f"{len(sources) + 1}. Search all sites")

    source_choice = input(f"\nSelect job site (1-{len(sources) + 1}): ").strip()

    selected_sources = []
    if source_choice.isdigit() and 1 <= int(source_choice) <= len(sources):
        selected_sources = [sources[int(source_choice) - 1]]
    elif source_choice == str(len(sources) + 1):
        selected_sources = sources
    else:
        print(f"Invalid choice. Please enter 1-{len(sources) + 1}.")
        input("\nPress Enter to continue...")
        return

    # Get defaults from config
    defaults = config.job_search_defaults
    default_keywords = defaults.get("keywords", "")
    default_location = defaults.get("location", "")
    default_remote = defaults.get("remote_only", False)
    default_date = defaults.get("date_posted", "")

    # Get search parameters - show defaults in prompts
    print("\nEnter search criteria (press Enter to use default):")

    if default_keywords:
        keywords = input(f"Keywords [{default_keywords}]: ").strip() or default_keywords
    else:
        keywords = input("Keywords (e.g., 'software engineer python'): ").strip()

    if default_location:
        location = input(f"Location [{default_location}]: ").strip() or default_location
    else:
        location = input("Location (e.g., 'Dublin', 'Remote'): ").strip()

    # Job type
    print("\nJob Type (select multiple by entering numbers separated by commas):")
    print("1. Full-time")
    print("2. Part-time")
    print("3. Contract")
    print("4. Internship")
    job_type_input = input("Job types (e.g., '1,3' or leave blank): ").strip()
    job_types = []
    if job_type_input:
        job_type_map = {1: "Full-time", 2: "Part-time", 3: "Contract", 4: "Internship"}
        for num in job_type_input.split(","):
            if num.strip().isdigit():
                job_types.append(job_type_map.get(int(num.strip()), ""))

    # Remote only - show default
    default_remote_str = "y" if default_remote else "n"
    remote_input = input(f"Remote only? (y/n) [{default_remote_str}]: ").strip().lower()
    if remote_input == "":
        remote_only = default_remote
    else:
        remote_only = remote_input == "y"

    # Experience level
    print(
        "\nExperience Level (select multiple by entering numbers separated by commas):"
    )
    print("1. Entry")
    print("2. Mid")
    print("3. Senior")
    print("4. Director")
    print("5. Executive")
    exp_input = input("Experience levels (e.g., '2,3' or leave blank): ").strip()
    experience_levels = []
    if exp_input:
        exp_map = {1: "Entry", 2: "Mid", 3: "Senior", 4: "Director", 5: "Executive"}
        for num in exp_input.split(","):
            if num.strip().isdigit():
                experience_levels.append(exp_map.get(int(num.strip()), ""))

    # Date posted - show default
    print("\nDate Posted:")
    print("1. Last 24 hours")
    print("2. Last week")
    print("3. Last month")
    print("4. Any time")
    default_date_display = {"24h": "1", "week": "2", "month": "3"}.get(default_date, "4")
    date_choice = input(f"Select (1-4) [{default_date_display}]: ").strip() or default_date_display
    date_map = {"1": "24h", "2": "week", "3": "month", "4": None}
    date_posted = date_map.get(date_choice)

    # Create filters
    filters = SearchFilters(
        keywords=keywords if keywords else None,
        location=location if location else None,
        job_type=job_types if job_types else None,
        remote_only=remote_only,
        experience_level=experience_levels if experience_levels else None,
        date_posted=date_posted,
    )

    # Ask if user wants to save this search
    save_search = input("\nSave this search for later? (y/n): ").strip().lower()
    if save_search == "y":
        search_name = input("Enter a name for this search: ").strip()
        if search_name and len(selected_sources) == 1:
            job_scraper_manager.saved_search_manager.create_search(
                name=search_name, source=selected_sources[0], filters=filters
            )
            print(f"Search '{search_name}' saved successfully!")

    # Perform the search
    max_results = config.max_job_results_per_search
    print(f"\nSearching for jobs (max {max_results} per site)...")

    all_jobs = []
    if len(selected_sources) == 1:
        jobs = job_scraper_manager.search_jobs(
            selected_sources[0], filters, max_results
        )
        all_jobs.extend(jobs)
        print(f"Found {len(jobs)} jobs on {selected_sources[0]}")
    else:
        results = job_scraper_manager.search_all_sources(filters, max_results)
        for source, jobs in results.items():
            print(f"Found {len(jobs)} jobs on {source}")
            all_jobs.extend(jobs)

    print(f"\nTotal jobs found: {len(all_jobs)}")

    if all_jobs:
        # Display sample results
        display_count = min(5, len(all_jobs))
        print(f"\nShowing first {display_count} results:")
        for i, job in enumerate(all_jobs[:display_count], 1):
            print(f"\n{i}. {job.title}")
            print(f"   Company: {job.company}")
            print(f"   Location: {job.location}")
            print(f"   Source: {job.source}")
            if job.salary:
                print(f"   Salary: {job.salary}")

    input("\nPress Enter to continue...")


def manage_saved_searches(config, job_scraper_manager):
    """Manage saved job searches"""
    while True:
        print("\n--- Manage Saved Searches ---")
        saved_searches = job_scraper_manager.saved_search_manager.get_all_searches()

        if not saved_searches:
            print("No saved searches found.")
            input("\nPress Enter to continue...")
            return

        print("\nSaved searches:")
        for i, search in enumerate(saved_searches, 1):
            last_run = search.last_run if search.last_run else "Never"
            print(
                f"{i}. {search.name} ({search.source}) - Last run: {last_run}, Results: {search.results_count}"
            )

        print(f"\n{len(saved_searches) + 1}. Delete a saved search")
        print(f"{len(saved_searches) + 2}. Back")

        choice = input(f"\nSelect option (1-{len(saved_searches) + 2}): ").strip()

        if choice.isdigit() and 1 <= int(choice) <= len(saved_searches):
            # View search details
            search = saved_searches[int(choice) - 1]
            print(f"\n--- {search.name} ---")
            print(f"Source: {search.source}")
            print(f"Created: {search.created_at}")
            print(f"Last run: {search.last_run if search.last_run else 'Never'}")
            print(f"Last results count: {search.results_count}")
            print("\nFilters:")
            print(f"  Keywords: {search.filters.keywords or 'None'}")
            print(f"  Location: {search.filters.location or 'None'}")
            print(
                f"  Job type: {', '.join(search.filters.job_type) if search.filters.job_type else 'Any'}"
            )
            print(f"  Remote only: {search.filters.remote_only}")
            print(
                f"  Experience: {', '.join(search.filters.experience_level) if search.filters.experience_level else 'Any'}"
            )
            input("\nPress Enter to continue...")
        elif choice == str(len(saved_searches) + 1):
            # Delete a search
            del_choice = input(
                f"Enter number of search to delete (1-{len(saved_searches)}): "
            ).strip()
            if del_choice.isdigit() and 1 <= int(del_choice) <= len(saved_searches):
                search = saved_searches[int(del_choice) - 1]
                confirm = input(f"Delete '{search.name}'? (y/n): ").strip().lower()
                if confirm == "y":
                    job_scraper_manager.saved_search_manager.delete_search(search.id)
                    print("Search deleted successfully!")
        elif choice == str(len(saved_searches) + 2):
            break
        else:
            print("Invalid choice.")


def run_saved_search(config, job_scraper_manager):
    """Run a saved search"""
    print("\n--- Run Saved Search ---")
    saved_searches = job_scraper_manager.saved_search_manager.get_all_searches()

    if not saved_searches:
        print("No saved searches found.")
        input("\nPress Enter to continue...")
        return

    print("\nSaved searches:")
    for i, search in enumerate(saved_searches, 1):
        last_run = search.last_run if search.last_run else "Never"
        print(f"{i}. {search.name} ({search.source}) - Last run: {last_run}")

    choice = input(
        f"\nSelect search to run (1-{len(saved_searches)} or 0 to cancel): "
    ).strip()

    if choice == "0":
        return
    elif choice.isdigit() and 1 <= int(choice) <= len(saved_searches):
        search = saved_searches[int(choice) - 1]
        print(f"\nRunning search '{search.name}'...")

        jobs = job_scraper_manager.run_saved_search(
            search.id, config.max_job_results_per_search
        )
        print(f"Found {len(jobs)} jobs")

        if jobs:
            # Display sample results
            display_count = min(5, len(jobs))
            print(f"\nShowing first {display_count} results:")
            for i, job in enumerate(jobs[:display_count], 1):
                print(f"\n{i}. {job.title}")
                print(f"   Company: {job.company}")
                print(f"   Location: {job.location}")
                if job.salary:
                    print(f"   Salary: {job.salary}")
    else:
        print("Invalid choice.")

    input("\nPress Enter to continue...")


def view_saved_job_results(config, job_scraper_manager):
    """View previously saved job search results"""
    print("\n--- Saved Job Results ---")

    result_files = job_scraper_manager.get_saved_results()
    if not result_files:
        print("No saved results found.")
        input("\nPress Enter to continue...")
        return

    print("\nAvailable result files:")
    for i, filename in enumerate(result_files[:20], 1):  # Show latest 20
        print(f"{i}. {filename}")

    choice = input(
        f"\nSelect file to view (1-{min(20, len(result_files))} or 0 to cancel): "
    ).strip()

    if choice == "0":
        return
    elif choice.isdigit() and 1 <= int(choice) <= min(20, len(result_files)):
        filename = result_files[int(choice) - 1]
        try:
            jobs = job_scraper_manager.load_saved_results(filename)
            print(f"\n--- {filename} ---")
            print(f"Total jobs: {len(jobs)}")

            # Prefer displaying top-scored jobs if scores are available in the result file.
            results_path = os.path.join(config.job_search_results_folder, filename)
            ranked = job_scraper_manager.rank_jobs_in_results(results_path, top_n=10)

            if ranked:
                print(f"\nTop {len(ranked)} jobs by score:")
                for entry in ranked:
                    job_data = entry.get("job", {}) if isinstance(entry, dict) else {}
                    score = entry.get("job_score")
                    title = job_data.get("title", "")
                    company = job_data.get("company", "")
                    location = job_data.get("location", "")
                    url = job_data.get("url", "")
                    salary = job_data.get("salary", None)

                    print(f"\n{entry.get('rank', '?')}. {title}")
                    if isinstance(score, (int, float)):
                        print(f"   Score: {float(score):.2f}")
                    else:
                        print("   Score: N/A")
                    if company:
                        print(f"   Company: {company}")
                    if location:
                        print(f"   Location: {location}")
                    if url:
                        print(f"   URL: {url}")
                    if salary:
                        print(f"   Salary: {salary}")
            else:
                display_count = min(10, len(jobs))
                print(f"\nShowing first {display_count} jobs:")
                for i, job in enumerate(jobs[:display_count], 1):
                    print(f"\n{i}. {job.title}")
                    print(f"   Company: {job.company}")
                    print(f"   Location: {job.location}")
                    print(f"   Source: {job.source}")
                    print(f"   URL: {job.url}")
                    if job.salary:
                        print(f"   Salary: {job.salary}")
        except Exception as e:
            print(f"Error loading results: {e}")
    else:
        print("Invalid choice.")

    input("\nPress Enter to continue...")


def export_jobs_to_descriptions(config, job_scraper_manager):
    """Export job postings to job descriptions folder"""
    print("\n--- Export Jobs to Job Descriptions ---")

    result_files = job_scraper_manager.get_saved_results()
    if not result_files:
        print("No saved results found.")
        input("\nPress Enter to continue...")
        return

    print("\nAvailable result files:")
    for i, filename in enumerate(result_files[:20], 1):
        print(f"{i}. {filename}")

    choice = input(
        f"\nSelect file to export (1-{min(20, len(result_files))} or 0 to cancel): "
    ).strip()

    if choice == "0":
        return
    elif choice.isdigit() and 1 <= int(choice) <= min(20, len(result_files)):
        filename = result_files[int(choice) - 1]
        try:
            jobs = job_scraper_manager.load_saved_results(filename)
            print(f"\nLoaded {len(jobs)} jobs from {filename}")

            print("\nExport mode:")
            print("1. Export first N jobs (original order)")
            print("2. Export top-scored jobs")
            export_mode = input("Choose export mode (1-2): ").strip()

            if export_mode == "2":
                results_path = os.path.join(config.job_search_results_folder, filename)
                ranked = job_scraper_manager.rank_jobs_in_results(
                    results_path, top_n=100000
                )
                if not ranked:
                    print(
                        "No scored jobs found in this results file. Falling back to original order."
                    )
                    export_mode = "1"
                else:
                    export_count = input(
                        f"How many top-scored jobs to export? (1-{len(ranked)} or 'all'): "
                    ).strip()

                    if export_count.lower() == "all":
                        ranked_to_export = ranked
                    elif export_count.isdigit() and 1 <= int(export_count) <= len(
                        ranked
                    ):
                        ranked_to_export = ranked[: int(export_count)]
                    else:
                        print("Invalid number.")
                        input("\nPress Enter to continue...")
                        return

                    # Convert ranked raw dict jobs into JobPosting objects (ignore extra fields like job_score).
                    allowed = set(JobPosting.__dataclass_fields__.keys())
                    jobs_to_export = []
                    for entry in ranked_to_export:
                        job_data = (
                            entry.get("job", {}) if isinstance(entry, dict) else {}
                        )
                        if not isinstance(job_data, dict):
                            continue
                        filtered = {k: v for k, v in job_data.items() if k in allowed}
                        try:
                            jobs_to_export.append(JobPosting(**filtered))
                        except Exception:
                            continue

            if export_mode != "2":
                # Ask how many to export (original order)
                export_count = input(
                    f"How many jobs to export? (1-{len(jobs)} or 'all'): "
                ).strip()

                if export_count.lower() == "all":
                    jobs_to_export = jobs
                elif export_count.isdigit() and 1 <= int(export_count) <= len(jobs):
                    jobs_to_export = jobs[: int(export_count)]
                else:
                    print("Invalid number.")
                    input("\nPress Enter to continue...")
                    return

            # Export the jobs
            exported = job_scraper_manager.export_to_job_descriptions(
                jobs_to_export, config.job_descriptions_folder
            )
            print(
                f"\nSuccessfully exported {exported} jobs to {config.job_descriptions_folder}"
            )
            print("You can now use these job descriptions to tailor your resumes!")

        except Exception as e:
            print(f"Error exporting jobs: {e}")
    else:
        print("Invalid choice.")

    input("\nPress Enter to continue...")


def ai_model_configuration_menu(config, config_file_path):
    """Handle AI model configuration options"""
    while True:
        print("\n--- AI Model Configuration ---")
        print("Current Configuration:")
        view_current_configuration(config)
        print("\nOptions:")
        print("1. Change model for a specific agent")
        print("2. Load a provider profile")
        print("3. Test AI configuration")
        print("4. View available models")
        print("5. Back to main menu")

        choice = input("Enter your choice (1-5): ").strip()

        if choice == "1":
            change_agent_model(config, config_file_path)
        elif choice == "2":
            load_provider_profile(config, config_file_path)
        elif choice == "3":
            test_ai_configuration(config)
        elif choice == "4":
            view_available_models()
        elif choice == "5":
            break
        else:
            print("Invalid choice. Please try again.")


def view_current_configuration(config):
    """Display current AI model configuration"""
    agents = config.ai_agents
    for agent_name, agent_config in agents.items():
        print(f"  {agent_name}: {agent_config.provider}/{agent_config.model_name}")


def change_agent_model(config, config_file_path):
    """Change the provider and model for a specific agent"""
    print("\n--- Change Agent Model ---")

    agents = config.ai_agents
    agent_names = list(agents.keys())

    print("Select agent to modify:")
    for i, agent_name in enumerate(agent_names, 1):
        current = agents[agent_name]
        print(f"{i}. {agent_name} (current: {current.provider}/{current.model_name})")

    choice = input(f"\nEnter choice (1-{len(agent_names)}): ").strip()

    if not choice.isdigit() or not (1 <= int(choice) <= len(agent_names)):
        print("Invalid choice.")
        return

    agent_name = agent_names[int(choice) - 1]

    # Select provider
    providers = ["gemini", "openai", "anthropic", "llama"]
    print("\nSelect provider:")
    for i, provider in enumerate(providers, 1):
        print(f"{i}. {provider}")

    provider_choice = input(f"Enter choice (1-{len(providers)}): ").strip()
    if not provider_choice.isdigit() or not (1 <= int(provider_choice) <= len(providers)):
        print("Invalid choice.")
        return

    selected_provider = providers[int(provider_choice) - 1]

    # Get available models for provider
    models = get_available_models_for_provider(selected_provider)
    if not models:
        print(f"No models found for {selected_provider}")
        return

    print(f"\nAvailable models for {selected_provider}:")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model}")

    model_choice = input(f"Enter choice (1-{len(models)}): ").strip()
    if not model_choice.isdigit() or not (1 <= int(model_choice) <= len(models)):
        print("Invalid choice.")
        return

    selected_model = models[int(model_choice) - 1]

    # Update config
    config.ai_agents[agent_name].provider = selected_provider
    config.ai_agents[agent_name].model_name = selected_model

    # Save to config file
    try:
        config.save_config(config_file_path)
        print(f"\nSuccessfully updated {agent_name} to {selected_provider}/{selected_model}")
        print("Configuration saved.")
    except Exception as e:
        print(f"Error saving configuration: {e}")

    input("\nPress Enter to continue...")


def get_available_models_for_provider(provider):
    """Get list of available models for a provider"""
    models_by_provider = {
        "gemini": [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
        ],
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20250219",
            "claude-3-sonnet-20240229",
        ],
        "llama": [
            "meta-llama/Llama-3.3-70B-Instruct",
            "meta-llama/Llama-3.1-70B-Instruct",
            "meta-llama/Llama-3-70B-Instruct",
        ],
    }
    return models_by_provider.get(provider, [])


def load_provider_profile(config, config_file_path):
    """Load a pre-configured provider profile (optimized for cost vs quality)"""
    print("\n" + "=" * 60)
    print("         PRESET CONFIGURATIONS (Cost vs Quality)")
    print("=" * 60)

    profiles = {
        "1": {
            "name": "Budget",
            "path": "config/profiles/budget.toml",
            "cost": "FREE or $0.50-1 per 100 resumes",
            "quality": "Good",
            "description": "Minimal cost - perfect for testing & learning",
        },
        "2": {
            "name": "Balanced",
            "path": "config/profiles/balanced.toml",
            "cost": "$5-10 per 100 resumes",
            "quality": "Excellent",
            "description": "RECOMMENDED - best value, most users",
        },
        "3": {
            "name": "Quality",
            "path": "config/profiles/quality.toml",
            "cost": "$20-50 per 100 resumes",
            "quality": "Maximum",
            "description": "Premium quality for competitive positions",
        },
    }

    print("\nAvailable Presets:\n")
    for key, profile in profiles.items():
        print(f"{key}. {profile['name']:12} │ {profile['cost']:30} │ {profile['quality']:10}")
        print(f"   {profile['description']}")
        print()

    print("For detailed comparison, see: docs/PROVIDER_PRESETS.md\n")

    choice = input("Select preset (1-3): ").strip()

    if choice not in profiles:
        print("Invalid choice.")
        input("\nPress Enter to continue...")
        return

    profile_info = profiles[choice]
    profile_name = profile_info["name"]
    profile_path = profile_info["path"]

    # Check if profile file exists
    if not os.path.exists(profile_path):
        print(f"Profile file {profile_path} not found.")
        input("\nPress Enter to continue...")
        return

    # Load profile config
    try:
        from config import load_config_from_file
        profile_config = load_config_from_file(profile_path)

        # Merge profile AI agents into current config
        if hasattr(profile_config, 'ai_agents'):
            config.ai_agents = profile_config.ai_agents
            config.save_config(config_file_path)
            print("\n" + "=" * 60)
            print(f"✓ Successfully loaded {profile_name} preset!")
            print("=" * 60)
            print(f"\nCost: {profile_info['cost']}")
            print(f"Quality: {profile_info['quality']}")
            print(f"\nCurrent Configuration:")
            view_current_configuration(config)
            print("\nConfiguration saved!")
        else:
            print("Profile does not contain AI agent configuration.")
    except Exception as e:
        print(f"Error loading profile: {e}")

    input("\nPress Enter to continue...")


def test_ai_configuration(config):
    """Test AI configuration by checking API connectivity"""
    print("\n--- Test AI Configuration ---")
    print("Testing connectivity for configured agents...\n")

    agents = config.ai_agents
    all_ok = True

    for agent_name, agent_config in agents.items():
        provider = agent_config.provider
        model_name = agent_config.model_name

        # Map provider to environment variable
        env_vars = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "llama": ["TOGETHER_API_KEY", "GROQ_API_KEY"],
        }

        # Check if API key exists
        required_env = env_vars.get(provider)
        if isinstance(required_env, list):
            has_key = any(os.environ.get(env) for env in required_env)
            env_status = f"({' or '.join(required_env)})"
        else:
            has_key = os.environ.get(required_env) is not None
            env_status = f"({required_env})"

        if has_key:
            print(f"✓ {agent_name:20} {provider:12} {model_name:40} - API key found {env_status}")
        else:
            print(f"✗ {agent_name:20} {provider:12} {model_name:40} - Missing {env_status}")
            all_ok = False

    if all_ok:
        print("\n✓ All API keys are configured!")
    else:
        print("\n✗ Some API keys are missing. Please set up the required environment variables.")
        print("\nAPI Key Setup Instructions:")
        print("  Gemini: https://ai.google.dev/")
        print("  OpenAI: https://platform.openai.com/api-keys")
        print("  Anthropic: https://console.anthropic.com/")
        print("  Llama (Together AI): https://www.together.ai/")
        print("  Llama (Groq): https://console.groq.com/")

    input("\nPress Enter to continue...")


def view_available_models():
    """Display all available models per provider"""
    print("\n--- Available Models ---")

    providers = {
        "Gemini (Google)": {
            "gemini-2.0-flash-exp": "Latest Gemini model (experimental)",
            "gemini-1.5-pro": "Pro tier (high quality)",
            "gemini-1.5-flash": "Flash tier (fast)",
            "gemini-1.5-flash-latest": "Flash tier (latest)",
        },
        "OpenAI": {
            "gpt-4o": "GPT-4 Omni (latest, high quality)",
            "gpt-4o-mini": "GPT-4 Omni Mini (fast, cost-effective)",
            "gpt-4-turbo": "GPT-4 Turbo (previous generation)",
            "gpt-3.5-turbo": "GPT-3.5 Turbo (fast, cheap)",
        },
        "Anthropic": {
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet (latest, high quality)",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku (fast, efficient)",
            "claude-3-opus-20250219": "Claude 3 Opus (most capable, slower)",
            "claude-3-sonnet-20240229": "Claude 3 Sonnet (previous generation)",
        },
        "Meta Llama (via Together AI or Groq)": {
            "meta-llama/Llama-3.3-70B-Instruct": "Llama 3.3 70B (latest)",
            "meta-llama/Llama-3.1-70B-Instruct": "Llama 3.1 70B",
            "meta-llama/Llama-3-70B-Instruct": "Llama 3 70B",
        },
    }

    for provider_name, models in providers.items():
        print(f"\n{provider_name}:")
        for model_id, description in models.items():
            print(f"  {model_id}")
            print(f"    {description}")

    print("\n--- Recommendations ---")
    print("  Enhancement: OpenAI GPT-4o or Anthropic Claude 3.5 Sonnet (best quality)")
    print("  Job Summarization: OpenAI GPT-4o-mini or Anthropic Claude 3.5 Haiku (fast, cheap)")
    print("  Scoring: Gemini Flash or OpenAI GPT-4o-mini (quick scoring)")
    print("  Revision: OpenAI GPT-4o (high quality output)")

    input("\nPress Enter to continue...")


def main_menu(config, config_file_path):
    """Main menu loop"""
    # Initialize job scraper manager with portal config and defaults
    job_scraper_manager = JobScraperManager(
        results_folder=config.job_search_results_folder,
        saved_searches_path=config.saved_searches_file,
        portals_config=config.job_search_portals,
        jobspy_config=config.job_search_jobspy,
        search_defaults=config.job_search_defaults,
    )

    while True:
        display_menu()
        choice = input("Enter your choice (1-9): ").strip()

        if choice == "1":
            process_resumes_menu(config)
        elif choice == "2":
            convert_files_menu(config)
        elif choice == "3":
            job_search_menu(config, job_scraper_manager)
        elif choice == "4":
            view_edit_settings(config, config_file_path)
        elif choice == "5":
            ai_model_configuration_menu(config, config_file_path)
        elif choice == "6":
            view_available_files(config)
        elif choice == "7":
            view_generated_outputs(config)
        elif choice == "8":
            test_ocr_functionality(config)
        elif choice == "9":
            print("Thank you for using ATS Resume Checker!")
            break
        else:
            print("Invalid choice. Please try again.")


def main():
    # Non-interactive CLI subcommands (skip the interactive menu).
    # This is intentionally checked before argparse parsing, because these subcommands
    # have their own argument structure.
    if len(sys.argv) > 1 and sys.argv[1] in (
        "score-resume",
        "score-match",
        "rank-jobs",
    ):
        from cli_commands import main as cli_main

        raise SystemExit(cli_main(sys.argv[1:]))

    parser = argparse.ArgumentParser(description="ATS Checker")
    parser.add_argument(
        "--config_file",
        type=str,
        default="config/config.toml",
        help="Path to the configuration TOML file.",
    )
    parser.add_argument(
        "--job_description",
        type=str,
        help="Optional: Name of the job description file (e.g., 'software_engineer.txt') to tailor resumes.",
    )
    args = parser.parse_args()
    config = load_config(config_file_path=args.config_file, cli_args=args)

    # Create output folder if it doesn't exist
    os.makedirs(config.output_folder, exist_ok=True)

    # Check if we're running with CLI arguments for backward compatibility
    if args.job_description:
        # Run in CLI mode for backward compatibility
        try:
            state_manager = StateManager(
                config.state_file
            )  # Initialize StateManager here
            input_handler = InputHandler(
                state_manager, job_description_folder=config.job_descriptions_folder
            )

            job_description_to_use = None
            if args.job_description:
                job_descriptions = input_handler.get_job_descriptions()
                if args.job_description in job_descriptions:
                    job_description_to_use = args.job_description
                    logging.info(f"Selected job description: {job_description_to_use}")
                else:
                    logging.warning(
                        f"Job description '{args.job_description}' not found in '{config.job_descriptions_folder}'. Processing without tailoring."
                    )
            else:
                logging.info(
                    "No specific job description provided. Processing all resumes without tailoring."
                )

            logging.info(
                f"Starting resume processing for input folder: {config.input_resumes_folder}"
            )
            processor = ResumeProcessor(
                input_folder=config.input_resumes_folder,
                output_folder=config.output_folder,
                model_name=config.model_name,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                max_output_tokens=config.max_output_tokens,
                num_versions_per_job=config.num_versions_per_job,
                job_description_folder=config.job_descriptions_folder,
                tesseract_cmd=config.tesseract_cmd,
                ai_agents=config.ai_agents,
                scoring_weights_file=config.scoring_weights_file,
                structured_output_format=config.structured_output_format,
                iterate_until_score_reached=config.iterate_until_score_reached,
                target_score=config.target_score,
                max_iterations=config.max_iterations,
                min_score_delta=config.min_score_delta,
                iteration_strategy=config.iteration_strategy,
                iteration_patience=config.iteration_patience,
                stop_on_regression=config.stop_on_regression,
                max_regressions=config.max_regressions,
                state_filepath=config.state_file,
                schema_validation_enabled=config.schema_validation_enabled,
                resume_schema_path=config.resume_schema_path,
                schema_validation_max_retries=config.schema_validation_max_retries,
                recommendations_enabled=config.recommendations_enabled,
                recommendations_max_items=config.recommendations_max_items,
                output_subdir_pattern=config.output_subdir_pattern,
                write_score_summary_file=config.write_score_summary_file,
                score_summary_filename=config.score_summary_filename,
                write_manifest_file=config.write_manifest_file,
                manifest_filename=config.manifest_filename,
                max_concurrent_requests=config.max_concurrent_requests,
                score_cache_enabled=config.score_cache_enabled,
            )
            processor.process_resumes(job_description_name=job_description_to_use)
            logging.info("Resume processing completed successfully.")
        except ValueError as e:
            logging.error(f"Configuration Error: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    else:
        # Run in interactive menu mode
        main_menu(config, args.config_file)


if __name__ == "__main__":
    main()
