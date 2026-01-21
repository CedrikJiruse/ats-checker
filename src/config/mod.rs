//! Configuration management module.
//!
//! This module handles loading, validating, and managing configuration
//! from TOML files with support for profile overlays.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::error::{AtsError, Result};

/// Main configuration struct for the ATS Checker.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    // -------------------------
    // Paths
    // -------------------------
    /// Folder containing input resumes.
    #[serde(default = "default_input_resumes_folder")]
    pub input_resumes_folder: PathBuf,

    /// Folder containing job descriptions.
    #[serde(default = "default_job_descriptions_folder")]
    pub job_descriptions_folder: PathBuf,

    /// Folder for generated outputs.
    #[serde(default = "default_output_folder")]
    pub output_folder: PathBuf,

    /// Path to the state file.
    #[serde(default = "default_state_file")]
    pub state_file: PathBuf,

    /// Path to scoring weights TOML.
    #[serde(default = "default_scoring_weights_file")]
    pub scoring_weights_file: PathBuf,

    /// Path to saved searches file.
    #[serde(default = "default_saved_searches_file")]
    pub saved_searches_file: PathBuf,

    /// Folder for job search results.
    #[serde(default = "default_job_search_results_folder")]
    pub job_search_results_folder: PathBuf,

    /// Path to Tesseract command (for OCR).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tesseract_cmd: Option<String>,

    // -------------------------
    // AI Settings
    // -------------------------
    /// Environment variable name for Gemini API key.
    #[serde(default = "default_gemini_api_key_env")]
    pub gemini_api_key_env: String,

    /// Default model name.
    #[serde(default = "default_model_name")]
    pub default_model_name: String,

    /// Default temperature.
    #[serde(default = "default_temperature")]
    pub default_temperature: f64,

    /// Default top_p.
    #[serde(default = "default_top_p")]
    pub default_top_p: f64,

    /// Default top_k.
    #[serde(default = "default_top_k")]
    pub default_top_k: i32,

    /// Default max output tokens.
    #[serde(default = "default_max_output_tokens")]
    pub default_max_output_tokens: i32,

    // -------------------------
    // Processing Settings
    // -------------------------
    /// Number of resume versions per job.
    #[serde(default = "default_num_versions_per_job")]
    pub num_versions_per_job: i32,

    /// Whether to iterate until score is reached.
    #[serde(default)]
    pub iterate_until_score_reached: bool,

    /// Target score for iteration.
    #[serde(default = "default_target_score")]
    pub target_score: f64,

    /// Maximum number of iterations.
    #[serde(default = "default_max_iterations")]
    pub max_iterations: i32,

    /// Iteration strategy (best_of, first_hit, patience).
    #[serde(default = "default_iteration_strategy")]
    pub iteration_strategy: String,

    /// Maximum regressions before stopping.
    #[serde(default = "default_max_regressions")]
    pub max_regressions: i32,

    /// Maximum concurrent API requests.
    #[serde(default = "default_max_concurrent_requests")]
    pub max_concurrent_requests: i32,

    /// Whether to enable score caching.
    #[serde(default)]
    pub score_cache_enabled: bool,

    /// Output format (json, toml, both).
    #[serde(default = "default_structured_output_format")]
    pub structured_output_format: String,

    /// Whether schema validation is enabled.
    #[serde(default)]
    pub schema_validation_enabled: bool,

    /// Path to resume JSON schema.
    #[serde(default = "default_resume_schema_path")]
    pub resume_schema_path: PathBuf,

    /// Whether recommendations are enabled.
    #[serde(default = "default_recommendations_enabled")]
    pub recommendations_enabled: bool,

    /// Maximum recommendation items.
    #[serde(default = "default_recommendations_max_items")]
    pub recommendations_max_items: i32,

    /// Output subdirectory pattern.
    #[serde(default = "default_output_subdir_pattern")]
    pub output_subdir_pattern: String,

    // -------------------------
    // AI Agents
    // -------------------------
    /// AI agent configurations.
    #[serde(default)]
    pub ai_agents: HashMap<String, AgentConfig>,

    // -------------------------
    // Job Search
    // -------------------------
    /// Job portal configurations.
    #[serde(default)]
    pub job_portals: HashMap<String, PortalConfig>,

    /// Default job search sources.
    #[serde(default)]
    pub job_search_default_sources: Vec<String>,

    /// Default max results for job search.
    #[serde(default = "default_job_search_max_results")]
    pub job_search_default_max_results: i32,

    /// Default location for job search.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub job_search_default_location: Option<String>,

    /// Default remote only filter.
    #[serde(default)]
    pub job_search_default_remote_only: bool,

    /// Default date posted filter.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub job_search_default_date_posted: Option<String>,

    /// Default job type filter.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub job_search_default_job_type: Option<Vec<String>>,

    // -------------------------
    // Profile
    // -------------------------
    /// Optional profile file path.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub profile_file: Option<PathBuf>,
}

