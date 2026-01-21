//! Job scraper manager implementation.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use crate::error::{AtsError, Result};
use crate::scraper::{JobPosting, JobScraper, SearchFilters};

/// Manages job scraping across multiple sources.
///
/// The manager coordinates searching across multiple job sources,
/// deduplicates results, and handles result persistence.
pub struct JobScraperManager {
    /// Directory for storing results.
    results_folder: PathBuf,
    /// Path to saved searches file.
    saved_searches_path: PathBuf,
    /// Registered scrapers.
    scrapers: HashMap<String, Box<dyn JobScraper>>,
}

impl JobScraperManager {
    /// Create a new job scraper manager.
    ///
    /// # Arguments
    ///
    /// * `results_folder` - Directory for storing search results
    /// * `saved_searches_path` - Path to the saved searches TOML file
    ///
    /// # Errors
    ///
    /// Returns an error if the results folder cannot be created.
    pub fn new(
        results_folder: impl AsRef<Path>,
        saved_searches_path: impl AsRef<Path>,
    ) -> Result<Self> {
        let results_folder = results_folder.as_ref().to_path_buf();
        let saved_searches_path = saved_searches_path.as_ref().to_path_buf();

        // Ensure results folder exists
        if !results_folder.exists() {
            std::fs::create_dir_all(&results_folder).map_err(|e| AtsError::DirectoryCreation {
                path: results_folder.clone(),
                source: e,
            })?;
        }

        Ok(Self {
            results_folder,
            saved_searches_path,
            scrapers: HashMap::new(),
        })
    }

    /// Register a job scraper.
    pub fn register_scraper(&mut self, scraper: Box<dyn JobScraper>) {
        let name = scraper.name().to_string();
        self.scrapers.insert(name, scraper);
    }

    /// Get the list of registered scraper names.
    pub fn available_sources(&self) -> Vec<&str> {
        self.scrapers.keys().map(String::as_str).collect()
    }

    /// Search for jobs across multiple sources.
    ///
    /// # Arguments
    ///
    /// * `filters` - Search filters to apply
    /// * `sources` - List of source names to search
    /// * `max_results` - Maximum number of results per source
    ///
    /// # Returns
    ///
    /// A vector of job postings, deduplicated by URL.
    pub async fn search_jobs(
        &self,
        filters: &SearchFilters,
        sources: &[&str],
        max_results: i32,
    ) -> Result<Vec<JobPosting>> {
        let mut all_jobs = Vec::new();
        let mut seen_urls = std::collections::HashSet::new();

        for source in sources {
            if let Some(scraper) = self.scrapers.get(*source) {
                match scraper.search_jobs(filters, max_results).await {
                    Ok(jobs) => {
                        for job in jobs {
                            if seen_urls.insert(job.url.clone()) {
                                all_jobs.push(job);
                            }
                        }
                    }
                    Err(e) => {
                        log::warn!("Failed to search {}: {}", source, e);
                    }
                }
            } else {
                log::warn!("Unknown job source: {}", source);
            }
        }

        Ok(all_jobs)
    }

    /// Save job search results to a file.
    ///
    /// # Arguments
    ///
    /// * `results` - Job postings to save
    /// * `filename` - Name of the output file (relative to results folder)
    ///
    /// # Returns
    ///
    /// The full path to the saved file.
    pub fn save_results(&self, results: &[JobPosting], filename: &str) -> Result<PathBuf> {
        let path = self.results_folder.join(filename);

        // Determine format from extension
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("toml");

        match ext {
            "json" => {
                let json = serde_json::to_string_pretty(results)?;
                std::fs::write(&path, json)?;
            }
            _ => {
                // Default to TOML
                let wrapper = ResultsWrapper {
                    jobs: results.to_vec(),
                };
                let toml_str =
                    toml::to_string_pretty(&wrapper).map_err(|e| AtsError::TomlParse {
                        message: e.to_string(),
                        source: None,
                    })?;
                std::fs::write(&path, toml_str)?;
            }
        }

        Ok(path)
    }

    /// Load job search results from a file.
    pub fn load_results(&self, path: impl AsRef<Path>) -> Result<Vec<JobPosting>> {
        let path = path.as_ref();
        let content = std::fs::read_to_string(path)?;

        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("toml");

        match ext {
            "json" => {
                let jobs: Vec<JobPosting> = serde_json::from_str(&content)?;
                Ok(jobs)
            }
            _ => {
                let wrapper: ResultsWrapper = toml::from_str(&content)?;
                Ok(wrapper.jobs)
            }
        }
    }

