//! Llama (Ollama) API integration module.
//!
//! This module provides a client for the Ollama API for running Llama models locally.
//!
//! # Environment Variables
//!
//! - `OLLAMA_HOST`: Optional host URL (defaults to <http://localhost:11434>)
//!
//! # Example
//!
//! ```no_run
//! use ats_checker::llama::LlamaClient;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = LlamaClient::new("llama3.2")?;
//!     let response = client.generate_content("Write a haiku").await?;
//!     println!("{}", response);
//!     Ok(())
//! }
//! ```

use crate::error::{AtsError, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Default Ollama host.
const DEFAULT_OLLAMA_HOST: &str = "http://localhost:11434";

/// Default timeout for API requests (60 seconds - longer for local models).
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(60);

/// Generation configuration for Llama/Ollama API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationConfig {
    /// Temperature for sampling (0.0 to 2.0).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f64>,

    /// Top-p sampling parameter.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub top_p: Option<f64>,

    /// Top-k sampling parameter.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub top_k: Option<i32>,

    /// Maximum output tokens.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub num_predict: Option<i32>,
}

impl Default for GenerationConfig {
    fn default() -> Self {
        Self {
            temperature: Some(0.7),
            top_p: Some(0.95),
            top_k: Some(40),
            num_predict: Some(4096),
        }
    }
}

/// Request payload for Ollama generate API.
#[derive(Debug, Serialize)]
struct GenerateRequest {
    model: String,
    prompt: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    options: Option<GenerateOptions>,
    stream: bool,
}

/// Generation options for Ollama.
#[derive(Debug, Serialize)]
struct GenerateOptions {
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_p: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_k: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    num_predict: Option<i32>,
}

/// Response from Ollama API.
#[derive(Debug, Deserialize)]
struct GenerateResponse {
    response: String,
    #[allow(dead_code)]
    done: bool,
}

/// Llama/Ollama API client.
#[derive(Debug)]
pub struct LlamaClient {
    host: String,
    model_name: String,
    generation_config: GenerationConfig,
    client: Client,
}

impl LlamaClient {
    /// Create a new Llama client.
    ///
    /// # Arguments
    ///
    /// * `model_name` - Model to use (e.g., "llama3.2", "llama3.1", "llama2")
    ///
    /// # Errors
    ///
    /// Returns an error if the model name is empty.
    pub fn new(model_name: impl Into<String>) -> Result<Self> {
        let model_name = model_name.into();

        if model_name.trim().is_empty() {
            return Err(AtsError::AgentConfig {
                message: "Model name cannot be empty".to_string(),
            });
        }

        let host = std::env::var("OLLAMA_HOST").unwrap_or_else(|_| DEFAULT_OLLAMA_HOST.to_string());

        let client = Client::builder()
            .timeout(DEFAULT_TIMEOUT)
            .build()
            .map_err(|e| AtsError::ApiRequest {
                message: format!("Failed to build HTTP client: {e}"),
                source: Some(e),
            })?;

        Ok(Self {
            host,
            model_name,
            generation_config: GenerationConfig::default(),
            client,
        })
    }

    /// Create a client with a specific host.
    #[must_use]
    pub fn with_host(mut self, host: impl Into<String>) -> Self {
        self.host = host.into();
        self
    }

    /// Set the generation configuration.
    #[must_use]
    pub fn with_generation_config(mut self, config: GenerationConfig) -> Self {
        self.generation_config = config;
        self
    }

    /// Set the temperature.
    #[must_use]
    pub fn with_temperature(mut self, temperature: f64) -> Self {
        self.generation_config.temperature = Some(temperature);
        self
    }

    /// Set the `top_p` parameter.
    #[must_use]
    pub fn with_top_p(mut self, top_p: f64) -> Self {
        self.generation_config.top_p = Some(top_p);
        self
    }

    /// Set the `top_k` parameter.
    #[must_use]
    pub fn with_top_k(mut self, top_k: i32) -> Self {
        self.generation_config.top_k = Some(top_k);
        self
    }

    /// Set the maximum output tokens.
    #[must_use]
    pub fn with_num_predict(mut self, num_predict: i32) -> Self {
        self.generation_config.num_predict = Some(num_predict);
        self
    }

