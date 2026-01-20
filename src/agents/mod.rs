//! LLM agent abstraction layer.

use crate::error::Result;
use async_trait::async_trait;

/// Agent trait for LLM providers.
#[async_trait]
pub trait Agent: Send + Sync {
    /// Generate text from a prompt.
    async fn generate_text(&self, prompt: &str) -> Result<String>;

    /// Generate JSON from a prompt.
    async fn generate_json(&self, prompt: &str) -> Result<serde_json::Value>;
}

/// Agent registry for managing multiple agents.
pub struct AgentRegistry {
    // TODO: Implement agent registry
}

impl AgentRegistry {
    /// Create a new agent registry.
    pub fn new() -> Self {
        Self {}
    }
}

impl Default for AgentRegistry {
    fn default() -> Self {
        Self::new()
    }
}
