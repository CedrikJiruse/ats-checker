//! Input handling module.

use std::path::PathBuf;
use crate::error::Result;

/// Input handler for resumes and job descriptions.
pub struct InputHandler {
    // TODO: Implement input handler
}

impl InputHandler {
    /// Create a new input handler.
    pub fn new() -> Self {
        Self {}
    }

    /// List available resumes.
    pub fn list_resumes(&self) -> Result<Vec<PathBuf>> {
        Ok(vec![])
    }

    /// List available job descriptions.
    pub fn list_job_descriptions(&self) -> Result<Vec<PathBuf>> {
        Ok(vec![])
    }
}

impl Default for InputHandler {
    fn default() -> Self {
        Self::new()
    }
}
