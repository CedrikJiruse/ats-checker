"""
Tests for multi-provider agent implementations.

Tests OpenAI, Anthropic, and Llama agents with mocked API responses.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from agents import AgentConfig


class TestOpenAIAgent:
    """Tests for OpenAI provider agent."""

    @pytest.fixture
    def config(self):
        return AgentConfig(
            name="test_agent",
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
        )

    def test_agent_requires_api_key(self):
        """Test that OpenAI agent requires API key."""
        # Skip if openai not installed
        try:
            from providers.openai_agent import OpenAIAgent
        except ImportError:
            pytest.skip("openai SDK not installed")

        with patch.dict("os.environ", {}, clear=True):
            config = AgentConfig(name="test", provider="openai", model_name="gpt-4o")
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIAgent(config)

    def test_agent_initializes_with_api_key(self, config):
        """Test that agent initializes successfully with API key."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                from providers.openai_agent import OpenAIAgent
                agent = OpenAIAgent(config)
                assert agent.config == config

    def test_generate_text_with_valid_response(self, config):
        """Test text generation with valid response."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                # Mock the API response
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
                mock_client.chat.completions.create.return_value = mock_response

                from providers.openai_agent import OpenAIAgent
                agent = OpenAIAgent(config)
                result = agent.generate_text("Test prompt")

                assert result == "Test response"
                mock_client.chat.completions.create.assert_called_once()

    def test_generate_text_requires_non_empty_prompt(self, config):
        """Test that generate_text requires non-empty prompt."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                from providers.openai_agent import OpenAIAgent
                agent = OpenAIAgent(config)

                with pytest.raises(ValueError, match="non-empty"):
                    agent.generate_text("")

    def test_generate_json_with_valid_json(self, config):
        """Test JSON generation with valid JSON response."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                test_json = {"name": "John", "age": 30}
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(
                    content=json.dumps(test_json)
                ))]
                mock_client.chat.completions.create.return_value = mock_response

                from providers.openai_agent import OpenAIAgent
                agent = OpenAIAgent(config)
                result = agent.generate_json("Generate JSON")

                assert result == test_json

    def test_generate_json_strips_markdown_fences(self, config):
        """Test that generate_json strips markdown fences."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                test_json = {"name": "John"}
                json_with_fences = f"```json\n{json.dumps(test_json)}\n```"
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(
                    content=json_with_fences
                ))]
                mock_client.chat.completions.create.return_value = mock_response

                from providers.openai_agent import OpenAIAgent
                agent = OpenAIAgent(config)
                result = agent.generate_json("Generate JSON")

                assert result == test_json

    def test_generate_text_retries_on_empty_response(self, config):
        """Test that generate_text retries on empty response."""
        config_with_retry = AgentConfig(
            name="test",
            provider="openai",
            model_name="gpt-4o",
            max_retries=2,
            retry_on_empty=True,
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                with patch("providers.openai_agent.time.sleep"):
                    mock_client = MagicMock()
                    mock_openai.return_value = mock_client

                    # First two calls return empty, third returns content
                    responses = [
                        MagicMock(choices=[MagicMock(message=MagicMock(content=""))]),
                        MagicMock(choices=[MagicMock(message=MagicMock(content=""))]),
                        MagicMock(choices=[MagicMock(message=MagicMock(content="Success"))]),
                    ]
                    mock_client.chat.completions.create.side_effect = responses

                    from providers.openai_agent import OpenAIAgent
                    agent = OpenAIAgent(config_with_retry)
                    result = agent.generate_text("Test prompt")

                    assert result == "Success"
                    assert mock_client.chat.completions.create.call_count == 3


class TestAnthropicAgent:
    """Tests for Anthropic provider agent."""

    @pytest.fixture
    def config(self):
        return AgentConfig(
            name="test_agent",
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
        )

    def test_agent_requires_api_key(self):
        """Test that Anthropic agent requires API key."""
        with patch.dict("os.environ", {}, clear=True):
            from providers.anthropic_agent import AnthropicAgent
            config = AgentConfig(name="test", provider="anthropic")
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                AnthropicAgent(config)

    def test_agent_initializes_with_api_key(self, config):
        """Test that agent initializes successfully with API key."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("providers.anthropic_agent.Anthropic"):
                from providers.anthropic_agent import AnthropicAgent
                agent = AnthropicAgent(config)
                assert agent.config == config

    def test_generate_text_with_valid_response(self, config):
        """Test text generation with valid response."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("providers.anthropic_agent.Anthropic") as mock_anthropic:
                mock_client = MagicMock()
                mock_anthropic.return_value = mock_client

                mock_response = MagicMock()
                mock_response.content = [MagicMock(text="Test response")]
                mock_client.messages.create.return_value = mock_response

                from providers.anthropic_agent import AnthropicAgent
                agent = AnthropicAgent(config)
                result = agent.generate_text("Test prompt")

                assert result == "Test response"
                mock_client.messages.create.assert_called_once()

    def test_generate_json_uses_prefill_technique(self, config):
        """Test that generate_json uses Anthropic's prefill technique."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("providers.anthropic_agent.Anthropic") as mock_anthropic:
                mock_client = MagicMock()
                mock_anthropic.return_value = mock_client

                test_json_body = '"name": "John"}'
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text=test_json_body)]
                mock_client.messages.create.return_value = mock_response

                from providers.anthropic_agent import AnthropicAgent
                agent = AnthropicAgent(config)
                result = agent.generate_json("Generate JSON")

                # Should reconstruct to valid JSON
                assert "name" in result
                # Verify prefill was used in the call
                call_kwargs = mock_client.messages.create.call_args[1]
                messages = call_kwargs["messages"]
                # Last message should be assistant with "{"
                assert messages[-1]["role"] == "assistant"
                assert messages[-1]["content"] == "{"

    def test_generate_json_with_valid_json(self, config):
        """Test JSON generation with valid JSON response."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("providers.anthropic_agent.Anthropic") as mock_anthropic:
                mock_client = MagicMock()
                mock_anthropic.return_value = mock_client

                test_json = {"name": "John", "age": 30}
                # Anthropic response continues after the prefilled "{"
                json_body = '"name": "John", "age": 30}'
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text=json_body)]
                mock_client.messages.create.return_value = mock_response

                from providers.anthropic_agent import AnthropicAgent
                agent = AnthropicAgent(config)
                result = agent.generate_json("Generate JSON")

                assert result["name"] == "John"
                assert result["age"] == 30


