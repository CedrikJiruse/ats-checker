# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ATS Resume Checker** is a Python application that enhances resumes using AI (Gemini API) and scores them against job descriptions. It combines resume optimization, job scraping, and iterative improvement with a comprehensive scoring system.

## Core Architecture

### Main Data Flow

1. **Input**: Raw resumes (TXT, PDF, DOCX, images with OCR support) + optional job descriptions
2. **Enhancement**: Gemini API restructures resumes into JSON format
3. **Scoring**: Multi-dimensional scoring system for resume quality and job match
4. **Iteration**: Optional iterative loop to improve scores until target is reached
5. **Output**: Structured files (TOML/JSON) + human-readable TXT files

### Key Modules

**Core Processing Pipeline**
- `main.py`: Interactive CLI menu + entry point for both menu and batch modes
- `config.py`: TOML-based configuration management with backward-compatible JSON support, profile overlays
- `resume_processor.py`: Orchestrates the full pipeline: enhancement → scoring → iteration → output
- `input_handler.py`: Loads resumes (with OCR support for images), job descriptions, and manages file hashing
- `state_manager.py`: TOML-backed persistent state tracking to avoid reprocessing

**AI Integration**
- `gemini_integrator.py`: Multi-agent interface to Google Gemini API (enhancement, revision, summarization)

**Output & Artifacts**
- `output_generator.py`: Generates TXT, JSON, and TOML output files with configurable layout patterns
- `scoring.py`: Multi-category scoring system (resume quality + job match scoring)
- `recommendations.py`: Generates actionable improvement suggestions from scores

**Job Search & Scraping**
- `job_scraper_manager.py`: Unified interface for job scraping across multiple sites
- `job_scraper_base.py`: Data structures (JobPosting, SearchFilters)
- `saved_search_manager.py`: Persistence layer for saved searches

**Utilities**
- `utils.py`: File hashing, text extraction, validation helpers
- `schema_validation.py`: JSON schema validation with best-effort retry

## Configuration

Configuration uses **TOML as primary format** (default: `config/config.toml`). Legacy JSON configs are auto-migrated.

### Key Configuration Areas

**Processing Settings** (`config.py` defaults section):
- Resume enhancement versions per job: `num_versions_per_job`
- Iterative improvement: `iterate_until_score_reached`, `target_score`, `max_iterations`, `iteration_strategy` (best_of/first_hit/patience)
- Output format: `structured_output_format` (json/toml/both)
- Schema validation: `schema_validation_enabled`, `resume_schema_path`
- Recommendations: `recommendations_enabled`, `recommendations_max_items`
- Performance: `max_concurrent_requests`, `score_cache_enabled`

**Paths** (relative paths expand to absolute):
- `input_resumes_folder`: Source resumes
- `job_descriptions_folder`: Job descriptions for tailoring
- `output_folder`: Where outputs are written
- `state_file`: Tracks processed resumes (TOML)
- `scoring_weights_file`: Weights for scoring categories

**Multi-Agent Configuration**:
Defined in `ai.agents` section as nested tables with role, provider, model_name for: enhancer, job_summarizer, scorer, reviser.

### Profile Overlays

Config can reference a profile overlay file via:
```toml
[profile]
file = "config/profiles/safe.toml"
```

Profiles are loaded before the main config, allowing preset configurations.

## Running the Application

### Interactive Mode (Default)

```bash
# With default config (config/config.toml)
python main.py

# With custom config
python main.py --config_file path/to/config.toml
```

The menu provides:
1. Process resumes (all/with job description/specific resume)
2. Convert files to standard format
3. Job search & scraping
4. View/edit settings
5. View available files
6. View generated outputs
7. Test OCR functionality

### Batch Mode (Legacy CLI)

```bash
# Process resumes tailored to a specific job description
python main.py --config_file config/config.toml --job_description "job_title.txt"
```

### Specialized CLI Subcommands

