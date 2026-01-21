//! CLI command handlers.

use crate::config::Config;
use crate::error::{AtsError, Result};
use crate::scoring::{score_job, score_match, score_resume};
use crate::scraper::JobScraperManager;
use std::path::Path;

// -------------------------
// Score Resume Command
// -------------------------

/// Handle the score-resume subcommand.
pub fn handle_score_resume(resume_path: &str, weights_path: Option<&str>, config: &Config) -> Result<i32> {
    log::info!("Scoring resume: {}", resume_path);

    // Determine weights file path
    let weights = if let Some(w) = weights_path {
        Path::new(w)
    } else {
        &config.scoring_weights_file
    };

    // Load resume file
    let resume_content = std::fs::read_to_string(resume_path)
        .map_err(|e| AtsError::InputError(format!("Failed to read resume file: {}", e)))?;

    // Parse resume as JSON
    let resume: serde_json::Value = if resume_path.ends_with(".json") {
        serde_json::from_str(&resume_content)
            .map_err(|e| AtsError::ValidationError(format!("Invalid JSON: {}", e)))?
    } else if resume_path.ends_with(".toml") {
        let toml_value: toml::Value = toml::from_str(&resume_content)
            .map_err(|e| AtsError::TomlError(format!("Invalid TOML: {}", e)))?;
        serde_json::to_value(toml_value)
            .map_err(|e| AtsError::ValidationError(format!("Failed to convert TOML to JSON: {}", e)))?
    } else {
        return Err(AtsError::ValidationError(
            "Resume file must be .json or .toml".to_string(),
        ));
    };

    // Score the resume
    let score_report = score_resume(&resume, Some(weights))?;

    // Print results
    println!("\n{}", "=".repeat(60));
    println!("RESUME SCORE REPORT");
    println!("{}", "=".repeat(60));
    println!("\nTotal Score: {:.2}/100", score_report.total);
    println!("\nCategory Breakdown:");
    for category in &score_report.categories {
        println!(
            "  {} (weight: {:.0}%): {:.2}/100",
            category.name,
            category.weight * 100.0,
            category.score
        );
    }
    println!("\n{}", "=".repeat(60));

    Ok(0)
}

// -------------------------
// Score Match Command
// -------------------------

/// Handle the score-match subcommand.
pub fn handle_score_match(
    resume_path: &str,
    job_path: &str,
    weights_path: Option<&str>,
    config: &Config,
) -> Result<i32> {
    log::info!("Scoring match: {} vs {}", resume_path, job_path);

    // Determine weights file path
    let weights = if let Some(w) = weights_path {
        Path::new(w)
    } else {
        &config.scoring_weights_file
    };

    // Load resume file
    let resume_content = std::fs::read_to_string(resume_path)
        .map_err(|e| AtsError::InputError(format!("Failed to read resume file: {}", e)))?;

    // Parse resume as JSON
    let resume: serde_json::Value = if resume_path.ends_with(".json") {
        serde_json::from_str(&resume_content)
            .map_err(|e| AtsError::ValidationError(format!("Invalid JSON: {}", e)))?
    } else if resume_path.ends_with(".toml") {
        let toml_value: toml::Value = toml::from_str(&resume_content)
            .map_err(|e| AtsError::TomlError(format!("Invalid TOML: {}", e)))?;
        serde_json::to_value(toml_value)
            .map_err(|e| AtsError::ValidationError(format!("Failed to convert TOML to JSON: {}", e)))?
    } else {
        return Err(AtsError::ValidationError(
            "Resume file must be .json or .toml".to_string(),
        ));
    };

    // Load job description
    let job_text = std::fs::read_to_string(job_path)
        .map_err(|e| AtsError::InputError(format!("Failed to read job file: {}", e)))?;

    // Score resume quality
    let resume_score = score_resume(&resume, Some(weights))?;

    // Score resume-job match
    let match_score = score_match(&resume, &job_text, Some(weights))?;

    // Calculate combined score
    let combined_score = (resume_score.total + match_score.total) / 2.0;

    // Print results
    println!("\n{}", "=".repeat(60));
    println!("RESUME-JOB MATCH REPORT");
    println!("{}", "=".repeat(60));

    println!("\nResume Quality Score: {:.2}/100", resume_score.total);
    println!("  Category Breakdown:");
    for category in &resume_score.categories {
        println!(
            "    {} (weight: {:.0}%): {:.2}/100",
            category.name,
            category.weight * 100.0,
            category.score
        );
    }

    println!("\nResume-Job Match Score: {:.2}/100", match_score.total);
    println!("  Category Breakdown:");
    for category in &match_score.categories {
        println!(
            "    {} (weight: {:.0}%): {:.2}/100",
            category.name,
            category.weight * 100.0,
            category.score
        );
    }

    println!("\nCombined Score: {:.2}/100", combined_score);
    println!("{}", "=".repeat(60));

    Ok(0)
}

