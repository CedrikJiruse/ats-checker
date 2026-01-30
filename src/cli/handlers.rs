//! CLI command handlers.

use crate::cli::table;
use crate::config::Config;
use crate::error::{AtsError, Result};
use crate::scoring::{score_job, score_match, score_resume};
use std::path::Path;

// -------------------------
// Score Resume Command
// -------------------------

/// Handle the score-resume subcommand.
///
/// # Errors
///
/// Returns an error if:
/// - The resume file cannot be read or parsed
/// - The weights file cannot be loaded
/// - Scoring fails
pub fn handle_score_resume(
    resume_path: &str,
    weights_path: Option<&str>,
    config: &Config,
) -> Result<i32> {
    log::info!("Scoring resume: {resume_path}");

    // Determine weights file path
    let weights = if let Some(w) = weights_path {
        Path::new(w)
    } else {
        &config.scoring_weights_file
    };

    // Load resume file
    let resume_content = std::fs::read_to_string(resume_path)
        .map_err(|e| AtsError::io("Failed to read resume file".to_string(), e))?;

    // Parse resume as JSON
    let resume: serde_json::Value = if Path::new(resume_path)
        .extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("json"))
    {
        serde_json::from_str(&resume_content)
            .map_err(|e| AtsError::internal(format!("Invalid JSON: {e}")))?
    } else if Path::new(resume_path)
        .extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("toml"))
    {
        let toml_value: toml::Value = toml::from_str(&resume_content)
            .map_err(|e| AtsError::config_parse(format!("Invalid TOML: {e}")))?;
        serde_json::to_value(toml_value)
            .map_err(|e| AtsError::internal(format!("Failed to convert TOML to JSON: {e}")))?
    } else {
        return Err(AtsError::internal("Resume file must be .json or .toml"));
    };

    // Score the resume
    let score_report = score_resume(&resume, weights.to_str())?;

    // Convert score report to JSON for table formatting
    let mut categories = serde_json::Map::new();
    for category in &score_report.categories {
        categories.insert(
            category.name.to_lowercase().replace(' ', "_"),
            serde_json::json!({
                "score": category.score,
                "weight": category.weight
            }),
        );
    }

    let scores_json = serde_json::json!({
        "overall": score_report.total,
        "categories": categories
    });

    // Print results using table formatting
    println!("\n{}", "=".repeat(60));
    println!("RESUME SCORE REPORT");
    println!("{}", "=".repeat(60));
    println!("\n{}", table::format_resume_scores(&scores_json));
    println!("{}", "=".repeat(60));

    Ok(0)
}

// -------------------------
// Score Match Command
// -------------------------

/// Handle the score-match subcommand.
///
/// # Errors
///
/// Returns an error if:
/// - The resume or job file cannot be read or parsed
/// - The weights file cannot be loaded
/// - Scoring fails
pub fn handle_score_match(
    resume_path: &str,
    job_path: &str,
    weights_path: Option<&str>,
    config: &Config,
) -> Result<i32> {
    log::info!("Scoring match: {resume_path} vs {job_path}");

    // Determine weights file path
    let weights = if let Some(w) = weights_path {
        Path::new(w)
    } else {
        &config.scoring_weights_file
    };

    // Load resume file
    let resume_content = std::fs::read_to_string(resume_path)
        .map_err(|e| AtsError::io("Failed to read resume file".to_string(), e))?;

    // Parse resume as JSON
    let resume: serde_json::Value = if Path::new(resume_path)
        .extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("json"))
    {
        serde_json::from_str(&resume_content)
            .map_err(|e| AtsError::internal(format!("Invalid JSON: {e}")))?
    } else if Path::new(resume_path)
        .extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("toml"))
    {
        let toml_value: toml::Value = toml::from_str(&resume_content)
            .map_err(|e| AtsError::config_parse(format!("Invalid TOML: {e}")))?;
        serde_json::to_value(toml_value)
            .map_err(|e| AtsError::internal(format!("Failed to convert TOML to JSON: {e}")))?
    } else {
        return Err(AtsError::internal("Resume file must be .json or .toml"));
    };

    // Load job description
    let job_text = std::fs::read_to_string(job_path)
        .map_err(|e| AtsError::io("Failed to read job file".to_string(), e))?;

    // Convert job text to JSON structure
    let job_json = serde_json::json!({
        "description": job_text,
        "raw_text": job_text
    });

    // Score resume quality
    let resume_score = score_resume(&resume, weights.to_str())?;

    // Score resume-job match
    let match_score = score_match(&resume, &job_json, weights.to_str())?;

    // Calculate combined score
    let combined_score = f64::midpoint(resume_score.total, match_score.total);

    // Convert resume score to JSON
    let mut resume_categories = serde_json::Map::new();
    for category in &resume_score.categories {
        resume_categories.insert(
            category.name.to_lowercase().replace(' ', "_"),
            serde_json::json!({
                "score": category.score,
                "weight": category.weight
            }),
        );
    }
    let resume_scores_json = serde_json::json!({
        "overall": resume_score.total,
        "categories": resume_categories
    });

    // Convert match score to JSON
    let mut match_categories = serde_json::Map::new();
    for category in &match_score.categories {
        match_categories.insert(
            category.name.to_lowercase().replace(' ', "_"),
            serde_json::json!(category.score),
        );
    }
    let match_scores_json = serde_json::json!({
        "overall": match_score.total,
        "categories": match_categories
    });

    // Print results using table formatting
    println!("\n{}", "=".repeat(80));
    println!("RESUME-JOB MATCH REPORT");
    println!("{}", "=".repeat(80));

    println!("\nResume Quality Score:");
    println!("{}", table::format_resume_scores(&resume_scores_json));

    println!("\nResume-Job Match Score:");
    println!("{}", table::format_match_scores(&match_scores_json));

    println!("\nCombined Score: {combined_score:.2}/100");
    println!("{}", "=".repeat(80));

    Ok(0)
}