```bash
# Score a single resume
python main.py score-resume --resume path/to/resume.json --weights config/scoring_weights.toml

# Score resume-job match
python main.py score-match --resume path/to/resume.json --job path/to/job.json --weights config/scoring_weights.toml

# Rank jobs by score
python main.py rank-jobs --results path/to/results.json --weights config/scoring_weights.toml
```

See `cli_commands.py` for implementation.

## Testing

### Running Tests

```bash
# Run all tests with pytest (recommended)
python -m pytest -q

# Run specific test class
python -m pytest tests/test_job_scrapers.py::TestJobSpyScraperIsRemote -v

# Run single test
python -m pytest tests/test_job_scrapers.py::TestJobSpyScraperIsRemote::test_remote_only_true_passes_is_remote -v

# Run with unittest (alternative)
python -m unittest tests.test_job_scrapers -v
```

### Test Coverage

- `tests/test_job_scrapers.py`: Job scraping, data validation, JobSpy integration
- `tests/test_resume_processor.py`: Resume processing orchestration
- `tests/test_output_generator.py`: Output generation (TXT/JSON/TOML)
- `tests/test_state_manager.py`: State persistence
- `tests/test_config_profiles.py`: Config & profile loading
- `tests/test_resume_processor_artifacts.py`: Artifacts (manifest, scores)
- `tests/test_resume_processor_score_cache.py`: Score caching

**Known Issue**: When `python-jobspy` is installed, it pulls heavy dependencies (numpy/pandas). Unit tests use mocks to avoid importing these during test discovery.

## Code Organization

### Directory Structure (Key Files)

```
ats-checker/
├── main.py                          # Interactive menu + batch entry point
├── config.py                        # Configuration management
├── resume_processor.py              # Main processing pipeline
├── gemini_integrator.py             # AI agent integration
├── output_generator.py              # Output generation (TXT/JSON/TOML)
├── scoring.py                       # Resume + job match scoring
├── job_scraper_manager.py           # Job scraping interface
├── input_handler.py                 # Resume/job input + OCR
├── state_manager.py                 # State tracking (TOML-backed)
├── utils.py                         # Utility functions
├── cli_commands.py                  # Specialized CLI subcommands
├── config/
│   ├── config.toml                  # Main configuration (TOML)
│   ├── scoring_weights.toml         # Scoring category weights
│   └── profiles/
│       ├── safe.toml                # Conservative profile
│       └── aggressive.toml          # Aggressive profile
├── workspace/
│   ├── input_resumes/               # User-provided resumes
│   ├── job_descriptions/            # Job descriptions for tailoring
│   ├── output/                      # Generated outputs
│   └── job_search_results/          # Saved job search results
├── data/
│   ├── processed_resumes_state.toml # Resume processing state
│   └── saved_searches.toml          # Saved job search configurations
└── tests/                           # Comprehensive test suite
```

## Important Implementation Details

### State Management

**StateManager** (`state_manager.py`) tracks processed resumes by content hash to avoid reprocessing:
- Stores mapping: `file_hash` → `output_path` in TOML
- Called after each resume is successfully processed
- Enables resuming interrupted runs

### Resume Processing Workflow

1. **Input**: Scan folder for new/modified resumes (via hash comparison)
2. **Enhancement**: Send to Gemini to restructure into JSON format
3. **Schema Validation** (optional): Validate output, retry if needed
4. **Iteration** (optional): Revise until target score reached using configured strategy
5. **Scoring**: Compute resume quality + job match scores
6. **Recommendations** (optional): Generate improvement suggestions
7. **Output**: Write structured (TOML/JSON) + text TXT files
8. **Artifacts**: Write manifest and score summary files
9. **State Update**: Record hash → output path to prevent reprocessing

### Scoring System

**Three-tier scoring model**:
- **Resume Score**: Evaluates resume quality (structure, keywords, impact)
- **Job Score**: Evaluates job posting quality
- **Match Score**: Evaluates resume-job alignment (keyword overlap, skill relevance)
- **Iteration Score**: Combines resume + match scores (weighted)

