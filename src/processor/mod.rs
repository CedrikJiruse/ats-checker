//! Resume processor module - main processing pipeline.
//!
//! This module orchestrates the complete resume processing workflow:
//! 1. Load and hash input files
//! 2. Check state to skip already-processed resumes
//! 3. Enhance resume using AI agents
//! 4. Score enhanced resume (and optionally match against job)
//! 5. Generate recommendations (optional)
//! 6. Iterate to improve scores (optional)
//! 7. Write outputs (TOML/JSON/TXT)
//! 8. Update state
//!
//! # Example
//!
//! ```rust,no_run
//! use ats_checker::{Config, ResumeProcessor};
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let config = Config::load("config/config.toml")?;
//!     let mut processor = ResumeProcessor::new(config)?;
//!
//!     let result = processor.process_resume("resume.txt", Some("job.txt")).await?;
//!     println!("Success: {}", result.success);
//!
//!     Ok(())
//! }
//! ```

use crate::agents::{Agent, AgentRegistry};
use crate::config::Config;
use crate::error::{AtsError, Result};
use crate::input::InputHandler;
use crate::output::{OutputData, OutputGenerator};
use crate::recommendations::{generate_recommendations, Recommendation};
use crate::scoring::{score_match, score_resume, ScoreReport};
use crate::state::StateManager;
use crate::utils::hash::calculate_file_hash;
use crate::validation::{validate_resume_json, ValidationResult};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

// -------------------------
// Data Structures
// -------------------------

/// Result of resume processing.
#[derive(Debug, Clone)]
pub struct ProcessingResult {
    /// Whether processing succeeded.
    pub success: bool,
    /// Path to output directory (if successful).
    pub output_dir: Option<PathBuf>,
    /// Scores if available.
    pub scores: Option<ScoreReport>,
    /// Enhanced resume data.
    pub enhanced_resume: Option<serde_json::Value>,
    /// Recommendations.
    pub recommendations: Vec<Recommendation>,
    /// Error message if failed.
    pub error: Option<String>,
}

/// Iteration strategy for improving scores.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IterationStrategy {
    /// Keep best candidate, stop on target/no_progress/max_iterations.
    BestOf,
    /// Stop immediately when target score reached.
    FirstHit,
    /// Stop if no improvement for N consecutive iterations.
    Patience,
}

impl IterationStrategy {
    /// Parse from string.
    pub fn from_str(s: &str) -> Result<Self> {
        match s.to_lowercase().as_str() {
            "best_of" => Ok(Self::BestOf),
            "first_hit" => Ok(Self::FirstHit),
            "patience" => Ok(Self::Patience),
            _ => Err(AtsError::ConfigError(format!(
                "Invalid iteration strategy: {}",
                s
            ))),
        }
    }
}

// -------------------------
// ResumeProcessor
// -------------------------

/// Main resume processor.
pub struct ResumeProcessor {
    config: Config,
    state_manager: StateManager,
    input_handler: InputHandler,
    output_generator: OutputGenerator,
    agent_registry: AgentRegistry,
}

impl ResumeProcessor {
    /// Create a new resume processor.
    pub fn new(config: Config) -> Result<Self> {
        // Initialize state manager
        let state_manager = StateManager::new(config.state_file.clone())?;

        // Initialize input handler
        let input_handler = InputHandler::new(
            config.input_resumes_folder.clone(),
            config.job_descriptions_folder.clone(),
            config.tesseract_cmd.clone(),
        );

        // Initialize output generator
        let output_generator = OutputGenerator::new(
            config.output_folder.clone(),
            config.structured_output_format.clone(),
            config.output_subdir_pattern.clone(),
        );

        // Initialize agent registry from config
        let agent_registry = AgentRegistry::from_config(&config)?;

        Ok(Self {
            config,
            state_manager,
            input_handler,
            output_generator,
            agent_registry,
        })
    }

