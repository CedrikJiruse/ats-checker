import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from gemini_integrator import GeminiAPIIntegrator
from input_handler import InputHandler
from output_generator import OutputGenerator
from scoring import compute_iteration_score, score_match, score_resume
from state_manager import StateManager

logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    best_resume_json: str
    best_score: float
    history: List[Dict[str, Any]]
    stopped_reason: str
    details: Dict[str, Any]


class ResumeProcessor:
    """
    Orchestrates the resume processing workflow.

    Enhancements in this version:
    - Multi-agent Gemini support (via GeminiAPIIntegrator agents config).
    - Scoring system (resume quality + resume↔job match) using `scoring.py`.
    - Iterative improvement option to revise a resume until a target score is reached.
    - TOML structured outputs (via OutputGenerator structured output format).
    """

    def __init__(
        self,
        input_folder: str,
        output_folder: str,
        model_name: str,
        temperature: float,
        top_p: float,
        top_k: int,
        max_output_tokens: int,
        num_versions_per_job: int,
        job_description_folder: Optional[str] = None,
        tesseract_cmd: Optional[str] = None,
        # New optional knobs (backward-compatible defaults)
        ai_agents: Optional[Dict[str, Dict[str, Any]]] = None,
        scoring_weights_file: str = "config/scoring_weights.toml",
        structured_output_format: str = "toml",
        iterate_until_score_reached: bool = False,
        target_score: float = 80.0,
        max_iterations: int = 3,
        min_score_delta: float = 0.1,
        state_filepath: Optional[str] = None,
    ):
        self.state_manager = StateManager(
            state_filepath or "data/processed_resumes_state.toml"
        )
        self.input_handler = InputHandler(
            self.state_manager,
            job_description_folder=job_description_folder,
            tesseract_cmd=tesseract_cmd,
        )

        self.gemini_integrator = GeminiAPIIntegrator(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            agents=ai_agents,
        )

        self.output_generator = OutputGenerator(
            output_folder=output_folder,
            structured_output_format=structured_output_format,
        )

        self.input_folder = input_folder
        self.output_folder = output_folder
        self.num_versions_per_job = int(num_versions_per_job)
        self.job_description_folder = job_description_folder

        # Scoring + iteration config
        self.scoring_weights_file = scoring_weights_file
        self.iterate_until_score_reached = bool(iterate_until_score_reached)
        self.target_score = float(target_score)
        self.max_iterations = int(max_iterations)
        self.min_score_delta = float(min_score_delta)

        logger.info(
            "ResumeProcessor initialized. input_folder=%s output_folder=%s versions=%s iterate=%s target=%s max_iter=%s",
            self.input_folder,
            self.output_folder,
            self.num_versions_per_job,
            self.iterate_until_score_reached,
            self.target_score,
            self.max_iterations,
        )

    # -------------------------
    # Public entry point
    # -------------------------

    def process_resumes(self, job_description_name: Optional[str] = None) -> None:
        """
        Orchestrates the resume processing workflow:
        1. Scans input folder for new/modified resumes.
        2. Enhances resumes via Gemini.
        3. Optionally iterates until a score threshold is reached.
        4. Writes outputs (TXT + structured JSON/TOML).
        5. Updates StateManager.

        Args:
            job_description_name: Optional name of a job description file found in the job description folder.
        """
        job_description_content = None
        job_title_for_filename = "generic"

        if job_description_name:
            job_descriptions = self.input_handler.get_job_descriptions()
            if job_description_name in job_descriptions:
                job_description_content = job_descriptions[job_description_name]
                job_title_for_filename = self._sanitize_job_title(job_description_name)
                logger.info(
                    "Using job description '%s' for resume tailoring.",
                    job_description_name,
                )
            else:
                logger.warning(
                    "Job description '%s' not found. Processing without tailoring.",
                    job_description_name,
                )
                job_title_for_filename = self._sanitize_job_title(job_description_name)

        logger.info(
            "Starting resume processing for input folder: %s", self.input_folder
        )
        resumes_to_process = self.input_handler.get_resumes_to_process(
            self.input_folder
        )

        if not resumes_to_process:
            logger.info("No new or modified resumes to process.")
            return

        logger.info(
            "Found %d new/modified resumes to process.", len(resumes_to_process)
        )

        for resume in resumes_to_process:
            filepath = resume["filepath"]
            content = resume["content"]
            file_hash = resume["hash"]

            logger.info("Processing resume: %s", filepath)

            last_structured_path: Optional[str] = None
            try:
                for version_idx in range(1, self.num_versions_per_job + 1):
                    logger.info(
                        "Enhancing resume '%s' (job=%s version=%d/%d)",
                        filepath,
                        job_description_name or "none",
                        version_idx,
                        self.num_versions_per_job,
                    )

                    enhanced_resume_json = self.gemini_integrator.enhance_resume(
                        content, job_description=job_description_content
                    )
                    logger.info(
                        "Resume '%s' enhanced by Gemini (version %d).",
                        filepath,
                        version_idx,
                    )

                    # Optional iterative improvement loop
                    if self.iterate_until_score_reached:
                        iter_result = self._iterate_until_target(
                            enhanced_resume_json=enhanced_resume_json,
                            job_description_name=job_description_name,
                            job_description_content=job_description_content,
                        )
                        enhanced_resume_json = iter_result.best_resume_json
                        logger.info(
                            "Iteration complete (version %d): best_score=%.2f stopped_reason=%s",
                            version_idx,
                            iter_result.best_score,
                            iter_result.stopped_reason,
                        )

                    # Compute scores, display them, and embed them into the resume JSON so they are
                    # written into the structured output and included in the TXT output.
                    iteration_score, score_details = self._score_for_iteration(
                        resume_json=enhanced_resume_json,
                        job_description_name=job_description_name,
                        job_description_content=job_description_content,
                    )

                    # Display scores (best-effort, avoids crashing on unexpected shapes)
                    try:
                        mode = (
                            score_details.get("mode")
                            if isinstance(score_details, dict)
                            else None
                        )
                        resume_total = None
                        match_total = None

                        if isinstance(score_details, dict) and isinstance(
                            score_details.get("resume_report"), dict
                        ):
                            resume_total = score_details["resume_report"].get("total")

                        if isinstance(score_details, dict) and isinstance(
                            score_details.get("match_report"), dict
                        ):
                            match_total = score_details["match_report"].get("total")

                        if mode == "resume_only":
                            logger.info(
                                "Scores (version %d): overall=%.2f resume=%s",
                                version_idx,
                                float(iteration_score),
                                resume_total,
                            )
                        else:
                            logger.info(
                                "Scores (version %d): overall=%.2f resume=%s match=%s",
                                version_idx,
                                float(iteration_score),
                                resume_total,
                                match_total,
                            )
                    except Exception:
                        logger.info(
                            "Scores (version %d): overall=%.2f",
                            version_idx,
                            float(iteration_score),
                        )

                    # Embed scoring into the JSON under `_scoring`
                    try:
                        resume_obj = json.loads(enhanced_resume_json)
                        if isinstance(resume_obj, dict):
                            resume_obj["_scoring"] = {
                                "iteration_score": float(iteration_score),
                                **(
                                    score_details
                                    if isinstance(score_details, dict)
                                    else {}
                                ),
                            }
                            enhanced_resume_json = json.dumps(
                                resume_obj, ensure_ascii=False, indent=2
                            )
                    except Exception as e:
                        logger.warning(
                            "Failed to embed scoring metadata into resume JSON: %s", e
                        )

                    # Structured output (TOML/JSON/BOTH depending on OutputGenerator config)
                    last_structured_path = (
                        self.output_generator.generate_structured_output(
                            enhanced_resume_json, filepath, job_title_for_filename
                        )
                    )
                    logger.info(
                        "Generated structured output for '%s' at: %s",
                        filepath,
                        last_structured_path,
                    )

                    # Human-readable text output
                    text_output_path = self.output_generator.generate_text_output(
                        enhanced_resume_json, filepath, job_title_for_filename
                    )
                    logger.info(
                        "Generated text output for '%s' at: %s",
                        filepath,
                        text_output_path,
                    )

                if last_structured_path:
                    self.state_manager.update_resume_state(
                        file_hash, last_structured_path
                    )
                    logger.info("State updated for '%s'.", filepath)
            except Exception as e:
                logger.error(
                    "Failed to process resume '%s': %s", filepath, e, exc_info=True
                )

    # -------------------------
    # Iteration + scoring
    # -------------------------

    def _iterate_until_target(
        self,
        enhanced_resume_json: str,
        job_description_name: Optional[str],
        job_description_content: Optional[str],
    ) -> IterationResult:
        """
        Iterate via Gemini reviser agent until target score is reached.

        If job_description_content is missing, iteration optimizes resume quality only.
        """
        history: List[Dict[str, Any]] = []

        best_json = enhanced_resume_json
        best_score, best_details = self._score_for_iteration(
            resume_json=best_json,
            job_description_name=job_description_name,
            job_description_content=job_description_content,
        )
        history.append({"iteration": 0, "score": best_score, "details": best_details})

        if best_score >= self.target_score:
            return IterationResult(
                best_resume_json=best_json,
                best_score=best_score,
                history=history,
                stopped_reason="target_reached",
                details={"initial": best_details},
            )

        stopped_reason = "max_iterations"
        for i in range(1, self.max_iterations + 1):
            candidate_json = self.gemini_integrator.revise_resume(
                enhanced_resume_json=best_json,
                job_description=job_description_content,
                goals=[
                    "Improve ATS keyword alignment without lying",
                    "Increase quantified impact where possible (keep truthful phrasing)",
                    "Keep formatting consistent and concise",
                ],
            )

            candidate_score, candidate_details = self._score_for_iteration(
                resume_json=candidate_json,
                job_description_name=job_description_name,
                job_description_content=job_description_content,
            )
            history.append(
                {"iteration": i, "score": candidate_score, "details": candidate_details}
            )

            delta = candidate_score - best_score
            improved = candidate_score > best_score

            if improved:
                best_json = candidate_json
                best_score = candidate_score
                best_details = candidate_details

            if best_score >= self.target_score:
                stopped_reason = "target_reached"
                break

            # Stop if we don't improve enough (prevents long flapping)
            if delta < self.min_score_delta:
                stopped_reason = "no_progress"
                break

        return IterationResult(
            best_resume_json=best_json,
            best_score=best_score,
            history=history,
            stopped_reason=stopped_reason,
            details={"best": best_details},
        )

    def _score_for_iteration(
        self,
        resume_json: str,
        job_description_name: Optional[str],
        job_description_content: Optional[str],
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Compute a single score used to drive iteration.

        - With a job description: combine resume quality + resume↔job match via `compute_iteration_score`.
        - Without a job description: use resume quality score only.
        """
        resume = json.loads(resume_json)
        if not isinstance(resume, dict):
            raise ValueError("Enhanced resume must be a JSON object")

        resume_report = score_resume(
            resume, weights_toml_path=self.scoring_weights_file
        )

        if not job_description_content:
            # No JD => optimize resume quality only
            return float(resume_report.total), {
                "mode": "resume_only",
                "resume_report": resume_report.as_dict(),
            }

        job = self._job_dict_from_description(
            job_description_name=job_description_name,
            job_description_content=job_description_content,
        )
        match_report = score_match(
            resume, job, weights_toml_path=self.scoring_weights_file
        )

        iteration_score, combine_details = compute_iteration_score(
            resume_report=resume_report,
            match_report=match_report,
            weights_toml_path=self.scoring_weights_file,
        )

        return float(iteration_score), {
            "mode": "resume_plus_match",
            "resume_report": resume_report.as_dict(),
            "match_report": match_report.as_dict(),
            "combined": combine_details,
        }

    # -------------------------
    # Helpers
    # -------------------------

    def _sanitize_job_title(self, job_description_name: str) -> str:
        """
        Convert a job description filename into a stable token for output filenames.
        """
        if not job_description_name:
            return "generic"
        name = job_description_name
        for ext in (".txt", ".md"):
            if name.lower().endswith(ext):
                name = name[: -len(ext)]
        name = name.strip().replace(" ", "_")
        # Keep filenames tame
        name = "".join(ch for ch in name if ch.isalnum() or ch in ("_", "-", "."))
        return name or "generic"

    def _job_dict_from_description(
        self,
        job_description_name: Optional[str],
        job_description_content: str,
    ) -> Dict[str, Any]:
        """
        Build a minimal job dict compatible with scoring functions from a raw job description.
        """
        title = self._sanitize_job_title(job_description_name or "job_description")
        return {
            "title": title,
            "company": "",
            "location": "",
            "description": job_description_content or "",
            "url": "",
            "source": "job_description",
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    # Example usage (requires GEMINI_API_KEY):
    # processor = ResumeProcessor(
    #     input_folder="input_resumes",
    #     output_folder="output",
    #     model_name="gemini-1.5-flash-latest",
    #     temperature=0.7,
    #     top_p=0.95,
    #     top_k=40,
    #     max_output_tokens=8192,
    #     num_versions_per_job=1,
    #     job_description_folder="job_descriptions",
    #     structured_output_format="toml",
    #     iterate_until_score_reached=True,
    #     target_score=80.0,
    #     max_iterations=3,
    # )
    # processor.process_resumes(job_description_name=None)
