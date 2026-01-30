//! LLM agent abstraction layer.
//!
//! This module provides a provider-agnostic interface for working with LLMs.
//! It supports multiple providers (Gemini, `OpenAI`, Claude, Llama) through a
//! unified Agent trait.
//!
//! # Agent Roles
//!
//! - **enhancer**: Converts raw resume text to structured JSON
//! - **`job_summarizer`**: Summarizes job descriptions
//! - **scorer**: Scores resumes (currently deterministic, not LLM-based)
//! - **reviser**: Iteratively improves resumes based on feedback
//!
//! # Example
//!
//! ```no_run
//! use ats_checker::agents::{Agent, AgentConfig, GeminiAgent};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let config = AgentConfig::builder()
//!         .name("enhancer")
//!         .role("resume_enhancement")
//!         .require_json(true)
//!         .build();
//!
//!     let agent = GeminiAgent::from_env(config)?;
//!     let result: serde_json::Value = agent.generate_json("Enhance this resume: John Doe, Engineer").await?;
//!     println!("{}", serde_json::to_string_pretty(&result)?);
//!     Ok(())
//! }
//! ```

use crate::anthropic::{AnthropicClient, GenerationConfig as AnthropicGenerationConfig};
use crate::error::{AtsError, Result};
use crate::gemini::{GeminiClient, GenerationConfig as GeminiGenerationConfig};
use crate::llama::{GenerationConfig as LlamaGenerationConfig, LlamaClient};
use crate::openai::{GenerationConfig as OpenAiGenerationConfig, OpenAiClient};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// -------------------------
// Agent Configuration
// -------------------------

/// Configuration for an LLM agent.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    /// Agent name (e.g., "enhancer", "reviser").
    pub name: String,

    /// Provider (e.g., "gemini", "openai", "anthropic").
    #[serde(default = "default_provider")]
    pub provider: String,

    /// Agent role (e.g., "`resume_enhancement`", "`job_summary`").
    #[serde(default = "default_role")]
    pub role: String,

    /// Model name (e.g., "gemini-1.5-flash").
    pub model_name: String,

    /// Temperature (0.0 to 2.0).
    #[serde(default = "default_temperature")]
    pub temperature: f64,

    /// Top-p sampling.
    #[serde(default = "default_top_p")]
    pub top_p: f64,

    /// Top-k sampling.
    #[serde(default = "default_top_k")]
    pub top_k: i32,

    /// Maximum output tokens.
    #[serde(default = "default_max_output_tokens")]
    pub max_output_tokens: i32,

    /// Maximum retries on failure.
    #[serde(default)]
    pub max_retries: i32,

    /// Retry on empty responses.
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

fn default_role() -> String {
    "generic".to_string()
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

fn default_true() -> bool {
    true
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            name: "default".to_string(),
            provider: default_provider(),
            role: default_role(),
            model_name: "gemini-1.5-flash".to_string(),
            temperature: default_temperature(),
            top_p: default_top_p(),
            top_k: default_top_k(),
            max_output_tokens: default_max_output_tokens(),
            max_retries: 0,
            retry_on_empty: true,
            require_json: false,
            extras: HashMap::new(),
        }
    }
}

impl AgentConfig {
    /// Create a builder for `AgentConfig`.
    pub fn builder() -> AgentConfigBuilder {
        AgentConfigBuilder::default()
    }
}

/// Builder for `AgentConfig`.
#[derive(Default)]
pub struct AgentConfigBuilder {
    name: Option<String>,
    provider: Option<String>,
    role: Option<String>,
    model_name: Option<String>,
    temperature: Option<f64>,
    top_p: Option<f64>,
    top_k: Option<i32>,
    max_output_tokens: Option<i32>,
    max_retries: Option<i32>,
    retry_on_empty: Option<bool>,
    require_json: Option<bool>,
}

impl AgentConfigBuilder {
    /// Set the agent name.
    #[must_use]
    pub fn name(mut self, name: impl Into<String>) -> Self {
        self.name = Some(name.into());
        self
    }

