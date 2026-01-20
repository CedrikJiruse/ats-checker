//! Resume processor module - main processing pipeline.

use crate::config::Config;
use crate::error::Result;

/// Main resume processor.
pub struct ResumeProcessor {
    // TODO: Implement resume processor
}

impl ResumeProcessor {
    /// Create a new resume processor.
    pub fn new(_config: Config) -> Result<Self> {
        Ok(Self {})
    }

    /// Process a resume.
    pub async fn process_resume(
        &mut self,
        _resume_path: &str,
        _job_path: Option<&str>,
    ) -> Result<ProcessingResult> {
        Ok(ProcessingResult {
            success: true,
            scores: None,
        })
    }
}

/// Result of resume processing.
pub struct ProcessingResult {
    /// Whether processing succeeded.
    pub success: bool,
    /// Scores if available.
    pub scores: Option<crate::scoring::ScoreReport>,
}
