"""
OpenAI provider agent for multi-LLM support.

Supports models:
- gpt-4o (latest, most capable)
- gpt-4o-mini (faster, cheaper)
- gpt-4-turbo (legacy, good for complex reasoning)
- gpt-3.5-turbo (older, cheapest)

Requires:
- openai >= 1.0.0 (pip install openai)
- OPENAI_API_KEY environment variable set
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from agents import AgentConfig, AgentResponseError, strip_markdown_fences

logger = logging.getLogger(__name__)


class OpenAIAgent:
    """
    OpenAI-based agent using the OpenAI Python SDK.

    Supports JSON output via response_format parameter.
    Handles exponential backoff for rate limits.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize OpenAI agent.

        Args:
            config: AgentConfig with provider='openai' and model_name

        Raises:
            AgentConfigError: If OPENAI_API_KEY not set or openai SDK unavailable
        """
        self.config = config
        self._client = None

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Get one at: https://platform.openai.com/api-keys"
            )

        # Lazy import to avoid import-time overhead if OpenAI isn't used
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI SDK not found. Install it with: pip install openai>=1.0.0"
            ) from e

        self._client = OpenAI(api_key=api_key)
        logger.info(f"OpenAI agent initialized with model: {config.model_name}")

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using OpenAI API.

        Args:
            prompt: The prompt string

        Returns:
            Generated text

        Raises:
            AgentResponseError: If generation fails after retries
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")

        # Build messages list
        messages = [{"role": "user", "content": prompt}]

        # Determine if JSON is required
        response_format = None
        if self.config.require_json:
            response_format = {"type": "json_object"}

        # Attempt with retries
        max_attempts = max(1, self.config.max_retries + 1)
        for attempt in range(max_attempts):
            try:
                response = self._client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    max_tokens=self.config.max_output_tokens,
                    response_format=response_format,
                )

                text = response.choices[0].message.content
                if not text:
                    if self.config.retry_on_empty and attempt < max_attempts - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    raise AgentResponseError("OpenAI returned empty response")

                # Validate JSON if required
                if self.config.require_json:
                    # OpenAI should return valid JSON with response_format
                    text = strip_markdown_fences(text)
                    try:
                        json.loads(text)  # Validate it's valid JSON
                    except json.JSONDecodeError as e:
                        raise AgentResponseError(
                            f"OpenAI did not return valid JSON: {e}"
                        ) from e
                    # Return the validated JSON string
                    return json.dumps(json.loads(text), ensure_ascii=False, indent=2)

                return text

            except Exception as e:
                # Handle rate limits with exponential backoff
                if "rate_limit" in str(e).lower() and attempt < max_attempts - 1:
                    wait_time = min(2 ** attempt, 60)  # Cap at 60 seconds
                    logger.warning(
                        f"Rate limited on attempt {attempt + 1}. Waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                if attempt == max_attempts - 1:
                    raise AgentResponseError(
                        f"OpenAI API failed after {max_attempts} attempt(s): {e}"
                    ) from e

                # For other errors, retry with backoff
                time.sleep(2 ** attempt)

        raise AgentResponseError("OpenAI generation failed after all retries")

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """
        Generate JSON using OpenAI API.

        Uses response_format={"type": "json_object"} for guaranteed JSON output.

        Args:
            prompt: The prompt string (should mention JSON)

        Returns:
            Parsed JSON object

        Raises:
            AgentResponseError: If JSON generation/parsing fails
        """
        # Ensure prompt mentions JSON (OpenAI requirement)
        if "json" not in prompt.lower():
            prompt = prompt + "\n\nRespond with a valid JSON object."

        # Use JSON response format
        messages = [{"role": "user", "content": prompt}]

        max_attempts = max(1, self.config.max_retries + 1)
        for attempt in range(max_attempts):
            try:
                response = self._client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    max_tokens=self.config.max_output_tokens,
                    response_format={"type": "json_object"},
                )

                text = response.choices[0].message.content
                text = strip_markdown_fences(text)

                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    raise AgentResponseError(f"Invalid JSON from OpenAI: {e}") from e

            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < max_attempts - 1:
                    wait_time = min(2 ** attempt, 60)
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if attempt == max_attempts - 1:
                    raise AgentResponseError(
                        f"OpenAI JSON generation failed: {e}"
                    ) from e

                time.sleep(2 ** attempt)

        raise AgentResponseError("OpenAI JSON generation failed after all retries")
