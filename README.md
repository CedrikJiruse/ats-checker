# ATS Resume Checker

> A high-performance Rust application that enhances resumes using AI and scores them against job descriptions.

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]() [![Tests](https://img.shields.io/badge/tests-296%20passing-brightgreen)]() [![Clippy](https://img.shields.io/badge/clippy-zero%20warnings-blue)]() [![License](https://img.shields.io/badge/license-MIT-blue)]()

This is a complete Rust rewrite of the original Python application, focusing on performance, type safety, and enhanced features. The Python version is preserved in [`python-original/`](./python-original/) for reference.

## ✨ Features

### Core Capabilities
- 🤖 **AI-Powered Resume Enhancement** - Restructure resumes using Gemini, OpenAI, Claude, or Llama
- 📊 **Multi-Dimensional Scoring System** - Comprehensive scoring across multiple categories
  - Resume Quality Score (completeness, skills, experience, impact)
  - Job Posting Score (clarity, requirements, compensation)
  - Match Score (keyword overlap, skills alignment, role fit)
- 🔄 **Iterative Optimization** - Automatically improve resumes until target score reached
  - Multiple strategies: `best_of`, `first_hit`, `patience`
  - Configurable target scores and iteration limits
- 🔍 **Job Scraping** - Search across LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter
- 📁 **Multiple Format Support** - TXT, PDF, DOCX input; TOML, JSON, TXT output
- 🖼️ **OCR Support** - Extract text from scanned resume images (PNG, JPG, TIFF, BMP)
- 📋 **Beautiful CLI Tables** - Color-coded, formatted terminal output
- ⚡ **High Performance** - Rust-based with comprehensive benchmarks

### Quality Assurance
- ✅ **296 Tests** - 111 unit + 163 integration + 22 doc tests
- 🔍 **Zero Clippy Warnings** - Strict linting enforced
- 🎯 **71% Complete** - 1130/1600 items from rewrite checklist
- 📈 **Performance Benchmarks** - Track optimization progress

## 🚀 Quick Start

### Prerequisites

- **Rust 1.70+** - Install from [rustup.rs](https://rustup.rs/)
- **API Key** - At least one AI provider (Gemini recommended)
  - Set `GEMINI_API_KEY` environment variable
- **Tesseract OCR** (optional) - For image resume support
  - Windows: [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
  - Linux: `sudo apt-get install tesseract-ocr`
  - macOS: `brew install tesseract`

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/ats-checker.git
cd ats-checker

# Build optimized release binary
cargo build --release

# Set up API key
export GEMINI_API_KEY="your-api-key-here"

# Run interactive mode
cargo run --release
```

## 📖 Usage

### Interactive Mode

```bash
# Launch interactive menu
cargo run --release

# Or run the binary directly
./target/release/ats-checker
```

The interactive menu provides:
- Process resumes with AI enhancement
- Search and scrape job postings
- Score resumes and jobs
- View processing history
- Manage configuration

### CLI Commands

#### Score a Resume

```bash
# Score a resume with default weights
cargo run --release -- score-resume --resume output/john_doe.json

# Score with custom weights
cargo run --release -- score-resume \
  --resume output/resume.toml \
  --weights config/scoring_weights.toml
```

**Output:**
```
============================================================
RESUME SCORE REPORT
============================================================

┌──────────────┬───────┬────────┬──────────┐
│ Category     │ Score │ Weight │ Weighted │
├══════════════╪═══════╪════════╪══════════┤
│ OVERALL      │  85.5 │    -   │     -    │
├──────────────┼───────┼────────┼──────────┤
│ Completeness │  90.0 │   25%  │   22.5   │
│ Skills       │  82.0 │   30%  │   24.6   │
│ Experience   │  88.0 │   25%  │   22.0   │
│ Impact       │  80.0 │   20%  │   16.0   │
└──────────────┴───────┴────────┴──────────┘
============================================================
```

#### Score Resume-Job Match

```bash
# Score how well a resume matches a job
cargo run --release -- score-match \
  --resume output/resume.json \
  --job workspace/jobs/software_engineer.txt
```

**Output includes:**
- Resume quality breakdown
- Match score with category analysis
- Combined overall score
- Color-coded status indicators

#### Rank Jobs by Score

```bash
# Rank top 20 jobs from search results
cargo run --release -- rank-jobs \
  --results workspace/saved_searches.toml \
  --top 20
```

**Output:**
```
================================================================================
TOP 20 JOBS (sorted by score)
================================================================================

┌──────┬───────────────────────────────┬──────────────────┬───────┬──────────┐
│ Rank │ Job Title                     │ Company          │ Score │ Location │
├══════╪═══════════════════════════════╪══════════════════╪═══════╪══════════┤
│  #1  │ Senior Software Engineer      │ Tech Corp        │  92.5 │ Remote   │
│  #2  │ Full Stack Developer          │ StartUp Inc      │  88.0 │ SF       │
│  #3  │ Backend Engineer              │ BigTech          │  85.5 │ Seattle  │
...
└──────┴───────────────────────────────┴──────────────────┴───────┴──────────┘

Total jobs: 47 | Showing top: 20
================================================================================
```

#### Job Search

Search for jobs across multiple job boards using the integrated JobSpy library.

**Prerequisites:**
- Python 3.9+ with `python-jobspy` package installed:
  ```bash
  pip install python-jobspy
  ```

**Basic Usage:**

```bash
# Search for Rust developer jobs on LinkedIn
cargo run --release -- job-search \
  --keywords "rust developer" \
  --sources linkedin

# Search multiple sources with location
cargo run --release -- job-search \
  --keywords "software engineer" \
  --location "San Francisco, CA" \
  --sources linkedin,indeed,glassdoor

# Search for remote jobs only
cargo run --release -- job-search \
  --keywords "backend engineer" \
  --remote \
  --sources linkedin,indeed \
  --max-results 100

# Save to custom output file
cargo run --release -- job-search \
  --keywords "full stack developer" \
  --location "Remote" \
  --sources linkedin \
  --output my_job_search.toml
```

**Supported Job Sources:**
- `linkedin` - LinkedIn Jobs
- `indeed` - Indeed
- `glassdoor` - Glassdoor
- `google` - Google Jobs
- `ziprecruiter` - ZipRecruiter

**Features:**
- **Automatic Retry** - Built-in retry logic with exponential backoff for transient failures
- **Result Caching** - 30-minute cache to avoid redundant API calls (persistent across runs)
- **Dependency Check** - Verifies Python and JobSpy are available before scraping
- **TOML Output** - Results saved to `workspace/output/job_searches/` by default
- **Table Display** - Beautiful terminal output with top 20 results preview

**Output:**
```
🔍 Searching for jobs...
   Keywords: rust developer
   Location: Remote
   Remote only: Yes
   Sources: linkedin, indeed
   Max results per source: 50

✓ Registered linkedin scraper
✓ Registered indeed scraper
✓ Found 87 jobs

✓ Results saved to: workspace/output/job_searches/jobs_rust_developer_20240115_143022.toml

================================================================================
JOB SEARCH RESULTS
================================================================================

┌──────┬───────────────────────────────┬──────────────────┬───────────┬──────────┐
│ Rank │ Job Title                     │ Company          │ Source    │ Location │
├══════╪═══════════════════════════════╪══════════════════╪═══════════╪══════════┤
│  #1  │ Senior Rust Engineer          │ TechCorp         │ linkedin  │ Remote   │
│  #2  │ Rust Backend Developer        │ StartupXYZ       │ indeed    │ Remote   │
│  #3  │ Systems Programmer (Rust)     │ BigTech Inc      │ linkedin  │ Remote   │
...
└──────┴───────────────────────────────┴──────────────────┴───────────┴──────────┘

... and 67 more jobs (see full results in output file)

================================================================================
```

**Combine with Ranking:**

After searching for jobs, rank them by quality score:

```bash
# 1. Search for jobs
cargo run --release -- job-search \
  --keywords "software engineer" \
  --sources linkedin \
  --output my_search.toml

# 2. Rank the results
cargo run --release -- rank-jobs \
  --results workspace/output/job_searches/my_search.toml \
  --top 10
```

### Configuration Profiles

```bash
# Use safe profile (conservative settings)
cargo run --release -- --config config/config.toml

# Profile selection in config.toml:
[profile]
file = "config/profiles/safe.toml"  # or "aggressive.toml"
```

## ⚙️ Configuration

### Main Configuration (`config/config.toml`)

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

[ai]
gemini_api_key_env = "GEMINI_API_KEY"
default_model_name = "gemini-1.5-flash"
default_temperature = 0.7

[ai.agents.enhancer]
role = "enhancer"
provider = "gemini"
model_name = "gemini-1.5-flash"
```

### Scoring Weights (`config/scoring_weights.toml`)

Customize scoring category weights (must sum to 1.0):

```toml
[resume]
completeness = 0.25
skills = 0.30
experience = 0.25
impact = 0.20

[match]
keyword_overlap = 0.35
skills_match = 0.30
role_fit = 0.20
experience_match = 0.15
```

## 🏗️ Architecture

### Core Modules

```
src/
├── agents/         # Multi-agent LLM abstraction (Gemini, OpenAI, Claude, Llama)
├── cli/            # Command-line interface
│   ├── handlers.rs # Command handlers
│   ├── interactive.rs # Interactive menu
│   └── table.rs    # Table formatting utilities
├── config/         # Configuration management
├── error.rs        # Unified error handling (30+ error types)
├── gemini/         # Gemini API integration
├── input/          # File ingestion (TXT, PDF, DOCX)
├── output/         # Multi-format output generation
├── processor/      # Resume enhancement pipeline
├── recommendations/ # Improvement suggestions
├── scoring/        # Three-tier scoring system
├── scraper/        # Job scraping framework
├── state/          # State management with content hashing
├── toml_io/        # TOML serialization utilities
├── utils/          # Shared utilities
│   ├── extract.rs  # Text extraction
│   ├── file.rs     # Atomic file operations
│   ├── hash.rs     # SHA256 hashing
│   ├── ocr.rs      # Tesseract OCR integration
│   └── validation.rs # Input validation
└── validation/     # JSON schema validation
```

### Data Flow

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│ Raw Resume  │ ───> │ Text Extract │ ───> │ AI Enhance  │
│ (TXT/PDF/   │      │ + Hash Check │      │ (Gemini/etc)│
│  DOCX/IMG)  │      └──────────────┘      └─────────────┘
└─────────────┘              │                     │
                             v                     v
                      ┌──────────────┐      ┌─────────────┐
                      │ StateManager │      │  Validate   │
                      │ (Skip if     │      │   Schema    │
                      │  processed)  │      └─────────────┘
                      └──────────────┘             │
                                                   v
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Output    │ <─── │ Iterate Loop │ <─── │  Score      │
│ (TOML/JSON/ │      │ (Until target│      │  (3-tier)   │
│    TXT)     │      │  reached)    │      └─────────────┘
└─────────────┘      └──────────────┘             │
                                                   v
                                            ┌─────────────┐
                                            │ Recommend-  │
                                            │  ations     │
                                            └─────────────┘
```

## 🧪 Development

### Build and Test

```bash
# Development build (fast, unoptimized)
cargo build

# Optimized release build
cargo build --release

# Run all tests (296 tests)
cargo test

# Run specific test file
cargo test --test test_scoring

# Run with output
cargo test -- --nocapture

# Run with debug logging
RUST_LOG=debug cargo test
```

### Code Quality

```bash
# Check for errors (fast)
cargo check

# Lint with clippy (treat warnings as errors)
cargo clippy --all-targets --all-features -- -D warnings

# Format code
cargo fmt

# Check formatting without changes
cargo fmt -- --check

# Generate documentation
cargo doc --no-deps --open
```

### Benchmarking

```bash
# Run all benchmarks
cargo bench

# Run specific benchmark
cargo bench hashing

# Generate detailed reports
cargo bench -- --save-baseline main
```

**Available benchmarks:**
- `benches/hashing.rs` - String and bytes hashing (100 to 100K bytes)
- `benches/scoring.rs` - Resume, job, and match scoring
- `benches/toml_io.rs` - TOML dumps/loads (small, medium, large data)

## 📊 Project Status

**Current Progress:** 71% Complete (1130/1600 items)

### ✅ Completed Phases
- Core infrastructure (config, error handling, state management)
- Text extraction (TXT, PDF, DOCX)
- OCR support (Tesseract integration)
- Scoring algorithms (resume, job, match)
- Agent registry (multi-provider LLM support)
- Processing pipeline with iteration strategies
- Output generation with comprehensive testing (TOML, JSON, TXT)
- CLI with table formatting
- Job scraper with retry logic and caching (JobSpy integration)
- Comprehensive test suite (296 tests)
- Performance benchmarks

### 🚧 In Progress
- Interactive menu full feature set
- Additional LLM providers (OpenAI, Claude, Llama)
- Additional integration tests

### 📋 Upcoming
- Performance comparison vs Python version
- Docker containerization
- CI/CD pipeline
- Extended documentation

See [RUST_REWRITE_TODO_ACTIVE.md](./RUST_REWRITE_TODO_ACTIVE.md) for detailed progress tracking.

## 📚 Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Project instructions for AI assistants
- **[RUST_REWRITE_TODO.md](./RUST_REWRITE_TODO.md)** - Complete implementation checklist
- **[RUST_REWRITE_TODO_ACTIVE.md](./RUST_REWRITE_TODO_ACTIVE.md)** - Active TODO items
- **[RUST_REWRITE_PROGRESS.md](./RUST_REWRITE_PROGRESS.md)** - Completed work summary
- **[config/README.md](./config/README.md)** - Configuration guide
- **[python-original/README_PYTHON.md](./python-original/README_PYTHON.md)** - Original Python docs

## 🔧 Troubleshooting

### Common Issues

**OCR not working:**
```bash
# Check Tesseract installation
tesseract --version

# Ensure Tesseract is in PATH
export PATH="$PATH:/usr/local/bin"  # macOS/Linux
# Windows: Add C:\Program Files\Tesseract-OCR to system PATH
```

**API errors:**
```bash
# Verify API key is set
echo $GEMINI_API_KEY

# Test with debug logging
RUST_LOG=debug cargo run --release
```

**Build errors:**
```bash
# Update Rust toolchain
rustup update

# Clean and rebuild
cargo clean
cargo build --release
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and clippy: `cargo test && cargo clippy -- -D warnings`
5. Format code: `cargo fmt`
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

- Original Python implementation team
- Rust community for excellent tooling
- AI providers (Gemini, OpenAI, Anthropic, Meta)
- Open source dependencies (see [Cargo.toml](./Cargo.toml))

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/your-username/ats-checker/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-username/ats-checker/discussions)
- **Documentation:** Run `cargo doc --open` for API docs

---

**Note:** This is a Rust rewrite focusing on performance and type safety. For the original Python version with different features, see [`python-original/`](./python-original/).
