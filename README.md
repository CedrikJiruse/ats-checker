# ATS Resume Checker

A high-performance Rust application for enhancing resumes using AI and scoring them against job descriptions.

> **Note:** This is a Rust rewrite of the original Python application. The Python version is preserved in [`python-original/`](./python-original/) for reference.

## Features

- **Resume Enhancement**: AI-powered restructuring using Gemini, OpenAI, Claude, or Llama
- **Multi-Dimensional Scoring**: Resume quality + Job match + Iterative improvement
- **Iterative Optimization**: Automatically improve resumes until target score reached
- **Job Scraping**: Search across LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter
- **Multiple Output Formats**: TOML, JSON, and human-readable TXT

## Quick Start

### Prerequisites

- Rust 1.70+ (install from [rustup.rs](https://rustup.rs/))
- API key for at least one AI provider (Gemini recommended)

### Installation

```bash
git clone https://github.com/your-username/ats-checker.git
cd ats-checker
cargo build --release
```

### Usage

```bash
# Interactive mode
cargo run --release

# Score a resume
cargo run --release -- score-resume --resume output/resume.toml

# Score resume against job
cargo run --release -- score-match --resume output/resume.toml --job workspace/job.txt

# Rank jobs
cargo run --release -- rank-jobs --results workspace/results.toml --top 20
```

## Configuration

Edit [`config/config.toml`](./config/config.toml) to customize:

- **Paths**: Input/output directories
- **AI Settings**: Provider, model, temperature
- **Processing**: Iteration strategy, target score, max iterations
- **Job Search**: Filters and defaults

See [`config/profiles/`](./config/profiles/) for preset configurations.

## Project Structure

```
ats-checker/
├── src/              # Rust source code
├── config/           # Configuration files
├── workspace/        # Input/output data
├── data/             # State files
├── python-original/  # Original Python implementation
└── RUST_REWRITE_TODO.md  # Rewrite progress checklist
```

## Development

```bash
cargo build          # Development build
cargo test           # Run tests
cargo clippy         # Lint code
cargo fmt            # Format code
RUST_LOG=debug cargo run  # Run with logging
```

## Documentation

- [Rust Rewrite TODO](./RUST_REWRITE_TODO.md) - Detailed implementation checklist
- [Python Version](./python-original/README_PYTHON.md) - Original Python documentation
- [Configuration Guide](./config/README.md) - Configuration options

## License

MIT License - see LICENSE file for details
