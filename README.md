# ATS Resume Checker

> A high-performance Rust application that enhances resumes using AI and scores them against job descriptions.

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]() [![Tests](https://img.shields.io/badge/tests-308%20passing-brightgreen)]() [![Clippy](https://img.shields.io/badge/clippy-zero%20warnings-blue)]() [![License](https://img.shields.io/badge/license-MIT-blue)]()

Rust rewrite focusing on performance, type safety, and multi-provider AI support. Original Python version preserved in [`python-original/`](./python-original/).

## ✨ Features

### Core Capabilities
- 🤖 **Multi-Provider AI Support** - Gemini, OpenAI, Claude, or Llama (auto-detects available APIs)
- 📊 **Three-Tier Scoring** - Resume quality, job posting quality, and match score
- 🔄 **Iterative Optimization** - Auto-improve resumes with `best_of`, `first_hit`, or `patience` strategies
- 🔍 **Job Scraping** - LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter (auto-setup)
- 📁 **Multiple Formats** - TXT, PDF, DOCX input; TOML, JSON, TXT output
- 🖼️ **OCR Support** - Extract text from scanned images (PNG, JPG, TIFF, BMP)
- 📋 **Interactive CLI** - Menu-driven interface with API key management
- ⚡ **High Performance** - Rust-based with comprehensive benchmarks

### Quality Assurance
- ✅ **308 Tests** - Comprehensive coverage
- 🔍 **Zero Clippy Warnings** - Strict linting
- 📈 **Performance Benchmarks** - Continuous optimization

## 🚀 Quick Start

### Prerequisites

- **Rust 1.70+** - Install from <https://rustup.rs>
- **AI API Key** - At least one of:
  - `GEMINI_API_KEY` (Google Gemini - recommended)
  - `OPENAI_API_KEY` (OpenAI GPT)
  - `ANTHROPIC_API_KEY` (Claude)
  - Or use local Llama via Ollama (set `OLLAMA_HOST`)
- **Python 3.8+** (optional) - For job scraping (auto-installed)
- **Tesseract OCR** (optional) - For image resume support
  - Windows: <https://github.com/UB-Mannheim/tesseract/wiki>
  - Linux: `sudo apt-get install tesseract-ocr`
  - macOS: `brew install tesseract`

### Installation

```bash
git clone https://github.com/your-username/ats-checker.git
cd ats-checker
cargo build --release
export GEMINI_API_KEY="your-api-key-here"  # Or other AI key
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

Search across LinkedIn, Indeed, Glassdoor, Google Jobs, and ZipRecruiter.

**Auto-Setup:** Dependencies are installed automatically on first use. If needed, run menu option 11 or:
```bash
cargo run --release -- --setup-jobspy
```

**Basic Usage:**
```bash
# Search LinkedIn for remote Rust jobs
cargo run --release -- job-search --keywords "rust developer" --sources linkedin --remote

# Search multiple sources with location
cargo run --release -- job-search --keywords "software engineer" --location "SF" --sources linkedin,indeed,glassdoor
```

**Features:**
- **Auto-Setup** - Python and JobSpy installed automatically
- **Caching** - 30-minute cache to avoid redundant calls
- **Retry Logic** - Exponential backoff for failures
- **TOML Output** - Results saved to `workspace/output/job_searches/`

**Combine with Ranking:**
```bash
cargo run --release -- job-search --keywords "engineer" --sources linkedin --output search.toml
cargo run --release -- rank-jobs --results workspace/output/job_searches/search.toml --top 10
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

# Configure multiple AI providers
[ai.agents.gemini_enhancer]
role = "enhancer"
provider = "gemini"
model_name = "gemini-1.5-flash"

[ai.agents.openai_enhancer]
role = "enhancer"
provider = "openai"
model_name = "gpt-4"

[ai.agents.claude_enhancer]
role = "enhancer"
provider = "anthropic"
model_name = "claude-3-sonnet-20240229"
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
├── agents/         # Multi-provider LLM abstraction
├── anthropic/      # Claude API integration
├── cli/            # Command-line interface (interactive menu, handlers)
├── config/         # Configuration management
├── error.rs        # Unified error handling
├── gemini/         # Gemini API integration
├── input/          # File ingestion (TXT, PDF, DOCX)
├── llama/          # Ollama/Llama API integration
├── openai/         # OpenAI API integration
├── output/         # Multi-format output (TOML, JSON, TXT)
├── processor/      # Resume enhancement pipeline
├── recommendations/ # AI improvement suggestions
├── scoring/        # Three-tier scoring system
├── scraper/        # Job scraping (LinkedIn, Indeed, etc.)
│   ├── jobspy.rs   # Python bridge
│   └── setup.rs    # Auto-dependency setup
├── state/          # Processing state management
├── utils/          # Shared utilities
└── validation/     # Input validation
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

# Run all tests (308 tests)
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

**Status:** Core features complete and stable

### ✅ Completed
- Multi-provider AI support (Gemini, OpenAI, Claude, Llama)
- Automatic dependency setup for job scraping
- Interactive CLI with API key management
- Comprehensive test suite (308 tests)
- Zero clippy warnings

### 📋 Future
- Performance comparison vs Python version
- Docker containerization
- CI/CD pipeline

## 📚 Documentation

- **[python_jobspy/README.md](./python_jobspy/README.md)** - Job scraping setup guide
- **[config/README.md](./config/README.md)** - Configuration guide

## 🔧 Troubleshooting

**Job scraping fails:**
```bash
# Run interactive setup (Menu option 11)
cargo run --release
# Select "11. Setup JobSpy"

# Or check dependencies
cargo run --release -- --setup-jobspy
```

**API errors:**
```bash
# Check available API keys
cargo run --release
# Select "10. Check API keys"

# Or verify in shell
echo $GEMINI_API_KEY
echo $OPENAI_API_KEY
```

**OCR not working:**
```bash
tesseract --version  # Verify installation
# Add to PATH if missing
```

## 📄 License

MIT License - see [LICENSE](./LICENSE)

---

**Note:** Rust rewrite focusing on performance and multi-provider AI support. Original Python version in [`python-original/`](./python-original/)
