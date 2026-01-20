import concurrent.futures
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from gemini_integrator import GeminiAPIIntegrator
from input_handler import InputHandler
from output_generator import OutputGenerator
from recommendations import generate_recommendations
from schema_validation import load_schema, validate_json_str
from scoring import compute_iteration_score, score_job, score_match, score_resume
from state_manager import StateManager

try:
    import toml_io  # project-local TOML writer (dependency-free)
except Exception:
    toml_io = None

logger = logging.getLogger(__name__)


def _sanitize_for_toml(value: Any) -> Any:
    """
    TOML does not support null/None or list-of-dicts with this project's minimal TOML writer.
    This helper:
    - drops None entries
    - converts dict keys to strings
    - drops list elements that are dicts (caller should pre-flatten if needed)
    """
    if value is None:
        return None

    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
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
            if isinstance(item, dict):
                # avoid list-of-dicts in TOML output
                logger.debug(
                    "Dropping dict from list during TOML sanitization: %s",
                    str(item)[:100],  # Limit log size
                )
                continue
            sv = _sanitize_for_toml(item)
            if sv is None:
                continue
            out_list.append(sv)
        return out_list

    return value


def _score_report_to_toml(report: Any) -> Dict[str, Any]:
    """
    Convert a scoring report (typically ScoreReport.as_dict()) into a TOML-friendly shape.

    Key idea:
    - Replace `categories: [ {name, score, ...}, ... ]` with:
        categories.<category_name>.score = ...
        categories.<category_name>.weight = ...
        categories.<category_name>.details = {...}

    This preserves detailed scoring in TOML outputs without using list-of-dicts.
    """
    if not isinstance(report, dict):
        return {}

    out: Dict[str, Any] = {}

    kind = report.get("kind")
    if isinstance(kind, str):
        out["kind"] = kind

    total = report.get("total")
    if isinstance(total, (int, float)):
        out["total"] = float(total)

    meta = report.get("meta")
    if isinstance(meta, dict):
        out["meta"] = _sanitize_for_toml(meta) or {}

    categories = report.get("categories")
    categories_tbl: Dict[str, Any] = {}
    if isinstance(categories, list):
        used_names = set()
        for idx, c in enumerate(categories):
            if not isinstance(c, dict):
                continue

            name = c.get("name")
            if not isinstance(name, str) or not name.strip():
                name = f"category_{idx}"

            base = name.strip()
            key = base
            suffix = 2
            while key in used_names:
                key = f"{base}_{suffix}"
                suffix += 1
            used_names.add(key)

            entry: Dict[str, Any] = {}

            score = c.get("score")
            if isinstance(score, (int, float)):
                entry["score"] = float(score)

            weight = c.get("weight")
            if isinstance(weight, (int, float)):
                entry["weight"] = float(weight)

            details = c.get("details")
            if isinstance(details, dict):
                entry["details"] = _sanitize_for_toml(details) or {}

            categories_tbl[key] = entry

    out["categories"] = categories_tbl
    return out


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
        # Iteration strategy controls (advanced)
        iteration_strategy: str = "best_of",
        iteration_patience: int = 2,
        stop_on_regression: bool = True,
        max_regressions: int = 2,
        # Performance
        max_concurrent_requests: int = 1,
        score_cache_enabled: bool = True,
        state_filepath: Optional[str] = None,
        # New: schema validation / recommendations / output layout
        schema_validation_enabled: bool = False,
        resume_schema_path: str = "",
        schema_validation_max_retries: int = 1,
        recommendations_enabled: bool = False,
        recommendations_max_items: int = 5,
        output_subdir_pattern: str = "{resume_name}/{job_title}/{timestamp}",
        # Output artifacts (TOML)
        write_score_summary_file: bool = True,
        score_summary_filename: str = "scores.toml",
        write_manifest_file: bool = True,
        manifest_filename: str = "manifest.toml",
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
            output_subdir_pattern=output_subdir_pattern,
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

        self.iteration_strategy = (iteration_strategy or "best_of").strip().lower()
        self.iteration_patience = max(0, int(iteration_patience))
        self.stop_on_regression = bool(stop_on_regression)
        self.max_regressions = max(0, int(max_regressions))

        # Schema validation / recommendations / output layout config
        self.schema_validation_enabled = bool(schema_validation_enabled)
        self.resume_schema_path = resume_schema_path or ""
        self.schema_validation_max_retries = int(schema_validation_max_retries)
        self.recommendations_enabled = bool(recommendations_enabled)
        self.recommendations_max_items = int(recommendations_max_items)

        # Performance
        self.max_concurrent_requests = max(1, int(max_concurrent_requests))
        self.score_cache_enabled = bool(score_cache_enabled)
        self._score_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

        # Output artifacts (TOML)
        self.write_score_summary_file = bool(write_score_summary_file)
        self.score_summary_filename = str(score_summary_filename or "scores.toml")
        self.write_manifest_file = bool(write_manifest_file)
        self.manifest_filename = str(manifest_filename or "manifest.toml")

        self._resume_schema: Optional[Dict[str, Any]] = None
        if self.schema_validation_enabled and self.resume_schema_path:
            try:
                self._resume_schema = load_schema(self.resume_schema_path)
            except Exception as e:
                logger.warning(
                    "Schema validation enabled but failed to load schema at '%s': %s",
                    self.resume_schema_path,
                    e,
                )
                self._resume_schema = None

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

        # Parallelize across resumes (AI calls are I/O bound) when configured.
        # Important: StateManager writes the full state file, so we only update state
        # on the main thread after workers finish to avoid concurrent file writes.
        def _process_one(resume_entry: Dict[str, Any]) -> Tuple[str, Optional[str]]:
            filepath = resume_entry["filepath"]
            content = resume_entry["content"]
            file_hash = resume_entry["hash"]

            logger.info("Processing resume: %s", filepath)

            # Use a dedicated OutputGenerator per worker to avoid shared "bundle timestamp" state.
            local_output_generator = OutputGenerator(
                output_folder=self.output_folder,
                structured_output_format=self.output_generator.structured_output_format,
                output_subdir_pattern=self.output_generator.output_subdir_pattern,
            )

            last_structured_path: Optional[str] = None
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

                # Optional schema validation (best-effort). If enabled and a schema is loaded,
                # validate and retry a limited number of times by asking the model to fix the schema.
                if self.schema_validation_enabled and self._resume_schema is not None:
                    attempts = 0
                    while True:
                        result = validate_json_str(
                            enhanced_resume_json,
                            self._resume_schema,
                            instance_name="enhanced_resume",
                            max_errors=20,
                        )
                        if result.ok:
                            break

                        attempts += 1
                        if attempts > max(0, self.schema_validation_max_retries):
                            raise ValueError(
                                "Enhanced resume failed schema validation:\n"
                                + (result.detail or "\n".join(result.errors))
                            )

                        logger.warning(
                            "Schema validation failed (attempt %d/%d). Asking model to correct schema. Summary=%s",
                            attempts,
                            self.schema_validation_max_retries,
                            result.summary,
                        )

                        enhanced_resume_json = self.gemini_integrator.revise_resume(
                            enhanced_resume_json=enhanced_resume_json,
                            job_description=job_description_content,
                            goals=[
                                "Fix the JSON schema to match the required structure exactly",
                                "Do not add markdown fences",
                                "Preserve all existing information; only restructure/normalize fields as needed",
                            ],
                        )

                # Optional iterative improvement loop
                iteration_result: Optional[IterationResult] = None
                if self.iterate_until_score_reached:
                    iteration_result = self._iterate_until_target(
                        enhanced_resume_json=enhanced_resume_json,
                        job_description_name=job_description_name,
                        job_description_content=job_description_content,
                    )
                    enhanced_resume_json = iteration_result.best_resume_json
                    logger.info(
                        "Iteration complete (version %d): best_score=%.2f stopped_reason=%s",
                        version_idx,
                        iteration_result.best_score,
                        iteration_result.stopped_reason,
                    )

                # Compute scores, display them, and embed TOML-friendly scoring into the resume JSON
                iteration_score, score_details = self._score_for_iteration(
                    resume_json=enhanced_resume_json,
                    job_description_name=job_description_name,
                    job_description_content=job_description_content,
                )

                # Display scores (best-effort)
                try:
                    mode = (
                        score_details.get("mode")
                        if isinstance(score_details, dict)
                        else None
                    )
                    resume_total = (
                        score_details.get("resume_total")
                        if isinstance(score_details, dict)
                        else None
                    )
                    match_total = (
                        score_details.get("match_total")
                        if isinstance(score_details, dict)
                        else None
                    )

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

                # Embed scoring (TOML-safe) into the resume JSON under `_scoring`
                scoring_blob: Dict[str, Any] = {
                    "iteration_score": float(iteration_score),
                }
                if isinstance(score_details, dict):
                    scoring_blob.update(score_details)

                # Optional heuristic recommendations (deterministic; no API calls)
                if self.recommendations_enabled:
                    try:
                        recs = generate_recommendations(
                            scoring_payload=scoring_blob,
                            max_items=self.recommendations_max_items,
                        )
                        scoring_blob["recommendations"] = recs
                    except Exception as e:
                        logger.warning("Failed to generate recommendations: %s", e)

                # Attach iteration metadata if we have it (TOML-safe)
                if iteration_result is not None:
                    scoring_blob["iteration"] = {
                        "stopped_reason": iteration_result.stopped_reason,
                        "best_score": float(iteration_result.best_score),
                    }

                try:
                    resume_obj = json.loads(enhanced_resume_json)
                    if isinstance(resume_obj, dict):
                        # Avoid TOML-incompatible structures (list-of-dicts) by keeping this minimal.
                        resume_obj["_scoring"] = _sanitize_for_toml(scoring_blob) or {
                            "iteration_score": float(iteration_score)
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
                    local_output_generator.generate_structured_output(
                        enhanced_resume_json, filepath, job_title_for_filename
                    )
                )
                logger.info(
                    "Generated structured output for '%s' at: %s",
                    filepath,
                    last_structured_path,
                )

                # Human-readable text output
                text_output_path = local_output_generator.generate_text_output(
                    enhanced_resume_json, filepath, job_title_for_filename
                )
                logger.info(
                    "Generated text output for '%s' at: %s",
                    filepath,
                    text_output_path,
                )

                out_dir = (
                    os.path.dirname(last_structured_path)
                    if last_structured_path
                    else None
                )

                # Score summary (TOML)
                score_summary_path: Optional[str] = None
                if self.write_score_summary_file and out_dir and toml_io is not None:
                    try:
                        score_summary_path = os.path.join(
                            out_dir, self.score_summary_filename
                        )
                        toml_io.dump(
                            _sanitize_for_toml(scoring_blob) or {}, score_summary_path
                        )
                        logger.info(
                            "Wrote score summary file for '%s' at: %s",
                            filepath,
                            score_summary_path,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to write score summary TOML for '%s': %s",
                            filepath,
                            e,
                        )

                # Manifest (TOML)
                if self.write_manifest_file and out_dir and toml_io is not None:
                    try:
                        manifest_path = os.path.join(out_dir, self.manifest_filename)
                        base = os.path.splitext(os.path.basename(filepath))[0]
                        manifest: Dict[str, Any] = {
                            "meta": {
                                "resume_filename": os.path.basename(filepath),
                                "resume_basename": base,
                                "job_description_name": job_description_name or "",
                                "job_title": job_title_for_filename,
                                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                                "version_index": int(version_idx),
                            },
                            "outputs": {
                                "structured_output_path": last_structured_path or "",
                                "text_output_path": text_output_path or "",
                                "score_summary_path": score_summary_path or "",
                            },
                            "scoring": _sanitize_for_toml(scoring_blob) or {},
                            "processing": {
                                "iterate_until_score_reached": bool(
                                    self.iterate_until_score_reached
                                ),
                                "target_score": float(self.target_score),
                                "max_iterations": int(self.max_iterations),
                                "min_score_delta": float(self.min_score_delta),
                                "iteration_strategy": str(self.iteration_strategy),
                                "iteration_patience": int(self.iteration_patience),
                                "stop_on_regression": bool(self.stop_on_regression),
                                "max_regressions": int(self.max_regressions),
                                "schema_validation_enabled": bool(
                                    self.schema_validation_enabled
                                ),
                                "recommendations_enabled": bool(
                                    self.recommendations_enabled
                                ),
                            },
                        }
                        toml_io.dump(_sanitize_for_toml(manifest) or {}, manifest_path)
                        logger.info(
                            "Wrote manifest file for '%s' at: %s",
                            filepath,
                            manifest_path,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to write manifest TOML for '%s': %s", filepath, e
                        )

            return file_hash, last_structured_path

        # Decide sequential vs parallel execution
        results: List[Tuple[str, Optional[str]]] = []

        if self.max_concurrent_requests <= 1 or len(resumes_to_process) <= 1:
            for resume in resumes_to_process:
                try:
                    results.append(_process_one(resume))
                except Exception as e:
                    logger.error(
                        "Failed to process resume '%s': %s",
                        resume.get("filepath"),
                        e,
                        exc_info=True,
                    )
                    # Even on failure, track the file_hash so we can mark it as attempted
                    file_hash = resume.get("hash")
                    if file_hash:
                        results.append((file_hash, None))
        else:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_concurrent_requests
            ) as executor:
                # Map futures to resume entries so we can track which resume failed
                future_to_resume = {
                    executor.submit(_process_one, r): r for r in resumes_to_process
                }
                for fut in concurrent.futures.as_completed(future_to_resume):
                    resume = future_to_resume[fut]
                    try:
                        results.append(fut.result())
                    except Exception as e:
                        logger.error(
                            "Failed to process resume '%s' in parallel worker: %s",
                            resume.get("filepath"),
                            e,
                            exc_info=True,
                        )
                        # Even on failure, track the file_hash so we can mark it as attempted
                        file_hash = resume.get("hash")
                        if file_hash:
                            results.append((file_hash, None))

        # Update StateManager sequentially (avoid concurrent state file writes)
        for file_hash, last_structured_path in results:
            if last_structured_path:
                try:
                    self.state_manager.update_resume_state(
                        file_hash, last_structured_path
                    )
                except Exception as e:
                    logger.error(
                        "Failed to update state for hash %s -> %s: %s",
                        file_hash,
                        last_structured_path,
                        e,
                        exc_info=True,
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

        # Iteration stop logic:
        # - best_of: keep the best candidate seen so far (default)
        # - first_hit: stop immediately when target_score is reached
        # - patience: stop when no improvement has occurred for N iterations
        # - optional: stop after too many regressions
        stopped_reason = "max_iterations"
        no_improve_streak = 0
        regression_count = 0
        previous_score = best_score

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

            # Regression tracking (relative to previous iteration score)
            if candidate_score < previous_score:
                regression_count += 1
            previous_score = candidate_score

            # Only treat as an improvement if it clears min_score_delta vs the current best
            improvement_amount = candidate_score - best_score
            improved_enough = improvement_amount >= self.min_score_delta

            if improved_enough:
                best_json = candidate_json
                best_score = candidate_score
                best_details = candidate_details
                no_improve_streak = 0
            else:
                no_improve_streak += 1

            # Stop conditions
            if best_score >= self.target_score:
                stopped_reason = "target_reached"
                if self.iteration_strategy == "first_hit":
                    break
                # For other strategies, once target is reached we can stop as well.
                break

            if self.stop_on_regression and regression_count >= self.max_regressions:
                stopped_reason = "regression"
                break

            if self.iteration_strategy == "patience" and self.iteration_patience > 0:
                if no_improve_streak >= self.iteration_patience:
                    stopped_reason = "no_progress"
                    break
            else:
                # Default behavior: stop on first insufficient improvement
                if improvement_amount < self.min_score_delta:
                    stopped_reason = "no_progress"
                    break

        return IterationResult(
            best_resume_json=best_json,
            best_score=best_score,
            history=history,
            stopped_reason=stopped_reason,
            details={
                "best": best_details,
                "iteration_strategy": self.iteration_strategy,
                "iteration_patience": self.iteration_patience,
                "stop_on_regression": self.stop_on_regression,
                "max_regressions": self.max_regressions,
                "regression_count": regression_count,
                "no_improve_streak": no_improve_streak,
            },
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
        # Score caching (performance): cache by hash of resume JSON + job description content.
        cache_key = None
        if self.score_cache_enabled:
            h = hashlib.sha256()
            h.update((resume_json or "").encode("utf-8", errors="ignore"))
            h.update(b"\n||JD||\n")
            h.update((job_description_content or "").encode("utf-8", errors="ignore"))
            cache_key = h.hexdigest()
            cached = self._score_cache.get(cache_key)
            if cached is not None:
                return cached

        resume = json.loads(resume_json)
        if not isinstance(resume, dict):
            raise ValueError("Enhanced resume must be a JSON object")

        resume_report = score_resume(
            resume, weights_toml_path=self.scoring_weights_file
        )

        if not job_description_content:
            # No JD => optimize resume quality only.
            # Include full resume report in TOML-friendly form (categories as tables).
            resume_report_toml = _score_report_to_toml(resume_report.as_dict())

            result = (
                float(resume_report.total),
                {
                    "mode": "resume_only",
                    "resume_total": float(resume_report.total),
                    "resume_report": resume_report_toml,
                },
            )
            if cache_key is not None:
                self._score_cache[cache_key] = result
            return result

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

        # Extract keyword samples for usability (TOML-friendly; lists of strings)
        matched_keywords: List[str] = []
        missing_keywords: List[str] = []
        try:
            mr = match_report.as_dict()
            cats = mr.get("categories")
            if isinstance(cats, list):
                for c in cats:
                    if not isinstance(c, dict):
                        continue
                    if c.get("name") != "keyword_overlap":
                        continue
                    details = c.get("details")
                    if isinstance(details, dict):
                        overlap = details.get("sample_overlap")
                        missing = details.get("sample_missing")
                        if isinstance(overlap, list):
                            matched_keywords = [
                                str(x) for x in overlap if isinstance(x, str)
                            ]
                        if isinstance(missing, list):
                            missing_keywords = [
                                str(x) for x in missing if isinstance(x, str)
                            ]
                    break
        except Exception:
            pass

        # Full reports in TOML-friendly form (categories as tables)
        resume_report_toml = _score_report_to_toml(resume_report.as_dict())
        match_report_toml = _score_report_to_toml(match_report.as_dict())

        # Job report is useful context, even though iteration_score combines resume+match.
        try:
            job_report = score_job(job, weights_toml_path=self.scoring_weights_file)
            job_report_toml = _score_report_to_toml(job_report.as_dict())
            job_total = float(job_report.total)
        except Exception:
            job_report_toml = {}
            job_total = None

        result = (
            float(iteration_score),
            {
                "mode": "resume_plus_match",
                "resume_total": float(resume_report.total),
                "match_total": float(match_report.total),
                "job_total": job_total,
                "resume_report": resume_report_toml,
                "match_report": match_report_toml,
                "job_report": job_report_toml,
                "combined": _sanitize_for_toml(combine_details) or {},
                "keywords": {
                    "matched": matched_keywords[:20],
                    "missing": missing_keywords[:20],
                },
            },
        )

        if cache_key is not None:
            self._score_cache[cache_key] = result

        return result

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
