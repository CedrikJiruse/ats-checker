//! Scoring module for resume, job, and match scoring.

use serde::{Deserialize, Serialize};
use crate::error::Result;

/// A score report with category breakdowns.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreReport {
    /// Total score (0-100).
    pub total: f64,
    /// Category scores.
    pub categories: Vec<CategoryScore>,
}

impl ScoreReport {
    /// Convert to a dictionary.
    pub fn as_dict(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// A category score.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CategoryScore {
    /// Category name.
    pub name: String,
    /// Score (0-100).
    pub score: f64,
    /// Weight.
    pub weight: f64,
}

/// Score a resume.
pub fn score_resume(_resume: &serde_json::Value, _weights_path: &str) -> Result<ScoreReport> {
    // TODO: Implement resume scoring
    Ok(ScoreReport {
        total: 0.0,
        categories: vec![],
    })
}

/// Score a job posting.
pub fn score_job(_job: &serde_json::Value, _weights_path: &str) -> Result<ScoreReport> {
    // TODO: Implement job scoring
    Ok(ScoreReport {
        total: 0.0,
        categories: vec![],
    })
}

/// Score the match between a resume and a job.
pub fn score_match(
    _resume: &serde_json::Value,
    _job: &serde_json::Value,
    _weights_path: &str,
) -> Result<ScoreReport> {
    // TODO: Implement match scoring
    Ok(ScoreReport {
        total: 0.0,
        categories: vec![],
    })
}
