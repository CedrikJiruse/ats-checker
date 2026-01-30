//! End-to-end integration tests for job search functionality.

use ats_checker::config::Config;
use ats_checker::scraper::{
    jobspy::JobSpyScraper, CacheConfig, CacheWrapper, JobScraper, JobScraperManager, RetryConfig,
    RetryWrapper, SearchFilters,
};
use std::time::Duration;
use tempfile::TempDir;

#[tokio::test]
async fn test_job_scraper_manager_workflow() {
    let temp_dir = TempDir::new().unwrap();
    let results_folder = temp_dir.path().join("results");
    let saved_searches = temp_dir.path().join("saved_searches.toml");

    let manager = JobScraperManager::new(&results_folder, &saved_searches).unwrap();

    // Verify manager was created
    assert!(results_folder.exists());
    assert_eq!(manager.available_sources().len(), 0); // No scrapers registered yet
}

#[tokio::test]
async fn test_job_scraper_with_retry_and_cache() {
    // This test verifies the scraper wrapper stack works correctly
    // We can't test actual scraping without Python/JobSpy, so we test the wrappers

    let scraper = JobSpyScraper::new("linkedin").unwrap();

    // Add retry wrapper
    let retry_config = RetryConfig {
        max_retries: 2,
        initial_backoff: Duration::from_millis(10),
        max_backoff: Duration::from_millis(100),
        backoff_multiplier: 2.0,
    };
    let retry_scraper = RetryWrapper::new(scraper, retry_config);

    // Add cache wrapper
    let temp_dir = TempDir::new().unwrap();
    let cache_config = CacheConfig {
        ttl: Duration::from_secs(60),
        cache_dir: Some(temp_dir.path().to_path_buf()),
        persistent: false,
    };
    let cached_scraper = CacheWrapper::new(retry_scraper, cache_config);

    // Verify scraper name propagates through wrappers
    assert_eq!(cached_scraper.name(), "linkedin");
}

#[tokio::test]
async fn test_job_search_filters_builder() {
    let filters = SearchFilters::builder()
        .keywords("rust developer")
        .location("Remote")
        .remote_only(true)
        .salary_min(100_000)
        .build();

    assert_eq!(filters.keywords, Some("rust developer".to_string()));
    assert_eq!(filters.location, Some("Remote".to_string()));
    assert!(filters.remote_only);
    assert_eq!(filters.salary_min, Some(100_000));
}

#[tokio::test]
async fn test_job_search_manager_registration() {
    let temp_dir = TempDir::new().unwrap();
    let manager = JobScraperManager::new(
        temp_dir.path().join("results"),
        temp_dir.path().join("saved.toml"),
    )
    .unwrap();

    let available = manager.available_sources();
    assert_eq!(available.len(), 0);

    // In a real scenario with Python/JobSpy installed, scrapers would be registered
    // For now, we verify the manager structure is correct
}

#[tokio::test]
async fn test_scraper_dependency_check() {
    let scraper = JobSpyScraper::new("linkedin").unwrap();

    // This will fail if Python/JobSpy isn't installed, which is expected in CI
    match scraper.check_dependencies() {
        Ok(_) => {
            // Dependencies are available - great!
            println!("✓ Python and JobSpy are installed");
        }
        Err(e) => {
            // Expected in environments without Python/JobSpy
            assert!(
                e.to_string().contains("Python") || e.to_string().contains("JobSpy"),
                "Error should mention missing dependency"
            );
        }
    }
}

#[test]
fn test_config_output_folders() {
    let config = Config::default();

    // Verify default paths are set
    assert!(config.output_folder.to_str().is_some());

    // Job search results should be saved under output folder
    let job_results = config.output_folder.join("job_searches");
    assert!(job_results.to_str().is_some());
}

#[tokio::test]
async fn test_job_results_save_and_load() {
    use ats_checker::scraper::JobPosting;

    let temp_dir = TempDir::new().unwrap();
    let manager = JobScraperManager::new(
        temp_dir.path().join("results"),
        temp_dir.path().join("saved.toml"),
    )
    .unwrap();

    // Create sample jobs
    let jobs = vec![
        JobPosting::new(
            "Software Engineer",
            "Acme Inc",
            "San Francisco, CA",
            "Great opportunity",
            "https://example.com/job1",
            "linkedin",
        )
        .with_salary("$100k-$150k")
        .with_remote(true),
        JobPosting::new(
            "Rust Developer",
            "TechCorp",
            "Remote",
            "Work with cutting-edge Rust",
            "https://example.com/job2",
            "indeed",
        )
        .with_salary("$120k-$180k")
        .with_remote(true),
    ];

    // Save results
    let path = manager.save_results(&jobs, "test_jobs.toml").unwrap();
    assert!(path.exists());

    // Load results
    let loaded_jobs = manager.load_results(&path).unwrap();
    assert_eq!(loaded_jobs.len(), 2);
    assert_eq!(loaded_jobs[0].title, "Software Engineer");
    assert_eq!(loaded_jobs[1].title, "Rust Developer");
}

#[tokio::test]
async fn test_job_ranking() {
    use ats_checker::scraper::JobPosting;

    let temp_dir = TempDir::new().unwrap();
    let manager = JobScraperManager::new(
        temp_dir.path().join("results"),
        temp_dir.path().join("saved.toml"),
    )
    .unwrap();

    // Create jobs with different scores
    let jobs = vec![
        JobPosting::new("A", "Co", "Loc", "Desc", "url1", "src").with_score(50.0),
        JobPosting::new("B", "Co", "Loc", "Desc", "url2", "src").with_score(90.0),
        JobPosting::new("C", "Co", "Loc", "Desc", "url3", "src").with_score(70.0),
    ];

    let path = manager.save_results(&jobs, "ranked_jobs.toml").unwrap();

    // Rank jobs
    let ranked = manager.rank_jobs_in_results(&path, 2, false).unwrap();

    assert_eq!(ranked.len(), 2);
    assert_eq!(ranked[0].job.title, "B"); // Highest score
    assert_eq!(ranked[0].rank, 1);
    assert_eq!(ranked[1].job.title, "C"); // Second highest
    assert_eq!(ranked[1].rank, 2);
}

#[tokio::test]
async fn test_cache_prevents_duplicate_searches() {
    use ats_checker::scraper::cache::CacheWrapper;

    let temp_dir = TempDir::new().unwrap();
    let scraper = JobSpyScraper::new("linkedin").unwrap();

    let cache_config = CacheConfig {
        ttl: Duration::from_secs(3600),
        cache_dir: Some(temp_dir.path().to_path_buf()),
        persistent: false,
    };
    let cached_scraper = CacheWrapper::new(scraper, cache_config);

    // Verify cache is empty initially
    let stats = cached_scraper.cache_stats();
    assert_eq!(stats.total_entries, 0);

    // Note: We can't test actual scraping without Python/JobSpy
    // This test verifies the cache infrastructure is in place
}
