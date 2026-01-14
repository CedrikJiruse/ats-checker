import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import toml_io  # project-local TOML writer (dependency-free)
except Exception:
    toml_io = None


def _sanitize_for_toml(value: Any) -> Any:
    """
    TOML does not support null/None. This helper recursively removes None values from
    dicts/lists before writing TOML.
    - dict: drops keys where value is None (after sanitization)
    - list: drops None items (after sanitization)
    - other scalars: returned as-is
    """
    if value is None:
        return None

    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            # TOML keys must be strings in our writer; skip non-string keys
            if not isinstance(k, str):
                continue
            sv = _sanitize_for_toml(v)
            if sv is None:
                continue
            out[k] = sv
        return out

    if isinstance(value, list):
        out_list: List[Any] = []
        for item in value:
            sv = _sanitize_for_toml(item)
            if sv is None:
                continue
            out_list.append(sv)
        return out_list

    return value


class OutputGenerator:
    def __init__(
        self,
        output_folder: str = "output",
        structured_output_format: str = "json",
        output_subdir_pattern: str = "{resume_name}/{job_title}/{timestamp}",
    ):
        """
        Args:
            output_folder: Where to write output files.
            structured_output_format: "json" (default), "toml", or "both".
                - "toml": write TOML first, fallback to JSON if TOML writing fails
                - "both": write both TOML and JSON (returns TOML path)
            output_subdir_pattern: Relative subdirectory pattern under output_folder.
                Supported placeholders:
                  - {resume_name}: resume filename without extension
                  - {job_title}: job title token passed in by caller
                  - {timestamp}: shared timestamp for a bundle of outputs
        """
        self.output_folder = os.path.abspath(output_folder)
        os.makedirs(self.output_folder, exist_ok=True)

        # Test writability of output folder
        try:
            test_file = os.path.join(self.output_folder, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            raise RuntimeError(
                f"Cannot write to output folder {self.output_folder}: {e}"
            ) from e

        self.structured_output_format = (structured_output_format or "json").lower()
        self.output_subdir_pattern = (
            output_subdir_pattern or "{resume_name}/{job_title}/{timestamp}"
        )

        # Bundle context for sharing timestamps across sequential outputs
        # (e.g., structured output then text output) without changing call sites.
        self._bundle_key: Optional[str] = None
        self._bundle_timestamp: Optional[str] = None

        logger.info(
            f"OutputGenerator initialized with output folder: {self.output_folder}"
        )

    def _now_timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _sanitize_path_segment(self, segment: str) -> str:
        # Keep it Windows-safe and filesystem-safe.
        # Replace reserved chars: <>:"/\|?*
        # Also prevent directory traversal
        seg_str = str(segment or "").strip()

        # Block directory traversal attempts
        if seg_str in (".", ".."):
            return "unknown"
        if ".." in seg_str:
            # Replace .. with underscores to prevent traversal
            seg_str = seg_str.replace("..", "__")

        bad = '<>:"/\\|?*'
        out = []
        for ch in seg_str:
            out.append("_" if ch in bad else ch)
        s = "".join(out).strip()
        return s or "unknown"

    def _format_output_subdir(
        self, resume_filename: str, job_title: str, timestamp: str
    ) -> str:
        resume_name = os.path.splitext(os.path.basename(resume_filename))[0]
        values = {
            "resume_name": self._sanitize_path_segment(resume_name),
            "job_title": self._sanitize_path_segment(job_title),
            "timestamp": self._sanitize_path_segment(timestamp),
        }

        try:
            rel = self.output_subdir_pattern.format(**values)
        except Exception:
            rel = "{resume_name}/{job_title}/{timestamp}".format(**values)

        # Normalize separators and sanitize each segment
        rel = rel.replace("\\", "/")
        parts = [p for p in rel.split("/") if p and p.strip()]
        safe_parts = [self._sanitize_path_segment(p) for p in parts]
        return os.path.join(*safe_parts) if safe_parts else values["timestamp"]

    def _bundle_key_for(self, resume_filename: str, job_title: str) -> str:
        return f"{os.path.abspath(resume_filename)}|{job_title}"

    def _get_or_begin_bundle_timestamp(
        self,
        resume_filename: str,
        job_title: str,
        timestamp: Optional[str] = None,
    ) -> str:
        if timestamp:
            self._bundle_key = self._bundle_key_for(resume_filename, job_title)
            self._bundle_timestamp = timestamp
            return timestamp

        key = self._bundle_key_for(resume_filename, job_title)
        if self._bundle_key == key and self._bundle_timestamp:
            return self._bundle_timestamp

        ts = self._now_timestamp()
        self._bundle_key = key
        self._bundle_timestamp = ts
        return ts

    def _resolve_output_dir(
        self, resume_filename: str, job_title: str, timestamp: str
    ) -> str:
        rel = self._format_output_subdir(resume_filename, job_title, timestamp)
        out_dir = os.path.join(self.output_folder, rel)
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

    def generate_text_output(
        self,
        resume_data_str: str,
        resume_filename: str,
        job_title: str,
        timestamp: Optional[str] = None,
    ) -> str:
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

        ts = self._get_or_begin_bundle_timestamp(resume_filename, job_title, timestamp)
        output_dir = self._resolve_output_dir(resume_filename, job_title, ts)
        filepath = os.path.join(output_dir, output_filename)

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

                # Keyword Match Highlighting (optional)
                # If match scoring details exist, surface matched/missing keywords to make the TXT output actionable.
                scoring = resume_data.get("_scoring") or resume_data.get("scoring")
                if isinstance(scoring, dict):
                    match_rep = None
                    for candidate_key in ("match_report", "match"):
                        candidate = scoring.get(candidate_key)
                        if isinstance(candidate, dict):
                            match_rep = candidate
                            break

                    if isinstance(match_rep, dict):
                        categories = match_rep.get("categories")
                        kw_details = None

                        if isinstance(categories, list):
                            # Legacy format: list of category dicts
                            for cat in categories:
                                if not isinstance(cat, dict):
                                    continue
                                if cat.get("name") == "keyword_overlap":
                                    details = cat.get("details")
                                    if isinstance(details, dict):
                                        kw_details = details
                                    break
                        elif isinstance(categories, dict):
                            # TOML-friendly format: categories keyed by name
                            ko = categories.get("keyword_overlap")
                            if isinstance(ko, dict):
                                details = ko.get("details")
                                if isinstance(details, dict):
                                    kw_details = details

                        if isinstance(kw_details, dict):
                            missing = kw_details.get("sample_missing")
                            overlap = kw_details.get("sample_overlap")

                            has_overlap = (
                                isinstance(overlap, list) and len(overlap) > 0
                            )
                            has_missing = (
                                isinstance(missing, list) and len(missing) > 0
                            )

                            if has_overlap or has_missing:
                                f.write("Keyword Match:\n")
                                if has_overlap:
                                    f.write(
                                        f"  Matched: {', '.join(str(x) for x in overlap[:20])}\n"
                                    )
                                if has_missing:
                                    f.write(
                                        f"  Missing: {', '.join(str(x) for x in missing[:20])}\n"
                                    )
                                f.write("\n")

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

                # Scores (optional)
                scoring = resume_data.get("_scoring") or resume_data.get("scoring")
                if isinstance(scoring, dict):
                    f.write("Scores:\n")

                    overall = (
                        scoring.get("iteration_score")
                        or scoring.get("overall")
                        or scoring.get("total")
                    )
                    if overall is not None:
                        f.write(f"  Overall: {overall}\n")

                    # Support both:
                    # - scoring.resume / scoring.match / scoring.job
                    # - scoring.resume_report / scoring.match_report / scoring.job_report
                    key_candidates = {
                        "resume": ["resume", "resume_report"],
                        "match": ["match", "match_report"],
                        "job": ["job", "job_report"],
                    }

                    for key, label in [
                        ("resume", "Resume"),
                        ("match", "Match"),
                        ("job", "Job"),
                    ]:
                        rep = None
                        for candidate_key in key_candidates.get(key, [key]):
                            candidate = scoring.get(candidate_key)
                            if isinstance(candidate, dict):
                                rep = candidate
                                break

                        if not isinstance(rep, dict):
                            continue

                        total = (
                            rep.get("total")
                            if rep.get("total") is not None
                            else rep.get("score")
                        )
                        if total is not None:
                            f.write(f"  {label}: {total}\n")

                        cats = rep.get("categories")
                        if isinstance(cats, list):
                            # Legacy format: categories as a list of dicts
                            for c in cats:
                                if not isinstance(c, dict):
                                    continue
                                n = c.get("name")
                                s = c.get("score")
                                w = c.get("weight")
                                if n is None or s is None:
                                    continue
                                if w is not None:
                                    f.write(f"    - {n}: {s} (weight {w})\n")
                                else:
                                    f.write(f"    - {n}: {s}\n")
                        elif isinstance(cats, dict):
                            # TOML-friendly format: categories as a table/dict keyed by category name
                            for n, c in cats.items():
                                if not isinstance(n, str) or not isinstance(c, dict):
                                    continue
                                s = c.get("score")
                                w = c.get("weight")
                                if s is None:
                                    continue
                                if w is not None:
                                    f.write(f"    - {n}: {s} (weight {w})\n")
                                else:
                                    f.write(f"    - {n}: {s}\n")

                    f.write("\n")

            logger.info(f"Successfully generated text file: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Error writing text file {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during text generation for {output_filename}: {e}",
                exc_info=True,
            )
            raise

    def generate_json_output(
        self,
        resume_data_str: str,
        resume_filename: str,
        job_title: str,
        timestamp: Optional[str] = None,
    ) -> str:
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

        ts = self._get_or_begin_bundle_timestamp(resume_filename, job_title, timestamp)
        output_dir = self._resolve_output_dir(resume_filename, job_title, ts)
        filepath = os.path.join(output_dir, output_filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(resume_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Successfully generated JSON file: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Error writing JSON file {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during JSON generation for {output_filename}: {e}",
                exc_info=True,
            )
            raise

    def generate_toml_output(
        self,
        resume_data_str: str,
        resume_filename: str,
        job_title: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Generates a TOML file from a JSON string of structured resume data.

        Args:
            resume_data_str: A JSON string containing the structured resume information.
            resume_filename: The original filename of the resume (e.g., "my_resume.txt").
            job_title: The title of the job the resume is tailored for (e.g., "Software_Engineer").

        Returns:
            The full path to the generated TOML file.

        Raises:
            IOError: If there's an error writing the TOML file.
            json.JSONDecodeError: If resume_data_str is not a valid JSON string.
            RuntimeError: If TOML writing support isn't available.
        """
        try:
            resume_data = json.loads(resume_data_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding resume data string for TOML generation: {e}")
            raise

        base_name = os.path.splitext(os.path.basename(resume_filename))
        output_filename = f"{base_name[0]}_{job_title}_enhanced.toml"

        ts = self._get_or_begin_bundle_timestamp(resume_filename, job_title, timestamp)
        output_dir = self._resolve_output_dir(resume_filename, job_title, ts)
        filepath = os.path.join(output_dir, output_filename)

        if toml_io is None:
            raise RuntimeError(
                "TOML output requested but TOML writer is unavailable (toml_io import failed)."
            )

        try:
            sanitized_resume_data = _sanitize_for_toml(resume_data)
            # In case the entire document becomes empty (rare), write an empty table instead of failing.
            if sanitized_resume_data is None:
                sanitized_resume_data = {}
            toml_io.dump(sanitized_resume_data, filepath)
            logger.info(f"Successfully generated TOML file: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Error writing TOML file {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during TOML generation for {output_filename}: {e}",
                exc_info=True,
            )
            raise

    def generate_structured_output(
        self,
        resume_data_str: str,
        resume_filename: str,
        job_title: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Generate structured output based on `self.structured_output_format`.

        - "json": JSON only (backward compatible)
        - "toml": TOML first, fallback to JSON
        - "both": write both TOML and JSON (returns TOML path)

        Returns:
            Path to the primary structured output.
        """
        fmt = (self.structured_output_format or "json").lower()

        # Begin/continue a bundle so subsequent outputs (e.g. TXT) share the same timestamp.
        ts = self._get_or_begin_bundle_timestamp(resume_filename, job_title, timestamp)

        # Best-effort: embed a shared timestamp into the structured resume under `_meta.timestamp`
        # so it is preserved inside TOML/JSON as well.
        try:
            obj = json.loads(resume_data_str)
            if isinstance(obj, dict):
                meta = obj.get("_meta")
                if not isinstance(meta, dict):
                    meta = {}
                if not meta.get("timestamp"):
                    meta["timestamp"] = ts
                if not meta.get("job_title"):
                    meta["job_title"] = job_title
                if not meta.get("source_resume"):
                    meta["source_resume"] = os.path.basename(resume_filename)
                obj["_meta"] = meta
                resume_data_str = json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            # If parsing fails, downstream generators will raise as before.
            pass

        if fmt == "json":
            return self.generate_json_output(
                resume_data_str, resume_filename, job_title, timestamp=ts
            )

        if fmt == "toml":
            try:
                return self.generate_toml_output(
                    resume_data_str, resume_filename, job_title, timestamp=ts
                )
            except Exception as e:
                logger.warning(f"TOML generation failed, falling back to JSON: {e}")
                return self.generate_json_output(
                    resume_data_str, resume_filename, job_title, timestamp=ts
                )

        if fmt == "both":
            toml_path = self.generate_toml_output(
                resume_data_str, resume_filename, job_title, timestamp=ts
            )
            # Always attempt JSON as well; if it fails, TOML is still returned.
            try:
                self.generate_json_output(
                    resume_data_str, resume_filename, job_title, timestamp=ts
                )
            except Exception as e:
                logger.warning(f"JSON generation failed after TOML succeeded: {e}")
            return toml_path

        # Unknown format -> default to JSON
        logger.warning(f"Unknown structured_output_format '{fmt}', defaulting to JSON")
        return self.generate_json_output(resume_data_str, resume_filename, job_title)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
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
    output_txt_path = output_gen.generate_text_output(
        sample_resume_data_str, "Alice_Wonderland_Resume.txt", "Software_Engineer"
    )
    logger.info(f"Generated TXT: {output_txt_path}")

    # Clean up test output folder
    # os.remove(output_txt_path)
    # os.rmdir(output_gen.output_folder)
