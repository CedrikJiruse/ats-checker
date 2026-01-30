# AGENTS.md - Coding Guidelines for ATS Resume Checker

## Build Commands

```bash
# Build (development)
cargo build

# Build optimized release
cargo build --release

# Run the application
cargo run --release

# Run with custom config
cargo run --release -- --config path/to/config.toml
```

## Test Commands

```bash
# Run all tests (296 total)
cargo test

# Run a specific test by name
cargo test test_hash_consistency

# Run tests from a specific file
cargo test --test test_scoring

# Run only unit tests (in src/)
cargo test --lib

# Run only integration tests (in tests/)
cargo test --test '*'

# Run tests with output visible
cargo test -- --nocapture

# Run tests with logging
RUST_LOG=debug cargo test
```

## Lint & Format Commands

```bash
# Check for compilation errors (fast)
cargo check

# Lint with clippy (treats warnings as errors)
cargo clippy --all-targets --all-features -- -D warnings

# Format code
cargo fmt

# Check formatting without changing files
cargo fmt -- --check

# Full quality check (run before committing)
cargo test && cargo clippy --all-targets --all-features -- -D warnings && cargo fmt
```

## Code Style Guidelines

### Imports Order
1. Standard library (`std::`)
2. External crates (e.g., `serde`, `tokio`)
3. Internal modules (`crate::`)

```rust
use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use crate::error::Result;
```

### Naming Conventions
- **Functions/Variables**: `snake_case` (e.g., `process_resume`, `output_dir`)
- **Types/Structs/Enums**: `PascalCase` (e.g., `ResumeProcessor`, `AtsError`)
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g., `DEFAULT_CONFIG_PATH`)
- **Modules**: `snake_case` (e.g., `src/scoring/mod.rs`)

### Error Handling
- All functions return `Result<T, AtsError>` from `crate::error`
- Use `?` operator for error propagation
- Add context to errors with `map_err()` when needed
- Use `thiserror` derive for error variants

```rust
use crate::error::{AtsError, Result};

pub fn load_file(path: &Path) -> Result<String> {
    std::fs::read_to_string(path)
        .map_err(|e| AtsError::Io {
            message: format!("Failed to read {path:?}"),
            source: e,
        })
}
```

### Types & Traits
- Use `impl AsRef<Path>` for path parameters
- Prefer `PathBuf` over `String` for paths
- Derive common traits: `#[derive(Debug, Clone, Serialize, Deserialize)]`
- Use type aliases for complex types

### Async Code
- Use `tokio` runtime
- Mark async functions with `async fn`
- Use `#[tokio::test]` for async tests
- Avoid blocking operations in async contexts

### Documentation
- Module docs: `//!` at top of file
- Item docs: `///` before functions/types
- Include examples in doc comments
- Document errors with `# Errors` section

### Testing
- Unit tests: In `src/` files under `#[cfg(test)]` modules
- Integration tests: In `tests/` directory
- Use `tests/common/mod.rs` for shared utilities
- Use `tempfile` crate for temp directories in tests

### File Organization
```
src/
├── lib.rs              # Library root with re-exports
├── bin/main.rs         # CLI binary entry point
├── module/mod.rs       # Module with public API
└── module/submodule.rs # Private implementation details
```

### Key Patterns
- **State Management**: Use `StateManager` for persistence
- **Configuration**: Use `Config::load()` with profile overlays
- **Paths**: Always use `PathBuf`, sanitize with `sanitize_filename()`
- **Serialization**: TOML for config/state, JSON for AI interactions
- **Output**: Use `atomic_write()` for file operations

### Before Committing
Always run:
```bash
cargo test && cargo clippy --all-targets --all-features -- -D warnings && cargo fmt
```

## Project Structure

- **71% Complete** (1,140/1,600 items)
- **296 Tests** (111 unit + 163 integration + 22 doc)
- **Zero Clippy Warnings** (enforced)
- Rust Edition 2021
