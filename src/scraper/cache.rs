//! Caching layer for job scrapers.
//!
//! This module provides result caching to avoid redundant scraping operations
//! and reduce load on job boards.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, RwLock};
use std::time::{Duration, SystemTime};

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::error::{AtsError, Result};
use crate::scraper::{JobPosting, JobScraper, SearchFilters};

/// Configuration for cache behavior.
#[derive(Debug, Clone)]
pub struct CacheConfig {
    /// Time-to-live for cache entries.
    pub ttl: Duration,
    /// Directory for persistent cache storage.
    pub cache_dir: Option<PathBuf>,
    /// Enable persistent cache (save to disk).
    pub persistent: bool,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            ttl: Duration::from_secs(3600), // 1 hour
            cache_dir: None,
            persistent: false,
        }
    }
}

/// A cached search result.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct CacheEntry {
    jobs: Vec<JobPosting>,
    timestamp_millis: u128,
}

impl CacheEntry {
    fn new(jobs: Vec<JobPosting>) -> Self {
        Self {
            jobs,
            timestamp_millis: SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_millis(),
        }
    }

    fn is_expired(&self, ttl: Duration) -> bool {
        let now = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_millis();
        now - self.timestamp_millis > ttl.as_millis()
    }
}

/// Wrapper that adds caching to any `JobScraper` implementation.
///
/// # Example
///
/// ```rust,no_run
/// use ats_checker::scraper::jobspy::JobSpyScraper;
/// use ats_checker::scraper::cache::{CacheWrapper, CacheConfig};
/// use std::time::Duration;
///
/// let scraper = JobSpyScraper::new("linkedin").unwrap();
/// let config = CacheConfig {
///     ttl: Duration::from_secs(1800), // 30 minutes
///     ..Default::default()
/// };
/// let cached_scraper = CacheWrapper::new(scraper, config);
/// ```
pub struct CacheWrapper<S: JobScraper> {
    inner: S,
    config: CacheConfig,
    cache: Arc<RwLock<HashMap<String, CacheEntry>>>,
}

impl<S: JobScraper> CacheWrapper<S> {
    /// Create a new cache wrapper with the given scraper and config.
    pub fn new(scraper: S, config: CacheConfig) -> Self {
        let mut cache_wrapper = Self {
            inner: scraper,
            config,
            cache: Arc::new(RwLock::new(HashMap::new())),
        };

        // Load cache from disk if persistent
        if cache_wrapper.config.persistent {
            if let Err(e) = cache_wrapper.load_cache() {
                log::warn!("Failed to load cache from disk: {e}");
            }
        }

        cache_wrapper
    }

    /// Create a cache wrapper with default configuration.
    pub fn with_defaults(scraper: S) -> Self {
        Self::new(scraper, CacheConfig::default())
    }

    /// Generate a cache key from filters and `max_results`.
    fn cache_key(&self, filters: &SearchFilters, max_results: i32) -> String {
        let mut hasher = Sha256::new();
        hasher.update(self.inner.name().as_bytes());
        hasher.update(serde_json::to_string(filters).unwrap_or_default().as_bytes());
        hasher.update(max_results.to_string().as_bytes());
        hex::encode(&hasher.finalize()[..16])
    }

    /// Get cached result if available and not expired.
    fn get_cached(&self, key: &str) -> Option<Vec<JobPosting>> {
        let cache = self.cache.read().ok()?;
        let entry = cache.get(key)?;

        if entry.is_expired(self.config.ttl) {
            log::debug!("Cache entry expired for key: {key}");
            return None;
        }

        log::debug!("Cache hit for key: {key}");
        Some(entry.jobs.clone())
    }

    /// Store result in cache.
    fn put_cached(&self, key: String, jobs: Vec<JobPosting>) {
        let entry = CacheEntry::new(jobs);
        if let Ok(mut cache) = self.cache.write() {
            cache.insert(key.clone(), entry);
            log::debug!("Cached result for key: {key}");
        }

        // Save to disk if persistent
        if self.config.persistent {
            if let Err(e) = self.save_cache() {
                log::warn!("Failed to save cache to disk: {e}");
            }
        }
    }

    /// Clear all cached entries.
    pub fn clear_cache(&self) {
        if let Ok(mut cache) = self.cache.write() {
            cache.clear();
            log::info!("Cache cleared for scraper: {}", self.inner.name());
        }
    }