// Default value functions
fn default_input_resumes_folder() -> PathBuf {
    PathBuf::from("workspace/input_resumes")
}
fn default_job_descriptions_folder() -> PathBuf {
    PathBuf::from("workspace/job_descriptions")
}
fn default_output_folder() -> PathBuf {
    PathBuf::from("workspace/output")
}
fn default_state_file() -> PathBuf {
    PathBuf::from("data/processed_resumes_state.toml")
}
fn default_scoring_weights_file() -> PathBuf {
    PathBuf::from("config/scoring_weights.toml")
}
fn default_saved_searches_file() -> PathBuf {
    PathBuf::from("data/saved_searches.toml")
}
fn default_job_search_results_folder() -> PathBuf {
    PathBuf::from("workspace/job_search_results")
}
fn default_gemini_api_key_env() -> String {
    "GEMINI_API_KEY".to_string()
}
fn default_model_name() -> String {
    "gemini-pro".to_string()
}
fn default_temperature() -> f64 {
    0.7
}
fn default_top_p() -> f64 {
    0.95
}
fn default_top_k() -> i32 {
    40
}
fn default_max_output_tokens() -> i32 {
    8192
}
fn default_num_versions_per_job() -> i32 {
    1
}
fn default_target_score() -> f64 {
    80.0
}
fn default_max_iterations() -> i32 {
    3
}
fn default_iteration_strategy() -> String {
    "best_of".to_string()
}
fn default_max_regressions() -> i32 {
    2
}
fn default_max_concurrent_requests() -> i32 {
    1
}
fn default_structured_output_format() -> String {
    "toml".to_string()
}
fn default_resume_schema_path() -> PathBuf {
    PathBuf::from("config/resume_schema.json")
}
fn default_recommendations_enabled() -> bool {
    true
}
fn default_recommendations_max_items() -> i32 {
    5
}
fn default_output_subdir_pattern() -> String {
    "{resume_name}/{job_title}/{timestamp}".to_string()
}
fn default_job_search_max_results() -> i32 {
    50
}

impl Default for Config {
    fn default() -> Self {
        Self {
            input_resumes_folder: default_input_resumes_folder(),
            job_descriptions_folder: default_job_descriptions_folder(),
            output_folder: default_output_folder(),
            state_file: default_state_file(),
            scoring_weights_file: default_scoring_weights_file(),
            saved_searches_file: default_saved_searches_file(),
            job_search_results_folder: default_job_search_results_folder(),
            tesseract_cmd: None,
            gemini_api_key_env: default_gemini_api_key_env(),
            default_model_name: default_model_name(),
            default_temperature: default_temperature(),
            default_top_p: default_top_p(),
            default_top_k: default_top_k(),
            default_max_output_tokens: default_max_output_tokens(),
            num_versions_per_job: default_num_versions_per_job(),
            iterate_until_score_reached: false,
            target_score: default_target_score(),
            max_iterations: default_max_iterations(),
            iteration_strategy: default_iteration_strategy(),
            max_regressions: default_max_regressions(),
            max_concurrent_requests: default_max_concurrent_requests(),
            score_cache_enabled: false,
            structured_output_format: default_structured_output_format(),
            schema_validation_enabled: false,
            resume_schema_path: default_resume_schema_path(),
            recommendations_enabled: default_recommendations_enabled(),
            recommendations_max_items: default_recommendations_max_items(),
            output_subdir_pattern: default_output_subdir_pattern(),
            ai_agents: HashMap::new(),
            job_portals: HashMap::new(),
            job_search_default_sources: vec!["linkedin".to_string(), "indeed".to_string()],
            job_search_default_max_results: default_job_search_max_results(),
            job_search_default_location: None,
            job_search_default_remote_only: false,
            job_search_default_date_posted: None,
            job_search_default_job_type: None,
            profile_file: None,
        }
    }
}

impl Config {
    /// Load configuration from a TOML file.
    pub fn load(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref();

        if !path.exists() {
            return Err(AtsError::ConfigNotFound {
                path: path.to_path_buf(),
            });
        }

        let content = std::fs::read_to_string(path)?;
        let mut config: Config = toml::from_str(&content)?;

        // Load profile overlay if specified
        if let Some(ref profile_path) = config.profile_file {
            if profile_path.exists() {
                let profile_content = std::fs::read_to_string(profile_path)?;
                let profile: Config = toml::from_str(&profile_content)?;
                config = config.merge(profile);
            }
        }

        // Expand relative paths
        config.expand_paths(path.parent());

        Ok(config)
    }

    /// Merge another config into this one (overlay pattern).
    pub fn merge(mut self, overlay: Config) -> Self {
        // Only merge non-default values
        // This is a simplified merge - a real implementation would be more sophisticated
        if overlay.iterate_until_score_reached {
            self.iterate_until_score_reached = overlay.iterate_until_score_reached;
        }
        if overlay.target_score != default_target_score() {
            self.target_score = overlay.target_score;
        }
        if overlay.max_iterations != default_max_iterations() {
            self.max_iterations = overlay.max_iterations;
        }
        // ... additional field merging would go here
        self
    }