    /// Generate content from a text prompt.
    ///
    /// This is the main method for interacting with the Ollama API.
    ///
    /// # Errors
    ///
    /// Returns an error if the API request fails or the response cannot be parsed.
    pub async fn generate_content(&self, prompt: &str) -> Result<String> {
        if prompt.trim().is_empty() {
            return Err(AtsError::ApiRequest {
                message: "Prompt cannot be empty".to_string(),
                source: None,
            });
        }

        let options = if self.generation_config.temperature.is_some()
            || self.generation_config.top_p.is_some()
            || self.generation_config.top_k.is_some()
            || self.generation_config.num_predict.is_some()
        {
            Some(GenerateOptions {
                temperature: self.generation_config.temperature,
                top_p: self.generation_config.top_p,
                top_k: self.generation_config.top_k,
                num_predict: self.generation_config.num_predict,
            })
        } else {
            None
        };

        let request = GenerateRequest {
            model: self.model_name.clone(),
            prompt: prompt.to_string(),
            options,
            stream: false,
        };

        let url = format!("{}/api/generate", self.host);

        let response = self
            .client
            .post(&url)
            .json(&request)
            .send()
            .await
            .map_err(|e| AtsError::ApiRequest {
                message: format!("Failed to send request to Ollama API: {e}"),
                source: Some(e),
            })?;

        let status = response.status();

        if !status.is_success() {
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());

            return Err(AtsError::ApiResponse {
                message: format!("API error ({status}): {error_text}"),
                status_code: Some(status.as_u16()),
            });
        }

        let response_data: GenerateResponse =
            response.json().await.map_err(|e| AtsError::ApiResponse {
                message: format!("Failed to parse API response: {e}"),
                status_code: None,
            })?;

        let text = response_data.response;

        if text.trim().is_empty() {
            return Err(AtsError::ApiResponse {
                message: "API returned empty response".to_string(),
                status_code: None,
            });
        }

        Ok(text)
    }

    /// Generate JSON content from a prompt.
    ///
    /// This method automatically strips markdown code fences and parses JSON.
    ///
    /// # Errors
    ///
    /// Returns an error if the API request fails or the response is not valid JSON.
    pub async fn generate_json(&self, prompt: &str) -> Result<serde_json::Value> {
        let text = self.generate_content(prompt).await?;
        let cleaned = strip_markdown_fences(&text);

        serde_json::from_str(&cleaned).map_err(|e| AtsError::ApiResponse {
            message: format!("Failed to parse JSON from response: {e}"),
            status_code: None,
        })
    }
}

/// Strip markdown code fences from text.
///
/// Handles patterns like:
/// - ` ```json\n{...}\n``` `
/// - ` ```\n{...}\n``` `
fn strip_markdown_fences(text: &str) -> String {
    let trimmed = text.trim();

    if trimmed.starts_with("```") && trimmed.ends_with("```") {
        // Find the first newline after ```
        if let Some(first_newline) = trimmed.find('\n') {
            let header = &trimmed[..first_newline];

            // Check if it's ```json or just ```
            if header.starts_with("```") {
                // Extract body between first newline and final ```
                let body_start = first_newline + 1;
                let body_end = trimmed.len() - 3;

                if body_start < body_end {
                    return trimmed[body_start..body_end].trim().to_string();
                }
            }
        }

        // Fallback: just strip ``` from both ends
        return trimmed[3..trimmed.len() - 3].trim().to_string();
    }

    trimmed.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strip_markdown_fences() {
        let input = "```json\n{\"key\": \"value\"}\n```";
        let expected = "{\"key\": \"value\"}";
        assert_eq!(strip_markdown_fences(input), expected);

        let input2 = "```\n{\"key\": \"value\"}\n```";
        assert_eq!(strip_markdown_fences(input2), expected);

        let input3 = "{\"key\": \"value\"}";
        assert_eq!(strip_markdown_fences(input3), expected);
    }

    #[test]
    fn test_generation_config_default() {
        let config = GenerationConfig::default();
        assert_eq!(config.temperature, Some(0.7));
        assert_eq!(config.top_p, Some(0.95));
        assert_eq!(config.top_k, Some(40));
        assert_eq!(config.num_predict, Some(4096));
    }

    #[test]
    fn test_llama_client_new_validation() {
        let result = LlamaClient::new("");
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AtsError::AgentConfig { .. }));
    }
}
