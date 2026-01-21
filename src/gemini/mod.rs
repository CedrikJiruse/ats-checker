//! Gemini API integration module.
//!
//! This module provides a client for the Google Gemini API.
//!
//! # Environment Variables
//!
//! - `GEMINI_API_KEY`: Required API key for authentication
//!
//! # Example
//!
//! ```no_run
//! use ats_checker::gemini::GeminiClient;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = GeminiClient::from_env()?;
//!     let response = client.generate_content("Write a haiku").await?;
//!     println!("{}", response);
//!     Ok(())
//! }
//! ```

use crate::error::{AtsError, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Gemini API base URL.
const GEMINI_API_BASE: &str = "https://generativelanguage.googleapis.com/v1beta/models";

/// Default timeout for API requests (30 seconds).
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);

/// Generation configuration for Gemini API.
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
    pub max_output_tokens: Option<i32>,
}

impl Default for GenerationConfig {
    fn default() -> Self {
        Self {
            temperature: Some(0.7),
            top_p: Some(0.95),
            top_k: Some(40),
            max_output_tokens: Some(8192),
        }
    }
}

/// Request payload for Gemini generateContent API.
#[derive(Debug, Serialize)]
struct GenerateContentRequest {
    contents: Vec<Content>,
    #[serde(skip_serializing_if = "Option::is_none")]
    generation_config: Option<GenerationConfig>,
}

/// Content part in a request.
#[derive(Debug, Serialize)]
struct Content {
    parts: Vec<Part>,
}

/// Text part.
#[derive(Debug, Serialize)]
struct Part {
    text: String,
}

/// Response from Gemini API.
#[derive(Debug, Deserialize)]
struct GenerateContentResponse {
    candidates: Vec<Candidate>,
}

/// A response candidate.
#[derive(Debug, Deserialize)]
struct Candidate {
    content: ContentResponse,
    #[serde(default)]
    finish_reason: Option<String>,
}

/// Content in a response.
#[derive(Debug, Deserialize)]
struct ContentResponse {
    parts: Vec<PartResponse>,
}

/// Part in a response.
#[derive(Debug, Deserialize)]
struct PartResponse {
    text: String,
}

/// Gemini API client.
pub struct GeminiClient {
    api_key: String,
    model_name: String,
    generation_config: GenerationConfig,
    client: Client,
}

impl GeminiClient {
    /// Create a new Gemini client.
    ///
    /// # Arguments
    ///
    /// * `api_key` - Gemini API key
    /// * `model_name` - Model to use (e.g., "gemini-1.5-flash", "gemini-1.5-pro")
    pub fn new(api_key: impl Into<String>, model_name: impl Into<String>) -> Result<Self> {
        let api_key = api_key.into();

        if api_key.trim().is_empty() {
            return Err(AtsError::ApiAuth {
                message: "Gemini API key cannot be empty".to_string(),
            });
        }

        let client = Client::builder()
            .timeout(DEFAULT_TIMEOUT)
            .build()
            .map_err(|e| AtsError::ApiRequest {
                message: format!("Failed to build HTTP client: {}", e),
                source: Some(e),
            })?;

        Ok(Self {
            api_key,
            model_name: model_name.into(),
            generation_config: GenerationConfig::default(),
            client,
        })
    }

    /// Create a client from the `GEMINI_API_KEY` environment variable.
    pub fn from_env() -> Result<Self> {
        let api_key = std::env::var("GEMINI_API_KEY").map_err(|_| AtsError::ApiAuth {
            message: "GEMINI_API_KEY environment variable not set".to_string(),
        })?;

        Self::new(api_key, "gemini-1.5-flash")
    }

    /// Create a client with a specific model from environment.
    pub fn from_env_with_model(model_name: impl Into<String>) -> Result<Self> {
        let api_key = std::env::var("GEMINI_API_KEY").map_err(|_| AtsError::ApiAuth {
            message: "GEMINI_API_KEY environment variable not set".to_string(),
        })?;

        Self::new(api_key, model_name)
    }

    /// Set the generation configuration.
    pub fn with_generation_config(mut self, config: GenerationConfig) -> Self {
        self.generation_config = config;
        self
    }

    /// Set the temperature.
    pub fn with_temperature(mut self, temperature: f64) -> Self {
        self.generation_config.temperature = Some(temperature);
        self
    }

    /// Set the top_p parameter.
    pub fn with_top_p(mut self, top_p: f64) -> Self {
        self.generation_config.top_p = Some(top_p);
        self
    }

    /// Set the top_k parameter.
    pub fn with_top_k(mut self, top_k: i32) -> Self {
        self.generation_config.top_k = Some(top_k);
        self
    }

    /// Set the maximum output tokens.
    pub fn with_max_output_tokens(mut self, max_tokens: i32) -> Self {
        self.generation_config.max_output_tokens = Some(max_tokens);
        self
    }

    /// Generate content from a text prompt.
    ///
    /// This is the main method for interacting with the Gemini API.
    pub async fn generate_content(&self, prompt: &str) -> Result<String> {
        if prompt.trim().is_empty() {
            return Err(AtsError::ApiRequest {
                message: "Prompt cannot be empty".to_string(),
                source: None,
            });
        }

        let request = GenerateContentRequest {
            contents: vec![Content {
                parts: vec![Part {
                    text: prompt.to_string(),
                }],
            }],
            generation_config: Some(self.generation_config.clone()),
        };

        let url = format!(
            "{}/{}:generateContent?key={}",
            GEMINI_API_BASE, self.model_name, self.api_key
        );

        let response = self
            .client
            .post(&url)
            .json(&request)
            .send()
            .await
            .map_err(|e| AtsError::ApiRequest {
                message: format!("Failed to send request to Gemini API: {}", e),
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
                    message: format!("Authentication failed: {}", error_text),
                },
                429 => AtsError::ApiRateLimit {
                    message: format!("Rate limit exceeded: {}", error_text),
                    retry_after: None,
                },
                _ => AtsError::ApiResponse {
                    message: format!("API error ({}): {}", status, error_text),
                    status_code: Some(status.as_u16()),
                },
            });
        }

        let response_data: GenerateContentResponse =
            response.json().await.map_err(|e| AtsError::ApiResponse {
                message: format!("Failed to parse API response: {}", e),
                status_code: None,
            })?;

        // Extract text from the first candidate
        let text = response_data
            .candidates
            .first()
            .and_then(|c| c.content.parts.first())
            .map(|p| p.text.clone())
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
    pub async fn generate_json(&self, prompt: &str) -> Result<serde_json::Value> {
        let text = self.generate_content(prompt).await?;
        let cleaned = strip_markdown_fences(&text);

        serde_json::from_str(&cleaned).map_err(|e| AtsError::ApiResponse {
            message: format!("Failed to parse JSON from response: {}", e),
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
        assert_eq!(config.max_output_tokens, Some(8192));
    }

    #[test]
    fn test_gemini_client_new_validation() {
        let result = GeminiClient::new("", "gemini-1.5-flash");
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AtsError::ApiAuth { .. }));
    }
}
