//! Retry logic for job scrapers.
//!
//! This module provides retry capabilities with exponential backoff
//! for handling transient failures in job scraping operations.

use std::time::Duration;

use async_trait::async_trait;

use crate::error::Result;
use crate::scraper::{JobPosting, JobScraper, SearchFilters};

/// Configuration for retry behavior.
#[derive(Debug, Clone)]
pub struct RetryConfig {
    /// Maximum number of retry attempts.
    pub max_retries: u32,
    /// Initial backoff duration.
    pub initial_backoff: Duration,
    /// Maximum backoff duration.
    pub max_backoff: Duration,
    /// Backoff multiplier for exponential backoff.
    pub backoff_multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            initial_backoff: Duration::from_secs(1),
            max_backoff: Duration::from_secs(60),
            backoff_multiplier: 2.0,
        }
    }
}

/// Wrapper that adds retry logic to any `JobScraper` implementation.
///
/// # Example
///
/// ```rust,no_run
/// use ats_checker::scraper::jobspy::JobSpyScraper;
/// use ats_checker::scraper::retry::{RetryWrapper, RetryConfig};
///
/// let scraper = JobSpyScraper::new("linkedin").unwrap();
/// let retry_scraper = RetryWrapper::new(scraper, RetryConfig::default());
/// ```
pub struct RetryWrapper<S: JobScraper> {
    inner: S,
    config: RetryConfig,
}

impl<S: JobScraper> RetryWrapper<S> {
    /// Create a new retry wrapper with the given scraper and config.
    pub fn new(scraper: S, config: RetryConfig) -> Self {
        Self {
            inner: scraper,
            config,
        }
    }

    /// Create a retry wrapper with default configuration.
    pub fn with_defaults(scraper: S) -> Self {
        Self::new(scraper, RetryConfig::default())
    }

    /// Execute an async operation with retry logic.
    async fn retry_with_backoff<F, Fut, T>(&self, operation: F) -> Result<T>
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = Result<T>>,
    {
        let mut attempt = 0;
        let mut backoff = self.config.initial_backoff;

        loop {
            match operation().await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    attempt += 1;

                    // Check if error is retryable
                    if !e.is_retryable() {
                        log::debug!("Non-retryable error, failing immediately: {e}");
                        return Err(e);
                    }

                    // Check if we've exhausted retries
                    if attempt >= self.config.max_retries {
                        log::warn!(
                            "Max retries ({}) exceeded for {}: {}",
                            self.config.max_retries,
                            self.inner.name(),
                            e
                        );
                        return Err(e);
                    }

                    // Log retry attempt
                    log::info!(
                        "Retry attempt {}/{} for {} after {:?}: {}",
                        attempt,
                        self.config.max_retries,
                        self.inner.name(),
                        backoff,
                        e
                    );

                    // Wait before retrying
                    tokio::time::sleep(backoff).await;

                    // Calculate next backoff (exponential with max cap)
                    backoff = Duration::from_secs_f64(
                        (backoff.as_secs_f64() * self.config.backoff_multiplier)
                            .min(self.config.max_backoff.as_secs_f64()),
                    );
                }
            }
        }
    }
}

#[async_trait]
impl<S: JobScraper + Send + Sync> JobScraper for RetryWrapper<S> {
    fn name(&self) -> &'static str {
        self.inner.name()
    }

    async fn search_jobs(
        &self,
        filters: &SearchFilters,
        max_results: i32,
    ) -> Result<Vec<JobPosting>> {
        self.retry_with_backoff(|| self.inner.search_jobs(filters, max_results))
            .await
    }

    async fn get_job_details(&self, job_url: &str) -> Result<Option<JobPosting>> {
        self.retry_with_backoff(|| self.inner.get_job_details(job_url))
            .await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::AtsError;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;

    // Mock scraper for testing
    struct MockScraper {
        attempts: Arc<AtomicU32>,
        fail_count: u32,
    }

    impl MockScraper {
        fn new(fail_count: u32) -> Self {
            Self {
                attempts: Arc::new(AtomicU32::new(0)),
                fail_count,
            }
        }
    }

    #[async_trait]
    impl JobScraper for MockScraper {
        fn name(&self) -> &'static str {
            "mock"
        }

        async fn search_jobs(
            &self,
            _filters: &SearchFilters,
            _max_results: i32,
        ) -> Result<Vec<JobPosting>> {
            let attempt = self.attempts.fetch_add(1, Ordering::SeqCst);

            if attempt < self.fail_count {
                Err(AtsError::ScraperError {
                    message: format!("Simulated failure {attempt}"),
                    source: None,
                })
            } else {
                Ok(vec![JobPosting::new(
                    "Test Job",
                    "Test Co",
                    "Test Loc",
                    "Test Desc",
                    "http://test.com",
                    "mock",
                )])
            }
        }

        async fn get_job_details(&self, _job_url: &str) -> Result<Option<JobPosting>> {
            Ok(None)
        }
    }

    #[tokio::test]
    async fn test_retry_success_after_failures() {
        let mock = MockScraper::new(2); // Fail twice, then succeed
        let retry = RetryWrapper::new(
            mock,
            RetryConfig {
                max_retries: 5,
                initial_backoff: Duration::from_millis(10),
                max_backoff: Duration::from_millis(100),
                backoff_multiplier: 2.0,
            },
        );

        let filters = SearchFilters::default();
        let result = retry.search_jobs(&filters, 10).await;

        assert!(result.is_ok());
        let jobs = result.unwrap();
        assert_eq!(jobs.len(), 1);
    }

    #[tokio::test]
    async fn test_retry_exhausted() {
        let mock = MockScraper::new(10); // Always fail
        let retry = RetryWrapper::new(
            mock,
            RetryConfig {
                max_retries: 3,
                initial_backoff: Duration::from_millis(10),
                max_backoff: Duration::from_millis(100),
                backoff_multiplier: 2.0,
            },
        );

        let filters = SearchFilters::default();
        let result = retry.search_jobs(&filters, 10).await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_retry_immediate_success() {
        let mock = MockScraper::new(0); // Succeed immediately
        let retry = RetryWrapper::with_defaults(mock);

        let filters = SearchFilters::default();
        let result = retry.search_jobs(&filters, 10).await;

        assert!(result.is_ok());
    }
}
