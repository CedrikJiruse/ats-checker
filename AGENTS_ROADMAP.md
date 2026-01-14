# Claude Code Agents - Development Roadmap

## Overview

Five specialized Claude Code agents designed to enhance development velocity, code quality, and system reliability for the ATS Resume Checker project.

## Agent Ecosystem

```
┌──────────────────────────────────────────────────────────────────┐
│           Claude Code Agent Development Ecosystem                │
└──────────────────────────────────────────────────────────────────┘

       ┌─────────────────────────────────────────────────────┐
       │   Integration & Pipeline Tester (COMPLETED)         │
       │   - Tests end-to-end workflows                      │
       │   - Validates all major components                  │
       │   - Catches integration breaks early                │
       └─────────────────────────────────────────────────────┘
                              │
                              ↓
       ┌─────────────────────────────────────────────────────┐
       │   Test Coverage & Quality Analyzer (PLANNED)        │
       │   - Runs pytest with coverage reports               │
       │   - Identifies untested code paths                  │
       │   - Suggests test improvements                      │
       └─────────────────────────────────────────────────────┘
                              │
                              ↓
       ┌─────────────────────────────────────────────────────┐
       │   Config & Schema Validator (PLANNED)               │
       │   - Validates TOML structure                        │
       │   - Tests profile loading                           │
       │   - Detects config breaking changes                 │
       └─────────────────────────────────────────────────────┘
                              │
                              ↓
       ┌─────────────────────────────────────────────────────┐
       │   API & Dependency Health Checker (PLANNED)         │
       │   - Monitors Gemini API availability                │
       │   - Checks library compatibility                    │
       │   - Validates version support                       │
       └─────────────────────────────────────────────────────┘
                              │
                              ↓
       ┌─────────────────────────────────────────────────────┐
       │   Documentation & Code Auditor (PLANNED)            │
       │   - Checks docstring completeness                   │
       │   - Verifies comment accuracy                       │
       │   - Keeps CLAUDE.md in sync                         │
       └─────────────────────────────────────────────────────┘
```

## Agent Details

### 1. ✅ Integration & Pipeline Tester (COMPLETE)

**Status**: Built and tested

**Purpose**: Validates the complete end-to-end workflow

**Key Tests**:
- Configuration loading (TOML, JSON, profiles)
- State management and persistence
- Resume/job input handling
- Output file generation (TXT, JSON)
- Scoring system accuracy
- Gemini API connectivity
- Concurrent processing

**Usage**:
```bash
python -m agents.integration_tester --mode quick      # 30 seconds
python -m agents.integration_tester --mode full       # 2-5 minutes
python -m agents.integration_tester --mode api-only   # 10 seconds
```

**When to Run**:
- Before committing changes
- After modifying configuration
- When changing core pipeline logic
- Regular CI/CD health checks

**Files**:
- `agents/integration_tester.py` - Implementation
- `agents/README.md` - Documentation
- `AGENTS_QUICKSTART.md` - Quick start guide

---

### 2. Test Coverage & Quality Analyzer (PLANNED)

**Purpose**: Ensure code quality through coverage analysis

**What It Would Do**:
```python
def tests_to_run():
    return [
        "Run pytest with coverage (pytest --cov=.)",
        "Identify uncovered code paths",
        "Suggest tests for new functions",
        "Flag flaky/slow tests",
        "Recommend testability improvements",
    ]
```

**Example Output**:
```
Coverage Report:
  resume_processor.py ........... 85% (3 missing)
  scoring.py ................... 92% (1 missing)
  gemini_integrator.py ......... 78% (5 missing)
  output_generator.py .......... 95%

Suggestions:
  - Add test for ResumeProcessor._iterate_until_target timeout case
  - Improve coverage in scoring.py for edge cases
  - Test concurrent processing with >2 resumes
```

**When to Run**:
- After adding new features
- Before releases
- During code review
- Monthly coverage audits

**Expected Metrics**:
- Run time: 1-2 minutes
- Coverage target: 85%+

---

### 3. Config & Schema Validator (PLANNED)

**Purpose**: Prevent configuration bugs and breaking changes

**What It Would Do**:
```python
def validations():
    return [
        "Load and validate all TOML files",
        "Test profile overlay loading",
        "Verify all config paths exist",
        "Check for unused config keys",
        "Validate CLI override compatibility",
        "Test config migration paths",
    ]
```

**Example Usage**:
```bash
python -m agents.config_validator
python -m agents.config_validator --check-profiles
python -m agents.config_validator --test-migrations
```

**What It Catches**:
```
❌ ISSUES FOUND:

1. Invalid TOML syntax in config/scoring_weights.toml
   Line 42: Missing closing quote in weights.role_alignment

2. Deprecated config key detected
   - max_job_results (deprecated, use job_search.max_job_results_per_search)
   - Found in: 3 tests, 1 config file

3. Path validation failed
   - workspace/nonexistent_path referenced but doesn't exist

4. Profile reference broken
   - config.toml references "config/profiles/custom.toml" (not found)
```

