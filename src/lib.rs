//! # ATS Resume Checker
//!
//! A Rust library for enhancing resumes using AI and scoring them against job descriptions.
//!
//! ## Overview
//!
//! This library provides functionality to:
//! - Parse and process resumes from various formats (TXT, PDF, DOCX)
//! - Enhance resumes using AI models (Gemini, OpenAI, Anthropic, Llama)
//! - Score resumes against job descriptions
//! - Scrape job postings from various job boards
//! - Generate optimized output in multiple formats
//!
//! ## Modules
//!
//! - [`config`] - Configuration management with TOML support
//! - [`state`] - Persistent state management for tracking processed resumes
//! - [`utils`] - Utility functions for hashing, text extraction, file operations
//! - [`scoring`] - Resume, job, and match scoring system
//! - [`agents`] - LLM agent abstraction layer
//! - [`scraper`] - Job scraping from multiple sources
//! - [`input`] - Input file handling and selection
//! - [`output`] - Output generation in various formats
//! - [`processor`] - Main resume processing pipeline
//! - [`recommendations`] - Improvement recommendations generation
//! - [`validation`] - JSON Schema validation
//! - [`gemini`] - Gemini API integration
//!
//! ## Example
//!
//! ```rust,no_run
//! use ats_checker::{Config, ResumeProcessor};
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     // Load configuration
//!     let config = Config::load("config/config.toml")?;
//!
//!     // Create processor
//!     let mut processor = ResumeProcessor::new(config)?;
//!
//!     // Process a resume
//!     let result = processor.process_resume("resume.txt", Some("job.txt")).await?;
//!
//!     println!("Score: {}", result.scores.map(|s| s.total).unwrap_or(0.0));
//!     Ok(())
//! }
//! ```

#![warn(missing_docs)]
#![warn(clippy::all)]
#![warn(clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]
#![allow(clippy::must_use_candidate)]

// Public modules
pub mod agents;
pub mod cli;
pub mod config;
pub mod error;
pub mod gemini;
pub mod input;
pub mod output;
pub mod processor;
pub mod recommendations;
pub mod scoring;
pub mod scraper;
pub mod state;
pub mod toml_io;
pub mod utils;
pub mod validation;

// Re-exports for convenience
pub use config::Config;
pub use error::{AtsError, Result};
pub use output::{OutputData, OutputGenerator, OutputManifest};
pub use processor::ResumeProcessor;
pub use recommendations::Recommendation;
pub use scoring::{score_job, score_match, score_resume, ScoreReport};
pub use scraper::{JobPosting, JobScraperManager, SearchFilters};
pub use state::StateManager;
pub use validation::ValidationResult;

/// Library version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Default configuration file path
pub const DEFAULT_CONFIG_PATH: &str = "config/config.toml";

/// Prelude module for convenient imports
pub mod prelude {
    //! Convenient imports for common use cases.
    //!
    //! ```rust
    //! use ats_checker::prelude::*;
    //! ```

    pub use crate::config::Config;
    pub use crate::error::{AtsError, Result};
    pub use crate::processor::ResumeProcessor;
    pub use crate::recommendations::Recommendation;
    pub use crate::scoring::{score_job, score_match, score_resume, ScoreReport};
    pub use crate::scraper::{JobPosting, SearchFilters};
    pub use crate::state::StateManager;
}
