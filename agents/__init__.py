"""
Claude Code Agents for ATS Resume Checker

This package contains specialized agents that help with development and maintenance:

- integration_tester: Tests end-to-end workflows and detects integration breaks
- [future: test_coverage_analyzer]
- [future: config_validator]
- [future: api_health_checker]
- [future: documentation_auditor]

NOTE: Due to Python's module shadowing, when an agents/ directory exists, it takes
precedence over agents.py during imports. This file re-exports from the root agents.py
module to maintain compatibility.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Workaround: Load the root-level agents.py as a separate module
# This is necessary because this agents/ directory shadows agents.py
parent_dir = str(Path(__file__).parent.parent.absolute())
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    # Import from file explicitly using loader approach
    # We import from a temporary namespace to avoid circular import
    import importlib.util
    agents_py_path = Path(__file__).parent.parent / "agents.py"

    if agents_py_path.exists():
        spec = importlib.util.spec_from_file_location("_agents_core", str(agents_py_path))
        if spec and spec.loader:
            _core = importlib.util.module_from_spec(spec)
            # Register in sys.modules before loading to avoid circular imports
            sys.modules["_agents_core"] = _core
            spec.loader.exec_module(_core)

            # Re-export
            AgentConfig = _core.AgentConfig
            Agent = _core.Agent
            AgentRegistry = _core.AgentRegistry
            AgentError = _core.AgentError
            AgentConfigError = _core.AgentConfigError
            AgentProviderError = _core.AgentProviderError
            AgentResponseError = _core.AgentResponseError
            GeminiAgent = _core.GeminiAgent
            create_agent = _core.create_agent
            strip_markdown_fences = _core.strip_markdown_fences
            ensure_json_object = _core.ensure_json_object

            __all__ = [
                "AgentConfig",
                "Agent",
                "AgentRegistry",
                "AgentError",
                "AgentConfigError",
                "AgentProviderError",
                "AgentResponseError",
                "GeminiAgent",
                "create_agent",
                "strip_markdown_fences",
                "ensure_json_object",
            ]
except Exception as e:
    # Fallback: at least provide the error message
    import warnings
    warnings.warn(f"Failed to re-export from root agents.py: {e}")

__version__ = "0.1.0"