    /// Set the provider (e.g., "gemini", "openai").
    #[must_use]
    pub fn provider(mut self, provider: impl Into<String>) -> Self {
        self.provider = Some(provider.into());
        self
    }

    /// Set the agent role (e.g., "`resume_enhancement`").
    #[must_use]
    pub fn role(mut self, role: impl Into<String>) -> Self {
        self.role = Some(role.into());
        self
    }

    /// Set the model name (e.g., "gemini-1.5-flash").
    #[must_use]
    pub fn model_name(mut self, model: impl Into<String>) -> Self {
        self.model_name = Some(model.into());
        self
    }

    /// Set the temperature (0.0-2.0).
    #[must_use]
    pub fn temperature(mut self, temp: f64) -> Self {
        self.temperature = Some(temp);
        self
    }

    /// Set top-p sampling parameter.
    #[must_use]
    pub fn top_p(mut self, p: f64) -> Self {
        self.top_p = Some(p);
        self
    }

    /// Set top-k sampling parameter.
    #[must_use]
    pub fn top_k(mut self, k: i32) -> Self {
        self.top_k = Some(k);
        self
    }

    /// Set maximum output tokens.
    #[must_use]
    pub fn max_output_tokens(mut self, tokens: i32) -> Self {
        self.max_output_tokens = Some(tokens);
        self
    }

    /// Set maximum retry attempts.
    #[must_use]
    pub fn max_retries(mut self, retries: i32) -> Self {
        self.max_retries = Some(retries);
        self
    }

    /// Set whether to retry on empty responses.
    #[must_use]
    pub fn retry_on_empty(mut self, retry: bool) -> Self {
        self.retry_on_empty = Some(retry);
        self
    }

    /// Set whether JSON output is required.
    #[must_use]
    pub fn require_json(mut self, require: bool) -> Self {
        self.require_json = Some(require);
        self
    }

    /// Build the `AgentConfig`.
    pub fn build(self) -> AgentConfig {
        let defaults = AgentConfig::default();

        AgentConfig {
            name: self.name.unwrap_or(defaults.name),
            provider: self.provider.unwrap_or(defaults.provider),
            role: self.role.unwrap_or(defaults.role),
            model_name: self.model_name.unwrap_or(defaults.model_name),
            temperature: self.temperature.unwrap_or(defaults.temperature),
            top_p: self.top_p.unwrap_or(defaults.top_p),
            top_k: self.top_k.unwrap_or(defaults.top_k),
            max_output_tokens: self.max_output_tokens.unwrap_or(defaults.max_output_tokens),
            max_retries: self.max_retries.unwrap_or(defaults.max_retries),
            retry_on_empty: self.retry_on_empty.unwrap_or(defaults.retry_on_empty),
            require_json: self.require_json.unwrap_or(defaults.require_json),
            extras: HashMap::new(),
        }
    }
}

// -------------------------
// Agent Trait
// -------------------------

/// Agent trait for LLM providers.
#[async_trait]
pub trait Agent: Send + Sync {
    /// Get the agent's configuration.
    fn config(&self) -> &AgentConfig;

    /// Generate text from a prompt.
    async fn generate_text(&self, prompt: &str) -> Result<String>;

    /// Generate JSON from a prompt.
    async fn generate_json(&self, prompt: &str) -> Result<serde_json::Value>;
}

// -------------------------
// Gemini Agent Implementation
// -------------------------

/// Gemini-based agent implementation.
pub struct GeminiAgent {
    config: AgentConfig,
    client: GeminiClient,
}

impl GeminiAgent {
    /// Create a new Gemini agent from environment.
    ///
    /// # Errors
    ///
    /// Returns an error if the `GEMINI_API_KEY` environment variable is not set.
    pub fn from_env(config: AgentConfig) -> Result<Self> {
        let generation_config = GeminiGenerationConfig {
            temperature: Some(config.temperature),
            top_p: Some(config.top_p),
            top_k: Some(config.top_k),
            max_output_tokens: Some(config.max_output_tokens),
        };

        let client = GeminiClient::from_env_with_model(&config.model_name)?
            .with_generation_config(generation_config);

        Ok(Self { config, client })
    }