**When to Run**:
- After editing any TOML file
- Before merging config changes
- When releasing new versions
- During onboarding

---

### 4. API & Dependency Health Checker (PLANNED)

**Purpose**: Monitor API health and library compatibility

**What It Would Do**:
```python
def health_checks():
    return [
        "Test Gemini API connectivity",
        "Check API rate limits/quota",
        "Monitor library versions",
        "Detect breaking changes",
        "Validate Python version support",
        "Test fallback behaviors",
    ]
```

**Example Usage**:
```bash
python -m agents.api_health --check-gemini
python -m agents.api_health --check-dependencies
python -m agents.api_health --full
```

**What It Reports**:
```
API Health Status:
  Gemini API ...................... OK (100k req/day remaining)
  Response time ................... 450ms (good)
  Model availability .............. gemini-1.5-flash: OK
                                     gemini-pro: OK

Dependency Health:
  google-generativeai ............ 0.3.5 (latest: 0.3.6 - upgrade available)
  PyPDF2 ......................... 3.17 (OK)
  python-jobspy .................. 1.2.0 (OK, optional)

Compatibility Check:
  Python 3.11 .................... PASS
  Python 3.12 .................... PASS
  Python 3.10 .................... WARN (no longer supported)
```

**When to Run**:
- Daily automated health checks
- Before production deployments
- Debugging API issues
- Quarterly dependency audits

---

### 5. Documentation & Code Auditor (PLANNED)

**Purpose**: Keep code and documentation in sync

**What It Would Do**:
```python
def audits():
    return [
        "Check for missing docstrings",
        "Verify comment accuracy vs code",
        "Update CLAUDE.md for architecture changes",
        "Flag outdated documentation",
        "Validate API documentation completeness",
        "Check config option documentation",
    ]
```

**Example Usage**:
```bash
python -m agents.doc_auditor --check-docstrings
python -m agents.doc_auditor --check-comments
python -m agents.doc_auditor --sync-claude-md
```

**What It Checks**:
```
Documentation Audit Results:

Missing Docstrings:
  ❌ ResumeProcessor._score_for_iteration (public method)
  ❌ GeminiAPIIntegrator._normalize_agents_config (private but important)
  ✓ 247/249 functions documented (99%)

Comment Accuracy:
  ⚠️  resume_processor.py:402 - Comment says "handles up to 100 resumes"
                                 but code limit is 50 (OUTDATED)
  ❌ scoring.py:156 - Comment references removed parameter "legacy_mode"

CLAUDE.md Sync:
  ⚠️  New agent 'scorer' added to config but not documented
  ⚠️  scoring_weights_file moved to [paths] section (update architecture)
  ✓ All major components documented
```

**When to Run**:
- Before code reviews
- Before releases
- When refactoring
- Monthly documentation audits

---

## Development Workflow

### Pre-Commit
```bash
#!/bin/bash
set -e
python -m agents.integration_tester --mode quick
python -m agents.config_validator
echo "✓ Pre-commit checks passed"
```

### Pre-Push
```bash
#!/bin/bash
set -e
python -m agents.integration_tester --mode quick
python -m agents.test_coverage --min-coverage 85
python -m agents.config_validator
python -m agents.api_health --check-gemini
python -m agents.doc_auditor --check-docstrings
echo "✓ All checks passed - ready to push"
```

### CI/CD Pipeline
```yaml
name: Full Agent Suite

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: python -m agents.integration_tester --mode full

  test-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: python -m agents.test_coverage --min-coverage 85

  config-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: python -m agents.config_validator --check-profiles

  api-health:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: python -m agents.api_health --check-gemini
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

  documentation-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: python -m agents.doc_auditor --check-docstrings
```

## Impact Analysis

| Agent | Code Quality | Release Safety | Dev Speed | Maintenance | Priority |
|-------|---|---|---|---|---|
| Integration Tester | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🥇 |
| Test Coverage | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🥈 |
| Config Validator | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🥉 |
| API Health Checker | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | 4️⃣ |
| Doc Auditor | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | 5️⃣ |

## Timeline

| Phase | Agents | Target |
|-------|--------|--------|
| ✅ Phase 1 | Integration & Pipeline Tester | Jan 2025 |
| 📋 Phase 2 | Test Coverage & Config Validator | Jan-Feb 2025 |
| 📋 Phase 3 | API Health & Doc Auditor | Feb-Mar 2025 |

## Resources

- **CLAUDE.md** - Overall project architecture
- **AGENTS_QUICKSTART.md** - Quick start for Integration Tester
- **agents/README.md** - Detailed agent documentation
- **agents/integration_tester.py** - Source code (complete)

## Success Metrics

After all agents are deployed:

✓ 100% test coverage for critical paths
✓ Zero configuration errors in production
✓ <5 minute pre-commit checks
✓ <15 minute CI/CD pipeline
✓ Automated documentation keeping docs in sync
✓ Proactive detection of dependency issues
✓ 50% reduction in integration bugs

---

**Last Updated**: January 2025
**Status**: 1/5 agents complete
**Next**: Test Coverage & Quality Analyzer
