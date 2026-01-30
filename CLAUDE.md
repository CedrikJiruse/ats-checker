# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ATS Resume Checker** is a high-performance Rust application that enhances resumes using AI (Gemini, OpenAI, Claude, Llama) and scores them against job descriptions. It combines resume optimization, job scraping, and iterative improvement with a comprehensive scoring system.

**Current Status:** 71% Complete (1130/1600 items) | 296 Tests Passing | Zero Warnings

> **Note:** This is a Rust rewrite. The original Python implementation is preserved in [`python-original/`](./python-original/) for reference.

## Essential Commands

### Development
```bash
# Build (development)
cargo build

# Build (optimized release)
cargo build --release

# Run with default config
cargo run --release

# Run with custom config
cargo run --release -- --config path/to/config.toml

# Enable debug logging
RUST_LOG=debug cargo run
```

### Testing
```bash
# Run all tests (296 total: 111 unit + 163 integration + 22 doc)
cargo test

# Run specific test file
cargo test --test test_scoring

# Run specific test by name
cargo test test_hash_consistency

# Run tests with output
cargo test -- --nocapture

# Run tests with logging
RUST_LOG=debug cargo test

# Run only unit tests (in src/)
cargo test --lib

# Run only integration tests (in tests/)
cargo test --test '*'

# Run only doc tests
cargo test --doc
```

### Code Quality
```bash
# Check for issues (fast)
cargo check

# Lint with clippy (treat warnings as errors)
cargo clippy --all-targets --all-features -- -D warnings

# Format code
cargo fmt

# Check formatting without changing files
cargo fmt -- --check

# Generate documentation
cargo doc --no-deps

# Generate and open docs in browser
cargo doc --no-deps --open
```

### Benchmarking
```bash
# Run all benchmarks
cargo bench

# Run specific benchmark
cargo bench hashing

# Run scoring benchmarks
cargo bench scoring

# Run TOML I/O benchmarks
cargo bench toml_io
```

**Available benchmarks:**
- `benches/hashing.rs` - String and bytes hashing (100 to 100K bytes)
- `benches/scoring.rs` - Resume, job, and match scoring
- `benches/toml_io.rs` - TOML dumps/loads (small, medium, large data)

### CLI Subcommands
```bash
# Score a resume
cargo run --release -- score-resume --resume output/resume.toml --weights config/scoring_weights.toml

# Score resume-job match
cargo run --release -- score-match --resume output/resume.toml --job workspace/job.txt --weights config/scoring_weights.toml

# Rank jobs by score
cargo run --release -- rank-jobs --results workspace/results.toml --weights config/scoring_weights.toml --top 20
```

## Core Architecture

### Main Data Flow

1. **Input**: Raw resumes (TXT, PDF, DOCX, images via OCR) + optional job descriptions
2. **Enhancement**: AI API restructures resumes into JSON format
3. **Scoring**: Multi-dimensional scoring system for resume quality and job match
4. **Iteration**: Optional iterative loop to improve scores until target is reached
5. **Output**: Structured files (TOML/JSON) + human-readable TXT files

### Critical Architectural Patterns

**State Management via Content Hashing**
- Resumes are hashed (SHA256) to detect changes
- `StateManager` maintains hash → output_path mapping in TOML
- Atomic writes prevent corruption (write to .tmp, then rename)
- Enables resuming interrupted runs without reprocessing

**Multi-Agent System**
- `Agent` trait abstracts different LLM providers (Gemini, OpenAI, Claude, Llama)
- `AgentRegistry` manages multiple specialized agents (enhancer, scorer, reviser)
- Each agent has configurable role, model, temperature, retry logic
- Defined in `src/agents/mod.rs` and configured via `config.toml`

**Three-Tier Scoring Model**
1. **Resume Score**: Quality metrics (completeness, skills, experience, impact)
2. **Job Score**: Posting quality (completeness, clarity, compensation transparency)
3. **Match Score**: Alignment metrics (keyword overlap, skills match, role fit)

