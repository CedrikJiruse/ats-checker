//! Integration tests for job scraping types and basic functionality.

use ats_checker::scraper::{JobPosting, JobSource, SearchFilters};
use std::str::FromStr;

#[tokio::test]
async fn test_job_posting_creation() {
    let job = JobPosting::new(
        "Software Engineer",
        "Acme Corp",
        "Seattle, WA",
        "Great opportunity",
        "https://example.com/job",
        "linkedin",
    );

    assert_eq!(job.title, "Software Engineer");
    assert_eq!(job.company, "Acme Corp");
    assert_eq!(job.location, "Seattle, WA");
    assert_eq!(job.source, "linkedin");
}

#[tokio::test]
async fn test_job_posting_with_builder() {
    let job = JobPosting::new(
        "Engineer",
        "Company",
        "Location",
        "Description",
        "https://url.com",
        "source",
    )
    .with_salary("$100k")
    .with_remote(true)
    .with_experience_level("senior");

    assert_eq!(job.salary, Some("$100k".to_string()));
    assert_eq!(job.remote, Some(true));
    assert!(job.is_remote());
}

#[tokio::test]
async fn test_job_posting_id_generation() {
    let job1 = JobPosting::new(
        "Title",
        "Company",
        "Location",
        "Desc",
        "https://url1.com",
        "src",
    );
    let job2 = JobPosting::new(
        "Title",
        "Company",
        "Location",
        "Desc",
        "https://url2.com",
        "src",
    );

    // Different URLs should generate different IDs
    assert_ne!(job1.id(), job2.id());

    // Same URL should generate same ID
    let job3 = JobPosting::new(
        "Title",
        "Company",
        "Location",
        "Desc",
        "https://url1.com",
        "src",
    );
    assert_eq!(job1.id(), job3.id());
}

#[tokio::test]
async fn test_search_filters_builder() {
    let filters = SearchFilters::builder()
        .keywords("software engineer")
        .location("New York")
        .salary_min(100_000)
        .experience_level(vec!["senior".to_string()])
        .build();

    assert_eq!(filters.keywords, Some("software engineer".to_string()));
    assert_eq!(filters.location, Some("New York".to_string()));
    assert_eq!(filters.salary_min, Some(100_000));
}

#[tokio::test]
async fn test_job_source_parsing() {
    assert_eq!(
        JobSource::from_str("linkedin").unwrap(),
        JobSource::LinkedIn
    );
    assert_eq!(JobSource::from_str("indeed").unwrap(), JobSource::Indeed);
    assert_eq!(
        JobSource::from_str("glassdoor").unwrap(),
        JobSource::Glassdoor
    );
    assert_eq!(JobSource::from_str("google").unwrap(), JobSource::Google);
    assert_eq!(
        JobSource::from_str("ziprecruiter").unwrap(),
        JobSource::ZipRecruiter
    );

    // Test case insensitivity
    assert_eq!(
        JobSource::from_str("LinkedIn").unwrap(),
        JobSource::LinkedIn
    );
    assert_eq!(JobSource::from_str("INDEED").unwrap(), JobSource::Indeed);
}

#[tokio::test]
async fn test_job_posting_serialization() {
    let job = JobPosting::new(
        "Engineer",
        "TestCo",
        "Remote",
        "Description",
        "https://test.com",
        "linkedin",
    )
    .with_salary("$100k");

    // Test serialization to JSON
    let json = serde_json::to_string(&job).unwrap();
    assert!(json.contains("Engineer"));
    assert!(json.contains("TestCo"));

    // Test deserialization
    let deserialized: JobPosting = serde_json::from_str(&json).unwrap();
    assert_eq!(deserialized.title, job.title);
    assert_eq!(deserialized.company, job.company);
    assert_eq!(deserialized.id(), job.id());
}

#[tokio::test]
async fn test_search_filters_is_empty() {
    let empty_filters = SearchFilters::default();
    assert!(empty_filters.is_empty());

    let non_empty_filters = SearchFilters::builder().keywords("rust").build();
    assert!(!non_empty_filters.is_empty());
}

#[test]
fn test_job_posting_default() {
    let job = JobPosting::default();
    assert_eq!(job.title, "");
    assert_eq!(job.company, "");
    assert_eq!(job.location, "");
}

#[test]
fn test_job_posting_remote_check() {
    let remote_job = JobPosting::default().with_remote(true);
    assert!(remote_job.is_remote());

    let non_remote_job = JobPosting::default().with_remote(false);
    assert!(!non_remote_job.is_remote());

    let unspecified_job = JobPosting::default();
    assert!(!unspecified_job.is_remote()); // Defaults to false
}

#[tokio::test]
async fn test_job_posting_metadata() {
    let job = JobPosting::new(
        "Title",
        "Company",
        "Location",
        "Desc",
        "https://url.com",
        "src",
    )
    .with_metadata("test_key", serde_json::json!({"nested": "value"}));

    assert!(job.metadata.contains_key("test_key"));
    assert_eq!(
        job.metadata.get("test_key"),
        Some(&serde_json::json!({"nested": "value"}))
    );
}

#[tokio::test]
async fn test_multiple_job_postings() {
    let jobs = [
        JobPosting::new(
            "Job 1",
            "Co 1",
            "Loc 1",
            "Desc 1",
            "https://url1.com",
            "linkedin",
        ),
        JobPosting::new(
            "Job 2",
            "Co 2",
            "Loc 2",
            "Desc 2",
            "https://url2.com",
            "indeed",
        ),
        JobPosting::new(
            "Job 3",
            "Co 3",
            "Loc 3",
            "Desc 3",
            "https://url3.com",
            "glassdoor",
        ),
    ];

    assert_eq!(jobs.len(), 3);
    assert_eq!(jobs[0].source, "linkedin");
    assert_eq!(jobs[1].source, "indeed");
    assert_eq!(jobs[2].source, "glassdoor");

    // All IDs should be different
    assert_ne!(jobs[0].id(), jobs[1].id());
    assert_ne!(jobs[1].id(), jobs[2].id());
    assert_ne!(jobs[0].id(), jobs[2].id());
}