    /// Process a single resume.
    ///
    /// # Arguments
    ///
    /// * `resume_path` - Path to the resume file
    /// * `job_path` - Optional path to job description file
    pub async fn process_resume(
        &mut self,
        resume_path: &str,
        job_path: Option<&str>,
    ) -> Result<ProcessingResult> {
        let resume_file = Path::new(resume_path);

        // Step 1: Calculate hash and check if already processed
        let resume_hash = calculate_file_hash(resume_file)?;
        if self.state_manager.is_processed(&resume_hash) {
            log::info!("Resume already processed (hash: {}), skipping", resume_hash);
            return Ok(ProcessingResult {
                success: true,
                output_dir: None,
                scores: None,
                enhanced_resume: None,
                recommendations: vec![],
                error: None,
            });
        }

        // Step 2: Load resume text
        log::info!("Loading resume from: {}", resume_path);
        let resume_text = self.input_handler.load_file(resume_file)?;

        // Step 3: Load job description (optional)
        let job_text = if let Some(jp) = job_path {
            log::info!("Loading job description from: {}", jp);
            Some(self.input_handler.load_file(Path::new(jp))?)
        } else {
            None
        };

        // Step 4: Enhance resume using AI
        log::info!("Enhancing resume with AI...");
        let enhanced_resume = self.enhance_resume(&resume_text, job_text.as_deref()).await?;

        // Step 5: Validate schema (if enabled)
        if self.config.schema_validation_enabled {
            log::info!("Validating enhanced resume against schema...");
            let validation = validate_resume_json(&enhanced_resume, &self.config.resume_schema_path)?;
            if !validation.valid {
                log::warn!("Schema validation failed: {:?}", validation.errors);
                // Optionally retry or fail here
            }
        }

        // Step 6: Score the enhanced resume
        log::info!("Scoring enhanced resume...");
        let resume_score = score_resume(&enhanced_resume, Some(&self.config.scoring_weights_file))?;

        // Step 7: Score match if job description provided
        let match_score = if let Some(job_txt) = &job_text {
            log::info!("Scoring resume-job match...");
            Some(score_match(
                &enhanced_resume,
                job_txt,
                Some(&self.config.scoring_weights_file),
            )?)
        } else {
            None
        };

        // Step 8: Combine scores for overall evaluation
        let combined_score = if let Some(ms) = &match_score {
            // Weighted average: 50% resume quality + 50% match quality
            (resume_score.total + ms.total) / 2.0
        } else {
            resume_score.total
        };

        // Step 9: Iterate to improve scores (if enabled)
        let (final_resume, final_resume_score, final_match_score) =
            if self.config.iterate_until_score_reached && combined_score < self.config.target_score
            {
                log::info!(
                    "Iterating to improve scores (current: {:.2}, target: {:.2})...",
                    combined_score,
                    self.config.target_score
                );
                self.iterate_improvement(
                    &resume_text,
                    job_text.as_deref(),
                    enhanced_resume,
                    resume_score,
                    match_score,
                )
                .await?
            } else {
                (enhanced_resume, resume_score, match_score)
            };

        // Step 10: Generate recommendations (if enabled)
        let recommendations = if self.config.recommendations_enabled {
            log::info!("Generating recommendations...");
            generate_recommendations(
                &final_resume,
                &final_resume_score,
                self.config.recommendations_max_items as usize,
            )
        } else {
            vec![]
        };

        // Step 11: Prepare output data
        let resume_name = resume_file
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("resume")
            .to_string();

        let job_title = job_path.and_then(|jp| {
            Path::new(jp)
                .file_stem()
                .and_then(|s| s.to_str())
                .map(|s| s.to_string())
        });

        let output_data = OutputData {
            resume_name: resume_name.clone(),
            job_title: job_title.clone(),
            enhanced_resume: final_resume.clone(),
            scores: Some(final_resume_score.clone()),
            recommendations: recommendations.clone(),
            metadata: HashMap::new(),
        };

        // Step 12: Generate outputs
        log::info!("Writing outputs...");
        let output_dir = self.output_generator.generate(&output_data)?;

        // Step 13: Update state
        self.state_manager
            .update_resume_state(&resume_hash, &output_dir.display().to_string())?;

        log::info!("Resume processing completed successfully!");
        Ok(ProcessingResult {
            success: true,
            output_dir: Some(output_dir),
            scores: Some(final_resume_score),
            enhanced_resume: Some(final_resume),
            recommendations,
            error: None,
        })
    }

