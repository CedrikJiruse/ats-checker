# Claude Code Agents - Quick Start

## What Was Built

A **Integration & Pipeline Tester** agent that validates the complete end-to-end workflow of the ATS Resume Checker application. This is the first of 5 planned development agents.

## Installation

No installation needed! The agent is built-in. Just run:

```bash
cd /path/to/ats-checker
python -m agents.integration_tester --mode quick
```

## Usage

### Quick Test (30 seconds)
Tests critical path - config loading, state management, and scoring:
```bash
python -m agents.integration_tester --mode quick
```

**Use case**: Before committing code, after modifying config, quick health check.

### Full Test (2-5 minutes, requires GEMINI_API_KEY)
Complete integration test suite including API connectivity:
```bash
python -m agents.integration_tester --mode full
```

**Use case**: Before major commits, validating new features, CI/CD pipelines.

### API-Only Test (10 seconds)
Just test Gemini API connectivity:
```bash
python -m agents.integration_tester --mode api-only
```

**Use case**: Debugging API issues, checking quota, validating credentials.

## What It Tests

| Component | What's Tested |
|-----------|---|
| **Config System** | TOML loading, nested sections, defaults, profiles |
| **State Manager** | TOML persistence, hash tracking, state retrieval |
| **Input Handling** | Resume parsing, text extraction |
| **Output Generation** | File creation (TXT, JSON), directory structure |
| **Scoring System** | Resume quality, job match scoring, categories |
| **API Integration** | Gemini connectivity, agent initialization, model availability |
| **Concurrency** | Multi-threaded resume processing |

## Example Output

```
================================================================================
INTEGRATION TEST RESULTS
================================================================================

Quick Tests: 3/3 passed (0.01s)
--------------------------------------------------------------------------------
[PASS]   | config_loading                 |    0.01s
         | -> output_folder: C:\...\workspace\output
         | -> model_name: gemini-1.5-flash-latest
         | -> agents: ['enhancer', 'job_summarizer', 'scorer', 'reviser']
[PASS]   | state_manager                  |    0.00s
         | -> state_file: C:\...\ats_test_state.toml
[PASS]   | scoring_system                 |    0.00s
         | -> resume_score: 63.48
         | -> match_score: 63.95
         | -> resume_categories: 4
         | -> match_categories: 3

================================================================================
SUMMARY: 3 passed, 0 failed
================================================================================
```

## Integration with Your Workflow

### Pre-Commit Hook
```bash
#!/bin/bash
python -m agents.integration_tester --mode quick || exit 1
```

### GitHub Actions CI
```yaml
- name: Run integration tests
  run: python -m agents.integration_tester --mode full
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

### Local Development
```bash
# After making changes
python -m agents.integration_tester --mode quick

# Before pushing
python -m agents.integration_tester --mode full
```

## Troubleshooting

### "GEMINI_API_KEY not set"
```bash
export GEMINI_API_KEY="your-api-key"
python -m agents.integration_tester --mode full
```

### Tests running slowly
- Use `--mode quick` for fast feedback
- Full tests may take 2-5 minutes due to API calls

### Import errors
```bash
# Make sure you're in the project root
cd /path/to/ats-checker
python -m agents.integration_tester --mode quick
```

## What's Next

Planned agents (coming soon):
1. ✅ **Integration & Pipeline Tester** (built)
2. **Test Coverage & Quality Analyzer** - Identifies untested code paths
3. **Config & Schema Validator** - Validates TOML structure
4. **API & Dependency Health Checker** - Monitors Gemini API and libraries
5. **Documentation & Code Auditor** - Keeps docs in sync

## Architecture Notes

The agent follows a modular test pattern:

```
1. Setup        -> Create temp workspace, load sample data
2. Execute      -> Run individual component tests
3. Collect      -> Gather results with timing and details
4. Report       -> Print structured output with metrics
5. Cleanup      -> Remove temporary artifacts
```

This makes it easy to:
- Add new tests
- Run tests independently
- Extend with more agents
- Integrate with CI/CD

## File Structure

```
agents/
├── __init__.py                 # Package initialization
├── README.md                   # Detailed agent documentation
├── integration_tester.py       # The integration tester agent
└── [future agents...]
```

## Key Features

✓ **Fast feedback** - Quick mode runs in ~30 seconds
✓ **Cross-platform** - Works on Windows, Mac, Linux (Windows-safe output)
✓ **Minimal setup** - No extra dependencies needed
✓ **Realistic data** - Uses sample resumes and job descriptions
✓ **Detailed reporting** - Shows exactly what passed/failed with metrics
✓ **Easy integration** - Ready for CI/CD, git hooks, local development

---

For more details, see `agents/README.md`.
