"""
Agent abstraction layer for ATS Checker.

Goal
----
Decouple the rest of the application from any specific LLM provider so you can:
- swap providers (Gemini / others) without rewriting business logic
- run multiple "agents" with different roles/models/configs
- standardize prompt/response handling (JSON-only, retry, etc.)

This module intentionally stays small and dependency-light.

Key Concepts
-----------
- Agent: a minimal interface: `generate_text(prompt)` and convenience helpers.
- AgentConfig: provider + model + generation settings.
- AgentFactory: creates an Agent from config.
- GeminiAgent: implementation using `google.generativeai` (Gemini).

Notes
-----
- This module does not assume your calling code uses tools or function calling.
- It provides a robust "strip markdown fences" helper because models sometimes wrap JSON.
- If you later add other providers, implement `Agent` and register in `create_agent(...)`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    runtime_checkable,
)

# -----------------------------
# Exceptions
# -----------------------------


class AgentError(RuntimeError):
    """Base class for agent-related errors."""


class AgentConfigError(AgentError):
    """Raised when agent configuration is invalid or incomplete."""


class AgentProviderError(AgentError):
    """Raised when the underlying provider call fails."""


class AgentResponseError(AgentError):
    """Raised when the model response is malformed (e.g., invalid JSON when required)."""


# -----------------------------
# Public data structures
# -----------------------------


@dataclass(frozen=True)
class AgentConfig:
    """
    Configuration for an agent.

    Fields are provider-agnostic; a provider implementation may ignore unsupported fields.
    """

    name: str
    provider: str = "gemini"
    role: str = "generic"

    model_name: str = "gemini-pro"
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 8192

    # Optional retry behavior
    max_retries: int = 0  # retries after the initial attempt
    retry_on_empty: bool = True

    # Optional safety: force JSON output and validate it.
    require_json: bool = False

    # Provider-specific freeform options (future-proofing).
    extras: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Agent(Protocol):
    """
    Minimal agent interface.

    Implementations should be side-effect free except for network calls to the provider.
    """

    config: AgentConfig

    def generate_text(self, prompt: str) -> str: ...

    def generate_json(self, prompt: str) -> Dict[str, Any]: ...


# -----------------------------
# Utilities
# -----------------------------


def strip_markdown_fences(text: str) -> str:
    """
    Strip common markdown code fences around model outputs.

    Handles:
      ```json
      {...}
      ```
    and
      ```
      {...}
      ```
    """
    if not isinstance(text, str):
        return ""

    s = text.strip()
    if s.startswith("```") and s.endswith("```"):
        # Try to remove ```json or ```<lang>
        first_newline = s.find("\n")
        if first_newline != -1:
            header = s[:first_newline].strip()
            body = s[first_newline + 1 : -3].strip()
            # If the header is just ``` or ```json etc., drop it
            if header.startswith("```"):
                return body
        return s[3:-3].strip()
    return s


def ensure_json_object(text: str) -> Dict[str, Any]:
    """
    Parse a JSON object from text (after stripping fences).
    Raises AgentResponseError if parsing fails or the root isn't an object.
    """
    s = strip_markdown_fences(text)
    try:
        obj = json.loads(s)
    except Exception as e:
        raise AgentResponseError(f"Model did not return valid JSON: {e}") from e

    if not isinstance(obj, dict):
        raise AgentResponseError(
            "Model returned JSON but the root is not an object/dict."
        )
    return obj


def _is_effectively_empty(text: str) -> bool:
    return not isinstance(text, str) or not text.strip()


# -----------------------------
# Gemini implementation
# -----------------------------


class GeminiAgent:
    """
    Gemini-based agent using google.generativeai.

    Requirements:
      - `google-generativeai` installed
      - `GEMINI_API_KEY` set in environment
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self._model = None

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AgentConfigError(
                "GEMINI_API_KEY not found. Please set it as an environment variable."
            )

        # Lazy import to avoid import-time overhead if Gemini isn't used in a run.
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as e:
            raise AgentProviderError(
                "Gemini provider is unavailable. Install google-generativeai."
            ) from e

        genai.configure(api_key=api_key)

        generation_kwargs: Dict[str, Any] = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "max_output_tokens": config.max_output_tokens,
        }

        # Allow provider-specific overrides via extras
        # (e.g., safety settings, stop sequences)
        for k, v in (config.extras or {}).items():
            if k in generation_kwargs:
                generation_kwargs[k] = v

        self._model = genai.GenerativeModel(
            model_name=config.model_name,
            generation_config=genai.GenerationConfig(**generation_kwargs),
        )

    def generate_text(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise AgentConfigError("Prompt must be a non-empty string.")

        attempts = 0
        last_error: Optional[Exception] = None

        # initial attempt + retries
        for attempts in range(0, max(0, self.config.max_retries) + 1):
            try:
                resp = self._model.generate_content(prompt)
                text = (getattr(resp, "text", None) or "").strip()

                if self.config.retry_on_empty and _is_effectively_empty(text):
                    raise AgentResponseError("Model returned an empty response.")

                if self.config.require_json:
                    # Validate but return the original (possibly fenced) content normalized to JSON text.
                    _ = ensure_json_object(text)
                    # Return de-fenced JSON string for downstream consistency
                    return json.dumps(_, ensure_ascii=False, indent=2)

                return text

            except Exception as e:
                last_error = e
                # continue to retry
                continue

        raise AgentProviderError(
            f"Gemini agent failed after {attempts + 1} attempt(s): {last_error}"
        ) from last_error

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        # Force JSON validation irrespective of config.require_json
        text = self.generate_text(prompt if prompt is not None else "")
        try:
            return ensure_json_object(text)
        except AgentResponseError:
            # If config.require_json is False, the text may not have been forced to JSON.
            # Try once more with strict instructions appended.
            strict_prompt = (
                prompt.rstrip()
                + "\n\nIMPORTANT: Output MUST be a raw JSON object only. No markdown fences. No commentary."
            )
            text2 = self.generate_text(strict_prompt)
            return ensure_json_object(text2)


# -----------------------------
# Factory / Registry
# -----------------------------


def create_agent(config: AgentConfig) -> Agent:
    """
    Create an agent implementation for the configured provider.
    """
    provider = (config.provider or "").lower().strip()
    if provider == "gemini":
        return GeminiAgent(config)
    raise AgentConfigError(f"Unknown agent provider: {config.provider!r}")


class AgentRegistry:
    """
    Simple in-process registry for named agents.

    Intended usage:
      registry = AgentRegistry.from_config_dict(ai_agents_dict, defaults=...)
      enhancer = registry.get("enhancer")
      text = enhancer.generate_text("...")
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def register(self, name: str, agent: Agent) -> None:
        if not name or not isinstance(name, str):
            raise AgentConfigError("Agent name must be a non-empty string.")
        self._agents[name] = agent

    def get(self, name: str) -> Agent:
        if name not in self._agents:
            raise AgentConfigError(f"Agent not found: {name}")
        return self._agents[name]

    def list(self) -> List[str]:
        return sorted(self._agents.keys())

    @classmethod
    def from_config_dict(
        cls,
        agents_cfg: Mapping[str, Mapping[str, Any]],
        *,
        default_provider: str = "gemini",
        default_model_name: str = "gemini-pro",
        default_generation: Optional[Mapping[str, Any]] = None,
    ) -> "AgentRegistry":
        """
        Build registry from a dict like config.ai_agents:

            {
              "enhancer": {"role":"resume_enhancement", "provider":"gemini", "model_name":"..."},
              "reviser": {...},
            }

        `default_generation` may include:
          temperature, top_p, top_k, max_output_tokens
        """
        reg = cls()
        defaults = dict(default_generation or {})
        for name, cfg in (agents_cfg or {}).items():
            if not isinstance(name, str) or not isinstance(cfg, Mapping):
                continue

            provider = str(cfg.get("provider", default_provider))
            role = str(cfg.get("role", "generic"))
            model_name = str(cfg.get("model_name", default_model_name))

            temperature = float(
                cfg.get("temperature", defaults.get("temperature", 0.7))
            )
            top_p = float(cfg.get("top_p", defaults.get("top_p", 0.95)))
            top_k = int(cfg.get("top_k", defaults.get("top_k", 40)))
            max_output_tokens = int(
                cfg.get("max_output_tokens", defaults.get("max_output_tokens", 8192))
            )

            max_retries = int(cfg.get("max_retries", 0))
            retry_on_empty = bool(cfg.get("retry_on_empty", True))
            require_json = bool(cfg.get("require_json", False))
            extras = (
                dict(cfg.get("extras", {}))
                if isinstance(cfg.get("extras"), dict)
                else {}
            )

            agent_cfg = AgentConfig(
                name=name,
                provider=provider,
                role=role,
                model_name=model_name,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_output_tokens=max_output_tokens,
                max_retries=max_retries,
                retry_on_empty=retry_on_empty,
                require_json=require_json,
                extras=extras,
            )
            reg.register(name, create_agent(agent_cfg))
        return reg