// -------------------------
// Rank Jobs Command
// -------------------------

/// Handle the rank-jobs subcommand.
///
/// # Errors
///
/// Returns an error if:
/// - The results file cannot be read or parsed
/// - Job score calculation fails
pub fn handle_rank_jobs(results_path: &str, top: i32, config: &Config) -> Result<i32> {
    log::info!("Ranking jobs from: {results_path} (top {top})");

    // Load results file
    let results_content = std::fs::read_to_string(results_path)
        .map_err(|e| AtsError::io("Failed to read results file".to_string(), e))?;

    // Parse as TOML
    let results_toml: toml::Value = toml::from_str(&results_content)
        .map_err(|e| AtsError::config_parse(format!("Invalid TOML: {e}")))?;

    // Extract jobs array
    let jobs = results_toml
        .get("jobs")
        .and_then(|v| v.as_array())
        .ok_or_else(|| AtsError::internal("No 'jobs' array in results file"))?;

    if jobs.is_empty() {
        println!("No jobs found in results file.");
        return Ok(0);
    }

    // Convert to JobPosting structs and score them
    let mut scored_jobs: Vec<(serde_json::Value, f64)> = Vec::new();

    for job_value in jobs {
        let job_json = serde_json::to_value(job_value)
            .map_err(|e| AtsError::internal(format!("Failed to convert job: {e}")))?;

        // Score the job posting
        let score = score_job(&job_json, config.scoring_weights_file.to_str())?;
        scored_jobs.push((job_json, score.total));
    }

    // Sort by score descending
    scored_jobs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

    // Convert to format expected by table formatter
    let jobs_for_table: Vec<serde_json::Value> = scored_jobs
        .iter()
        .map(|(job, score)| {
            let mut job_with_score = job.clone();
            if let Some(obj) = job_with_score.as_object_mut() {
                obj.insert("score".to_string(), serde_json::json!(score));
            }
            job_with_score
        })
        .collect();

    // Print top N jobs using table formatting
    println!("\n{}", "=".repeat(80));
    println!("TOP {top} JOBS (sorted by score)");
    println!("{}", "=".repeat(80));
    println!(
        "\n{}",
        table::format_job_rankings(&jobs_for_table, top as usize)
    );
    println!(
        "\nTotal jobs: {} | Showing top: {}",
        jobs.len(),
        top.min(jobs.len() as i32)
    );
    println!("{}", "=".repeat(80));

    Ok(0)
}

// -------------------------
// Job Search Command
// -------------------------