All scores 0-100 with weighted category breakdowns. See `src/scoring/mod.rs`.

**Iteration Strategies** (see `src/processor/mod.rs`)
- `best_of`: Keep best candidate, stop on target/plateau/max iterations
- `first_hit`: Stop immediately when target reached
- `patience`: Stop if no improvement for N iterations (more stable)

**Configuration Layering**
- Base config: `config/config.toml`
- Profile overlays: `config/profiles/*.toml` (safe, aggressive)
- Profiles loaded first, then merged with main config
- Relative paths auto-expand to absolute

### Key Module Responsibilities

**`src/processor/`** - Orchestrates entire pipeline
- Manages enhancement → validation → scoring → iteration loop
- Handles retry logic and error recovery
- Integrates with StateManager to avoid reprocessing

**`src/input/`** - File ingestion
- Loads resumes from TXT/PDF/DOCX (via `extract_text_from_file`)
- Computes SHA256 hashes for change detection
- Handles job description loading

**`src/output/`** - Artifact generation
- Creates TOML/JSON/TXT output files
- Generates manifest and score summaries
- Organizes output into pattern-based directories

**`src/scoring/`** - All scoring algorithms
- `score_resume()`: Resume quality scoring
- `score_job()`: Job posting scoring
- `score_match()`: Resume-job alignment scoring
- Weight loading from `config/scoring_weights.toml`

**`src/validation/`** - JSON schema validation
- Validates AI-generated JSON against schema
- Retry logic for malformed outputs
- Used in processor pipeline before scoring

**`src/recommendations/`** - Improvement suggestions
- Analyzes score reports to generate actionable recommendations
- Category-specific suggestions (completeness, skills, keywords, etc.)
- Prioritized by score thresholds

**`src/cli/`** - Command-line interface
- `handlers.rs`: Command handlers for score-resume, score-match, rank-jobs
- `interactive.rs`: Interactive menu (in progress)
- `table.rs`: Beautiful table formatting with color-coded output
  - `format_resume_scores()`: Resume quality breakdown
  - `format_match_scores()`: Match analysis
  - `format_job_rankings()`: Ranked job listings
  - `format_resume_list()`: Resume file listings
  - `format_recommendations()`: Improvement suggestions

**`src/utils/`** - Utilities
- `hash.rs`: SHA256 file hashing
- `extract.rs`: Text extraction (TXT/MD/TEX/PDF/DOCX)
- `ocr.rs`: Tesseract OCR integration for image resumes
  - `extract_text_from_image()`: Extract text from PNG, JPG, TIFF, BMP
  - `check_tesseract_installed()`: Verify Tesseract availability
  - `get_tesseract_version()`: Get Tesseract version info
- `file.rs`: Atomic writes, directory creation
- `validation.rs`: Email/URL validation, string sanitization

**`src/toml_io/`** - TOML operations
- `load()`: Load TOML file as JSON Value
- `dump()`: Save JSON Value as TOML
- `loads()`, `dumps()`: String-based variants

## Configuration System

### Structure
```toml
[paths]
input_resumes_folder = "workspace/input_resumes"
output_folder = "workspace/output"
state_file = "data/processed_resumes_state.toml"
scoring_weights_file = "config/scoring_weights.toml"

[processing]
num_versions_per_job = 3
iterate_until_score_reached = true
target_score = 85.0
max_iterations = 5
iteration_strategy = "best_of"  # or "first_hit", "patience"
structured_output_format = "json"  # or "toml", "both"

[processing.schema_validation]
enabled = true
resume_schema_path = "config/resume_schema.json"

[processing.recommendations]
enabled = true
max_items = 5

[ai]
gemini_api_key_env = "GEMINI_API_KEY"
default_model_name = "gemini-1.5-flash"
default_temperature = 0.7

[ai.agents.enhancer]
role = "enhancer"
provider = "gemini"
model_name = "gemini-1.5-flash"
```