// -------------------------
// Rank Jobs Command
// -------------------------

/// Handle the rank-jobs subcommand.
pub fn handle_rank_jobs(results_path: &str, top: i32, config: &Config) -> Result<i32> {
    log::info!("Ranking jobs from: {} (top {})", results_path, top);

    // Load results file
    let results_content = std::fs::read_to_string(results_path)
        .map_err(|e| AtsError::InputError(format!("Failed to read results file: {}", e)))?;

    // Parse as TOML
    let results_toml: toml::Value = toml::from_str(&results_content)
        .map_err(|e| AtsError::TomlError(format!("Invalid TOML: {}", e)))?;

    // Extract jobs array
    let jobs = results_toml
        .get("jobs")
        .and_then(|v| v.as_array())
        .ok_or_else(|| AtsError::ValidationError("No 'jobs' array in results file".to_string()))?;

    if jobs.is_empty() {
        println!("No jobs found in results file.");
        return Ok(0);
    }

    // Convert to JobPosting structs and score them
    let mut scored_jobs: Vec<(serde_json::Value, f64)> = Vec::new();

    for job_value in jobs {
        let job_json = serde_json::to_value(job_value)
            .map_err(|e| AtsError::ValidationError(format!("Failed to convert job: {}", e)))?;

        // Score the job posting
        let score = score_job(&job_json, Some(&config.scoring_weights_file))?;
        scored_jobs.push((job_json, score.total));
    }

    // Sort by score descending
    scored_jobs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

    // Print top N jobs
    println!("\n{}", "=".repeat(80));
    println!("TOP {} JOBS (sorted by score)", top);
    println!("{}", "=".repeat(80));
    println!();
    println!(
        "{:<5} {:<8} {:<30} {:<20} {:<15}",
        "Rank", "Score", "Title", "Company", "Location"
    );
    println!("{}", "-".repeat(80));

    for (i, (job, score)) in scored_jobs.iter().take(top as usize).enumerate() {
        let title = job
            .get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("N/A");
        let company = job
            .get("company")
            .and_then(|v| v.as_str())
            .unwrap_or("N/A");
        let location = job
            .get("location")
            .and_then(|v| v.as_str())
            .unwrap_or("N/A");

        println!(
            "{:<5} {:<8.2} {:<30} {:<20} {:<15}",
            i + 1,
            score,
            truncate(title, 30),
            truncate(company, 20),
            truncate(location, 15)
        );
    }

    println!("\n{}", "=".repeat(80));
    println!("Total jobs: {} | Showing top: {}", jobs.len(), top.min(jobs.len() as i32));
    println!("{}", "=".repeat(80));

    Ok(0)
}

/// Truncate a string to a maximum length, adding "..." if truncated.
fn truncate(s: &str, max_len: usize) -> String {
    if s.len() <= max_len {
        s.to_string()
    } else {
        format!("{}...", &s[0..(max_len - 3)])
    }
}

// -------------------------
// Tests
// -------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_truncate() {
        assert_eq!(truncate("short", 10), "short");
        assert_eq!(truncate("this is a very long string", 10), "this is...");
        assert_eq!(truncate("exactly10c", 10), "exactly10c");
    }
}
