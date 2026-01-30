//! Error types for the ATS Checker library.
//!
//! This module defines all error types used throughout the library,
//! providing structured error handling with context and error chaining.
//!
//! # Error Hierarchy
//!
//! - [`AtsError`] - Main error enum containing all error variants
//! - Configuration errors - Configuration-related errors (`ConfigNotFound`, `ConfigParse`, etc.)
//! - API errors - External API call errors (`ApiRequest`, `ApiResponse`, etc.)
//! - Scraper errors - Job scraping errors (`JobScraperOperation`, `JobPortalNotFound`, etc.)
//!
//! # Example
//!
//! ```rust
//! use ats_checker::error::{AtsError, Result};
//!
//! fn load_resume(path: &str) -> Result<String> {
//!     std::fs::read_to_string(path)
//!         .map_err(|e| AtsError::Io {
//!             message: format!("Failed to read resume: {}", path),
//!             source: e,
//!         })
//! }
//! ```

use std::path::PathBuf;
use thiserror::Error;

/// Result type alias for ATS Checker operations.
pub type Result<T> = std::result::Result<T, AtsError>;

/// Main error type for the ATS Checker library.
///
/// This enum encompasses all possible errors that can occur during
/// library operations.
#[derive(Error, Debug)]
pub enum AtsError {
    // -------------------------
    // Configuration Errors
    // -------------------------
    /// Configuration file not found.
    #[error("Configuration file not found: {path}")]
    ConfigNotFound {
        /// Path to the missing configuration file.
        path: PathBuf,
    },

    /// Configuration parsing error.
    #[error("Failed to parse configuration: {message}")]
    ConfigParse {
        /// Description of the parse error.
        message: String,
        /// The underlying error.
        #[source]
        source: Option<Box<dyn std::error::Error + Send + Sync>>,
    },

    /// Configuration validation error.
    #[error("Configuration validation failed: {message}")]
    ConfigValidation {
        /// Description of the validation error.
        message: String,
    },

    /// Missing required configuration field.
    #[error("Missing required configuration field: {field}")]
    ConfigMissingField {
        /// Name of the missing field.
        field: String,
    },

    /// Invalid configuration value.
    #[error("Invalid configuration value for {field}: {message}")]
    ConfigInvalidValue {
        /// Name of the field with invalid value.
        field: String,
        /// Description of why the value is invalid.
        message: String,
    },

    // -------------------------
    // I/O Errors
    // -------------------------
    /// General I/O error.
    #[error("I/O error: {message}")]
    Io {
        /// Description of the I/O operation that failed.
        message: String,
        /// The underlying I/O error.
        #[source]
        source: std::io::Error,
    },

    /// File not found error.
    #[error("File not found: {path}")]
    FileNotFound {
        /// Path to the missing file.
        path: PathBuf,
    },

    /// Permission denied error.
    #[error("Permission denied: {path}")]
    PermissionDenied {
        /// Path where permission was denied.
        path: PathBuf,
    },

    /// Directory creation error.
    #[error("Failed to create directory: {path}")]
    DirectoryCreation {
        /// Path of the directory that couldn't be created.
        path: PathBuf,
        /// The underlying error.
        #[source]
        source: std::io::Error,
    },

    // -------------------------
    // Parsing Errors
    // -------------------------
    /// TOML parsing error.
    #[error("TOML parsing error: {message}")]
    TomlParse {
        /// Description of the parse error.
        message: String,
        /// The underlying error.
        #[source]
        source: Option<toml::de::Error>,
    },

    /// JSON parsing error.
    #[error("JSON parsing error: {message}")]
    JsonParse {
        /// Description of the parse error.
        message: String,
        /// The underlying error.
        #[source]
        source: Option<serde_json::Error>,
    },

    /// PDF extraction error.
    #[error("PDF extraction error: {message}")]
    PdfExtraction {
        /// Description of the extraction error.
        message: String,
    },

    /// DOCX extraction error.
    #[error("DOCX extraction error: {message}")]
    DocxExtraction {
        /// Description of the extraction error.
        message: String,
    },

    /// Text extraction error.
    #[error("Text extraction error: {message}")]
    TextExtraction {
        /// Description of the extraction error.
        message: String,
    },

    // -------------------------
    // Validation Errors
    // -------------------------
    /// Schema validation error.
    #[error("Schema validation failed: {message}")]
    SchemaValidation {
        /// Description of the validation error.
        message: String,
        /// List of validation errors.
        errors: Vec<String>,
    },

