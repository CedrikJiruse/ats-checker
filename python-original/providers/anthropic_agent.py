"""
Anthropic provider agent for multi-LLM support.

Supports Claude models:
- claude-3-5-sonnet-20241022 (latest, best quality)
- claude-3-5-haiku-20241022 (fast, cheaper)
- claude-3-opus-20240229 (powerful reasoning)
- claude-3-sonnet-20240229 (balanced quality/cost)
- claude-3-haiku-20240307 (fastest)

Requires:
- anthropic >= 0.18.0 (pip install anthropic)
- ANTHROPIC_API_KEY environment variable set
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from agents import AgentConfig, AgentResponseError, strip_markdown_fences

logger = logging.getLogger(__name__)


class AnthropicAgent:
    """
    Anthropic Claude agent using the Anthropic Python SDK.

    Supports JSON output via prompt engineering and prefill technique.
    Handles exponential backoff for rate limits.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize Anthropic agent.

        Args:
            config: AgentConfig with provider='anthropic' and model_name

        Raises:
            ValueError: If ANTHROPIC_API_KEY not set or anthropic SDK unavailable
        """
        self.config = config
        self._client = None

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Get one at: https://console.anthropic.com/account/keys"
            )

        # Lazy import to avoid import-time overhead
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ImportError(
                "Anthropic SDK not found. Install it with: pip install anthropic>=0.18.0"
            ) from e

        self._client = Anthropic(api_key=api_key)
        logger.info(f"Anthropic agent initialized with model: {config.model_name}")

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using Anthropic API.

        Args:
            prompt: The prompt string

        Returns:
            Generated text

        Raises:
            AgentResponseError: If generation fails after retries
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")

        max_attempts = max(1, self.config.max_retries + 1)
        for attempt in range(max_attempts):
            try:
                # For Anthropic, we use the basic message format (no system parameter here)
                # If prefill is needed for JSON, it's handled in generate_json
                message = self._client.messages.create(
                    model=self.config.model_name,
                    max_tokens=self.config.max_output_tokens,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    top_k=self.config.top_k,
                )

                text = message.content[0].text
                if not text:
                    if self.config.retry_on_empty and attempt < max_attempts - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise AgentResponseError("Anthropic returned empty response")

                # Validate JSON if required
                if self.config.require_json:
                    text = strip_markdown_fences(text)
                    try:
                        json.loads(text)
                    except json.JSONDecodeError as e:
                        raise AgentResponseError(
                            f"Anthropic did not return valid JSON: {e}"
                        ) from e
                    return json.dumps(json.loads(text), ensure_ascii=False, indent=2)

                return text

            except Exception as e:
                # Handle rate limits with exponential backoff
                if "overloaded_error" in str(e).lower() or "rate_limit" in str(
                    e
                ).lower():
                    if attempt < max_attempts - 1:
                        wait_time = min(2 ** attempt, 60)
                        logger.warning(f"Rate limited. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                if attempt == max_attempts - 1:
                    raise AgentResponseError(
                        f"Anthropic API failed after {max_attempts} attempt(s): {e}"
                    ) from e

                time.sleep(2 ** attempt)

        raise AgentResponseError("Anthropic generation failed after all retries")

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """
        Generate JSON using Anthropic API.

        Uses the "prefill" technique: include "{" as assistant's first message
        to guide Claude to generate valid JSON.

        Args:
            prompt: The prompt string (should request JSON)

        Returns:
            Parsed JSON object

        Raises:
            AgentResponseError: If JSON generation/parsing fails
        """
        # Ensure prompt mentions JSON
        if "json" not in prompt.lower():
            prompt = prompt + "\n\nRespond with a valid JSON object."

        max_attempts = max(1, self.config.max_retries + 1)
        for attempt in range(max_attempts):
            try:
                # Use prefill technique: start assistant message with "{"
                message = self._client.messages.create(
                    model=self.config.model_name,
                    max_tokens=self.config.max_output_tokens,
                    system=prompt,
                    messages=[
                        {"role": "user", "content": "Generate the JSON object."},
                        {"role": "assistant", "content": "{"},
                    ],
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    top_k=self.config.top_k,
                )

                # The response continues from the "{" we provided
                text = "{" + message.content[0].text
                text = strip_markdown_fences(text)

                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    raise AgentResponseError(f"Invalid JSON from Anthropic: {e}") from e

            except Exception as e:
                if "overloaded_error" in str(e).lower() or "rate_limit" in str(
                    e
                ).lower():
                    if attempt < max_attempts - 1:
                        wait_time = min(2 ** attempt, 60)
                        logger.warning(f"Rate limited. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                if attempt == max_attempts - 1:
                    raise AgentResponseError(
                        f"Anthropic JSON generation failed: {e}"
                    ) from e

                time.sleep(2 ** attempt)

        raise AgentResponseError("Anthropic JSON generation failed after all retries")