    /// Create a new Gemini agent with explicit API key.
    ///
    /// # Errors
    ///
    /// Returns an error if the API key is invalid or the model name is not supported.
    pub fn new(api_key: impl Into<String>, config: AgentConfig) -> Result<Self> {
        let generation_config = GeminiGenerationConfig {
            temperature: Some(config.temperature),
            top_p: Some(config.top_p),
            top_k: Some(config.top_k),
            max_output_tokens: Some(config.max_output_tokens),
        };

        let client = GeminiClient::new(api_key, &config.model_name)?
            .with_generation_config(generation_config);

        Ok(Self { config, client })
    }

    /// Generate text with retry logic.
    async fn generate_with_retry(&self, prompt: &str) -> Result<String> {
        let mut last_error = None;
        let max_attempts = 1 + self.config.max_retries.max(0);

        for attempt in 0..max_attempts {
            match self.client.generate_content(prompt).await {
                Ok(text) => {
                    if self.config.retry_on_empty && text.trim().is_empty() {
                        last_error = Some(AtsError::ApiResponse {
                            message: "Empty response from API".to_string(),
                            status_code: None,
                        });
                        continue;
                    }

                    return Ok(text);
                }
                Err(e) => {
                    last_error = Some(e);

                    // Don't retry on auth errors
                    if matches!(last_error, Some(AtsError::ApiAuth { .. })) {
                        break;
                    }

                    // Add small delay before retry
                    if attempt < max_attempts - 1 {
                        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                    }
                }
            }
        }

        Err(last_error.unwrap_or_else(|| AtsError::ApiRequest {
            message: "All retry attempts failed".to_string(),
            source: None,
        }))
    }
}

#[async_trait]
impl Agent for GeminiAgent {
    fn config(&self) -> &AgentConfig {
        &self.config
    }

    async fn generate_text(&self, prompt: &str) -> Result<String> {
        let text = self.generate_with_retry(prompt).await?;

        // If require_json is set, validate it's valid JSON
        if self.config.require_json {
            let cleaned = strip_markdown_fences(&text);
            serde_json::from_str::<serde_json::Value>(&cleaned).map_err(|e| {
                AtsError::ApiResponse {
                    message: format!("Response is not valid JSON: {e}"),
                    status_code: None,
                }
            })?;

            // Return cleaned JSON
            return Ok(cleaned);
        }

        Ok(text)
    }

    async fn generate_json(&self, prompt: &str) -> Result<serde_json::Value> {
        // Add JSON instruction to prompt if not already present
        let enhanced_prompt = if prompt.to_lowercase().contains("json") {
            prompt.to_string()
        } else {
            format!(
                "{prompt}\n\nIMPORTANT: Output MUST be a raw JSON object only. No markdown fences. No commentary."
            )
        };

        let text = self.generate_with_retry(&enhanced_prompt).await?;
        let cleaned = strip_markdown_fences(&text);

        serde_json::from_str(&cleaned).map_err(|e| AtsError::ApiResponse {
            message: format!("Failed to parse JSON: {e}"),
            status_code: None,
        })
    }
}

// -------------------------
// OpenAI Agent Implementation
// -------------------------

/// OpenAI-based agent implementation.
pub struct OpenAiAgent {
    config: AgentConfig,
    client: OpenAiClient,
}

impl OpenAiAgent {
    /// Create a new OpenAI agent from environment.
    ///
    /// # Errors
    ///
    /// Returns an error if the `OPENAI_API_KEY` environment variable is not set.
    pub fn from_env(config: AgentConfig) -> Result<Self> {
        let generation_config = OpenAiGenerationConfig {
            temperature: Some(config.temperature),
            top_p: Some(config.top_p),
            max_tokens: Some(config.max_output_tokens),
        };

        let client = OpenAiClient::from_env_with_model(&config.model_name)?
            .with_generation_config(generation_config);

        Ok(Self { config, client })
    }

