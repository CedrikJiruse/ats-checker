import os
import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OutputGenerator:
    def __init__(self, output_folder: str = "output"):
        self.output_folder = os.path.abspath(output_folder)
        os.makedirs(self.output_folder, exist_ok=True)
        logger.info(f"OutputGenerator initialized with output folder: {self.output_folder}")

    def generate_text_output(self, resume_data_str: str, resume_filename: str, job_title: str) -> str:
        """
        Generates a text file from a JSON string of structured resume data.

        Args:
            resume_data_str: A JSON string containing the structured resume information.
            resume_filename: The original filename of the resume (e.g., "my_resume.txt").
            job_title: The title of the job the resume is tailored for (e.g., "Software_Engineer").

        Returns:
            The full path to the generated text file.

        Raises:
            IOError: If there's an error writing the text file.
            json.JSONDecodeError: If resume_data_str is not a valid JSON string.
            Exception: For other unexpected errors during text generation.
        """
        try:
            resume_data = json.loads(resume_data_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding resume data string for text generation: {e}")
            raise

        base_name = os.path.splitext(os.path.basename(resume_filename))
        output_filename = f"{base_name[0]}_{job_title}_enhanced.txt"
        filepath = os.path.join(self.output_folder, output_filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                # Personal Information
                personal_info = resume_data.get("personal_info", {})
                name = personal_info.get("name", "N/A")
                email = personal_info.get("email", "N/A")
                phone = personal_info.get("phone", "N/A")
                linkedin = personal_info.get("linkedin", "")
                github = personal_info.get("github", "")
                portfolio = personal_info.get("portfolio", "")

                f.write(f"Name: {name}\n")
                f.write(f"Email: {email}\n")
                if phone != "N/A":
                    f.write(f"Phone: {phone}\n")
                if linkedin:
                    f.write(f"LinkedIn: {linkedin}\n")
                if github:
                    f.write(f"GitHub: {github}\n")
                if portfolio:
                    f.write(f"Portfolio: {portfolio}\n")
                f.write("\n")

                # Summary
                summary = resume_data.get("summary")
                if summary:
                    f.write("Summary:\n")
                    f.write(f"{summary}\n\n")

                # Experience
                experience = resume_data.get("experience", [])
                if experience:
                    f.write("Experience:\n")
                    for job in experience:
                        title = job.get("title", "N/A")
                        company = job.get("company", "N/A")
                        location = job.get("location", "")
                        start_date = job.get("start_date", "")
                        end_date = job.get("end_date", "Present")
                        description = job.get("description", [])

                        f.write(f"  {title} - {company}\n")
                        date_location_info = f"{start_date} - {end_date}"
                        if location:
                            date_location_info += f" | {location}"
                        f.write(f"  {date_location_info}\n")
                        for desc_item in description:
                            f.write(f"    • {desc_item}\n")
                        f.write("\n")
                f.write("\n")

                # Education
                education = resume_data.get("education", [])
                if education:
                    f.write("Education:\n")
                    for edu in education:
                        degree = edu.get("degree", "N/A")
                        institution = edu.get("institution", "N/A")
                        location = edu.get("location", "")
                        graduation_date = edu.get("graduation_date", "")
                        gpa = edu.get("gpa", "")

                        f.write(f"  {degree}\n")
                        f.write(f"  {institution}, {location}\n")
                        edu_info = f"Graduation: {graduation_date}"
                        if gpa:
                            edu_info += f" | GPA: {gpa}"
                        f.write(f"  {edu_info}\n")
                        f.write("\n")
                f.write("\n")

                # Skills
                skills = resume_data.get("skills", [])
                if skills:
                    f.write("Skills:\n")
                    f.write(f"{', '.join(skills)}\n\n")

                # Projects
                projects = resume_data.get("projects", [])
                if projects:
                    f.write("Projects:\n")
                    for project in projects:
                        name = project.get("name", "N/A")
                        description = project.get("description", "N/A")
                        link = project.get("link", "")

                        f.write(f"  {name}\n")
                        f.write(f"  {description}\n")
                        if link:
                            f.write(f"  Link: {link}\n")
                        f.write("\n")
                f.write("\n")

            logger.info(f"Successfully generated text file: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Error writing text file {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during text generation for {output_filename}: {e}", exc_info=True)
            raise

    def generate_json_output(self, resume_data_str: str, resume_filename: str, job_title: str) -> str:
        """
        Generates a JSON file from a JSON string of structured resume data.

        Args:
            resume_data_str: A JSON string containing the structured resume information.
            resume_filename: The original filename of the resume (e.g., "my_resume.txt").
            job_title: The title of the job the resume is tailored for (e.g., "Software_Engineer").

        Returns:
            The full path to the generated JSON file.

        Raises:
            IOError: If there's an error writing the JSON file.
            json.JSONDecodeError: If resume_data_str is not a valid JSON string.
            Exception: For other unexpected errors during JSON generation.
        """
        try:
            resume_data = json.loads(resume_data_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding resume data string for JSON generation: {e}")
            raise

        base_name = os.path.splitext(os.path.basename(resume_filename))
        output_filename = f"{base_name[0]}_{job_title}_enhanced.json"
        filepath = os.path.join(self.output_folder, output_filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(resume_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully generated JSON file: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Error writing JSON file {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during JSON generation for {output_filename}: {e}", exc_info=True)
            raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Example usage:
    output_gen = OutputGenerator()

    sample_resume_data_str = """
    {
        "personal_info": {
            "name": "Alice Wonderland",
            "email": "alice.w@example.com",
            "phone": "987-654-3210",
            "linkedin": "https://linkedin.com/in/alicew",
            "github": "https://github.com/alicew"
        },
        "summary": "Highly motivated and detail-oriented software developer with 5+ years of experience in full-stack development and a strong background in machine learning.",
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Innovate Solutions",
                "location": "New York, NY",
                "start_date": "2022-03-01",
                "end_date": "Present",
                "description": [
                    "Led development of a new microservices architecture, improving system scalability by 40%.",
                    "Mentored junior developers and conducted code reviews.",
                    "Implemented CI/CD pipelines using Jenkins and Docker."
                ]
            },
            {
                "title": "Software Developer",
                "company": "Tech Innovations",
                "location": "Boston, MA",
                "start_date": "2019-06-01",
                "end_date": "2022-02-28",
                "description": [
                    "Developed and maintained RESTful APIs using Python and Flask.",
                    "Contributed to front-end development using React and Redux.",
                    "Participated in agile development sprints."
                ]
            }
        ],
        "education": [
            {
                "degree": "M.Sc. Computer Science",
                "institution": "MIT",
                "location": "Cambridge, MA",
                "graduation_date": "2019-05-01",
                "gpa": "3.9/4.0"
            },
            {
                "degree": "B.Sc. Software Engineering",
                "institution": "University of Example",
                "location": "Example City, EX",
                "graduation_date": "2017-05-01"
            }
        ],
        "skills": ["Python", "Java", "React", "Docker", "Kubernetes", "AWS", "Machine Learning", "SQL", "NoSQL"],
        "projects": [
            {
                "name": "AI Chatbot",
                "description": "Developed a conversational AI chatbot using natural language processing.",
                "link": "https://github.com/alicew/chatbot"
            },
            {
                "name": "E-commerce Platform",
                "description": "Built a full-stack e-commerce platform with user authentication and payment gateway integration.",
                "link": "https://github.com/alicew/ecommerce"
            }
        ]
    }
    """
    output_txt_path = output_gen.generate_text_output(sample_resume_data_str, "Alice_Wonderland_Resume.txt", "Software_Engineer")
    logger.info(f"Generated TXT: {output_txt_path}")

    # Clean up test output folder
    # os.remove(output_txt_path)
    # os.rmdir(output_gen.output_folder)