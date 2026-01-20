# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ATS Resume Checker** is a high-performance Rust application that enhances resumes using AI (Gemini, OpenAI, Claude, Llama) and scores them against job descriptions. It combines resume optimization, job scraping, and iterative improvement with a comprehensive scoring system.

> **Note:** This is a Rust rewrite. The original Python implementation is preserved in [`python-original/`](./python-original/) for reference.

## Core Architecture

### Main Data Flow

1. **Input**: Raw resumes (TXT, PDF, DOCX, images with OCR support) + optional job descriptions
2. **Enhancement**: AI API restructures resumes into JSON format
3. **Scoring**: Multi-dimensional scoring system for resume quality and job match
4. **Iteration**: Optional iterative loop to improve scores until target is reached
5. **Output**: Structured files (TOML/JSON) + human-readable TXT files

### Key Modules

**Core Processing Pipeline**
- `src/bin/main.rs`: CLI entry point with interactive and batch modes
- `src/config/`: TOML-based configuration management with profile overlays
- `src/processor/`: Orchestrates the full pipeline: enhancement → scoring → iteration → output
- `src/input/`: Loads resumes (with OCR support), job descriptions, and manages file hashing
- `src/state/`: TOML-backed persistent state tracking to avoid reprocessing

**AI Integration**
- `src/agents/`: Multi-provider agent abstraction (Gemini, OpenAI, Claude, Llama)
- `src/gemini/`: Google Gemini API client implementation

**Output & Artifacts**
- `src/output/`: Generates TXT, JSON, and TOML output files
- `src/scoring/`: Multi-category scoring system (resume quality + job match scoring)
- `src/recommendations/`: Generates actionable improvement suggestions from scores

**Job Search & Scraping**
- `src/scraper/`: Job scraping across multiple sites (LinkedIn, Indeed, Glassdoor, etc.)
  - `types.rs`: JobPosting, SearchFilters, SavedSearch data structures
  - `manager.rs`: Unified scraping interface

**Utilities**
- `src/utils/`: File hashing, text extraction, validation helpers
- `src/validation/`: JSON schema validation with retry logic
- `src/error.rs`: Comprehensive error types with 30+ variants

## Configuration

Configuration uses **TOML format** (default: `config/config.toml`).

### Key Configuration Areas

**Processing Settings**:
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
Defined in `[ai.agents.*]` sections with role, provider, model_name for: enhancer, job_summarizer, scorer, reviser.

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
cargo run --release

# With custom config
cargo run --release -- --config path/to/config.toml
```

### CLI Subcommands

```bash
# Score a single resume
cargo run --release -- score-resume --resume path/to/resume.toml --weights config/scoring_weights.toml

# Score resume-job match
cargo run --release -- score-match --resume path/to/resume.toml --job path/to/job.txt --weights config/scoring_weights.toml

# Rank jobs by score
cargo run --release -- rank-jobs --results path/to/results.toml --weights config/scoring_weights.toml --top 20
```

See `src/cli/mod.rs` for implementation.

## Testing

### Running Tests

```bash
# Run all tests
cargo test

# Run specific test
cargo test test_job_posting_creation

# Run with output
cargo test -- --nocapture