    /// Create a new OpenAI agent with explicit API key.
    ///
    /// # Errors
    ///
    /// Returns an error if the API key is invalid.
    pub fn new(api_key: impl Into<String>, config: AgentConfig) -> Result<Self> {
        let generation_config = OpenAiGenerationConfig {
            temperature: Some(config.temperature),
            top_p: Some(config.top_p),
            max_tokens: Some(config.max_output_tokens),
        };

        let client = OpenAiClient::new(api_key, &config.model_name)?
            .with_generation_config(generation_config);

        Ok(Self { config, client })
    }

    /// Generate text with retry logic.
    async fn generate_with_retry(&self, prompt: &str) -> Result<String> {
        let mut last_error = None;
        let max_attempts = 1 + self.config.max_retries.max(0);

        for attempt in 0..max_attempts {
            match self.client.generate_content(prompt).await {
                Ok(text) => {
                    if self.config.retry_on_empty && text.trim().is_empty() {
                        last_error = Some(AtsError::ApiResponse {
                            message: "Empty response from API".to_string(),
                            status_code: None,
                        });
                        continue;
                    }

                    return Ok(text);
                }
                Err(e) => {
                    last_error = Some(e);

                    // Don't retry on auth errors
                    if matches!(last_error, Some(AtsError::ApiAuth { .. })) {
                        break;
                    }

                    // Add small delay before retry
                    if attempt < max_attempts - 1 {
                        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                    }
                }
            }
        }

        Err(last_error.unwrap_or_else(|| AtsError::ApiRequest {
            message: "All retry attempts failed".to_string(),
            source: None,
        }))
    }
}

#[async_trait]
impl Agent for OpenAiAgent {
    fn config(&self) -> &AgentConfig {
        &self.config
    }

    async fn generate_text(&self, prompt: &str) -> Result<String> {
        let text = self.generate_with_retry(prompt).await?;

        // If require_json is set, validate it's valid JSON
        if self.config.require_json {
            let cleaned = strip_markdown_fences(&text);
            serde_json::from_str::<serde_json::Value>(&cleaned).map_err(|e| {
                AtsError::ApiResponse {
                    message: format!("Response is not valid JSON: {e}"),
                    status_code: None,
                }
            })?;

            // Return cleaned JSON
            return Ok(cleaned);
        }

        Ok(text)
    }

    async fn generate_json(&self, prompt: &str) -> Result<serde_json::Value> {
        // Add JSON instruction to prompt if not already present
        let enhanced_prompt = if prompt.to_lowercase().contains("json") {
            prompt.to_string()
        } else {
            format!(
                "{prompt}\n\nIMPORTANT: Output MUST be a raw JSON object only. No markdown fences. No commentary."
            )
        };

        let text = self.generate_with_retry(&enhanced_prompt).await?;
        let cleaned = strip_markdown_fences(&text);

        serde_json::from_str(&cleaned).map_err(|e| AtsError::ApiResponse {
            message: format!("Failed to parse JSON: {e}"),
            status_code: None,
        })
    }
}

// -------------------------
// Anthropic Agent Implementation
// -------------------------

/// Anthropic Claude-based agent implementation.
pub struct AnthropicAgent {
    config: AgentConfig,
    client: AnthropicClient,
}

impl AnthropicAgent {
    /// Create a new Anthropic agent from environment.
    ///
    /// # Errors
    ///
    /// Returns an error if the `ANTHROPIC_API_KEY` environment variable is not set.
    pub fn from_env(config: AgentConfig) -> Result<Self> {
        let generation_config = AnthropicGenerationConfig {
            temperature: Some(config.temperature),
            top_p: Some(config.top_p),
            top_k: Some(config.top_k),
            max_tokens: Some(config.max_output_tokens),
        };

        let client = AnthropicClient::from_env_with_model(&config.model_name)?
            .with_generation_config(generation_config);

        Ok(Self { config, client })
    }

