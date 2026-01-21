//! Job scraping module.
//!
//! This module provides functionality for scraping job postings from various
//! job boards including LinkedIn, Indeed, Glassdoor, Google Jobs, and ZipRecruiter.
//!
//! # Core Types
//!
//! - [`JobPosting`] - Represents a scraped job posting
//! - [`SearchFilters`] - Filters for job searches
//! - [`SavedSearch`] - A saved job search configuration
//! - [`JobScraperManager`] - Manages job scraping across multiple sources
//!
//! # Example
//!
//! ```rust,no_run
//! use ats_checker::scraper::{JobScraperManager, SearchFilters};
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let manager = JobScraperManager::new("results/", "data/saved_searches.toml")?;
//!
//!     let filters = SearchFilters::builder()
//!         .keywords("software engineer")
//!         .location("San Francisco, CA")
//!         .remote_only(true)
//!         .build();
//!
//!     let jobs = manager.search_jobs(&filters, &["linkedin", "indeed"], 50).await?;
//!     println!("Found {} jobs", jobs.len());
//!     Ok(())
//! }
//! ```

mod manager;
mod saved_search;
mod types;

pub use manager::JobScraperManager;
pub use saved_search::SavedSearchManager;
pub use types::{JobPosting, JobSource, SavedSearch, SearchFilters};

use crate::error::Result;
use async_trait::async_trait;

/// Trait for job scrapers.
///
/// Implement this trait to add support for a new job source.
#[async_trait]
pub trait JobScraper: Send + Sync {
    /// Get the name of this scraper.
    fn name(&self) -> &str;

    /// Search for jobs matching the given filters.
    async fn search_jobs(
        &self,
        filters: &SearchFilters,
        max_results: i32,
    ) -> Result<Vec<JobPosting>>;

    /// Get detailed information about a specific job.
    async fn get_job_details(&self, job_url: &str) -> Result<Option<JobPosting>>;
}
