"""
Meta Llama provider agent via OpenAI-compatible APIs.

Supports:
- Llama 3.3 70B Instruct (via Together AI or Groq)
- Model: meta-llama/Llama-3.3-70B-Instruct

Providers:
- Together AI: https://together.ai (requires TOGETHER_API_KEY)
- Groq: https://groq.com (requires GROQ_API_KEY)

Uses OpenAI SDK with custom base_url for compatibility.

Requires:
- openai >= 1.0.0 (pip install openai)
- TOGETHER_API_KEY or GROQ_API_KEY environment variable
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from agents import AgentConfig, AgentResponseError, strip_markdown_fences

logger = logging.getLogger(__name__)


class LlamaAgent:
    """
    Meta Llama agent via OpenAI-compatible API providers.

    Uses Together AI or Groq's OpenAI-compatible endpoints for Llama models.
    Falls back automatically if one provider's API key is unavailable.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize Llama agent.

        Args:
            config: AgentConfig with provider='llama' and model_name

        Raises:
            ValueError: If no API key set or openai SDK unavailable
        """
        self.config = config
        self._client = None
        self._provider = None

        # Lazy import
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI SDK not found. Install it with: pip install openai>=1.0.0"
            ) from e

        # Try Together AI first, then Groq
        together_key = os.getenv("TOGETHER_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        if together_key:
            self._client = OpenAI(
                api_key=together_key,
                base_url="https://api.together.xyz/v1",
            )
            self._provider = "Together AI"
            logger.info(f"Llama agent initialized via Together AI with model: {config.model_name}")
        elif groq_key:
            self._client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1",
            )
            self._provider = "Groq"
            logger.info(f"Llama agent initialized via Groq with model: {config.model_name}")
        else:
            raise ValueError(
                "Neither TOGETHER_API_KEY nor GROQ_API_KEY found in environment.\n"
                "Get Together AI key at: https://together.ai/signin\n"
                "Get Groq key at: https://console.groq.com/keys"
            )

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using Llama via OpenAI-compatible API.

        Args:
            prompt: The prompt string

        Returns:
            Generated text

        Raises:
            AgentResponseError: If generation fails after retries
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")

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
                )

                text = response.choices[0].message.content
                if not text:
                    if self.config.retry_on_empty and attempt < max_attempts - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise AgentResponseError("Llama returned empty response")

                # Validate JSON if required
                if self.config.require_json:
                    text = strip_markdown_fences(text)
                    try:
                        json.loads(text)
                    except json.JSONDecodeError as e:
                        raise AgentResponseError(
                            f"Llama did not return valid JSON: {e}"
                        ) from e
                    return json.dumps(json.loads(text), ensure_ascii=False, indent=2)

                return text

            except Exception as e:
                # Handle rate limits with exponential backoff
                if "rate_limit" in str(e).lower() or "overloaded" in str(e).lower():
                    if attempt < max_attempts - 1:
                        wait_time = min(2 ** attempt, 60)
                        logger.warning(
                            f"Rate limited on {self._provider}. Waiting {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        continue

                if attempt == max_attempts - 1:
                    raise AgentResponseError(
                        f"Llama ({self._provider}) API failed after {max_attempts} attempt(s): {e}"
                    ) from e

                time.sleep(2 ** attempt)

        raise AgentResponseError("Llama generation failed after all retries")

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """
        Generate JSON using Llama via OpenAI-compatible API.

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
                )

                text = response.choices[0].message.content
                text = strip_markdown_fences(text)

                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    raise AgentResponseError(f"Invalid JSON from Llama: {e}") from e

            except Exception as e:
                if "rate_limit" in str(e).lower() or "overloaded" in str(e).lower():
                    if attempt < max_attempts - 1:
                        wait_time = min(2 ** attempt, 60)
                        logger.warning(f"Rate limited. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                if attempt == max_attempts - 1:
                    raise AgentResponseError(
                        f"Llama JSON generation failed: {e}"
                    ) from e

                time.sleep(2 ** attempt)

        raise AgentResponseError("Llama JSON generation failed after all retries")
