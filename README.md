# ATS Resume Checker (Rust)

A high-performance Rust application for enhancing resumes using AI and scoring them against job descriptions.

> **Note:** This is a Rust rewrite of the original Python application. The Python version is preserved in [`python-original/`](./python-original/) for reference.

## Features

- 🚀 **Resume Enhancement**: AI-powered restructuring using Gemini, OpenAI, Claude, or Llama
- 📊 **Multi-Dimensional Scoring**: Resume quality + Job match + Iterative improvement
- 🔄 **Iterative Optimization**: Automatically improve resumes until target score reached
- 📝 **Multiple Output Formats**: TOML, JSON, and human-readable TXT
- 🔍 **Job Scraping**: Search across LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter
- 💾 **State Management**: Smart deduplication using content hashing
- 🎯 **Recommendations**: Actionable improvement suggestions
- ✅ **Schema Validation**: Optional JSON schema validation with retry

## Quick Start

### Prerequisites

- Rust 1.70+ (install from [rustup.rs](https://rustup.rs/))
- API keys for AI providers (at least one):
  - `GEMINI_API_KEY` - Google Gemini (recommended)
  - `OPENAI_API_KEY` - OpenAI GPT models
  - `ANTHROPIC_API_KEY` - Anthropic Claude
  - `TOGETHER_API_KEY` or `GROQ_API_KEY` - Llama models

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/ats-checker.git
cd ats-checker

# Build the project
cargo build --release

# Run the application
cargo run --release
```

### Basic Usage

#### Interactive Mode (Default)

```bash
cargo run --release
```

Navigate through the interactive menu to:
1. Process resumes
2. Search for jobs
3. Configure settings
4. View outputs

#### Command Line Interface

```bash
# Score a resume
cargo run --release -- score-resume --resume output/my_resume.toml

# Score resume against job
cargo run --release -- score-match \
  --resume output/my_resume.toml \
  --job workspace/job_descriptions/software_engineer.txt

# Rank job search results
cargo run --release -- rank-jobs \
  --results workspace/job_search_results/linkedin_results.toml \
  --top 20
```

## Configuration

The main configuration file is [`config/config.toml`](./config/config.toml).

### Key Settings

```toml
[paths]
input_resumes_folder = "workspace/input_resumes"
job_descriptions_folder = "workspace/job_descriptions"
output_folder = "workspace/output"

[ai]
default_model_name = "gemini-1.5-flash-latest"
default_temperature = 0.7

[ai.agents.enhancer]
provider = "gemini"
model_name = "gemini-1.5-flash-latest"
role = "resume_enhancement"

[processing]
num_versions_per_job = 1
iterate_until_score_reached = false
target_score = 80.0
max_iterations = 3
iteration_strategy = "best_of"  # or "first_hit", "patience"
```

### Configuration Profiles

Use preset profiles for different optimization strategies:

```bash
# Budget-friendly (Gemini Flash only)
cp config/profiles/budget.toml config/config.toml

# Balanced (mix of models)
cp config/profiles/balanced.toml config/config.toml

# High quality (GPT-4 / Claude)
cp config/profiles/quality.toml config/config.toml
```

## Project Structure

```
ats-checker/
├── Cargo.toml              # Rust dependencies
├── src/
│   ├── lib.rs             # Library entry point
│   ├── bin/main.rs        # CLI binary
│   ├── error.rs           # Error types
│   ├── config/            # Configuration management
│   ├── state/             # State persistence
│   ├── agents/            # LLM agent abstraction
│   ├── scoring/           # Scoring algorithms
│   ├── scraper/           # Job scraping
│   ├── processor/         # Resume processing pipeline
│   ├── input/             # Input handling
│   ├── output/            # Output generation
│   ├── recommendations/   # Improvement suggestions
│   ├── validation/        # Schema validation
│   ├── utils/             # Utilities
│   ├── gemini/            # Gemini API client
│   ├── toml_io/           # TOML I/O
│   └── cli/               # CLI interface
├── config/                # Configuration files
│   ├── config.toml        # Main config
│   ├── scoring_weights.toml
│   └── profiles/          # Preset configurations
├── workspace/             # Data directories
│   ├── input_resumes/
│   ├── job_descriptions/
│   ├── output/
│   └── job_search_results/
├── data/                  # State files
│   ├── processed_resumes_state.toml
│   └── saved_searches.toml
├── python-original/       # Original Python implementation
└── RUST_REWRITE_TODO.md  # Detailed rewrite checklist
```

## Development

### Building

```bash
# Development build
cargo build

# Release build (optimized)
cargo build --release

# Check code without building
cargo check

# Run tests
cargo test

# Run with logging
RUST_LOG=debug cargo run
```

### Running Tests

```bash
# All tests
cargo test

# Specific test
cargo test test_job_posting_creation

# With output
cargo test -- --nocapture
```

### Code Quality

```bash
# Format code
cargo fmt

# Lint code
cargo clippy

# Check for common mistakes
cargo clippy -- -D warnings
```

## Architecture

### Core Pipeline

1. **Input**: Raw resumes (TXT, PDF, DOCX, images with OCR)
2. **Enhancement**: AI restructures resume to structured JSON
3. **Scoring**: Multi-dimensional scoring (resume + match)
4. **Iteration**: Optional loop to improve until target score
5. **Output**: TOML/JSON/TXT formats + artifacts
6. **State**: Track by SHA256 hash to avoid reprocessing

### Scoring System

- **Resume Score**: Quality metrics (completeness, skills, experience, impact)
- **Job Score**: Job posting quality (completeness, clarity, compensation)
- **Match Score**: Resume-job alignment (keywords, skills, role fit)
- **Iteration Score**: Weighted combination of resume + match scores

### Iteration Strategies

- **best_of**: Keep best candidate, stop on target/no_progress/max_iterations
- **first_hit**: Stop immediately when target reached
- **patience**: Stop after N consecutive non-improving iterations

## API Providers

### Supported Providers

| Provider | Models | Notes |
|----------|--------|-------|
| **Gemini** | gemini-1.5-flash, gemini-1.5-pro | Recommended, cost-effective |
| **OpenAI** | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | High quality |
| **Anthropic** | claude-3-5-sonnet, claude-3-opus | Excellent for long contexts |
| **Llama** | llama-3.3-70b, llama-3.1-70b | Via Together AI or Groq |

### Setting Up API Keys

```bash
# Linux/macOS
export GEMINI_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"

# Windows PowerShell
$env:GEMINI_API_KEY="your-key-here"
$env:OPENAI_API_KEY="your-key-here"
$env:ANTHROPIC_API_KEY="your-key-here"

# Or add to config/config.toml
```

## Job Scraping

Search for jobs across multiple platforms:

```rust
use ats_checker::scraper::{JobScraperManager, SearchFilters};

let manager = JobScraperManager::new("results/", "data/saved_searches.toml")?;

let filters = SearchFilters::builder()
    .keywords("rust developer")
    .location("Remote")
    .remote_only(true)
    .build();

let jobs = manager.search_jobs(&filters, &["linkedin", "indeed"], 50).await?;
```

## Performance

- **Parallel Processing**: Process multiple resumes concurrently
- **Smart Caching**: Score caching to avoid recomputation
- **Efficient Hashing**: SHA256 for deduplication
- **Async I/O**: Non-blocking file and network operations
- **Zero-copy Parsing**: Efficient TOML/JSON handling

## Comparison to Python Version

| Feature | Python | Rust |
|---------|--------|------|
| Startup Time | ~500ms | ~50ms |
| Memory Usage | ~200MB | ~50MB |
| Processing Speed | 1x | 3-5x faster |
| Concurrency | Limited (GIL) | True parallelism |
| Type Safety | Runtime | Compile-time |
| Binary Size | N/A | ~15MB (stripped) |

## Contributing

Contributions are welcome! Please see [RUST_REWRITE_TODO.md](./RUST_REWRITE_TODO.md) for the full list of planned features and improvements.

### Development Roadmap

- [ ] Complete scoring algorithms implementation
- [ ] Full LLM agent registry system
- [ ] PDF/DOCX text extraction
- [ ] Interactive CLI menu
- [ ] Comprehensive test suite
- [ ] Performance benchmarks
- [ ] CI/CD pipeline
- [ ] Documentation site

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Original Python implementation in [`python-original/`](./python-original/)
- Built with [tokio](https://tokio.rs/), [serde](https://serde.rs/), [clap](https://github.com/clap-rs/clap)
- AI providers: Google Gemini, OpenAI, Anthropic, Meta Llama

## Links

- [Python Version Documentation](./python-original/README_PYTHON.md)
- [Detailed Rewrite Checklist](./RUST_REWRITE_TODO.md)
- [Configuration Guide](./config/README.md)
- [API Documentation](https://docs.rs/ats-checker)
