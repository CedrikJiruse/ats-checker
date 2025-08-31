import os
import logging
from typing import List, Dict, Any, Optional
from utils import calculate_file_hash
from state_manager import StateManager
import json

# OCR imports
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("OCR dependencies not available. Install pytesseract and Pillow for OCR functionality.")

# PDF imports
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PDF dependencies not available. Install PyPDF2 for PDF functionality.")

logger = logging.getLogger(__name__)

class InputHandler:
    def __init__(self, state_manager: StateManager, job_description_folder: Optional[str] = None):
        self.state_manager = state_manager
        self.job_description_folder = job_description_folder

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from an image using OCR.
        
        Args:
            image_path: The path to the image file.
            
        Returns:
            The extracted text from the image.
        """
        if not OCR_AVAILABLE:
            logger.error("OCR functionality is not available. Please install pytesseract and Pillow.")
            return ""
        
        try:
            # Open the image file
            image = Image.open(image_path)
            
            # Use pytesseract to extract text
            text = pytesseract.image_to_string(image)
            
            logger.info(f"Successfully extracted text from image: {image_path}")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}", exc_info=True)
            return ""

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: The path to the PDF file.
            
        Returns:
            The extracted text from the PDF.
        """
        if not PDF_AVAILABLE:
            logger.error("PDF functionality is not available. Please install PyPDF2.")
            return ""
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
            logger.info(f"Successfully extracted text from PDF: {pdf_path}")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}", exc_info=True)
            return ""

    def extract_text_from_json(self, json_path: str) -> str:
        """
        Extract text content from a JSON resume file.
        
        Args:
            json_path: The path to the JSON file.
            
        Returns:
            A string representation of the JSON resume content.
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Convert JSON data to a readable text format
            text_parts = []
            
            # Personal info
            if "personal_info" in data:
                personal_info = data["personal_info"]
                if "name" in personal_info:
                    text_parts.append(personal_info["name"])
                if "email" in personal_info:
                    text_parts.append(personal_info["email"])
                if "phone" in personal_info:
                    text_parts.append(personal_info["phone"])
                if "linkedin" in personal_info:
                    text_parts.append(personal_info["linkedin"])
                if "github" in personal_info:
                    text_parts.append(personal_info["github"])
            
            # Summary
            if "summary" in data:
                text_parts.append(data["summary"])
            
            # Experience
            if "experience" in data:
                text_parts.append("Experience:")
                for exp in data["experience"]:
                    if "title" in exp:
                        text_parts.append(exp["title"])
                    if "company" in exp:
                        text_parts.append(exp["company"])
                    if "description" in exp:
                        if isinstance(exp["description"], list):
                            text_parts.extend(exp["description"])
                        else:
                            text_parts.append(str(exp["description"]))
            
            # Education
            if "education" in data:
                text_parts.append("Education:")
                for edu in data["education"]:
                    if "degree" in edu:
                        text_parts.append(edu["degree"])
                    if "institution" in edu:
                        text_parts.append(edu["institution"])
            
            # Skills
            if "skills" in data:
                text_parts.append("Skills: " + ", ".join(data["skills"]))
            
            # Projects
            if "projects" in data:
                text_parts.append("Projects:")
                for proj in data["projects"]:
                    if "name" in proj:
                        text_parts.append(proj["name"])
                    if "description" in proj:
                        text_parts.append(proj["description"])
            
            logger.info(f"Successfully extracted text from JSON: {json_path}")
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting text from JSON {json_path}: {e}", exc_info=True)
            return ""

    def get_resumes_to_process(self, input_folder: str) -> List[Dict[str, Any]]:
        """
        Scans the input folder for text resume files and image files
        and identifies which ones need processing based on the StateManager.

        Args:
            input_folder: The path to the folder containing resume files.

        Returns:
            A list of dictionaries, where each dictionary contains:
            - 'filepath': The path to the file.
            - 'content': The content of the resume as a string.
            - 'hash': The SHA256 hash of the file content.
        """
        resumes_to_process = []
        if not os.path.isdir(input_folder):
            logger.error(f"Input folder '{input_folder}' does not exist or is not a directory.")
            return []

        logger.info(f"Scanning input folder: {input_folder}")
        for root, _, files in os.walk(input_folder):
            for filename in files:
                logger.debug(f"Found file: {filename}")
                filepath = os.path.join(root, filename)
                
                # Check file extension and process accordingly
                if filename.endswith(".txt") or filename.endswith(".tex"):
                    # Handle text and LaTeX files
                    logger.debug(f"Processing text/LaTeX file: {filepath}")
                    try:
                        file_hash = calculate_file_hash(filepath)
                        logger.debug(f"File hash for {filepath}: {file_hash}")

                        if not self.state_manager.is_processed(file_hash):
                            with open(filepath, "r", encoding="utf-8") as f:
                                resume_content = f.read()
                            resumes_to_process.append({
                                "filepath": filepath,
                                "content": resume_content,
                                "hash": file_hash
                            })
                            logger.info(f"Identified new/modified resume for processing: {filepath}")
                        else:
                            logger.info(f"Skipping already processed resume: {filepath}")
                    except FileNotFoundError:
                        logger.error(f"File not found during scan: {filepath}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while processing {filepath}: {e}", exc_info=True)
                elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")):
                    # Handle image files
                    logger.debug(f"Processing image file: {filepath}")
                    try:
                        file_hash = calculate_file_hash(filepath)
                        logger.debug(f"File hash for {filepath}: {file_hash}")

                        if not self.state_manager.is_processed(file_hash):
                            # Extract text from image using OCR
                            resume_content = self.extract_text_from_image(filepath)
                            if resume_content.strip():
                                resumes_to_process.append({
                                    "filepath": filepath,
                                    "content": resume_content,
                                    "hash": file_hash
                                })
                                logger.info(f"Identified new/modified resume for processing: {filepath}")
                            else:
                                logger.warning(f"Could not extract text from image: {filepath}")
                        else:
                            logger.info(f"Skipping already processed resume: {filepath}")
                    except FileNotFoundError:
                        logger.error(f"File not found during scan: {filepath}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while processing {filepath}: {e}", exc_info=True)
                elif filename.lower().endswith(".pdf"):
                    # Handle PDF files
                    logger.debug(f"Processing PDF file: {filepath}")
                    try:
                        file_hash = calculate_file_hash(filepath)
                        logger.debug(f"File hash for {filepath}: {file_hash}")

                        if not self.state_manager.is_processed(file_hash):
                            # Extract text from PDF
                            resume_content = self.extract_text_from_pdf(filepath)
                            if resume_content.strip():
                                resumes_to_process.append({
                                    "filepath": filepath,
                                    "content": resume_content,
                                    "hash": file_hash
                                })
                                logger.info(f"Identified new/modified resume for processing: {filepath}")
                            else:
                                logger.warning(f"Could not extract text from PDF: {filepath}")
                        else:
                            logger.info(f"Skipping already processed resume: {filepath}")
                    except FileNotFoundError:
                        logger.error(f"File not found during scan: {filepath}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while processing {filepath}: {e}", exc_info=True)
                elif filename.lower().endswith(".json"):
                    # Handle JSON files
                    logger.debug(f"Processing JSON file: {filepath}")
                    try:
                        file_hash = calculate_file_hash(filepath)
                        logger.debug(f"File hash for {filepath}: {file_hash}")

                        if not self.state_manager.is_processed(file_hash):
                            # Extract text from JSON
                            resume_content = self.extract_text_from_json(filepath)
                            if resume_content.strip():
                                resumes_to_process.append({
                                    "filepath": filepath,
                                    "content": resume_content,
                                    "hash": file_hash
                                })
                                logger.info(f"Identified new/modified resume for processing: {filepath}")
                            else:
                                logger.warning(f"Could not extract text from JSON: {filepath}")
                        else:
                            logger.info(f"Skipping already processed resume: {filepath}")
                    except FileNotFoundError:
                        logger.error(f"File not found during scan: {filepath}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while processing {filepath}: {e}", exc_info=True)
        return resumes_to_process

    def get_job_descriptions(self) -> Dict[str, str]:
        """
        Scans the job_description_folder for text files and returns their content.

        Returns:
            A dictionary where keys are job description filenames (without extension)
            and values are their content.
        """
        job_descriptions = {}
        if not self.job_description_folder or not os.path.isdir(self.job_description_folder):
            logger.warning(f"Job description folder '{self.job_description_folder}' does not exist or is not a directory. Skipping job description loading.")
            return {}

        logger.info(f"Scanning job description folder: {self.job_description_folder}")
        for root, _, files in os.walk(self.job_description_folder):
            for filename in files:
                if filename.endswith(".txt") or filename.endswith(".md"): # Assuming text or markdown files
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        job_descriptions[filename] = content
                        logger.info(f"Loaded job description: {filename} from {filepath}")
                    except Exception as e:
                        logger.error(f"Error reading job description file {filepath}: {e}", exc_info=True)
        return job_descriptions

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Setup for testing
    test_input_folder = "test_input_resumes"
    test_job_description_folder = "test_job_descriptions"
    os.makedirs(test_input_folder, exist_ok=True)
    os.makedirs(test_job_description_folder, exist_ok=True)
    os.makedirs("output", exist_ok=True) # For state manager test cleanup

    # Create dummy valid resume
    valid_resume_content = "John Doe\nSoftware Engineer\nExperienced software engineer with a passion for AI."
    with open(os.path.join(test_input_folder, "valid_resume.txt"), "w", encoding="utf-8") as f:
        f.write(valid_resume_content)

    # Create dummy invalid resume (for testing purposes, content doesn't matter as much without schema)
    invalid_resume_content = "Jane Doe\nJunior Developer\nLess experienced."
    with open(os.path.join(test_input_folder, "invalid_resume.txt"), "w", encoding="utf-8") as f:
        f.write(invalid_resume_content)

    # Create a state manager instance
    state_manager = StateManager("test_state_input_handler.json")
    input_handler = InputHandler(state_manager, job_description_folder=test_job_description_folder)

    logger.info("\n--- First run ---")
    resumes = input_handler.get_resumes_to_process(test_input_folder)
    for resume in resumes:
        logger.info(f"Found resume to process: {resume['filepath']}")
        # Simulate processing and updating state
        state_manager.update_resume_state(resume['hash'], f"output/{os.path.basename(resume['filepath']).replace('.txt', '.pdf')}")

    logger.info("\n--- Second run (should skip processed) ---")
    resumes = input_handler.get_resumes_to_process(test_input_folder)
    if not resumes:
        logger.info("No new resumes to process.")
    for resume in resumes:
        logger.info(f"Found resume to process: {resume['filepath']}")

    # Create dummy job description
    with open(os.path.join(test_job_description_folder, "software_engineer.txt"), "w") as f:
        f.write("We are looking for a skilled Software Engineer to join our team.")

    logger.info("\n--- Testing get_job_descriptions ---")
    job_descriptions = input_handler.get_job_descriptions()
    for name, content in job_descriptions.items():
        logger.info(f"Loaded job description: {name}, Content snippet: {content[:50]}...")

    # Clean up test files
    os.remove(os.path.join(test_input_folder, "valid_resume.txt"))
    os.remove(os.path.join(test_input_folder, "invalid_resume.txt"))
    os.rmdir(test_input_folder)
    os.remove(os.path.join(test_job_description_folder, "software_engineer.txt"))
    os.rmdir(test_job_description_folder)
    if os.path.exists("test_state_input_handler.json"):
        os.remove("test_state_input_handler.json")
    if os.path.exists("output"):
        os.rmdir("output")