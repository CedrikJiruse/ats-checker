import os
import logging
import google.generativeai as genai
from typing import Dict, Any, Optional
import json # Keep json for parsing Gemini's response

logger = logging.getLogger(__name__)

class GeminiAPIIntegrator:
    def __init__(self, model_name: str = "gemini-pro", temperature: float = 0.7,
                 top_p: float = 0.95, top_k: int = 40, max_output_tokens: int = 8192):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found. Please set it as an environment variable.")
            raise ValueError("GEMINI_API_KEY not found. Please set it as an environment variable.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_output_tokens=max_output_tokens,
            )
        )
        logger.info(f"GeminiAPIIntegrator initialized with model: {model_name}, temperature: {temperature}, top_p: {top_p}, top_k: {top_k}, max_output_tokens: {max_output_tokens}")

    def _craft_prompt(self, resume_content: str, job_description: Optional[str] = None) -> str:
        """
        Crafts a detailed prompt for the Gemini API to enhance and format resume content,
        optionally tailoring it to a specific job description.

        Args:
            resume_content: The raw resume content as a string.
            job_description: Optional. The text of the job description to tailor the resume to.

        Returns:
            A string prompt for the Gemini API.
        """
        try:
            prompt_parts = [
                "You are an expert resume builder. Your task is to take the provided resume content "
                "and enhance it for clarity, impact, and professional presentation. "
                "Focus on action verbs, quantifiable achievements, and industry-standard formatting. "
                "The output should be a well-structured JSON object representing the enhanced resume. "
                "The JSON should have the following top-level keys: 'personal_info', 'summary', 'experience', 'education', 'skills', 'projects'. "
                "Each section should be an array of objects or a single object as appropriate. "
                "For example, 'personal_info' should be an object with keys like 'name', 'email', 'phone', 'linkedin', 'github', 'portfolio'. "
                "The 'experience', 'education', and 'projects' sections should be arrays of objects, each with relevant details. "
                "The 'skills' section should be an array of strings. "
            ]

            if job_description:
                prompt_parts.append(
                    "Crucially, tailor the resume specifically to the following job description. "
                    "Highlight relevant skills and experiences, and rephrase accomplishments "
                    "to align with the requirements and keywords in the job description. "
                    "Here is the job description:\n\n"
                    f"{job_description}\n\n"
                )

            prompt_parts.append(
                "Here is the raw resume content:\n"
                f"{resume_content}\n\n"
                "The output MUST be a raw JSON object, with no markdown formatting (e.g., no ```json around it) or conversational filler."
            )
            prompt = "".join(prompt_parts)
            logger.debug("Gemini API prompt crafted successfully.")
            return prompt
        except Exception as e:
            logger.error(f"Error crafting Gemini API prompt: {e}", exc_info=True)
            raise

    def enhance_resume(self, resume_content: str, job_description: Optional[str] = None) -> str:
        """
        Sends resume content to the Gemini API for enhancement and returns the processed data as a JSON string.
        Optionally tailors the resume to a specific job description.

        Args:
            resume_content: The raw resume content as a string.
            job_description: Optional. The text of the job description to tailor the resume to.

        Returns:
            The enhanced resume data as a JSON string.

        Raises:
            Exception: If the Gemini API call fails or returns invalid JSON.
        """
        prompt = self._craft_prompt(resume_content, job_description)
        try:
            logger.info("Sending resume data to Gemini API for enhancement...")
            response = self.model.generate_content(prompt)
            enhanced_resume_str = response.text.strip()

            # Attempt to extract JSON from markdown if present
            if enhanced_resume_str.startswith("```json") and enhanced_resume_str.endswith("```"):
                enhanced_resume_str = enhanced_resume_str[7:-3].strip()
            elif enhanced_resume_str.startswith("```") and enhanced_resume_str.endswith("```"):
                # Catch cases where the language might be omitted, but it's still a code block
                enhanced_resume_str = enhanced_resume_str[3:-3].strip()

            # Validate if the response is valid JSON
            json.loads(enhanced_resume_str)
            logger.info("Successfully received and validated enhanced resume data from Gemini API.")
            return enhanced_resume_str
        except Exception as e:
            logger.error(f"Error calling Gemini API or parsing response: {e}", exc_info=True)
            raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Set your GEMINI_API_KEY environment variable before running this example
    # os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY"

    try:
        integrator = GeminiAPIIntegrator(
            model_name="gemini-1.5-flash-latest",
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192
        )

        sample_resume_content = """
        John Doe
        Software Engineer
        Summary: Software engineer with experience in Python.
        Experience: Tech Corp, Software Engineer, 2020-2023. Developed web applications.
        Education: University of Example, M.Sc. Computer Science, 2019.
        Skills: Python, JavaScript.
        """

        sample_job_description = "Looking for a software engineer with strong Python skills."

        logger.info("Sending resume data to Gemini API for enhancement (without job description)...")
        enhanced_data_no_jd_str = integrator.enhance_resume(sample_resume_content)
        logger.info("\nEnhanced Resume Data (without JD):")
        logger.info(enhanced_data_no_jd_str)

        logger.info("Sending resume data to Gemini API for enhancement (with job description)...")
        enhanced_data_with_jd_str = integrator.enhance_resume(sample_resume_content, job_description=sample_job_description)
        logger.info("\nEnhanced Resume Data (with JD):")
        logger.info(enhanced_data_with_jd_str)

    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.error(f"An error occurred during API call: {e}")