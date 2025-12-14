import json  # Keep json for parsing Gemini's response
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiAPIIntegrator:
    def __init__(
        self,
        model_name: str = "gemini-pro",
        temperature: float = 0.7,
        top_p: float = 0.95,
        top_k: int = 40,
        max_output_tokens: int = 8192,
        agents: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """
        Gemini API integrator with lightweight multi-agent support.

        Agents are separate model instances that can use different Gemini models
        and/or generation configs. This enables:
        - `enhancer`: default resume enhancement (backward-compatible with `self.model`)
        - `job_summarizer`: job description summarization
        - `reviser`: iterative resume revision based on feedback/score

        Args:
            model_name: Default Gemini model name.
            temperature/top_p/top_k/max_output_tokens: Default generation config.
            agents: Optional dict like:
                {
                    "enhancer": {"provider": "gemini", "model_name": "...", "temperature": 0.7, ...},
                    "job_summarizer": {...},
                    "reviser": {...},
                }
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error(
                "GEMINI_API_KEY not found. Please set it as an environment variable."
            )
            raise ValueError(
                "GEMINI_API_KEY not found. Please set it as an environment variable."
            )
        genai.configure(api_key=api_key)

        self._default_model_name = model_name
        self._default_generation_kwargs = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
        }

        # Default agent definitions (can be overridden by `agents`)
        default_agents: Dict[str, Dict[str, Any]] = {
            "enhancer": {"provider": "gemini", "model_name": model_name},
            "job_summarizer": {"provider": "gemini", "model_name": model_name},
            "reviser": {"provider": "gemini", "model_name": model_name},
        }
        if isinstance(agents, dict):
            for name, cfg in agents.items():
                if isinstance(name, str) and isinstance(cfg, dict):
                    merged = dict(default_agents.get(name, {}))
                    merged.update(cfg)
                    default_agents[name] = merged

        self.agents = default_agents
        self._models: Dict[str, Any] = {}

        # Build models per agent (Gemini only)
        for agent_name, cfg in self.agents.items():
            if not isinstance(cfg, dict):
                continue
            provider = str(cfg.get("provider", "gemini")).lower()
            if provider != "gemini":
                continue

            agent_model_name = str(cfg.get("model_name") or model_name)
            gen_kwargs = dict(self._default_generation_kwargs)
            # Optional per-agent overrides
            for k in ("temperature", "top_p", "top_k", "max_output_tokens"):
                if k in cfg and cfg[k] is not None:
                    gen_kwargs[k] = cfg[k]

            self._models[agent_name] = genai.GenerativeModel(
                model_name=agent_model_name,
                generation_config=genai.GenerationConfig(**gen_kwargs),
            )

        # Backward compatibility: `self.model` remains the default enhancement model
        self.model = self._models.get("enhancer") or genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(**self._default_generation_kwargs),
        )

        logger.info(
            "GeminiAPIIntegrator initialized. default_model=%s agents=%s",
            model_name,
            sorted(list(self._models.keys())),
        )

    def _craft_prompt(
        self, resume_content: str, job_description: Optional[str] = None
    ) -> str:
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

    def enhance_resume(
        self, resume_content: str, job_description: Optional[str] = None
    ) -> str:
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
            response = self._get_agent_model("enhancer").generate_content(prompt)
            enhanced_resume_str = response.text.strip()

            # Attempt to extract JSON from markdown if present
            if enhanced_resume_str.startswith(
                "```json"
            ) and enhanced_resume_str.endswith("```"):
                enhanced_resume_str = enhanced_resume_str[7:-3].strip()
            elif enhanced_resume_str.startswith("```") and enhanced_resume_str.endswith(
                "```"
            ):
                # Catch cases where the language might be omitted, but it's still a code block
                enhanced_resume_str = enhanced_resume_str[3:-3].strip()

            # Validate if the response is valid JSON
            json.loads(enhanced_resume_str)
            logger.info(
                "Successfully received and validated enhanced resume data from Gemini API."
            )
            return enhanced_resume_str
        except Exception as e:
            logger.error(
                f"Error calling Gemini API or parsing response: {e}", exc_info=True
            )
            raise

    def _get_agent_model(self, agent_name: str):
        """
        Return the model instance for a given agent name.
        Falls back to `self.model` for unknown/missing agents.
        """
        return self._models.get(agent_name) or self.model

    def _craft_job_summary_prompt(self, job_description: str) -> str:
        """
        Create a prompt that produces a compact, actionable job summary.
        Output is plain text (not JSON) to keep it easy to read in the CLI.
        """
        prompt = (
            "You are an expert technical recruiter.\n"
            "Summarize the following job description in a compact, actionable way.\n\n"
            "Return ONLY plain text with the following sections:\n"
            "1) One-line role summary\n"
            "2) Top responsibilities (5 bullets)\n"
            "3) Must-have requirements (5 bullets)\n"
            "4) Nice-to-haves (3 bullets)\n"
            "5) Keywords to mirror in a resume (comma-separated)\n\n"
            "Job description:\n"
            f"{job_description}\n"
        )
        return prompt

    def summarize_job_description(self, job_description: str) -> str:
        """
        Summarize a job description using the `job_summarizer` agent.
        """
        prompt = self._craft_job_summary_prompt(job_description)
        try:
            logger.info("Sending job description to Gemini for summarization...")
            response = self._get_agent_model("job_summarizer").generate_content(prompt)
            return (response.text or "").strip()
        except Exception as e:
            logger.error(
                f"Error calling Gemini API for job summarization: {e}", exc_info=True
            )
            raise

    def _craft_revision_prompt(
        self,
        enhanced_resume_json: str,
        job_description: Optional[str] = None,
        goals: Optional[List[str]] = None,
    ) -> str:
        """
        Create a prompt for iterative revision.
        The model is required to output a raw JSON object only.
        """
        goals = goals or [
            "Improve ATS keyword alignment without lying",
            "Increase quantified impact where possible (keep truthful phrasing)",
            "Keep formatting consistent and concise",
        ]

        parts = [
            "You are an expert ATS resume editor.\n"
            "You will be given a JSON resume. Revise it to be stronger.\n"
            "Rules:\n"
            "- Do NOT fabricate employers, dates, degrees, or certifications.\n"
            "- You may rephrase and improve clarity/impact.\n"
            "- Keep the same JSON schema as the input.\n"
            "- Output MUST be a raw JSON object only (no markdown fences).\n\n"
            "Goals:\n"
        ]
        for g in goals:
            parts.append(f"- {g}\n")

        if job_description:
            parts.append("\nJob description to tailor to:\n")
            parts.append(f"{job_description}\n")

        parts.append("\nCurrent resume JSON:\n")
        parts.append(f"{enhanced_resume_json}\n")

        return "".join(parts)

    def revise_resume(
        self,
        enhanced_resume_json: str,
        job_description: Optional[str] = None,
        goals: Optional[List[str]] = None,
    ) -> str:
        """
        Revise an already-structured resume JSON using the `reviser` agent.
        Returns a JSON string (validated).
        """
        # Validate the input is JSON so the model gets clean structure
        json.loads(enhanced_resume_json)

        prompt = self._craft_revision_prompt(
            enhanced_resume_json=enhanced_resume_json,
            job_description=job_description,
            goals=goals,
        )
        try:
            logger.info("Sending resume JSON to Gemini for revision...")
            response = self._get_agent_model("reviser").generate_content(prompt)
            revised = (response.text or "").strip()

            # Strip markdown code fences if the model adds them
            if revised.startswith("```json") and revised.endswith("```"):
                revised = revised[7:-3].strip()
            elif revised.startswith("```") and revised.endswith("```"):
                revised = revised[3:-3].strip()

            json.loads(revised)
            return revised
        except Exception as e:
            logger.error(
                f"Error calling Gemini API for resume revision: {e}", exc_info=True
            )
            raise

    def revise_resume_until_score_reached(
        self,
        enhanced_resume_json: str,
        score_fn: Callable[[str], float],
        job_description: Optional[str] = None,
        target_score: float = 80.0,
        max_iterations: int = 3,
        min_score_delta: float = 0.1,
        goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Iteratively revise a resume until `target_score` is reached.

        This function is scorer-agnostic: you provide `score_fn` that takes a JSON
        string and returns a numeric score (higher is better).

        Returns:
            {
              "best_resume_json": "...",
              "best_score": 84.2,
              "history": [
                 {"iteration": 0, "score": 72.0},
                 {"iteration": 1, "score": 78.1},
                 ...
              ],
              "stopped_reason": "target_reached" | "max_iterations" | "no_progress"
            }
        """
        if not callable(score_fn):
            raise ValueError(
                "score_fn must be callable and accept (resume_json_str) -> float"
            )

        # Validate JSON early
        json.loads(enhanced_resume_json)

        history: List[Dict[str, Any]] = []

        best_json = enhanced_resume_json
        best_score = float(score_fn(best_json))
        history.append({"iteration": 0, "score": best_score})

        if best_score >= target_score:
            return {
                "best_resume_json": best_json,
                "best_score": best_score,
                "history": history,
                "stopped_reason": "target_reached",
            }

        for i in range(1, max_iterations + 1):
            candidate = self.revise_resume(
                enhanced_resume_json=best_json,
                job_description=job_description,
                goals=goals,
            )
            candidate_score = float(score_fn(candidate))
            history.append({"iteration": i, "score": candidate_score})

            delta = candidate_score - best_score
            if candidate_score > best_score:
                best_json = candidate
                best_score = candidate_score

            if best_score >= target_score:
                return {
                    "best_resume_json": best_json,
                    "best_score": best_score,
                    "history": history,
                    "stopped_reason": "target_reached",
                }

            if delta < min_score_delta:
                return {
                    "best_resume_json": best_json,
                    "best_score": best_score,
                    "history": history,
                    "stopped_reason": "no_progress",
                }

        return {
            "best_resume_json": best_json,
            "best_score": best_score,
            "history": history,
            "stopped_reason": "max_iterations",
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    # Set your GEMINI_API_KEY environment variable before running this example
    # os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY"

    try:
        integrator = GeminiAPIIntegrator(
            model_name="gemini-1.5-flash-latest",
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
        )

        sample_resume_content = """
        John Doe
        Software Engineer
        Summary: Software engineer with experience in Python.
        Experience: Tech Corp, Software Engineer, 2020-2023. Developed web applications.
        Education: University of Example, M.Sc. Computer Science, 2019.
        Skills: Python, JavaScript.
        """

        sample_job_description = (
            "Looking for a software engineer with strong Python skills."
        )

        logger.info(
            "Sending resume data to Gemini API for enhancement (without job description)..."
        )
        enhanced_data_no_jd_str = integrator.enhance_resume(sample_resume_content)
        logger.info("\nEnhanced Resume Data (without JD):")
        logger.info(enhanced_data_no_jd_str)

        logger.info(
            "Sending resume data to Gemini API for enhancement (with job description)..."
        )
        enhanced_data_with_jd_str = integrator.enhance_resume(
            sample_resume_content, job_description=sample_job_description
        )
        logger.info("\nEnhanced Resume Data (with JD):")
        logger.info(enhanced_data_with_jd_str)

    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.error(f"An error occurred during API call: {e}")