    /// Clear expired entries from cache.
    pub fn clear_expired(&self) {
        if let Ok(mut cache) = self.cache.write() {
            let ttl = self.config.ttl;
            cache.retain(|_, entry| !entry.is_expired(ttl));
            log::debug!("Cleared expired cache entries for: {}", self.inner.name());
        }
    }

    /// Get cache statistics.
    pub fn cache_stats(&self) -> CacheStats {
        let cache = self.cache.read().ok();
        let total_entries = cache.as_ref().map_or(0, |c| c.len());
        let ttl = self.config.ttl;
        let expired = cache
            .as_ref()
            .map_or(0, |c| {
                c.values()
                    .filter(|e| e.is_expired(ttl))
                    .count()
            });

        CacheStats {
            total_entries,
            expired_entries: expired,
            active_entries: total_entries - expired,
        }
    }

    /// Load cache from disk.
    fn load_cache(&mut self) -> Result<()> {
        let cache_path = self.get_cache_file_path()?;

        if !cache_path.exists() {
            return Ok(());
        }

        let content = std::fs::read_to_string(&cache_path)?;
        let loaded: HashMap<String, CacheEntry> = serde_json::from_str(&content)?;

        if let Ok(mut cache) = self.cache.write() {
            *cache = loaded;
            log::info!("Loaded {} cache entries from disk", cache.len());
        }

        Ok(())
    }

    /// Save cache to disk.
    fn save_cache(&self) -> Result<()> {
        let cache_path = self.get_cache_file_path()?;

        // Ensure cache directory exists
        if let Some(parent) = cache_path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let cache = self.cache.read().map_err(|e| AtsError::CacheError {
            message: format!("Failed to read cache: {e}"),
        })?;

        let json = serde_json::to_string_pretty(&*cache)?;
        std::fs::write(&cache_path, json)?;

        log::debug!("Saved {} cache entries to disk", cache.len());
        Ok(())
    }

    /// Get the cache file path.
    fn get_cache_file_path(&self) -> Result<PathBuf> {
        let cache_dir = self.config.cache_dir.as_ref().ok_or_else(|| {
            AtsError::CacheError {
                message: "Cache directory not configured".to_string(),
            }
        })?;

        let filename = format!("scraper_cache_{}.json", self.inner.name());
        Ok(cache_dir.join(filename))
    }
}

/// Cache statistics.
#[derive(Debug, Clone)]
pub struct CacheStats {
    /// Total number of cache entries.
    pub total_entries: usize,
    /// Number of expired cache entries.
    pub expired_entries: usize,
    /// Number of active (non-expired) cache entries.
    pub active_entries: usize,
}