    /// Input validation error.
    #[error("Input validation failed: {message}")]
    InputValidation {
        /// Description of the validation error.
        message: String,
    },

    // -------------------------
    // API Errors
    // -------------------------
    /// API request error.
    #[error("API request failed: {message}")]
    ApiRequest {
        /// Description of the request error.
        message: String,
        /// The underlying error.
        #[source]
        source: Option<reqwest::Error>,
    },

    /// API response error.
    #[error("API response error: {message}")]
    ApiResponse {
        /// Description of the response error.
        message: String,
        /// HTTP status code if available.
        status_code: Option<u16>,
    },

    /// API authentication error.
    #[error("API authentication failed: {message}")]
    ApiAuth {
        /// Description of the authentication error.
        message: String,
    },

    /// API rate limit exceeded.
    #[error("API rate limit exceeded: {message}")]
    ApiRateLimit {
        /// Description of the rate limit error.
        message: String,
        /// Time to wait before retry (in seconds).
        retry_after: Option<u64>,
    },

    /// API timeout error.
    #[error("API request timed out: {message}")]
    ApiTimeout {
        /// Description of the timeout.
        message: String,
    },

    // -------------------------
    // Agent Errors
    // -------------------------
    /// Agent configuration error.
    #[error("Agent configuration error: {message}")]
    AgentConfig {
        /// Description of the configuration error.
        message: String,
    },

    /// Agent provider error.
    #[error("Agent provider error: {message}")]
    AgentProvider {
        /// Description of the provider error.
        message: String,
    },

    /// Agent response error.
    #[error("Agent response error: {message}")]
    AgentResponse {
        /// Description of the response error.
        message: String,
    },

    /// Unknown agent provider.
    #[error("Unknown agent provider: {provider}")]
    UnknownProvider {
        /// Name of the unknown provider.
        provider: String,
    },

    // -------------------------
    // Scraper Errors
    // -------------------------
    /// Job scraping error.
    #[error("Job scraping error: {message}")]
    Scraper {
        /// Description of the scraping error.
        message: String,
        /// The source that failed.
        source_name: Option<String>,
    },

    /// Scraper blocked error (anti-bot detection).
    #[error("Scraper blocked by {source_name}: {message}")]
    ScraperBlocked {
        /// The source that blocked the scraper.
        source_name: String,
        /// Description of the block.
        message: String,
    },

    /// General scraper error.
    #[error("Scraper error: {message}")]
    ScraperError {
        /// Description of the scraper error.
        message: String,
        /// The underlying error.
        #[source]
        source: Option<Box<dyn std::error::Error + Send + Sync>>,
    },

    /// Cache operation error.
    #[error("Cache error: {message}")]
    CacheError {
        /// Description of the cache error.
        message: String,
    },

    // -------------------------
    // Scoring Errors
    // -------------------------
    /// Scoring calculation error.
    #[error("Scoring error: {message}")]
    Scoring {
        /// Description of the scoring error.
        message: String,
    },

    /// Invalid scoring weights.
    #[error("Invalid scoring weights: {message}")]
    ScoringWeights {
        /// Description of the weights error.
        message: String,
    },

    // -------------------------
    // State Errors
    // -------------------------
    /// State file corruption.
    #[error("State file corrupted: {message}")]
    StateCorrupted {
        /// Description of the corruption.
        message: String,
        /// Path to the corrupted state file.
        path: PathBuf,
    },

    /// State operation error.
    #[error("State operation failed: {message}")]
    StateOperation {
        /// Description of the failed operation.
        message: String,
    },

    // -------------------------
    // Processing Errors
    // -------------------------
    /// Resume processing error.
    #[error("Resume processing error: {message}")]
    Processing {
        /// Description of the processing error.
        message: String,
    },

    /// Iteration error.
    #[error("Iteration error: {message}")]
    Iteration {
        /// Description of the iteration error.
        message: String,
        /// Current iteration number.
        iteration: u32,
    },

    // -------------------------
    // Output Errors
    // -------------------------
    /// Output generation error.
    #[error("Output generation error: {message}")]
    OutputGeneration {
        /// Description of the output error.
        message: String,
    },

    /// Unsupported output format.
    #[error("Unsupported output format: {format}")]
    UnsupportedFormat {
        /// The unsupported format.
        format: String,
    },