    /// Create a new Anthropic agent with explicit API key.
    ///
    /// # Errors
    ///
    /// Returns an error if the API key is invalid.
    pub fn new(api_key: impl Into<String>, config: AgentConfig) -> Result<Self> {
        let generation_config = AnthropicGenerationConfig {
            temperature: Some(config.temperature),
            top_p: Some(config.top_p),
            top_k: Some(config.top_k),
            max_tokens: Some(config.max_output_tokens),
        };

        let client = AnthropicClient::new(api_key, &config.model_name)?
            .with_generation_config(generation_config);

        Ok(Self { config, client })
    }

    /// Generate text with retry logic.
    async fn generate_with_retry(&self, prompt: &str) -> Result<String> {
        let mut last_error = None;
        let max_attempts = 1 + self.config.max_retries.max(0);

        for attempt in 0..max_attempts {
            match self.client.generate_content(prompt).await {
                Ok(text) => {
                    if self.config.retry_on_empty && text.trim().is_empty() {
                        last_error = Some(AtsError::ApiResponse {
                            message: "Empty response from API".to_string(),
                            status_code: None,
                        });
                        continue;
                    }

                    return Ok(text);
                }
                Err(e) => {
                    last_error = Some(e);

                    // Don't retry on auth errors
                    if matches!(last_error, Some(AtsError::ApiAuth { .. })) {
                        break;
                    }

                    // Add small delay before retry
                    if attempt < max_attempts - 1 {
                        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                    }
                }
            }
        }

        Err(last_error.unwrap_or_else(|| AtsError::ApiRequest {
            message: "All retry attempts failed".to_string(),
            source: None,
        }))
    }
}

#[async_trait]
impl Agent for AnthropicAgent {
    fn config(&self) -> &AgentConfig {
        &self.config
    }

    async fn generate_text(&self, prompt: &str) -> Result<String> {
        let text = self.generate_with_retry(prompt).await?;

        // If require_json is set, validate it's valid JSON
        if self.config.require_json {
            let cleaned = strip_markdown_fences(&text);
            serde_json::from_str::<serde_json::Value>(&cleaned).map_err(|e| {
                AtsError::ApiResponse {
                    message: format!("Response is not valid JSON: {e}"),
                    status_code: None,
                }
            })?;

            // Return cleaned JSON
            return Ok(cleaned);
        }

        Ok(text)
    }

    async fn generate_json(&self, prompt: &str) -> Result<serde_json::Value> {
        // Add JSON instruction to prompt if not already present
        let enhanced_prompt = if prompt.to_lowercase().contains("json") {
            prompt.to_string()
        } else {
            format!(
                "{prompt}\n\nIMPORTANT: Output MUST be a raw JSON object only. No markdown fences. No commentary."
            )
        };

        let text = self.generate_with_retry(&enhanced_prompt).await?;
        let cleaned = strip_markdown_fences(&text);

        serde_json::from_str(&cleaned).map_err(|e| AtsError::ApiResponse {
            message: format!("Failed to parse JSON: {e}"),
            status_code: None,
        })
    }
}

// -------------------------
// Llama Agent Implementation
// -------------------------

/// Llama (Ollama) based agent implementation.
pub struct LlamaAgent {
    config: AgentConfig,
    client: LlamaClient,
}

impl LlamaAgent {
    /// Create a new Llama agent with the specified model.
    ///
    /// # Errors
    ///
    /// Returns an error if the model name is empty or the client cannot be created.
    pub fn new(config: AgentConfig) -> Result<Self> {
        let generation_config = LlamaGenerationConfig {
            temperature: Some(config.temperature),
            top_p: Some(config.top_p),
            top_k: Some(config.top_k),
            num_predict: Some(config.max_output_tokens),
        };

        let client =
            LlamaClient::new(&config.model_name)?.with_generation_config(generation_config);

        Ok(Self { config, client })
    }

    /// Create a new Llama agent with a specific host.
    ///
    /// # Errors
    ///
    /// Returns an error if the model name is empty.
    pub fn with_host(config: AgentConfig, host: impl Into<String>) -> Result<Self> {
        let generation_config = LlamaGenerationConfig {
            temperature: Some(config.temperature),
            top_p: Some(config.top_p),
            top_k: Some(config.top_k),
            num_predict: Some(config.max_output_tokens),
        };

        let client = LlamaClient::new(&config.model_name)?
            .with_host(host)
            .with_generation_config(generation_config);

        Ok(Self { config, client })
    }