    /// Rank jobs in a results file by job score.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to the results file
    /// * `top_n` - Number of top results to return
    /// * `recompute_missing` - Whether to compute scores for jobs without scores
    ///
    /// # Returns
    ///
    /// A vector of ranked job entries.
    pub fn rank_jobs_in_results(
        &self,
        path: impl AsRef<Path>,
        top_n: i32,
        recompute_missing: bool,
    ) -> Result<Vec<RankedJob>> {
        let mut jobs = self.load_results(path)?;

        // Sort by score (descending)
        jobs.sort_by(|a, b| {
            let score_a = a.job_score.unwrap_or(0.0);
            let score_b = b.job_score.unwrap_or(0.0);
            score_b
                .partial_cmp(&score_a)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Take top N and add ranks
        let ranked: Vec<RankedJob> = jobs
            .into_iter()
            .take(top_n as usize)
            .enumerate()
            .map(|(i, job)| RankedJob {
                rank: (i + 1) as i32,
                job_score: job.job_score,
                job,
            })
            .collect();

        Ok(ranked)
    }

    /// Export top-scored jobs to individual job description files.
    ///
    /// # Arguments
    ///
    /// * `jobs` - Job postings to export
    /// * `folder` - Destination folder for job description files
    ///
    /// # Returns
    ///
    /// The number of jobs exported.
    pub fn export_to_job_descriptions(
        &self,
        jobs: &[JobPosting],
        folder: impl AsRef<Path>,
    ) -> Result<i32> {
        let folder = folder.as_ref();
        std::fs::create_dir_all(folder)?;

        let mut count = 0;
        for job in jobs {
            // Create safe filename
            let safe_title = job
                .title
                .replace(|c: char| !c.is_alphanumeric() && c != ' ', "");
            let safe_company = job
                .company
                .replace(|c: char| !c.is_alphanumeric() && c != ' ', "");
            let filename = format!("{}_{}.txt", safe_title, safe_company)
                .replace("  ", " ")
                .replace(' ', "_");

            let path = folder.join(&filename);

            // Format job description content
            let content = format!(
                "Title: {}\nCompany: {}\nLocation: {}\nURL: {}\n\n---\n\n{}",
                job.title, job.company, job.location, job.url, job.description
            );

            std::fs::write(&path, content)?;
            count += 1;
        }

        Ok(count)
    }

    /// Get the results folder path.
    pub fn results_folder(&self) -> &Path {
        &self.results_folder
    }

    /// Get the saved searches file path.
    pub fn saved_searches_path(&self) -> &Path {
        &self.saved_searches_path
    }
}

/// Wrapper for TOML serialization of job results.
#[derive(Debug, Serialize, Deserialize)]
struct ResultsWrapper {
    jobs: Vec<JobPosting>,
}

use serde::{Deserialize, Serialize};

/// A ranked job entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RankedJob {
    /// Rank (1-based).
    pub rank: i32,
    /// Job score (if available).
    pub job_score: Option<f64>,
    /// The job posting.
    pub job: JobPosting,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_manager_creation() {
        let dir = tempdir().unwrap();
        let results = dir.path().join("results");
        let saved = dir.path().join("saved.toml");

        let manager = JobScraperManager::new(&results, &saved).unwrap();
        assert!(results.exists());
        assert!(manager.available_sources().is_empty());
    }

    #[test]
    fn test_save_and_load_results() {
        let dir = tempdir().unwrap();
        let manager =
            JobScraperManager::new(dir.path().join("results"), dir.path().join("saved.toml"))
                .unwrap();

        let jobs = vec![
            JobPosting::new("Engineer", "Co", "SF", "Desc", "url1", "linkedin"),
            JobPosting::new("Developer", "Inc", "NY", "Desc2", "url2", "indeed"),
        ];

        let path = manager.save_results(&jobs, "test.toml").unwrap();
        let loaded = manager.load_results(&path).unwrap();

        assert_eq!(loaded.len(), 2);
        assert_eq!(loaded[0].title, "Engineer");
    }

    #[test]
    fn test_rank_jobs() {
        let dir = tempdir().unwrap();
        let manager =
            JobScraperManager::new(dir.path().join("results"), dir.path().join("saved.toml"))
                .unwrap();

        let jobs = vec![
            JobPosting::new("A", "Co", "SF", "Desc", "url1", "src").with_score(50.0),
            JobPosting::new("B", "Co", "SF", "Desc", "url2", "src").with_score(80.0),
            JobPosting::new("C", "Co", "SF", "Desc", "url3", "src").with_score(65.0),
        ];

        let path = manager.save_results(&jobs, "rank_test.toml").unwrap();
        let ranked = manager.rank_jobs_in_results(&path, 2, false).unwrap();

        assert_eq!(ranked.len(), 2);
        assert_eq!(ranked[0].job.title, "B"); // Highest score
        assert_eq!(ranked[0].rank, 1);
        assert_eq!(ranked[1].job.title, "C"); // Second highest
    }
}
