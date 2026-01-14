# Claude Code Agents

Specialized development and testing agents for the ATS Resume Checker project.

## Available Agents

### 1. Integration & Pipeline Tester

**Purpose**: Validates the complete end-to-end workflow including configuration loading, state management, input handling, output generation, scoring, and API connectivity.

**Features**:
- Tests all major components in isolation
- Validates configuration loading (TOML + profiles)
- Tests state management and persistence
- Validates input file handling
- Verifies output generation (TXT, JSON)
- Tests scoring system with sample data
- Checks Gemini API connectivity
- Tests concurrent processing capability

**Usage**:

```bash
# Quick sanity checks (30 seconds)
python -m agents.integration_tester --mode quick

# Full integration tests (2-5 minutes, requires GEMINI_API_KEY)
python -m agents.integration_tester --mode full

# API connectivity only
python -m agents.integration_tester --mode api-only
```

**What It Tests**:

| Test | What It Checks | Quick | Full | API-Only |
|------|---|---|---|---|
| Config Loading | TOML/JSON parsing, nested sections, defaults | ✓ | ✓ | ✓ |
| State Manager | TOML persistence, hash tracking | ✓ | ✓ | |
| Input Handler | Resume parsing, text extraction | | ✓ | |
| Output Generator | File creation (TXT, JSON), directory structure | | ✓ | |
| Scoring System | Resume quality, job match, categories | ✓ | ✓ | |
| Gemini API | API key, agent initialization, connectivity | | ✓ | ✓ |
| Concurrency | Multi-threaded processing | | ✓ | |

**When to Run**:
- After making changes to configuration system
- Before committing changes to core pipeline
- After updating dependencies
- When onboarding new features
- Regular health checks (schedule CI/CD job)

**Example Output**:
```
================================================================================
INTEGRATION TEST RESULTS
================================================================================

Quick Tests: 3/3 passed (2.34s)
--------------------------------------------------------------------------------
✓ PASS | config_loading                     |    0.12s
         | → output_folder: /home/user/output
         | → model_name: gemini-pro
         | → agents: ['enhancer', 'reviser', 'job_summarizer']
✓ PASS | state_manager                      |    0.08s
         | → state_file: /tmp/.../state.toml
✓ PASS | scoring_system                     |    0.45s
         | → resume_score: 78.5
         | → match_score: 82.3
         | → resume_categories: 4
         | → match_categories: 3

================================================================================
SUMMARY: 3 passed, 0 failed
================================================================================
```

## Planned Agents

### 2. Test Coverage & Quality Analyzer
- Runs pytest with coverage reports
- Identifies untested code paths
- Suggests new test cases
- Detects flaky/slow tests

### 3. Config & Schema Validator
- Validates TOML structure against schema
- Tests profile loading
- Verifies path accessibility
- Detects config breaking changes

### 4. API & Dependency Health Checker
- Tests Gemini API quota and rate limits
- Monitors dependency compatibility
- Checks Python version support
- Tests API fallback behavior

### 5. Documentation & Code Comment Auditor
- Checks docstring completeness
- Verifies code comments accuracy
- Updates CLAUDE.md for architectural changes
- Flags outdated documentation

## Integration with Development Workflow

### Pre-Commit Hook

```bash
#!/bin/bash
python -m agents.integration_tester --mode quick || exit 1
```

### CI/CD Pipeline

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: pip install -r requirements.txt
      - run: python -m agents.integration_tester --mode full
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

## Creating a New Agent

To add a new agent:

1. Create a new file: `agents/my_agent.py`
2. Inherit from or implement test logic similar to `IntegrationTester`
3. Add CLI entry point with `--mode` options
4. Document in this README
5. Add to GitHub Actions if needed

## Troubleshooting

### ImportError when running tests

```bash
# Make sure you're in the project root
cd /path/to/ats-checker
python -m agents.integration_tester --mode quick
```

### GEMINI_API_KEY not found

```bash
# Set the environment variable
export GEMINI_API_KEY="your-key-here"
python -m agents.integration_tester --mode full
```

### Temp files not cleaned up

```bash
# Manual cleanup
python -m agents.integration_tester --cleanup
# Or remove manually
rm -rf /tmp/ats_integration_test_*
```

## Architecture Notes

Each agent follows a similar pattern:

1. **Setup**: Create test environment, mock data
2. **Execute**: Run individual test functions
3. **Collect**: Gather results with timing and details
4. **Report**: Print structured output with metrics
5. **Cleanup**: Remove temporary artifacts

This ensures consistency and makes it easy to add new agents.