    /// Generate text with retry logic.
    async fn generate_with_retry(&self, prompt: &str) -> Result<String> {
        let mut last_error = None;
        let max_attempts = 1 + self.config.max_retries.max(0);

        for attempt in 0..max_attempts {
            match self.client.generate_content(prompt).await {
                Ok(text) => {
                    if self.config.retry_on_empty && text.trim().is_empty() {
                        last_error = Some(AtsError::ApiResponse {
                            message: "Empty response from API".to_string(),
                            status_code: None,
                        });
                        continue;
                    }

                    return Ok(text);
                }
                Err(e) => {
                    last_error = Some(e);

                    // Add small delay before retry
                    if attempt < max_attempts - 1 {
                        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                    }
                }
            }
        }

        Err(last_error.unwrap_or_else(|| AtsError::ApiRequest {
            message: "All retry attempts failed".to_string(),
            source: None,
        }))
    }
}

#[async_trait]
impl Agent for LlamaAgent {
    fn config(&self) -> &AgentConfig {
        &self.config
    }

    async fn generate_text(&self, prompt: &str) -> Result<String> {
        let text = self.generate_with_retry(prompt).await?;

        // If require_json is set, validate it's valid JSON
        if self.config.require_json {
            let cleaned = strip_markdown_fences(&text);
            serde_json::from_str::<serde_json::Value>(&cleaned).map_err(|e| {
                AtsError::ApiResponse {
                    message: format!("Response is not valid JSON: {e}"),
                    status_code: None,
                }
            })?;

            // Return cleaned JSON
            return Ok(cleaned);
        }

        Ok(text)
    }

    async fn generate_json(&self, prompt: &str) -> Result<serde_json::Value> {
        // Add JSON instruction to prompt if not already present
        let enhanced_prompt = if prompt.to_lowercase().contains("json") {
            prompt.to_string()
        } else {
            format!(
                "{prompt}\n\nIMPORTANT: Output MUST be a raw JSON object only. No markdown fences. No commentary."
            )
        };

        let text = self.generate_with_retry(&enhanced_prompt).await?;
        let cleaned = strip_markdown_fences(&text);

        serde_json::from_str(&cleaned).map_err(|e| AtsError::ApiResponse {
            message: format!("Failed to parse JSON: {e}"),
            status_code: None,
        })
    }
}

// -------------------------
// Agent Registry
// -------------------------

/// Agent registry for managing multiple agents.
pub struct AgentRegistry {
    agents: HashMap<String, Box<dyn Agent>>,
}

impl AgentRegistry {
    /// Create a new empty agent registry.
    pub fn new() -> Self {
        Self {
            agents: HashMap::new(),
        }
    }

    /// Register an agent.
    pub fn register(&mut self, name: impl Into<String>, agent: Box<dyn Agent>) {
        self.agents.insert(name.into(), agent);
    }

    /// Get an agent by name.
    ///
    /// # Errors
    ///
    /// Returns an error if no agent with the given name is registered.
    pub fn get(&self, name: &str) -> Result<&dyn Agent> {
        self.agents
            .get(name)
            .map(std::convert::AsRef::as_ref)
            .ok_or_else(|| AtsError::AgentConfig {
                message: format!("Agent '{name}' not found"),
            })
    }

    /// List all agent names.
    pub fn list(&self) -> Vec<&str> {
        self.agents
            .keys()
            .map(std::string::String::as_str)
            .collect()
    }

    /// Remove an agent from the registry.
    ///
    /// # Arguments
    ///
    /// * `name` - The name of the agent to remove
    ///
    /// # Returns
    ///
    /// The removed agent if it existed, or `None` if not found.
    pub fn remove(&mut self, name: &str) -> Option<Box<dyn Agent>> {
        self.agents.remove(name)
    }