Each score report includes category breakdowns (e.g., keyword_overlap, skill_alignment) with weights and sample details (matched/missing keywords).

### Iteration Strategies

- **best_of** (default): Keep best candidate seen, stop on target/no_progress/max_iterations
- **first_hit**: Stop immediately when target score reached
- **patience**: Stop if no improvement for N consecutive iterations (more stable)

Regression tracking prevents poor candidates. Optional early stopping on too many regressions.

### Output File Organization

Pattern configurable via `output_subdir_pattern` (default: `{resume_name}/{job_title}/{timestamp}`).

Example structure for a resume:
```
output/
└── John_Doe/
    └── Software_Engineer/
        └── 20240115_120345/
            ├── John_Doe_Software_Engineer_enhanced.toml
            ├── John_Doe_Software_Engineer_enhanced.json
            ├── John_Doe_Software_Engineer_enhanced.txt
            ├── scores.toml
            └── manifest.toml
```

### Job Scraping Integration

**Supported sources**: LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter (via JobSpy library).

SearchFilters support: keywords, location, job_type, remote_only, experience_level, date_posted.

Results saved with optional scoring for ranking by relevance.

## Common Development Tasks

### Running a Single Resume Processing Test

```bash
# Create a test resume in workspace/input_resumes/
echo "Your resume content..." > workspace/input_resumes/test_resume.txt

# Run interactively, select option 1 (Process all resumes)
python main.py

# Or batch mode with job description
python main.py --job_description "your_job.txt"
```

### Testing Configuration Changes

```bash
# Edit config/config.toml, then reload in interactive menu (option 4)
# Or pass overrides via CLI:
python main.py --config_file config/config.toml --num_versions_per_job 2 --target_score 75.0
```

### Debugging Score Issues

```bash
# Use specialized CLI to score an existing resume
python main.py score-resume --resume output/path/to/resume.json --weights config/scoring_weights.toml
```

### Checking Processed State

View `data/processed_resumes_state.toml` to see which resumes have been processed and their output paths.

## TOML Configuration Files

**Primary Config** (`config/config.toml`):
- Nested sections: `[paths]`, `[ai]`, `[processing]`, `[job_search]`
- Multi-agent definitions in `[ai.agents.*]`
- Profile overlay reference: `[profile] file = "..."`

**Scoring Weights** (`config/scoring_weights.toml`):
- Defines scoring categories and their weights
- Used by `scoring.py` to compute scores
- Format: `[scoring_weights]` section with category definitions

**State Files** (TOML-backed):
- `data/processed_resumes_state.toml`: Maps resume hashes to output paths
- `data/saved_searches.toml`: Saved job search configurations

**Output Artifacts** (TOML):
- `manifest.toml`: Metadata about a processing run (resume name, job, timestamp, versions)
- `scores.toml`: Detailed scoring breakdown in TOML-friendly format

## Performance Considerations

- **Concurrency**: Set `max_concurrent_requests` for parallel resume processing (I/O bound)
- **Score Caching**: Enable `score_cache_enabled` to avoid recomputing scores during iteration
- **OCR**: Only triggers on image inputs; optional Tesseract configuration via `tesseract_cmd`
- **Heavy Dependencies**: JobSpy scraping is optional; tests use mocks to avoid numpy/pandas

## Development Workflow

1. **Config changes**: Update `config/config.toml` or create a profile in `config/profiles/`
2. **New scoring categories**: Add to `config/scoring_weights.toml` and update `scoring.py`
3. **AI prompt tuning**: Modify agent prompts in `gemini_integrator.py`
4. **Output format changes**: Update `output_generator.py` formatting logic
5. **New job sources**: Implement in `job_scraper_manager.py` + add to tests
6. **New features**: Add CLI subcommands in `cli_commands.py`

Always run `pytest -q` before committing to ensure tests pass.