    // -------------------------
    // OCR Errors
    // -------------------------
    /// OCR processing error.
    #[error("OCR error: {message}")]
    Ocr {
        /// Description of the OCR error.
        message: String,
    },

    /// Tesseract not found.
    #[error("Tesseract not found at: {path}")]
    TesseractNotFound {
        /// Expected path to Tesseract.
        path: String,
    },

    // -------------------------
    // Hash Errors
    // -------------------------
    /// File hashing error.
    #[error("Hashing error: {message}")]
    Hash {
        /// Description of the hashing error.
        message: String,
    },

    // -------------------------
    // Network Errors
    // -------------------------
    /// Network connection error.
    #[error("Network error: {message}")]
    Network {
        /// Description of the network error.
        message: String,
        /// The underlying error.
        #[source]
        source: Option<reqwest::Error>,
    },

    // -------------------------
    // Generic Errors
    // -------------------------
    /// Generic internal error.
    #[error("Internal error: {message}")]
    Internal {
        /// Description of the internal error.
        message: String,
    },

    /// Operation not supported.
    #[error("Operation not supported: {message}")]
    NotSupported {
        /// Description of the unsupported operation.
        message: String,
    },

    /// Operation cancelled.
    #[error("Operation cancelled")]
    Cancelled,
}

impl AtsError {
    /// Create a new I/O error with context.
    pub fn io(message: impl Into<String>, source: std::io::Error) -> Self {
        Self::Io {
            message: message.into(),
            source,
        }
    }

    /// Create a new configuration parse error.
    pub fn config_parse(message: impl Into<String>) -> Self {
        Self::ConfigParse {
            message: message.into(),
            source: None,
        }
    }

    /// Create a new API request error.
    pub fn api_request(message: impl Into<String>, source: Option<reqwest::Error>) -> Self {
        Self::ApiRequest {
            message: message.into(),
            source,
        }
    }

    /// Create a new internal error.
    pub fn internal(message: impl Into<String>) -> Self {
        Self::Internal {
            message: message.into(),
        }
    }

    /// Check if this is a retryable error.
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            Self::ApiRateLimit { .. }
                | Self::ApiTimeout { .. }
                | Self::Network { .. }
                | Self::ScraperError { .. }
        )
    }

    /// Get the HTTP status code if this is an API error.
    pub fn status_code(&self) -> Option<u16> {
        match self {
            Self::ApiResponse { status_code, .. } => *status_code,
            _ => None,
        }
    }
}

// Implement From for common error types

impl From<std::io::Error> for AtsError {
    fn from(err: std::io::Error) -> Self {
        Self::Io {
            message: err.to_string(),
            source: err,
        }
    }
}

impl From<toml::de::Error> for AtsError {
    fn from(err: toml::de::Error) -> Self {
        Self::TomlParse {
            message: err.to_string(),
            source: Some(err),
        }
    }
}

impl From<serde_json::Error> for AtsError {
    fn from(err: serde_json::Error) -> Self {
        Self::JsonParse {
            message: err.to_string(),
            source: Some(err),
        }
    }
}

impl From<reqwest::Error> for AtsError {
    fn from(err: reqwest::Error) -> Self {
        if err.is_timeout() {
            Self::ApiTimeout {
                message: err.to_string(),
            }
        } else if err.is_connect() {
            Self::Network {
                message: err.to_string(),
                source: Some(err),
            }
        } else {
            Self::ApiRequest {
                message: err.to_string(),
                source: Some(err),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let err = AtsError::ConfigNotFound {
            path: PathBuf::from("/path/to/config.toml"),
        };
        assert!(err.to_string().contains("Configuration file not found"));
    }

    #[test]
    fn test_is_retryable() {
        let rate_limit = AtsError::ApiRateLimit {
            message: "Too many requests".to_string(),
            retry_after: Some(60),
        };
        assert!(rate_limit.is_retryable());

        let config_err = AtsError::ConfigNotFound {
            path: PathBuf::from("/path"),
        };
        assert!(!config_err.is_retryable());
    }

    #[test]
    fn test_from_io_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let ats_err: AtsError = io_err.into();
        assert!(matches!(ats_err, AtsError::Io { .. }));
    }

    #[test]
    fn test_helper_methods() {
        let err = AtsError::internal("something went wrong");
        assert!(err.to_string().contains("something went wrong"));

        let err = AtsError::config_parse("invalid TOML");
        assert!(err.to_string().contains("invalid TOML"));
    }
}