    /// Create a registry from a config map.
    ///
    /// Expected format from config TOML:
    /// ```toml
    /// [ai.agents.enhancer]
    /// provider = "gemini"
    /// model_name = "gemini-1.5-flash"
    /// role = "resume_enhancement"
    /// require_json = true
    /// ```
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - An unsupported provider is specified
    /// - Agent initialization fails (e.g., missing API keys)
    pub fn from_config(agents_config: &HashMap<String, AgentConfig>) -> Result<Self> {
        let mut registry = Self::new();

        for (name, config) in agents_config {
            let agent: Box<dyn Agent> = match config.provider.as_str() {
                "gemini" => Box::new(GeminiAgent::from_env(config.clone())?),
                "openai" => Box::new(OpenAiAgent::from_env(config.clone())?),
                "anthropic" | "claude" => Box::new(AnthropicAgent::from_env(config.clone())?),
                "llama" | "ollama" => Box::new(LlamaAgent::new(config.clone())?),
                other => {
                    return Err(AtsError::NotSupported {
                        message: format!("Provider '{other}' not supported"),
                    })
                }
            };

            registry.register(name.clone(), agent);
        }

        Ok(registry)
    }

    /// Save agent configurations to a TOML file.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to save the configuration file
    ///
    /// # Errors
    ///
    /// Returns an error if serialization or file writing fails.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use ats_checker::agents::AgentRegistry;
    ///
    /// let registry = AgentRegistry::new();
    /// // ... register agents ...
    /// registry.save_to_file("agents.toml").unwrap();
    /// ```
    pub fn save_to_file(&self, path: impl AsRef<std::path::Path>) -> Result<()> {
        let configs: HashMap<String, AgentConfig> = self
            .agents
            .iter()
            .map(|(name, agent)| (name.clone(), agent.config().clone()))
            .collect();

        crate::toml_io::dump_as(&configs, path)?;
        Ok(())
    }

    /// Load agent configurations from a TOML file.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to the configuration file
    ///
    /// # Errors
    ///
    /// Returns an error if file reading, parsing, or agent creation fails.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use ats_checker::agents::AgentRegistry;
    ///
    /// let registry = AgentRegistry::load_from_file("agents.toml").unwrap();
    /// ```
    pub fn load_from_file(path: impl AsRef<std::path::Path>) -> Result<Self> {
        let configs: HashMap<String, AgentConfig> = crate::toml_io::load_as(path)?;
        Self::from_config(&configs)
    }

    /// Reload the registry from a configuration file.
    ///
    /// Clears all current agents and reloads from the file.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to the configuration file
    ///
    /// # Errors
    ///
    /// Returns an error if file reading, parsing, or agent creation fails.
    pub fn reload_from_file(&mut self, path: impl AsRef<std::path::Path>) -> Result<()> {
        let new_registry = Self::load_from_file(path)?;
        self.agents = new_registry.agents;
        Ok(())
    }
}

impl Default for AgentRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// -------------------------
// Agent Defaults
// -------------------------

/// Default values for agent configuration.
///
/// Used to provide default values for agent configuration fields
/// when creating agents from configuration.
#[derive(Debug, Clone)]
pub struct AgentDefaults {
    /// Default provider (e.g., "gemini").
    pub provider: String,

    /// Default model name (e.g., "gemini-1.5-flash").
    pub model_name: String,

    /// Default temperature (0.0 to 2.0).
    pub temperature: f64,

    /// Default top-p sampling.
    pub top_p: f64,

    /// Default top-k sampling.
    pub top_k: i32,

    /// Default maximum output tokens.
    pub max_output_tokens: i32,

    /// Default maximum retries.
    pub max_retries: i32,

    /// Default retry on empty flag.
    pub retry_on_empty: bool,
}

impl AgentDefaults {
    /// Create default agent defaults.
    pub fn new() -> Self {
        Self {
            provider: "gemini".to_string(),
            model_name: "gemini-1.5-flash".to_string(),
            temperature: 0.7,
            top_p: 0.95,
            top_k: 40,
            max_output_tokens: 8192,
            max_retries: 3,
            retry_on_empty: true,
        }
    }

