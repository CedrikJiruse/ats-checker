import os
import logging
from typing import List, Dict, Any, Optional
from input_handler import InputHandler
from state_manager import StateManager
from gemini_integrator import GeminiAPIIntegrator
from output_generator import OutputGenerator

logger = logging.getLogger(__name__)

class ResumeProcessor:
    def __init__(self, input_folder: str, output_folder: str, model_name: str, temperature: float, top_p: float, top_k: int, max_output_tokens: int, num_versions_per_job: int, job_description_folder: Optional[str] = None):
        self.state_manager = StateManager()
        self.input_handler = InputHandler(self.state_manager, job_description_folder=job_description_folder)
        self.gemini_integrator = GeminiAPIIntegrator(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens
        )
        self.output_generator = OutputGenerator(output_folder=output_folder)
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.num_versions_per_job = num_versions_per_job
        self.job_description_folder = job_description_folder
        logger.info("ResumeProcessor initialized.")

    def process_resumes(self, job_description_name: Optional[str] = None) -> None:
        """
        Orchestrates the resume processing workflow:
        1. Scans input folder for new/modified text resumes.
        2. Sends new/modified resumes to Gemini API for enhancement, optionally tailoring to a job description.
        3. Generates JSON output from enhanced resume data.
        4. Updates state manager with processed resume information.

        Args:
            job_description_name: Optional. The name of the job description to use for tailoring.
        """
        job_description_content = None
        if job_description_name:
            job_descriptions = self.input_handler.get_job_descriptions()
            if job_description_name in job_descriptions:
                job_description_content = job_descriptions[job_description_name]
                logger.info(f"Using job description '{job_description_name}' for resume tailoring.")
            else:
                logger.warning(f"Job description '{job_description_name}' not found. Processing resumes without tailoring.")

        logger.info(f"Starting resume processing for input folder: {self.input_folder}")
        resumes_to_process = self.input_handler.get_resumes_to_process(self.input_folder)

        if not resumes_to_process:
            logger.info("No new or modified resumes to process.")
            return

        logger.info(f"Found {len(resumes_to_process)} new or modified resumes to process.")

        for resume in resumes_to_process:
            filepath = resume["filepath"]
            content = resume["content"]
            file_hash = resume["hash"]
            base_name_tuple = os.path.splitext(os.path.basename(filepath))
            base_name = base_name_tuple[0] # Get the name without extension

            logger.info(f"Processing resume: {filepath}")
            try:
                for i in range(1, self.num_versions_per_job + 1):
                    job_title_for_filename = job_description_name.replace('.txt', '').replace('.md', '') if job_description_name else "generic"
                    
                    logger.info(f"Enhancing resume '{filepath}' with job description '{job_description_name}' (Version {i}).")

                    enhanced_resume_data = self.gemini_integrator.enhance_resume(content, job_description=job_description_content)
                    logger.info(f"Resume '{filepath}' enhanced by Gemini API (Version {i}).")

                    json_output_path = self.output_generator.generate_json_output(enhanced_resume_data, filepath, job_title_for_filename)
                    logger.info(f"Generated JSON for '{filepath}' at: {json_output_path}")
                    text_output_path = self.output_generator.generate_text_output(enhanced_resume_data, filepath, job_title_for_filename)
                    logger.info(f"Generated TXT for '{filepath}' at: {text_output_path}")

                self.state_manager.update_resume_state(file_hash, json_output_path)
                logger.info(f"State updated for '{filepath}'.")

            except Exception as e:
                logger.error(f"Failed to process resume '{filepath}': {e}", exc_info=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Example usage:
    # Ensure you have a 'test_input_resumes' folder with valid JSON resumes
    # and your GEMINI_API_KEY set as an environment variable.
    # For testing, you might need to create a dummy resume_schema.json
    # and a dummy GEMINI_API_KEY in your environment.

    # Create dummy input folder and resume
    test_input_folder = "test_input_resumes_processor"
    test_output_folder = "test_output_resumes_processor"
    os.makedirs(test_input_folder, exist_ok=True)
    os.makedirs(test_output_folder, exist_ok=True)

    valid_resume_content = "Test User\nA highly motivated individual.\nSkills: Python, Testing"
    with open(os.path.join(test_input_folder, "test_resume.txt"), "w", encoding="utf-8") as f:
        f.write(valid_resume_content)

    # Initialize and run the processor
    try:
        processor = ResumeProcessor(
            input_folder=test_input_folder,
            output_folder=test_output_folder,
            model_name="gemini-pro",
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            num_versions_per_job=1, # For testing, generate only one version
            job_description_folder="test_job_descriptions_processor"
        )
        # Create a dummy job description for testing
        test_job_description_folder = "test_job_descriptions_processor"
        os.makedirs(test_job_description_folder, exist_ok=True)
        with open(os.path.join(test_job_description_folder, "software_engineer.txt"), "w", encoding="utf-8") as f:
            f.write("We are looking for a skilled Software Engineer with Python experience.")

        logger.info("\n--- Processing resumes without job description ---")
        processor.process_resumes()

        logger.info("\n--- Processing resumes with job description ---")
        processor.process_resumes(job_description_name="software_engineer.txt")

    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        # Clean up test files and folders
        if os.path.exists(os.path.join(test_input_folder, "test_resume.txt")):
            os.remove(os.path.join(test_input_folder, "test_resume.txt"))
        if os.path.exists(test_input_folder):
            os.rmdir(test_input_folder)
        if os.path.exists(os.path.join(test_output_folder, "test_resume_generic_enhanced.txt")):
            os.remove(os.path.join(test_output_folder, "test_resume_generic_enhanced.txt"))
        if os.path.exists(os.path.join(test_output_folder, "test_resume_software_engineer_enhanced.txt")):
            os.remove(os.path.join(test_output_folder, "test_resume_software_engineer_enhanced.txt"))
        if os.path.exists(test_output_folder):
            os.rmdir(test_output_folder)
        if os.path.exists("processed_resumes_state.json"):
            os.remove("processed_resumes_state.json")
        if os.path.exists(os.path.join(test_job_description_folder, "software_engineer.txt")):
            os.remove(os.path.join(test_job_description_folder, "software_engineer.txt"))
        if os.path.exists(test_job_description_folder):
            os.rmdir(test_job_description_folder)