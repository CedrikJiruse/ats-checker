//! Integration tests for CLI command handlers.

mod common;

use ats_checker::cli::handlers::{handle_rank_jobs, handle_score_match, handle_score_resume};
use ats_checker::config::Config;
use common::{
    create_temp_dir, create_test_file, sample_config_toml, sample_job_description,
    sample_resume_json, sample_scoring_weights,
};

#[test]
fn test_handle_score_resume_with_json() {
    let temp_dir = create_temp_dir();

    // Create test files
    let resume_path = create_test_file(
        temp_dir.path(),
        "resume.json",
        &serde_json::to_string_pretty(&sample_resume_json()).unwrap(),
    );

    let weights_path = create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());

    let config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Test scoring
    let result = handle_score_resume(
        resume_path.to_str().unwrap(),
        Some(weights_path.to_str().unwrap()),
        &config,
    );

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 0);
}

#[test]
fn test_handle_score_resume_with_toml() {
    let temp_dir = create_temp_dir();

    // Convert JSON to TOML
    let resume_value: toml::Value =
        serde_json::from_value(sample_resume_json()).expect("Failed to convert to TOML");

    // Create test files
    let resume_path = create_test_file(
        temp_dir.path(),
        "resume.toml",
        &toml::to_string_pretty(&resume_value).unwrap(),
    );

    let weights_path = create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());

    let config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Test scoring
    let result = handle_score_resume(
        resume_path.to_str().unwrap(),
        Some(weights_path.to_str().unwrap()),
        &config,
    );

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 0);
}

#[test]
fn test_handle_score_resume_with_invalid_file() {
    let temp_dir = create_temp_dir();
    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Test with non-existent file
    let result = handle_score_resume("nonexistent.json", None, &config);

    assert!(result.is_err());
}

#[test]
fn test_handle_score_resume_with_invalid_format() {
    let temp_dir = create_temp_dir();

    // Create test file with unsupported extension
    let resume_path = create_test_file(temp_dir.path(), "resume.txt", "invalid content");

    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Test scoring with unsupported file format
    let result = handle_score_resume(resume_path.to_str().unwrap(), None, &config);

    assert!(result.is_err());
}

#[test]
fn test_handle_score_match() {
    let temp_dir = create_temp_dir();

    // Create test files
    let resume_path = create_test_file(
        temp_dir.path(),
        "resume.json",
        &serde_json::to_string_pretty(&sample_resume_json()).unwrap(),
    );

    let job_path = create_test_file(temp_dir.path(), "job.txt", sample_job_description());

    let weights_path = create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());

    let config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Test scoring
    let result = handle_score_match(
        resume_path.to_str().unwrap(),
        job_path.to_str().unwrap(),
        Some(weights_path.to_str().unwrap()),
        &config,
    );

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 0);
}

#[test]
fn test_handle_score_match_with_missing_job() {
    let temp_dir = create_temp_dir();

    // Create resume file
    let resume_path = create_test_file(
        temp_dir.path(),
        "resume.json",
        &serde_json::to_string_pretty(&sample_resume_json()).unwrap(),
    );

    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Test with non-existent job file
    let result = handle_score_match(
        resume_path.to_str().unwrap(),
        "nonexistent_job.txt",
        None,
        &config,
    );

    assert!(result.is_err());
}

#[test]
fn test_handle_rank_jobs() {
    let temp_dir = create_temp_dir();

    // Create sample results file with multiple jobs
    let results_toml = r#"
[[jobs]]
title = "Senior Software Engineer"
company = "Tech Corp"
location = "San Francisco, CA"
description = "Looking for an experienced software engineer with expertise in distributed systems."
url = "https://example.com/job1"
source = "LinkedIn"
salary = "$150,000 - $200,000"

[[jobs]]
title = "Backend Developer"
company = "Startup Inc"
location = "Remote"
description = "Join our team to build scalable backend services."
url = "https://example.com/job2"
source = "Indeed"
salary = "$100,000 - $140,000"

[[jobs]]
title = "Software Developer"
company = "MegaCorp"
location = "New York, NY"
description = "Develop enterprise software solutions."
url = "https://example.com/job3"
source = "Glassdoor"
"#;

    let results_path = create_test_file(temp_dir.path(), "results.toml", results_toml);

    let weights_path = create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let mut config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Update the weights path in the loaded config
    config.scoring_weights_file = weights_path;

    // Test ranking
    let result = handle_rank_jobs(results_path.to_str().unwrap(), 10, &config);

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 0);
}

#[test]
fn test_handle_rank_jobs_with_empty_results() {
    let temp_dir = create_temp_dir();

    // Create empty results file
    let results_toml = r#"
jobs = []
"#;

    let results_path = create_test_file(temp_dir.path(), "results.toml", results_toml);

    let weights_path = create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let mut config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Update the weights path in the loaded config
    config.scoring_weights_file = weights_path;

    // Test ranking with empty jobs
    let result = handle_rank_jobs(results_path.to_str().unwrap(), 10, &config);

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 0);
}

#[test]
fn test_handle_rank_jobs_with_top_limit() {
    let temp_dir = create_temp_dir();

    // Create results file with 5 jobs
    let results_toml = r#"
[[jobs]]
title = "Job 1"
company = "Company 1"
location = "Location 1"
description = "Description 1"
url = "https://example.com/job1"
source = "LinkedIn"

[[jobs]]
title = "Job 2"
company = "Company 2"
location = "Location 2"
description = "Description 2"
url = "https://example.com/job2"
source = "Indeed"

[[jobs]]
title = "Job 3"
company = "Company 3"
location = "Location 3"
description = "Description 3"
url = "https://example.com/job3"
source = "Glassdoor"

[[jobs]]
title = "Job 4"
company = "Company 4"
location = "Location 4"
description = "Description 4"
url = "https://example.com/job4"
source = "LinkedIn"

[[jobs]]
title = "Job 5"
company = "Company 5"
location = "Location 5"
description = "Description 5"
url = "https://example.com/job5"
source = "Indeed"
"#;

    let results_path = create_test_file(temp_dir.path(), "results.toml", results_toml);

    let weights_path = create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let mut config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Update the weights path in the loaded config
    config.scoring_weights_file = weights_path;

    // Test ranking with top=2 (should show only 2 jobs)
    let result = handle_rank_jobs(results_path.to_str().unwrap(), 2, &config);

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 0);
}

#[test]
fn test_handle_rank_jobs_with_invalid_file() {
    let temp_dir = create_temp_dir();
    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Test with non-existent file
    let result = handle_rank_jobs("nonexistent.toml", 10, &config);

    assert!(result.is_err());
}