    /// Enhance resume using AI agent.
    async fn enhance_resume(
        &self,
        resume_text: &str,
        job_text: Option<&str>,
    ) -> Result<serde_json::Value> {
        // Get the enhancer agent
        let agent = self.agent_registry.get("enhancer").map_err(|_| {
            AtsError::AgentError("Enhancer agent not found in registry".to_string())
        })?;

        // Build prompt
        let prompt = if let Some(job) = job_text {
            format!(
                "Enhance the following resume for the given job description. \
                 Return a structured JSON object with fields: name, email, phone, \
                 location, summary, experience (array), skills (array), education (array), \
                 certifications (array).\n\n\
                 RESUME:\n{}\n\n\
                 JOB DESCRIPTION:\n{}",
                resume_text, job
            )
        } else {
            format!(
                "Enhance the following resume. Return a structured JSON object with \
                 fields: name, email, phone, location, summary, experience (array), \
                 skills (array), education (array), certifications (array).\n\n\
                 RESUME:\n{}",
                resume_text
            )
        };

        // Call agent
        let response = agent.generate(&prompt).await?;

        // Parse JSON response
        serde_json::from_str(&response).map_err(|e| {
            AtsError::ValidationError(format!("Failed to parse enhanced resume JSON: {}", e))
        })
    }

    /// Iterate to improve scores.
    #[allow(clippy::type_complexity)]
    async fn iterate_improvement(
        &self,
        resume_text: &str,
        job_text: Option<&str>,
        initial_resume: serde_json::Value,
        initial_resume_score: ScoreReport,
        initial_match_score: Option<ScoreReport>,
    ) -> Result<(serde_json::Value, ScoreReport, Option<ScoreReport>)> {
        let strategy = IterationStrategy::from_str(&self.config.iteration_strategy)?;

        let mut best_resume = initial_resume;
        let mut best_resume_score = initial_resume_score;
        let mut best_match_score = initial_match_score;
        let mut best_combined = self.calculate_combined_score(&best_resume_score, &best_match_score);

        let mut no_improvement_count = 0;

        for iteration in 1..=self.config.max_iterations {
            log::info!("Iteration {}/{}...", iteration, self.config.max_iterations);

            // Generate new candidate
            let candidate = self
                .revise_resume(&best_resume, &best_resume_score, job_text)
                .await?;

            // Score new candidate
            let candidate_resume_score =
                score_resume(&candidate, Some(&self.config.scoring_weights_file))?;

            let candidate_match_score = if job_text.is_some() {
                Some(score_match(
                    &candidate,
                    job_text.unwrap(),
                    Some(&self.config.scoring_weights_file),
                )?)
            } else {
                None
            };

            let candidate_combined =
                self.calculate_combined_score(&candidate_resume_score, &candidate_match_score);

            log::info!(
                "Candidate score: {:.2} (previous best: {:.2})",
                candidate_combined,
                best_combined
            );

            // Check for improvement
            if candidate_combined > best_combined {
                best_resume = candidate;
                best_resume_score = candidate_resume_score;
                best_match_score = candidate_match_score;
                best_combined = candidate_combined;
                no_improvement_count = 0;

                log::info!("New best score: {:.2}", best_combined);

                // FirstHit: stop immediately if target reached
                if strategy == IterationStrategy::FirstHit
                    && best_combined >= self.config.target_score
                {
                    log::info!("Target score reached, stopping iteration (FirstHit)");
                    break;
                }
            } else {
                no_improvement_count += 1;

                // Patience: stop if no improvement for too long
                if strategy == IterationStrategy::Patience
                    && no_improvement_count >= self.config.max_regressions
                {
                    log::info!("No improvement for {} iterations, stopping (Patience)", no_improvement_count);
                    break;
                }
            }

            // Check if target reached (for BestOf and Patience)
            if best_combined >= self.config.target_score {
                log::info!("Target score reached, stopping iteration");
                break;
            }
        }

        Ok((best_resume, best_resume_score, best_match_score))
    }