### Profile Overlays
To use a profile:
```toml
[profile]
file = "config/profiles/safe.toml"
```

Profiles are merged with main config (profile values take precedence).

## Testing Architecture

### Test Organization
```
tests/
├── common/mod.rs                # Shared utilities (sample data, helpers)
├── test_agent_registry.rs       # Agent system (9 tests)
├── test_cli.rs                  # CLI argument parsing (10 tests)
├── test_cli_handlers.rs         # CLI handlers (10 tests)
├── test_config.rs               # Config loading (4 tests)
├── test_cross_platform.rs       # Cross-platform paths (13 tests)
├── test_error_handling.rs       # Error propagation (16 tests)
├── test_hashing.rs              # File hashing (7 tests)
├── test_iteration.rs            # Iteration strategies (8 tests)
├── test_output.rs               # Output generation (12 tests)
├── test_pipeline_integration.rs # Full pipeline (5 tests)
├── test_recommendations.rs      # Recommendations (6 tests)
├── test_scoring.rs              # Scoring algorithms (5 tests)
├── test_state.rs                # State management (5 tests)
├── test_text_extraction.rs      # Text extraction (5 tests)
├── test_toml_io.rs              # TOML I/O (5 tests)
└── test_validation.rs           # JSON validation (6 tests)
```

**Total: 296 tests** (111 unit + 163 integration + 22 doc)

**Common test utilities** (`tests/common/mod.rs`):
- `create_temp_dir()`: Create temporary test directory
- `create_test_file()`: Create file with content
- `sample_resume_json()`: Structured resume data
- `sample_resume_text()`: Plain text resume
- `sample_job_description()`: Job description text
- `sample_config_toml()`: Minimal config
- `sample_scoring_weights()`: Default weights

### Running Specific Tests
```bash
# Run all hashing tests
cargo test test_hashing

# Run single test
cargo test test_hash_consistency

# Run with full output
cargo test test_score_resume_basic -- --nocapture
```

## Error Handling

All functions return `Result<T, AtsError>` where `AtsError` is defined in `src/error.rs`.

**Key error variants** (30+ total):
- Configuration: `ConfigNotFound`, `ConfigParse`, `ConfigValidation`
- I/O: `Io`, `FileNotFound`, `PermissionDenied`
- API: `ApiRequest`, `ApiResponse`, `ApiAuth`, `ApiRateLimit`
- Processing: `PdfExtraction`, `DocxExtraction`, `SchemaValidation`
- Scoring: `Scoring`, `ScoringWeights`
- State: `StateCorrupted`, `StateOperation`

**Adding new error variants:**
1. Add variant to `AtsError` enum in `src/error.rs`
2. Use `#[error("message")]` attribute from thiserror
3. Add source field with `#[source]` if wrapping another error

## Resume Processing Workflow

**Step-by-step flow:**
1. Scan `input_resumes_folder` for files
2. Calculate SHA256 hash of each file
3. Check `StateManager` - skip if already processed
4. Extract text via `extract_text_from_file()` (handles TXT/PDF/DOCX)
5. Send to AI agent for enhancement (converts to structured JSON)
6. Validate JSON against schema (if enabled)
7. Score the enhanced resume
8. If iteration enabled:
   - Loop: revise → score → check target/strategy
   - Keep best version based on strategy
9. Generate recommendations (if enabled)
10. Write outputs: TOML/JSON/TXT + manifest + scores
11. Update `StateManager` with hash → output mapping

**Key files**: `src/processor/mod.rs`, `src/input/mod.rs`, `src/output/mod.rs`

## Output File Organization

Default pattern: `{resume_name}/{job_title}/{timestamp}/`

Example:
```
workspace/output/
└── John_Doe/
    └── Software_Engineer/
        └── 20240115_120345/
            ├── John_Doe_Software_Engineer_enhanced.toml
            ├── John_Doe_Software_Engineer_enhanced.json
            ├── John_Doe_Software_Engineer_enhanced.txt
            ├── scores.toml
            └── manifest.toml
```