#[async_trait]
impl<S: JobScraper + Send + Sync> JobScraper for CacheWrapper<S> {
    fn name(&self) -> &'static str {
        self.inner.name()
    }

    async fn search_jobs(
        &self,
        filters: &SearchFilters,
        max_results: i32,
    ) -> Result<Vec<JobPosting>> {
        let cache_key = self.cache_key(filters, max_results);

        // Check cache first
        if let Some(cached) = self.get_cached(&cache_key) {
            return Ok(cached);
        }

        // Cache miss - fetch from scraper
        log::debug!("Cache miss for key: {cache_key}");
        let jobs = self.inner.search_jobs(filters, max_results).await?;

        // Store in cache
        self.put_cached(cache_key, jobs.clone());

        Ok(jobs)
    }

    async fn get_job_details(&self, job_url: &str) -> Result<Option<JobPosting>> {
        // For now, don't cache individual job details
        // This could be added later if needed
        self.inner.get_job_details(job_url).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;
    use tempfile::tempdir;

    // Mock scraper that tracks call count
    struct MockScraper {
        call_count: Arc<AtomicU32>,
    }

    impl MockScraper {
        fn new() -> Self {
            Self {
                call_count: Arc::new(AtomicU32::new(0)),
            }
        }

        fn calls(&self) -> u32 {
            self.call_count.load(Ordering::SeqCst)
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
            self.call_count.fetch_add(1, Ordering::SeqCst);
            Ok(vec![JobPosting::new(
                "Test Job",
                "Test Co",
                "Test Loc",
                "Test Desc",
                "http://test.com",
                "mock",
            )])
        }

        async fn get_job_details(&self, _job_url: &str) -> Result<Option<JobPosting>> {
            Ok(None)
        }
    }

    #[tokio::test]
    async fn test_cache_hit() {
        let mock = MockScraper::new();
        let cached = CacheWrapper::with_defaults(mock);

        let filters = SearchFilters::builder().keywords("test").build();

        // First call - cache miss
        let result1 = cached.search_jobs(&filters, 10).await;
        assert!(result1.is_ok());
        assert_eq!(cached.inner.calls(), 1);

        // Second call - cache hit
        let result2 = cached.search_jobs(&filters, 10).await;
        assert!(result2.is_ok());
        assert_eq!(cached.inner.calls(), 1); // Still 1 - didn't call scraper again
    }

    #[tokio::test]
    async fn test_cache_different_filters() {
        let mock = MockScraper::new();
        let cached = CacheWrapper::with_defaults(mock);

        let filters1 = SearchFilters::builder().keywords("test1").build();
        let filters2 = SearchFilters::builder().keywords("test2").build();

        // Different filters should result in different cache keys
        cached.search_jobs(&filters1, 10).await.unwrap();
        cached.search_jobs(&filters2, 10).await.unwrap();

        assert_eq!(cached.inner.calls(), 2);
    }

    #[tokio::test]
    async fn test_cache_expiration() {
        let mock = MockScraper::new();
        let config = CacheConfig {
            ttl: Duration::from_millis(100), // Very short TTL
            ..Default::default()
        };
        let cached = CacheWrapper::new(mock, config);

        let filters = SearchFilters::builder().keywords("test").build();

        // First call
        cached.search_jobs(&filters, 10).await.unwrap();
        assert_eq!(cached.inner.calls(), 1);

        // Wait for expiration
        tokio::time::sleep(Duration::from_millis(150)).await;

        // Second call after expiration - should call scraper again
        cached.search_jobs(&filters, 10).await.unwrap();
        assert_eq!(cached.inner.calls(), 2);
    }

    #[tokio::test]
    async fn test_cache_stats() {
        let mock = MockScraper::new();
        let cached = CacheWrapper::with_defaults(mock);

        let stats1 = cached.cache_stats();
        assert_eq!(stats1.total_entries, 0);

        let filters = SearchFilters::builder().keywords("test").build();
        cached.search_jobs(&filters, 10).await.unwrap();

        let stats2 = cached.cache_stats();
        assert_eq!(stats2.total_entries, 1);
        assert_eq!(stats2.active_entries, 1);
    }

    #[tokio::test]
    async fn test_cache_clear() {
        let mock = MockScraper::new();
        let cached = CacheWrapper::with_defaults(mock);

        let filters = SearchFilters::builder().keywords("test").build();
        cached.search_jobs(&filters, 10).await.unwrap();

        let stats = cached.cache_stats();
        assert_eq!(stats.total_entries, 1);

        cached.clear_cache();

        let stats_after = cached.cache_stats();
        assert_eq!(stats_after.total_entries, 0);
    }

    #[tokio::test]
    async fn test_persistent_cache() {
        let dir = tempdir().unwrap();

        // Create cached scraper with persistence
        {
            let mock = MockScraper::new();
            let config = CacheConfig {
                ttl: Duration::from_secs(3600),
                cache_dir: Some(dir.path().to_path_buf()),
                persistent: true,
            };
            let cached = CacheWrapper::new(mock, config);

            let filters = SearchFilters::builder().keywords("test").build();
            cached.search_jobs(&filters, 10).await.unwrap();
        }

        // Create new instance and verify cache is loaded
        {
            let mock = MockScraper::new();
            let config = CacheConfig {
                ttl: Duration::from_secs(3600),
                cache_dir: Some(dir.path().to_path_buf()),
                persistent: true,
            };
            let cached = CacheWrapper::new(mock, config);

            let stats = cached.cache_stats();
            assert_eq!(stats.total_entries, 1);

            // Should use cached result
            let filters = SearchFilters::builder().keywords("test").build();
            cached.search_jobs(&filters, 10).await.unwrap();
            assert_eq!(cached.inner.calls(), 0); // Didn't call scraper
        }
    }
}
