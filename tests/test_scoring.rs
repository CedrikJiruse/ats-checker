//! Integration tests for scoring algorithms.

mod common;

use ats_checker::scoring::{score_match, score_resume};
use common::*;

#[test]
fn test_score_resume_basic() {
    let temp_dir = create_temp_dir();
    let weights_path = temp_dir.path().join("weights.toml");

    // Create weights file
    create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let resume = sample_resume_json();

    let report = score_resume(&resume, Some(weights_path.to_str().unwrap()))
        .expect("Failed to score resume");

    // Score should be between 0 and 100
    assert!(report.total >= 0.0 && report.total <= 100.0);

    // Should have category scores
    assert!(!report.categories.is_empty());

    // All category scores should be valid
    for category in &report.categories {
        assert!(category.score >= 0.0 && category.score <= 100.0);
        assert!(category.weight >= 0.0 && category.weight <= 1.0);
    }
}

#[test]
fn test_score_resume_without_weights() {
    let resume = sample_resume_json();

    // Score without weights file (should use defaults)
    let report = score_resume(&resume, None).expect("Failed to score resume without weights");

    // Score should be between 0 and 100
    assert!(report.total >= 0.0 && report.total <= 100.0);
    assert!(!report.categories.is_empty());
}

#[test]
fn test_score_match_basic() {
    let temp_dir = create_temp_dir();
    let weights_path = temp_dir.path().join("weights.toml");
    create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let resume = sample_resume_json();

    // Create a job JSON value
    let job = serde_json::json!({
        "title": "Software Engineer",
        "description": sample_job_description()
    });

    let report = score_match(&resume, &job, Some(weights_path.to_str().unwrap()))
        .expect("Failed to score match");

    // Score should be between 0 and 100
    assert!(report.total >= 0.0 && report.total <= 100.0);

    // Should have category scores
    assert!(!report.categories.is_empty());
}

#[test]
fn test_score_resume_with_missing_fields() {
    let resume = serde_json::json!({
        "personal_info": {
            "name": "John Doe"
        }
    });

    let report = score_resume(&resume, None).expect("Should handle incomplete resume");

    // Score should still be valid, just lower
    assert!(report.total >= 0.0 && report.total <= 100.0);
}

#[test]
fn test_score_resume_completeness() {
    // Complete resume should score higher than incomplete one
    let complete_resume = sample_resume_json();
    let incomplete_resume = serde_json::json!({
        "personal_info": {
            "name": "John Doe"
        },
        "experience": []
    });

    let complete_score =
        score_resume(&complete_resume, None).expect("Failed to score complete resume");
    let incomplete_score =
        score_resume(&incomplete_resume, None).expect("Failed to score incomplete resume");

    assert!(complete_score.total > incomplete_score.total);
}