Pattern configurable via `output_subdir_pattern` in config.

## Current Status

**Progress**: 1,130 of 1,600 items complete (71%)

**Test Coverage**: 296 tests (111 unit + 163 integration + 22 doc)
- ✅ All tests passing
- ✅ Zero clippy warnings
- ✅ Zero documentation warnings

**Quality Metrics**:
- ✅ Comprehensive test suite with 255 tests
- ✅ Performance benchmarks (hashing, scoring, TOML I/O)
- ✅ Beautiful CLI table formatting with color coding
- ✅ Cross-platform compatibility tests (Windows, Linux, macOS)
- ✅ Error handling integration tests

**Completed Phases**:
- ✅ Phase 1-14: Core infrastructure, processing pipeline, scoring, agents
- ✅ Phase 5: Utilities (OCR support with Tesseract)
- ✅ Phase 9: Job Scraper (100% COMPLETE - JobSpy subprocess integration, retry logic, caching, CLI, E2E tests, documentation)
- ✅ Phase 11: Output Generator (100% COMPLETE - comprehensive testing for all output formats, edge cases, Unicode, manifest generation)
- ✅ Phase 15: CLI Module (table formatting, enhanced help text)
- ✅ Phase 18: Integration testing (60% complete - 20 test files)
- ✅ Benchmarking: 3 benchmark suites ready

**Recently Completed**:
- ✅ Phase 11: Output Generator Module - 100% COMPLETE (8 new comprehensive tests added)
- ✅ Output path generation tests (all placeholders, job title handling, timestamp)
- ✅ Unicode character handling tests
- ✅ Empty/minimal section handling tests
- ✅ Manifest generation and verification tests
- ✅ Complex nested data structure tests
- ✅ TXT format output verification tests
- ✅ Scores file format tests
- ✅ Job scraper E2E integration tests (9 tests in test_job_search_e2e.rs)
- ✅ Job search CLI command with full handler implementation
- ✅ Comprehensive job scraping documentation in README.md
- ✅ JobSpy subprocess scraper with Python integration (4 tests)
- ✅ Retry wrapper with exponential backoff (3 tests)
- ✅ Result caching with TTL and persistence (6 tests)
- ✅ ScraperError and CacheError variants added to error handling
- ✅ All job scraper components tested (37 tests total)
- ✅ Graceful degradation tests (21 tests)
- ✅ File locking tests (9 tests)
- ✅ Concurrent operations tests (9 tests)
- ✅ OCR text extraction (Tesseract integration for PNG, JPG, TIFF, BMP)
- ✅ CLI table formatting with color-coded output
- ✅ Error handling integration tests (16 tests)
- ✅ Cross-platform path tests (13 tests)
- ✅ Performance benchmarks (3 suites)

**Still TODO**:
- Interactive menu full feature set
- Additional LLM providers (OpenAI, Claude, Llama agents)
- Remaining integration tests
- Performance comparison vs Python version

See [RUST_REWRITE_TODO.md](./RUST_REWRITE_TODO.md) for detailed checklist.

## Development Notes

**Before committing:**
```bash
cargo test && cargo clippy --all-targets --all-features -- -D warnings && cargo fmt
```

**When adding new features:**
1. Add error variants to `AtsError` if needed
2. Update `config.toml` structure if adding configuration
3. Add integration tests in `tests/`
4. Update `RUST_REWRITE_TODO.md` checklist
5. Run all quality checks

**File references in code:**
- Always use `PathBuf` for paths
- Use `impl AsRef<Path>` for function parameters
- Prefer relative paths in config (auto-expanded to absolute)

**Async operations:**
- Uses `tokio` runtime
- Agent calls are async (`async fn`)
- Use `#[tokio::test]` for async tests

**Serialization:**
- Uses `serde` with `Serialize`/`Deserialize` derives
- TOML for config/state/output
- JSON for AI interactions
- Value interop via `serde_json::Value`