class TestLlamaAgent:
    """Tests for Llama provider agent via OpenAI-compatible API."""

    @pytest.fixture
    def config(self):
        return AgentConfig(
            name="test_agent",
            provider="llama",
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
        )

    def test_agent_requires_api_key(self):
        """Test that Llama agent requires Together or Groq API key."""
        with patch.dict("os.environ", {}, clear=True):
            from providers.llama_agent import LlamaAgent
            config = AgentConfig(name="test", provider="llama")
            with pytest.raises(ValueError, match="TOGETHER_API_KEY|GROQ_API_KEY"):
                LlamaAgent(config)

    def test_agent_prefers_together_ai(self, config):
        """Test that agent uses Together AI if key is available."""
        with patch.dict("os.environ", {
            "TOGETHER_API_KEY": "together-key",
            "GROQ_API_KEY": "groq-key",
        }):
            with patch("providers.llama_agent.OpenAI"):
                from providers.llama_agent import LlamaAgent
                agent = LlamaAgent(config)
                assert agent._provider == "Together AI"

    def test_agent_falls_back_to_groq(self, config):
        """Test that agent falls back to Groq if Together key is unavailable."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "groq-key"}, clear=True):
            with patch("providers.llama_agent.OpenAI"):
                from providers.llama_agent import LlamaAgent
                agent = LlamaAgent(config)
                assert agent._provider == "Groq"

    def test_agent_uses_together_base_url(self, config):
        """Test that agent configures Together AI base URL."""
        with patch.dict("os.environ", {"TOGETHER_API_KEY": "test-key"}):
            with patch("providers.llama_agent.OpenAI") as mock_openai:
                from providers.llama_agent import LlamaAgent
                LlamaAgent(config)

                # Verify Together base URL was used
                call_kwargs = mock_openai.call_args[1]
                assert "api.together.xyz" in call_kwargs["base_url"]

    def test_agent_uses_groq_base_url(self, config):
        """Test that agent configures Groq base URL."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=True):
            with patch("providers.llama_agent.OpenAI") as mock_openai:
                from providers.llama_agent import LlamaAgent
                LlamaAgent(config)

                # Verify Groq base URL was used
                call_kwargs = mock_openai.call_args[1]
                assert "api.groq.com" in call_kwargs["base_url"]

    def test_generate_text_with_valid_response(self, config):
        """Test text generation with valid response."""
        with patch.dict("os.environ", {"TOGETHER_API_KEY": "test-key"}):
            with patch("providers.llama_agent.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
                mock_client.chat.completions.create.return_value = mock_response

                from providers.llama_agent import LlamaAgent
                agent = LlamaAgent(config)
                result = agent.generate_text("Test prompt")

                assert result == "Test response"


class TestProviderErrorHandling:
    """Tests for error handling across providers."""

    def test_openai_handles_rate_limit_with_retry(self):
        """Test that OpenAI agent handles rate limits with exponential backoff."""
        config = AgentConfig(name="test", provider="openai", max_retries=2)

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                with patch("providers.openai_agent.time.sleep"):
                    mock_client = MagicMock()
                    mock_openai.return_value = mock_client

                    # First call raises rate limit, second succeeds
                    mock_client.chat.completions.create.side_effect = [
                        Exception("Rate limit exceeded"),
                        MagicMock(choices=[MagicMock(message=MagicMock(content="Success"))]),
                    ]

                    from providers.openai_agent import OpenAIAgent
                    agent = OpenAIAgent(config)
                    result = agent.generate_text("Test")

                    assert result == "Success"

    def test_anthropic_handles_overload_error(self):
        """Test that Anthropic agent handles overload errors."""
        config = AgentConfig(name="test", provider="anthropic", max_retries=1)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("providers.anthropic_agent.Anthropic") as mock_anthropic:
                with patch("providers.anthropic_agent.time.sleep"):
                    mock_client = MagicMock()
                    mock_anthropic.return_value = mock_client

                    # First call raises overload, second succeeds
                    mock_client.messages.create.side_effect = [
                        Exception("overloaded_error"),
                        MagicMock(content=[MagicMock(text="Success")]),
                    ]

                    from providers.anthropic_agent import AnthropicAgent
                    agent = AnthropicAgent(config)
                    result = agent.generate_text("Test")

                    assert result == "Success"

    def test_invalid_json_response_raises_error(self):
        """Test that invalid JSON response raises appropriate error."""
        config = AgentConfig(name="test", provider="openai")

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                # Return invalid JSON
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(
                    content="This is not JSON"
                ))]
                mock_client.chat.completions.create.return_value = mock_response

                from providers.openai_agent import OpenAIAgent
                agent = OpenAIAgent(config)

                with pytest.raises(Exception):  # Should raise AgentResponseError
                    agent.generate_json("Generate JSON")