# Run with logging
RUST_LOG=debug cargo test
```

### Test Coverage

Currently being developed. Tests will cover:
- `tests/test_scoring.rs`: Scoring algorithms
- `tests/test_config.rs`: Configuration loading
- `tests/test_state.rs`: State persistence
- `tests/test_scraper.rs`: Job scraping
- Integration tests for full pipeline

## Code Organization

### Directory Structure

```
ats-checker/
├── src/
│   ├── lib.rs                   # Library entry point
│   ├── bin/main.rs              # CLI binary
│   ├── error.rs                 # Error types (30+ variants)
│   ├── config/                  # Configuration management
│   │   └── mod.rs              # Config struct with TOML loading
│   ├── state/                   # State persistence
│   │   └── mod.rs              # StateManager with atomic writes
│   ├── agents/                  # LLM agent abstraction
│   │   ├── mod.rs              # Agent trait
│   │   └── registry.rs         # Multi-provider registry
│   ├── scoring/                 # Scoring algorithms
│   │   ├── mod.rs              # Main scoring functions
│   │   ├── resume.rs           # Resume quality scoring
│   │   ├── job.rs              # Job posting scoring
│   │   └── match.rs            # Resume-job match scoring
│   ├── scraper/                 # Job scraping
│   │   ├── mod.rs
│   │   ├── types.rs            # JobPosting, SearchFilters
│   │   └── manager.rs          # Scraping interface
│   ├── processor/               # Resume processing pipeline
│   ├── input/                   # Input handling
│   ├── output/                  # Output generation
│   ├── recommendations/         # Improvement suggestions
│   ├── validation/              # Schema validation
│   ├── utils/                   # Utilities
│   │   ├── hash.rs             # SHA256 file hashing
│   │   └── text.rs             # Text extraction
│   ├── gemini/                  # Gemini API client
│   ├── toml_io/                 # TOML I/O utilities
│   └── cli/                     # CLI interface
├── config/
│   ├── config.toml              # Main configuration (TOML)
│   ├── scoring_weights.toml     # Scoring category weights
│   └── profiles/
│       ├── safe.toml            # Conservative profile
│       └── aggressive.toml      # Aggressive profile
├── workspace/
│   ├── input_resumes/           # User-provided resumes
│   ├── job_descriptions/        # Job descriptions for tailoring
│   ├── output/                  # Generated outputs
│   └── job_search_results/      # Saved job search results
├── data/
│   ├── processed_resumes_state.toml # Resume processing state
│   └── saved_searches.toml      # Saved job search configurations
├── tests/                       # Test suite
├── python-original/             # Original Python implementation
├── Cargo.toml                   # Rust dependencies
└── RUST_REWRITE_TODO.md        # Rewrite progress checklist (1600+ items)
```

## Important Implementation Details

### Error Handling

All errors use the `AtsError` enum defined in `src/error.rs` with 30+ variants:
- Configuration errors (ConfigNotFound, ConfigParse, ConfigValidation)
- I/O errors (Io, FileNotFound, PermissionDenied)
- API errors (ApiRequest, ApiResponse, ApiAuth, ApiRateLimit)
- Scoring errors (Scoring, ScoringWeights)
- State errors (StateCorrupted, StateOperation)

The `Result<T>` type alias is `std::result::Result<T, AtsError>`.

### State Management

**StateManager** (`src/state/mod.rs`) tracks processed resumes by content hash:
- Stores mapping: `file_hash` → `output_path` in TOML
- Uses atomic file writes (write to .tmp, then rename)
- Enables resuming interrupted runs
- Auto-migrates from legacy JSON format

### Resume Processing Workflow

1. **Input**: Scan folder for new/modified resumes (via SHA256 hash comparison)
2. **Enhancement**: Send to AI to restructure into JSON format
3. **Schema Validation** (optional): Validate output, retry if needed
4. **Iteration** (optional): Revise until target score reached using configured strategy
5. **Scoring**: Compute resume quality + job match scores
6. **Recommendations** (optional): Generate improvement suggestions
7. **Output**: Write structured (TOML/JSON) + text TXT files
8. **Artifacts**: Write manifest and score summary files
9. **State Update**: Record hash → output path to prevent reprocessing

### Scoring System

**Three-tier scoring model** (all implemented in `src/scoring/`):
- **Resume Score**: Evaluates resume quality (structure, keywords, impact)
  - Categories: completeness, skills_quality, experience_quality, impact
- **Job Score**: Evaluates job posting quality
  - Categories: completeness, clarity, compensation_transparency, link_quality
- **Match Score**: Evaluates resume-job alignment
  - Categories: keyword_overlap, skills_overlap, role_alignment
- **Iteration Score**: Combines resume + match scores (weighted)

Each score report includes category breakdowns with weights and sample details.

### Iteration Strategies

- **best_of** (default): Keep best candidate seen, stop on target/no_progress/max_iterations
- **first_hit**: Stop immediately when target score reached
- **patience**: Stop if no improvement for N consecutive iterations (more stable)

### Output File Organization

Pattern configurable via `output_subdir_pattern` (default: `{resume_name}/{job_title}/{timestamp}`).

Example structure:
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

**Supported sources**: LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter

SearchFilters support: keywords, location, job_type, remote_only, experience_level, date_posted, salary_min

Results saved with optional scoring for ranking by relevance.

## Development Workflow

1. **Config changes**: Update `config/config.toml` or create a profile in `config/profiles/`
2. **New scoring categories**: Add to `config/scoring_weights.toml` and update `src/scoring/`
3. **AI prompt tuning**: Modify agent prompts in `src/agents/`
4. **Output format changes**: Update `src/output/` formatting logic
5. **New job sources**: Implement in `src/scraper/` + add to tests
6. **Error handling**: Add new variants to `src/error.rs` AtsError enum

Always run `cargo test && cargo clippy` before committing.

## Rust-Specific Notes

- **Async/await**: Uses tokio runtime for async operations
- **Error handling**: thiserror for error definitions, anyhow for error context
- **Serialization**: serde for JSON/TOML (de)serialization
- **Type safety**: Extensive use of Rust's type system to prevent bugs at compile time
- **Performance**: Zero-copy parsing, efficient hashing, true parallelism
- **Dependencies**: See `Cargo.toml` for full list (40+ crates)

## Current Status

This is an **active rewrite**. See [RUST_REWRITE_TODO.md](./RUST_REWRITE_TODO.md) for detailed progress (1600+ items across 20 phases).

Completed:
- ✅ Project structure and build system
- ✅ Error types and Result aliases
- ✅ Configuration management with TOML
- ✅ State management with persistence
- ✅ Core data structures (JobPosting, SearchFilters, Config)

In Progress:
- 🚧 Scoring algorithms implementation
- 🚧 Agent trait and registry system
- 🚧 Resume processing pipeline

For Python implementation details, see [python-original/README_PYTHON.md](./python-original/README_PYTHON.md).
