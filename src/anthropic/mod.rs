//! Anthropic Claude API integration module.
//!
//! This module provides a client for the Anthropic Claude API.
//!
//! # Environment Variables
//!
//! - `ANTHROPIC_API_KEY`: Required API key for authentication
//!
//! # Example
//!
//! ```no_run
//! use ats_checker::anthropic::AnthropicClient;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = AnthropicClient::from_env()?;
//!     let response = client.generate_content("Write a haiku").await?;
//!     println!("{}", response);
//!     Ok(())
//! }
//! ```

use crate::error::{AtsError, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Anthropic API base URL.
const ANTHROPIC_API_BASE: &str = "https://api.anthropic.com/v1";

/// Default timeout for API requests (30 seconds).
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);

/// API version header.
const ANTHROPIC_VERSION: &str = "2023-06-01";

/// Generation configuration for Anthropic API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationConfig {
    /// Temperature for sampling (0.0 to 1.0).
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
    pub max_tokens: Option<i32>,
}

impl Default for GenerationConfig {
    fn default() -> Self {
        Self {
            temperature: Some(0.7),
            top_p: Some(1.0),
            top_k: Some(40),
            max_tokens: Some(4096),
        }
    }
}

/// Request payload for Anthropic messages API.
#[derive(Debug, Serialize)]
struct MessagesRequest {
    model: String,
    messages: Vec<Message>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_p: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_k: Option<i32>,
}

/// Message in the conversation.
#[derive(Debug, Serialize)]
struct Message {
    role: String,
    content: String,
}

/// Response from Anthropic API.
#[derive(Debug, Deserialize)]
struct MessagesResponse {
    content: Vec<ContentBlock>,
}

/// Content block in the response.
#[derive(Debug, Deserialize)]
struct ContentBlock {
    #[serde(rename = "type")]
    content_type: String,
    text: Option<String>,
}

/// Anthropic API client.
#[derive(Debug)]
pub struct AnthropicClient {
    api_key: String,
    model_name: String,
    generation_config: GenerationConfig,
    client: Client,
}

impl AnthropicClient {
    /// Create a new Anthropic client.
    ///
    /// # Arguments
    ///
    /// * `api_key` - Anthropic API key
    /// * `model_name` - Model to use (e.g., "claude-3-opus-20240229", "claude-3-sonnet-20240229")
    ///
    /// # Errors
    ///
    /// Returns an error if the API key is empty or invalid.
    pub fn new(api_key: impl Into<String>, model_name: impl Into<String>) -> Result<Self> {
        let api_key = api_key.into();

        if api_key.trim().is_empty() {
            return Err(AtsError::ApiAuth {
                message: "Anthropic API key cannot be empty".to_string(),
            });
        }

        let client = Client::builder()
            .timeout(DEFAULT_TIMEOUT)
            .build()
            .map_err(|e| AtsError::ApiRequest {
                message: format!("Failed to build HTTP client: {e}"),
                source: Some(e),
            })?;

        Ok(Self {
            api_key,
            model_name: model_name.into(),
            generation_config: GenerationConfig::default(),
            client,
        })
    }

    /// Create a client from the `ANTHROPIC_API_KEY` environment variable.
    ///
    /// # Errors
    ///
    /// Returns an error if the `ANTHROPIC_API_KEY` environment variable is not set.
    pub fn from_env() -> Result<Self> {
        let api_key = std::env::var("ANTHROPIC_API_KEY").map_err(|_| AtsError::ApiAuth {
            message: "ANTHROPIC_API_KEY environment variable not set".to_string(),
        })?;

        Self::new(api_key, "claude-3-sonnet-20240229")
    }

    /// Create a client with a specific model from environment.
    ///
    /// # Errors
    ///
    /// Returns an error if the `ANTHROPIC_API_KEY` environment variable is not set.
    pub fn from_env_with_model(model_name: impl Into<String>) -> Result<Self> {
        let api_key = std::env::var("ANTHROPIC_API_KEY").map_err(|_| AtsError::ApiAuth {
            message: "ANTHROPIC_API_KEY environment variable not set".to_string(),
        })?;

        Self::new(api_key, model_name)
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
    pub fn with_max_tokens(mut self, max_tokens: i32) -> Self {
        self.generation_config.max_tokens = Some(max_tokens);
        self
    }

    /// Generate content from a text prompt.
    ///
    /// This is the main method for interacting with the Anthropic API.
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

        let request = MessagesRequest {
            model: self.model_name.clone(),
            messages: vec![Message {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
            max_tokens: self.generation_config.max_tokens,
            temperature: self.generation_config.temperature,
            top_p: self.generation_config.top_p,
            top_k: self.generation_config.top_k,
        };

        let url = format!("{}/messages", ANTHROPIC_API_BASE);

        let response = self
            .client
            .post(&url)
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", ANTHROPIC_VERSION)
            .header("content-type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(|e| AtsError::ApiRequest {
                message: format!("Failed to send request to Anthropic API: {e}"),
                source: Some(e),
            })?;

        let status = response.status();

        if !status.is_success() {
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());

            return Err(match status.as_u16() {
                401 | 403 => AtsError::ApiAuth {
                    message: format!("Authentication failed: {error_text}"),
                },
                429 => AtsError::ApiRateLimit {
                    message: format!("Rate limit exceeded: {error_text}"),
                    retry_after: None,
                },
                _ => AtsError::ApiResponse {
                    message: format!("API error ({status}): {error_text}"),
                    status_code: Some(status.as_u16()),
                },
            });
        }

        let response_data: MessagesResponse =
            response.json().await.map_err(|e| AtsError::ApiResponse {
                message: format!("Failed to parse API response: {e}"),
                status_code: None,
            })?;

        // Extract text from the first content block
        let text = response_data
            .content
            .first()
            .and_then(|c| c.text.clone())
            .ok_or_else(|| AtsError::ApiResponse {
                message: "No text in API response".to_string(),
                status_code: None,
            })?;

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
        assert_eq!(config.top_p, Some(1.0));
        assert_eq!(config.top_k, Some(40));
        assert_eq!(config.max_tokens, Some(4096));
    }

    #[test]
    fn test_anthropic_client_new_validation() {
        let result = AnthropicClient::new("", "claude-3-sonnet-20240229");
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AtsError::ApiAuth { .. }));
    }
}
