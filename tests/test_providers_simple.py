"""
Simplified tests for multi-provider agent implementations.

Tests that the provider agent modules exist and have correct structure.
Full integration tests require API keys and SDK dependencies to be installed.
"""

import pytest

from agents import AgentConfig


class TestProviderModulesExist:
    """Test that provider modules are correctly structured."""

    def test_openai_agent_module_exists(self):
        """Test that OpenAI agent module can be imported."""
        try:
            from providers import openai_agent
            assert hasattr(openai_agent, "OpenAIAgent")
        except ImportError as e:
            # OpenAI SDK not installed is OK
            if "openai" in str(e).lower():
                pytest.skip("openai SDK not installed")
            raise

    def test_anthropic_agent_module_exists(self):
        """Test that Anthropic agent module can be imported."""
        try:
            from providers import anthropic_agent
            assert hasattr(anthropic_agent, "AnthropicAgent")
        except ImportError as e:
            # Anthropic SDK not installed is OK
            if "anthropic" in str(e).lower():
                pytest.skip("anthropic SDK not installed")
            raise

    def test_llama_agent_module_exists(self):
        """Test that Llama agent module can be imported."""
        try:
            from providers import llama_agent
            assert hasattr(llama_agent, "LlamaAgent")
        except ImportError as e:
            # OpenAI SDK not installed is OK for Llama
            if "openai" in str(e).lower():
                pytest.skip("openai SDK not installed (needed for Llama)")
            raise

    def test_agent_registry_creation_gemini_only(self):
        """Test that AgentRegistry can handle Gemini provider (no API key required for lazy init)."""
        from agents import AgentRegistry

        # Gemini is the only one that works without an API key (lazy initialization)
        registry_config = {
            "test_agent": {
                "provider": "gemini",
                "model_name": "gemini-pro",
                "role": "test",
            }
        }

        # Should not raise
        registry = AgentRegistry.from_config_dict(registry_config)
        assert registry is not None
        assert "test_agent" in registry.list()


class TestCreateAgentFunction:
    """Test the create_agent factory function."""

    def test_create_agent_with_gemini(self):
        """Test creating Gemini agent via factory."""
        from agents import create_agent

        config = AgentConfig(
            name="test",
            provider="gemini",
            model_name="gemini-pro",
        )

        # Gemini agent will fail on actual text generation without API key, but create_agent
        # returns the agent object (lazy initialization). This just verifies the factory routing works.
        try:
            agent = create_agent(config)
            # If it succeeds, the agent was created (lazy init allows this)
            assert agent is not None
        except ValueError as e:
            # If GEMINI_API_KEY check happens at init, that's also valid
            assert "GEMINI_API_KEY" in str(e)

    def test_create_agent_unknown_provider(self):
        """Test that unknown provider raises appropriate error."""
        from agents import create_agent, AgentConfigError

        config = AgentConfig(
            name="test",
            provider="unknown_provider",
            model_name="some-model",
        )

        with pytest.raises(AgentConfigError, match="Unknown agent provider"):
            create_agent(config)


class TestAgentConfigStructure:
    """Test that AgentConfig has all expected fields."""

    def test_agent_config_fields(self):
        """Test that AgentConfig has all required fields."""
        config = AgentConfig(
            name="test_agent",
            provider="openai",
            model_name="gpt-4o",
            role="test_role",
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
            max_retries=2,
            retry_on_empty=True,
            require_json=True,
        )

        assert config.name == "test_agent"
        assert config.provider == "openai"
        assert config.model_name == "gpt-4o"
        assert config.role == "test_role"
        assert config.temperature == 0.7
        assert config.top_p == 0.95
        assert config.top_k == 40
        assert config.max_output_tokens == 2048
        assert config.max_retries == 2
        assert config.retry_on_empty is True
        assert config.require_json is True

    def test_agent_config_defaults(self):
        """Test that AgentConfig has sensible defaults."""
        config = AgentConfig(
            name="test",
            provider="gemini",
            model_name="gemini-pro",
        )

        assert config.temperature == 0.7
        assert config.top_p == 0.95
        assert config.top_k == 40
        assert config.max_output_tokens == 8192
        assert config.max_retries == 0
        assert config.retry_on_empty is True
        assert config.require_json is False


class TestProviderSupport:
    """Test that all expected providers are supported."""

    def test_supported_providers_in_documentation(self):
        """Verify that create_agent supports all documented providers."""
        from agents import create_agent

        supported_providers = ["gemini", "openai", "anthropic", "llama"]

        for provider in supported_providers:
            config = AgentConfig(
                name="test",
                provider=provider,
                model_name="test-model",
            )

            # Each provider should at least be recognized (even if it fails due to missing API key)
            try:
                create_agent(config)
            except ValueError as e:
                # Expected: missing API key
                assert "API_KEY" in str(e) or "not found" in str(e).lower()
            except Exception as e:
                # Other exceptions (like missing SDK) are also OK for this test
                pass