    /// Expand relative paths to absolute paths.
    fn expand_paths(&mut self, base: Option<&Path>) {
        let base = base.unwrap_or_else(|| Path::new("."));

        let expand = |p: &mut PathBuf| {
            if p.is_relative() {
                *p = base.join(&p);
            }
        };

        expand(&mut self.input_resumes_folder);
        expand(&mut self.job_descriptions_folder);
        expand(&mut self.output_folder);
        expand(&mut self.state_file);
        expand(&mut self.scoring_weights_file);
        expand(&mut self.saved_searches_file);
        expand(&mut self.job_search_results_folder);
        expand(&mut self.resume_schema_path);
    }

    /// Ensure all required directories exist.
    pub fn ensure_directories(&self) -> Result<()> {
        let dirs = [
            &self.input_resumes_folder,
            &self.job_descriptions_folder,
            &self.output_folder,
            &self.job_search_results_folder,
        ];

        for dir in dirs {
            if !dir.exists() {
                std::fs::create_dir_all(dir).map_err(|e| AtsError::DirectoryCreation {
                    path: dir.clone(),
                    source: e,
                })?;
            }
        }

        // Ensure parent dirs for files
        for file in [&self.state_file, &self.saved_searches_file] {
            if let Some(parent) = file.parent() {
                if !parent.exists() {
                    std::fs::create_dir_all(parent)?;
                }
            }
        }

        Ok(())
    }

    /// Validate the configuration.
    pub fn validate(&self) -> Result<()> {
        // Validate iteration strategy
        let valid_strategies = ["best_of", "first_hit", "patience"];
        if !valid_strategies.contains(&self.iteration_strategy.as_str()) {
            return Err(AtsError::ConfigInvalidValue {
                field: "iteration_strategy".to_string(),
                message: format!("Must be one of: {}", valid_strategies.join(", ")),
            });
        }

        // Validate temperature
        if !(0.0..=2.0).contains(&self.default_temperature) {
            return Err(AtsError::ConfigInvalidValue {
                field: "default_temperature".to_string(),
                message: "Must be between 0.0 and 2.0".to_string(),
            });
        }

        // Validate target score
        if !(0.0..=100.0).contains(&self.target_score) {
            return Err(AtsError::ConfigInvalidValue {
                field: "target_score".to_string(),
                message: "Must be between 0.0 and 100.0".to_string(),
            });
        }

        Ok(())
    }
}

/// Agent configuration.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AgentConfig {
    /// Provider name (gemini, openai, anthropic, llama).
    #[serde(default = "default_provider")]
    pub provider: String,

    /// Role/purpose of this agent.
    #[serde(default)]
    pub role: String,

    /// Model name.
    #[serde(default = "default_model_name")]
    pub model_name: String,

    /// Temperature.
    #[serde(default = "default_temperature")]
    pub temperature: f64,

    /// Top P.
    #[serde(default = "default_top_p")]
    pub top_p: f64,

    /// Top K.
    #[serde(default = "default_top_k")]
    pub top_k: i32,

    /// Max output tokens.
    #[serde(default = "default_max_output_tokens")]
    pub max_output_tokens: i32,

    /// Max retries.
    #[serde(default)]
    pub max_retries: i32,

    /// Retry on empty response.
    #[serde(default = "default_true")]
    pub retry_on_empty: bool,

    /// Require JSON output.
    #[serde(default)]
    pub require_json: bool,

    /// Extra provider-specific options.
    #[serde(default)]
    pub extras: HashMap<String, serde_json::Value>,
}

fn default_provider() -> String {
    "gemini".to_string()
}
fn default_true() -> bool {
    true
}

/// Job portal configuration.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PortalConfig {
    /// Whether this portal is enabled.
    #[serde(default = "default_true")]
    pub enabled: bool,

    /// Default location for this portal.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default_location: Option<String>,

    /// Default country code.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default_country: Option<String>,

    /// Default max results.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default_max_results: Option<i32>,

    /// Default date posted filter.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default_date_posted: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.default_temperature, 0.7);
        assert_eq!(config.iteration_strategy, "best_of");
    }

    #[test]
    fn test_config_validation() {
        let mut config = Config::default();
        assert!(config.validate().is_ok());

        config.iteration_strategy = "invalid".to_string();
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_config_load_not_found() {
        let result = Config::load("/nonexistent/config.toml");
        assert!(matches!(result, Err(AtsError::ConfigNotFound { .. })));
    }

    #[test]
    fn test_config_serialization() {
        let config = Config::default();
        let toml_str = toml::to_string(&config).unwrap();
        let parsed: Config = toml::from_str(&toml_str).unwrap();
        assert_eq!(config.default_temperature, parsed.default_temperature);
    }
}