    /// Apply defaults to a partial agent configuration.
    ///
    /// Fills in missing fields with default values.
    pub fn apply_to(&self, config: &mut AgentConfig) {
        if config.provider.is_empty() {
            config.provider.clone_from(&self.provider);
        }
        if config.model_name.is_empty() {
            config.model_name.clone_from(&self.model_name);
        }
        if config.temperature == 0.0 {
            config.temperature = self.temperature;
        }
        if config.top_p == 0.0 {
            config.top_p = self.top_p;
        }
        if config.top_k == 0 {
            config.top_k = self.top_k;
        }
        if config.max_output_tokens == 0 {
            config.max_output_tokens = self.max_output_tokens;
        }
        if config.max_retries == 0 {
            config.max_retries = self.max_retries;
        }
    }
}

impl Default for AgentDefaults {
    fn default() -> Self {
        Self::new()
    }
}

// -------------------------
// Thread-Safe Registry
// -------------------------

use std::sync::{Arc, RwLock};

/// Thread-safe agent registry.
///
/// Wraps `AgentRegistry` with `Arc<RwLock<>>` for safe concurrent access.
#[derive(Clone)]
pub struct SyncAgentRegistry {
    inner: Arc<RwLock<AgentRegistry>>,
}

impl SyncAgentRegistry {
    /// Create a new empty thread-safe registry.
    pub fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(AgentRegistry::new())),
        }
    }

    /// Register an agent (thread-safe).
    pub fn register(&self, name: impl Into<String>, agent: Box<dyn Agent>) {
        let mut registry = self.inner.write().unwrap();
        registry.register(name, agent);
    }

    /// Check if an agent exists (thread-safe).
    pub fn contains(&self, name: &str) -> bool {
        let registry = self.inner.read().unwrap();
        registry.get(name).is_ok()
    }

    /// List all agent names (thread-safe).
    pub fn list(&self) -> Vec<String> {
        let registry = self.inner.read().unwrap();
        registry.list().iter().map(|&s| s.to_string()).collect()
    }

    /// Remove an agent (thread-safe).
    pub fn remove(&self, name: &str) -> Option<Box<dyn Agent>> {
        let mut registry = self.inner.write().unwrap();
        registry.remove(name)
    }
}

impl Default for SyncAgentRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// -------------------------
// Utilities
// -------------------------

/// Strip markdown code fences from text.
fn strip_markdown_fences(text: &str) -> String {
    let trimmed = text.trim();

    if trimmed.starts_with("```") && trimmed.ends_with("```") {
        if let Some(first_newline) = trimmed.find('\n') {
            let header = &trimmed[..first_newline];
            if header.starts_with("```") {
                let body_start = first_newline + 1;
                let body_end = trimmed.len() - 3;
                if body_start < body_end {
                    return trimmed[body_start..body_end].trim().to_string();
                }
            }
        }
        return trimmed[3..trimmed.len() - 3].trim().to_string();
    }

    trimmed.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_config_builder() {
        let config = AgentConfig::builder()
            .name("test")
            .role("test_role")
            .temperature(0.5)
            .require_json(true)
            .build();

        assert_eq!(config.name, "test");
        assert_eq!(config.role, "test_role");
        assert_eq!(config.temperature, 0.5);
        assert!(config.require_json);
    }

    #[test]
    fn test_agent_config_default() {
        let config = AgentConfig::default();
        assert_eq!(config.provider, "gemini");
        assert_eq!(config.temperature, 0.7);
        assert!(!config.require_json);
    }

    #[test]
    fn test_agent_registry_operations() {
        let registry = AgentRegistry::new();
        assert!(registry.list().is_empty());

        // We can't easily test agent registration without mocking
        // But we can test the basic operations
        assert!(registry.get("nonexistent").is_err());
    }

    #[test]
    fn test_strip_markdown_fences() {
        let input = "```json\n{\"key\": \"value\"}\n```";
        assert_eq!(strip_markdown_fences(input), "{\"key\": \"value\"}");

        let input2 = "plain text";
        assert_eq!(strip_markdown_fences(input2), "plain text");
    }
}
