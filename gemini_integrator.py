"""
Gemini integrator (refactored) using the pluggable AgentRegistry + GeminiAgent.

Why this exists
---------------
The rest of the codebase wants a small, stable surface area for AI operations:
- Enhance a resume into a structured JSON object
- Summarize a job description
- Iteratively revise a structured resume JSON until a target score is reached

This module keeps that surface area but delegates the provider details to:
- `agents.py`:
    - AgentRegistry
    - AgentConfig / GeminiAgent
    - JSON fencing/validation helpers

Agent configuration
-------------------
`ResumeProcessor` passes `config.ai_agents` into this class. That dict is expected to look like:

{
  "enhancer": {"provider": "gemini", "model_name": "...", "role": "resume_enhancement", ...},
  "job_summarizer": {"provider": "gemini", "model_name": "...", "role": "job_summary", ...},
  "reviser": {"provider": "gemini", "model_name": "...", "role": "resume_revision", ...},
}

This module will apply sensible defaults:
- enhancer/reviser are JSON-required
- job_summarizer is plain text

Security
--------
Requires `GEMINI_API_KEY` to be set in the environment. The underlying Gemini agent
will enforce this.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from agents import Agent, AgentRegistry

logger = logging.getLogger(__name__)


class GeminiAPIIntegrator:
    """
    Backward-compatible integrator that exposes the previous API, but uses the new
    pluggable agent layer internally.
    """

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
        Args:
            model_name: Default Gemini model for agents that don't override it.
            temperature/top_p/top_k/max_output_tokens: Default generation config.
            agents: Optional dict of agent configs (typically from TOML config.ai.agents.*).
        """
        self._default_model_name = model_name
        self._default_generation = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
        }

        agents_cfg = self._normalize_agents_config(agents)

        # Build the registry (this constructs provider-specific clients lazily per agent).
        self.registry = AgentRegistry.from_config_dict(
            agents_cfg,
            default_provider="gemini",
            default_model_name=self._default_model_name,
            default_generation=self._default_generation,
        )

        # Keep a backward-compatible attribute name so older code/tests don't break.
        # Previously: self.model was a google.generativeai model; now it is the enhancer agent.
        self.model = self._get_agent("enhancer")

        logger.info(
            "GeminiAPIIntegrator ready. Agents registered: %s",
            ", ".join(self.registry.list()),
        )

    # ----------------------------
    # Agent registry helpers
    # ----------------------------

    def _normalize_agents_config(
        self, agents: Optional[Dict[str, Dict[str, Any]]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Apply defaults and ensure key agent behaviors:
        - enhancer/reviser: require_json=True
        - job_summarizer: require_json=False
        """
        # Baseline agents
        cfg: Dict[str, Dict[str, Any]] = {
            "enhancer": {"provider": "gemini", "role": "resume_enhancement"},
            "job_summarizer": {"provider": "gemini", "role": "job_summary"},
            "reviser": {"provider": "gemini", "role": "resume_revision"},
        }

        # Merge user config (if provided)
        if isinstance(agents, dict):
            for name, user_cfg in agents.items():
                if not isinstance(name, str) or not isinstance(user_cfg, dict):
                    continue
                merged = dict(cfg.get(name, {}))
                merged.update(user_cfg)
                cfg[name] = merged

        # Ensure model_name is set if omitted
        for name in list(cfg.keys()):
            if "model_name" not in cfg[name] or not cfg[name].get("model_name"):
                cfg[name]["model_name"] = self._default_model_name

        # Enforce JSON requirement for certain roles
        cfg.setdefault("enhancer", {})
        cfg.setdefault("reviser", {})
        cfg["enhancer"].setdefault("require_json", True)
        cfg["reviser"].setdefault("require_json", True)

        # job_summarizer should be plain text
        cfg.setdefault("job_summarizer", {})
        cfg["job_summarizer"].setdefault("require_json", False)

        return cfg

    def _get_agent(self, agent_name: str) -> Agent:
        """
        Get a named agent, falling back to enhancer if not present.
        """
        try:
            return self.registry.get(agent_name)
        except Exception:
            return self.registry.get("enhancer")

    # ----------------------------
    # Prompt construction
    # ----------------------------

    def _craft_prompt(
        self, resume_content: str, job_description: Optional[str] = None
    ) -> str:
        """
        Craft prompt for resume enhancement to structured JSON.
        """
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

        return "".join(prompt_parts)

    def _craft_job_summary_prompt(self, job_description: str) -> str:
        """
        Prompt that produces a compact, actionable job summary.
        Output is plain text (not JSON) for easy display.
        """
        return (
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

    def _craft_revision_prompt(
        self,
        enhanced_resume_json: str,
        job_description: Optional[str] = None,
        goals: Optional[List[str]] = None,
    ) -> str:
        """
        Prompt for iterative revision of an already-structured resume JSON.
        The model is required to output raw JSON only.
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

    # ----------------------------
    # Public API (backward compatible)
    # ----------------------------

    def enhance_resume(
        self, resume_content: str, job_description: Optional[str] = None
    ) -> str:
        """
        Enhance a raw resume to structured JSON (as a JSON string).

        Returns:
            JSON string (pretty printed).
        """
        prompt = self._craft_prompt(resume_content, job_description)
        agent = self._get_agent("enhancer")

        logger.info("Sending resume data to AI enhancer agent...")
        text = agent.generate_text(prompt)

        # Validate JSON (agent may already enforce it via require_json)
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError(
                "Enhanced resume output must be a JSON object at the top level."
            )
        return json.dumps(obj, ensure_ascii=False, indent=2)

    def summarize_job_description(self, job_description: str) -> str:
        """
        Summarize a job description using the job_summarizer agent.
        """
        prompt = self._craft_job_summary_prompt(job_description)
        agent = self._get_agent("job_summarizer")

        logger.info("Sending job description to AI job_summarizer agent...")
        text = agent.generate_text(prompt)
        return (text or "").strip()

    def revise_resume(
        self,
        enhanced_resume_json: str,
        job_description: Optional[str] = None,
        goals: Optional[List[str]] = None,
    ) -> str:
        """
        Revise an already-structured resume JSON using the reviser agent.

        Args:
            enhanced_resume_json: JSON string representing the structured resume.
            job_description: Optional job description content.
            goals: Optional list of goals to guide revision.

        Returns:
            Revised resume JSON string (pretty printed).
        """
        # Validate input JSON
        base = json.loads(enhanced_resume_json)
        if not isinstance(base, dict):
            raise ValueError("Input to revise_resume must be a JSON object.")

        prompt = self._craft_revision_prompt(
            enhanced_resume_json=json.dumps(base, ensure_ascii=False, indent=2),
            job_description=job_description,
            goals=goals,
        )
        agent = self._get_agent("reviser")

        logger.info("Sending resume JSON to AI reviser agent...")
        text = agent.generate_text(prompt)

        # Validate JSON
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError(
                "Revised resume output must be a JSON object at the top level."
            )
        return json.dumps(obj, ensure_ascii=False, indent=2)

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