    /// Revise resume to improve scores.
    async fn revise_resume(
        &self,
        current_resume: &serde_json::Value,
        current_scores: &ScoreReport,
        job_text: Option<&str>,
    ) -> Result<serde_json::Value> {
        // Get the reviser agent
        let agent = self.agent_registry.get("reviser").map_err(|_| {
            AtsError::AgentError("Reviser agent not found in registry".to_string())
        })?;

        // Build revision prompt with score feedback
        let score_feedback = format!(
            "Current total score: {:.2}/100\nCategory scores:\n{}",
            current_scores.total,
            current_scores
                .categories
                .iter()
                .map(|c| format!("  - {}: {:.2}/100", c.name, c.score))
                .collect::<Vec<_>>()
                .join("\n")
        );

        let prompt = if let Some(job) = job_text {
            format!(
                "Revise the following resume to improve its scores. Focus on the lower-scoring categories.\n\n\
                 CURRENT SCORES:\n{}\n\n\
                 CURRENT RESUME:\n{}\n\n\
                 JOB DESCRIPTION:\n{}\n\n\
                 Return an improved, structured JSON resume.",
                score_feedback,
                serde_json::to_string_pretty(current_resume).unwrap_or_default(),
                job
            )
        } else {
            format!(
                "Revise the following resume to improve its scores. Focus on the lower-scoring categories.\n\n\
                 CURRENT SCORES:\n{}\n\n\
                 CURRENT RESUME:\n{}\n\n\
                 Return an improved, structured JSON resume.",
                score_feedback,
                serde_json::to_string_pretty(current_resume).unwrap_or_default()
            )
        };

        // Call agent
        let response = agent.generate(&prompt).await?;

        // Parse JSON response
        serde_json::from_str(&response).map_err(|e| {
            AtsError::ValidationError(format!("Failed to parse revised resume JSON: {}", e))
        })
    }

    /// Calculate combined score from resume and match scores.
    fn calculate_combined_score(
        &self,
        resume_score: &ScoreReport,
        match_score: &Option<ScoreReport>,
    ) -> f64 {
        if let Some(ms) = match_score {
            // Weighted average: 50% resume quality + 50% match quality
            (resume_score.total + ms.total) / 2.0
        } else {
            resume_score.total
        }
    }

    /// Process all new resumes in the input folder.
    pub async fn process_all_resumes(&mut self) -> Result<Vec<ProcessingResult>> {
        let resume_paths = self.input_handler.list_files()?;
        let mut results = Vec::new();

        log::info!("Found {} resumes to process", resume_paths.len());

        for resume_path in resume_paths {
            log::info!("Processing: {}", resume_path.display());

            match self
                .process_resume(&resume_path.display().to_string(), None)
                .await
            {
                Ok(result) => results.push(result),
                Err(e) => {
                    log::error!("Failed to process {}: {}", resume_path.display(), e);
                    results.push(ProcessingResult {
                        success: false,
                        output_dir: None,
                        scores: None,
                        enhanced_resume: None,
                        recommendations: vec![],
                        error: Some(e.to_string()),
                    });
                }
            }
        }

        Ok(results)
    }
}

// -------------------------
// Tests
// -------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_iteration_strategy_parsing() {
        assert_eq!(
            IterationStrategy::from_str("best_of").unwrap(),
            IterationStrategy::BestOf
        );
        assert_eq!(
            IterationStrategy::from_str("first_hit").unwrap(),
            IterationStrategy::FirstHit
        );
        assert_eq!(
            IterationStrategy::from_str("patience").unwrap(),
            IterationStrategy::Patience
        );
    }

    #[test]
    fn test_combined_score_calculation() {
        // This test would require a full processor setup, skipping for now
    }
}