/// Handle the job search subcommand.
///
/// # Errors
///
/// Returns an error if:
/// - `JobSpy` is not installed or Python is not available
/// - Job search fails
/// - Results cannot be saved
pub async fn handle_job_search(
    keywords: &str,
    location: Option<&str>,
    sources: &[String],
    max_results: i32,
    remote_only: bool,
    output_file: Option<&str>,
    config: &Config,
) -> Result<i32> {
    use crate::scraper::{
        jobspy::JobSpyScraper, CacheConfig, CacheWrapper, JobScraperManager, RetryConfig,
        RetryWrapper, SearchFilters,
    };
    use std::time::Duration;

    log::info!("Searching for jobs: {keywords}");

    // Create scraper manager
    let results_folder = config.output_folder.join("job_searches");
    let saved_searches_path = config.output_folder.join("saved_searches.toml");
    let mut manager = JobScraperManager::new(&results_folder, &saved_searches_path)?;

    // Register scrapers for each source
    for source in sources {
        match JobSpyScraper::new(source) {
            Ok(scraper) => {
                // Check dependencies
                if let Err(e) = scraper.check_dependencies() {
                    eprintln!("⚠️  Warning: {source} scraper unavailable: {e}");
                    continue;
                }

                // Add retry wrapper
                let retry_config = RetryConfig {
                    max_retries: 3,
                    initial_backoff: Duration::from_secs(2),
                    max_backoff: Duration::from_secs(30),
                    backoff_multiplier: 2.0,
                };
                let retry_scraper = RetryWrapper::new(scraper, retry_config);

                // Add cache wrapper
                let cache_config = CacheConfig {
                    ttl: Duration::from_secs(1800), // 30 minutes
                    cache_dir: Some(config.output_folder.join("cache")),
                    persistent: true,
                };
                let cached_scraper = CacheWrapper::new(retry_scraper, cache_config);

                manager.register_scraper(Box::new(cached_scraper));
                println!("✓ Registered {source} scraper");
            }
            Err(e) => {
                eprintln!("⚠️  Warning: Invalid source '{source}': {e}");
            }
        }
    }

    // Build search filters
    let mut filters = SearchFilters::builder().keywords(keywords);

    if let Some(loc) = location {
        filters = filters.location(loc);
    }

    if remote_only {
        filters = filters.remote_only(true);
    }

    let filters = filters.build();

    // Search jobs
    println!("\n🔍 Searching for jobs...");
    println!("   Keywords: {keywords}");
    if let Some(loc) = location {
        println!("   Location: {loc}");
    }
    if remote_only {
        println!("   Remote only: Yes");
    }
    println!("   Sources: {}", sources.join(", "));
    println!("   Max results per source: {max_results}\n");

    let source_names: Vec<&str> = sources.iter().map(String::as_str).collect();
    let jobs = manager
        .search_jobs(&filters, &source_names, max_results)
        .await?;

    if jobs.is_empty() {
        println!("No jobs found matching your criteria.");
        return Ok(0);
    }

    println!("✓ Found {} jobs\n", jobs.len());

    // Save results if output file specified
    let saved_path = if let Some(output) = output_file {
        manager.save_results(&jobs, output)?
    } else {
        // Default filename based on keywords and timestamp
        let timestamp = chrono::Utc::now().format("%Y%m%d_%H%M%S");
        let safe_keywords = keywords
            .chars()
            .filter(|c| c.is_alphanumeric() || *c == ' ')
            .collect::<String>()
            .replace(' ', "_");
        let filename = format!("jobs_{safe_keywords}_{timestamp}.toml");
        manager.save_results(&jobs, &filename)?
    };

    println!("✓ Results saved to: {}\n", saved_path.display());

    // Display summary using table formatting
    let jobs_json: Vec<serde_json::Value> = jobs
        .iter()
        .map(|job| serde_json::to_value(job).unwrap_or_default())
        .collect();

    println!("{}", "=".repeat(80));
    println!("JOB SEARCH RESULTS");
    println!("{}", "=".repeat(80));
    println!(
        "\n{}",
        table::format_job_rankings(&jobs_json, jobs.len().min(20))
    );

    if jobs.len() > 20 {
        println!(
            "\n... and {} more jobs (see full results in output file)",
            jobs.len() - 20
        );
    }

    println!("\n{}", "=".repeat(80));

    Ok(0)
}

// -------------------------
// Tests
// -------------------------

#[cfg(test)]
mod tests {
    // Tests moved to integration tests in tests/ directory
}
