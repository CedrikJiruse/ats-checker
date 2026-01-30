//! `JobSpy` scraper implementation using subprocess.
//!
//! This module integrates with the Python `JobSpy` library via subprocess
//! to scrape job postings from various sources.

use std::process::Command;
use std::time::Duration;

use async_trait::async_trait;
use serde_json::Value;

use crate::error::{AtsError, Result};
use crate::scraper::{JobPosting, JobScraper, JobSource, SearchFilters};

/// `JobSpy` scraper that executes Python subprocess.
///
/// This scraper calls a Python script that uses the `JobSpy` library
/// to scrape job postings. The results are returned as JSON.
///
/// # Requirements
///
/// - Python 3.x must be installed and available in PATH
/// - `JobSpy` library must be installed: `pip install python-jobspy`
///
/// # Example
///
/// ```rust,no_run
/// use ats_checker::scraper::jobspy::JobSpyScraper;
/// use ats_checker::scraper::{SearchFilters, JobScraper};
///
/// #[tokio::main]
/// async fn main() -> anyhow::Result<()> {
///     let scraper = JobSpyScraper::new("linkedin")?;
///     let filters = SearchFilters::builder()
///         .keywords("rust developer")
///         .location("San Francisco")
///         .build();
///
///     let jobs = scraper.search_jobs(&filters, 50).await?;
///     println!("Found {} jobs", jobs.len());
///     Ok(())
/// }
/// ```
pub struct JobSpyScraper {
    /// The job source to scrape from.
    source: JobSource,
    /// Python executable path (default: "python" or "python3").
    python_exe: String,
    /// Timeout for subprocess execution in seconds.
    timeout_secs: u64,
}

impl JobSpyScraper {
    /// Create a new `JobSpy` scraper for the given source.
    ///
    /// # Arguments
    ///
    /// * `source` - The job source to scrape (e.g., "linkedin", "indeed")
    ///
    /// # Errors
    ///
    /// Returns an error if the source is invalid.
    pub fn new(source: impl AsRef<str>) -> Result<Self> {
        let source: JobSource =
            source
                .as_ref()
                .parse()
                .map_err(|e: String| AtsError::ScraperError {
                    message: e,
                    source: None,
                })?;

        Ok(Self {
            source,
            python_exe: Self::detect_python_exe(),
            timeout_secs: 120, // 2 minute timeout
        })
    }

    /// Create a scraper with custom Python executable.
    #[must_use]
    pub fn with_python_exe(mut self, exe: impl Into<String>) -> Self {
        self.python_exe = exe.into();
        self
    }

    /// Set the timeout for subprocess execution.
    #[must_use]
    pub fn with_timeout(mut self, timeout: Duration) -> Self {
        self.timeout_secs = timeout.as_secs();
        self
    }

    /// Detect available Python executable.
    fn detect_python_exe() -> String {
        // Try python3 first, then python
        if Command::new("python3").arg("--version").output().is_ok() {
            "python3".to_string()
        } else {
            "python".to_string()
        }
    }

    /// Check if Python and `JobSpy` are available.
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - Python executable is not found
    /// - `JobSpy` library is not installed
    pub fn check_dependencies(&self) -> Result<()> {
        // Check Python
        let python_check = Command::new(&self.python_exe)
            .arg("--version")
            .output()
            .map_err(|e| AtsError::ScraperError {
                message: format!("Python not found: {e}"),
                source: Some(Box::new(e)),
            })?;

        if !python_check.status.success() {
            return Err(AtsError::ScraperError {
                message: "Python execution failed".to_string(),
                source: None,
            });
        }

        // Check JobSpy installation
        let jobspy_check = Command::new(&self.python_exe)
            .arg("-c")
            .arg("import jobspy")
            .output()
            .map_err(|e| AtsError::ScraperError {
                message: format!("Failed to check JobSpy: {e}"),
                source: Some(Box::new(e)),
            })?;

        if !jobspy_check.status.success() {
            return Err(AtsError::ScraperError {
                message: "JobSpy library not installed. Install with: pip install python-jobspy"
                    .to_string(),
                source: None,
            });
        }

        Ok(())
    }

    /// Execute the `JobSpy` Python script.
    async fn execute_jobspy_script(
        &self,
        filters: &SearchFilters,
        max_results: i32,
    ) -> Result<Vec<JobPosting>> {
        // Serialize filters to JSON
        let filters_json = serde_json::to_string(filters).map_err(|e| AtsError::ScraperError {
            message: format!("Failed to serialize filters: {e}"),
            source: Some(Box::new(e)),
        })?;

        // Build Python script inline
        let python_script = self.build_python_script(&filters_json, max_results);

        // Execute Python script
        let output = tokio::task::spawn_blocking({
            let python_exe = self.python_exe.clone();
            move || {
                Command::new(python_exe)
                    .arg("-c")
                    .arg(python_script)
                    .output()
            }
        })
        .await
        .map_err(|e| AtsError::ScraperError {
            message: format!("Failed to execute Python subprocess: {e}"),
            source: Some(Box::new(e)),
        })?
        .map_err(|e| AtsError::ScraperError {
            message: format!("Failed to run Python command: {e}"),
            source: Some(Box::new(e)),
        })?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(AtsError::ScraperError {
                message: format!("JobSpy script failed: {stderr}"),
                source: None,
            });
        }

        // Parse JSON output
        let stdout = String::from_utf8_lossy(&output.stdout);
        let json_value: Value =
            serde_json::from_str(&stdout).map_err(|e| AtsError::ScraperError {
                message: format!("Failed to parse JobSpy output: {e}"),
                source: Some(Box::new(e)),
            })?;

        // Convert to JobPosting objects
        self.parse_jobspy_results(&json_value)
    }

    /// Build the inline Python script for scraping.
    fn build_python_script(&self, filters_json: &str, max_results: i32) -> String {
        format!(
            r#"
import json
import sys
from jobspy import scrape_jobs

# Parse filters
filters = json.loads('{filters_json}')

# Extract parameters
site_name = '{source}'
search_term = filters.get('keywords', '')
location = filters.get('location', '')
distance = filters.get('distance_miles')
is_remote = filters.get('remote_only', False)
job_type = filters.get('job_type')
results_wanted = {max_results}
hours_old = None  # Can be added to filters later

# Convert date_posted to hours_old if present
if 'date_posted' in filters and filters['date_posted']:
    date_str = filters['date_posted']
    if date_str.endswith('h'):
        hours_old = int(date_str[:-1])
    elif date_str.endswith('d'):
        hours_old = int(date_str[:-1]) * 24

try:
    # Scrape jobs
    jobs = scrape_jobs(
        site_name=site_name,
        search_term=search_term,
        location=location,
        distance=distance,
        is_remote=is_remote,
        job_type=job_type,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )

    # Convert DataFrame to list of dicts
    if jobs is not None and not jobs.empty:
        jobs_list = jobs.to_dict('records')
        # Output as JSON
        print(json.dumps(jobs_list, default=str))
    else:
        print("[]")

except Exception as e:
    print(f"Error: {{{{e}}}}", file=sys.stderr)
    sys.exit(1)
"#,
            filters_json = filters_json.replace('\'', "\\'"),
            source = self.source.as_str(),
            max_results = max_results
        )
    }

    /// Parse `JobSpy` results from JSON into `JobPosting` objects.
    fn parse_jobspy_results(&self, json_value: &Value) -> Result<Vec<JobPosting>> {
        let jobs_array = json_value
            .as_array()
            .ok_or_else(|| AtsError::ScraperError {
                message: "Expected JSON array from JobSpy".to_string(),
                source: None,
            })?;

        let mut results = Vec::new();

        for job_obj in jobs_array {
            // Extract fields from JobSpy output
            let title = job_obj
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let company = job_obj
                .get("company")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let location = job_obj
                .get("location")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let description = job_obj
                .get("description")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let url = job_obj
                .get("job_url")
                .or_else(|| job_obj.get("url"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();

            // Optional fields
            let posted_date = job_obj
                .get("date_posted")
                .and_then(|v| v.as_str())
                .map(String::from);
            let salary = job_obj
                .get("compensation")
                .or_else(|| job_obj.get("salary"))
                .and_then(|v| v.as_str())
                .map(String::from);
            let job_type = job_obj
                .get("job_type")
                .and_then(|v| v.as_str())
                .map(String::from);
            let is_remote = job_obj
                .get("is_remote")
                .and_then(serde_json::Value::as_bool)
                .or_else(|| job_obj.get("remote").and_then(serde_json::Value::as_bool));
            let experience_level = job_obj
                .get("experience_level")
                .or_else(|| job_obj.get("seniority_level"))
                .and_then(|v| v.as_str())
                .map(String::from);

            // Build JobPosting
            let mut job = JobPosting::new(
                title,
                company,
                location,
                description,
                url,
                self.source.as_str(),
            );

            if let Some(date) = posted_date {
                job = job.with_posted_date(date);
            }
            if let Some(sal) = salary {
                job = job.with_salary(sal);
            }
            if let Some(jt) = job_type {
                job = job.with_job_type(jt);
            }
            if let Some(remote) = is_remote {
                job = job.with_remote(remote);
            }
            if let Some(level) = experience_level {
                job = job.with_experience_level(level);
            }

            results.push(job);
        }

        Ok(results)
    }
}

#[async_trait]
impl JobScraper for JobSpyScraper {
    fn name(&self) -> &'static str {
        self.source.as_str()
    }

    async fn search_jobs(
        &self,
        filters: &SearchFilters,
        max_results: i32,
    ) -> Result<Vec<JobPosting>> {
        self.execute_jobspy_script(filters, max_results).await
    }

    async fn get_job_details(&self, _job_url: &str) -> Result<Option<JobPosting>> {
        // JobSpy doesn't support fetching individual job details
        // This would require a separate implementation
        Ok(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_jobspy_scraper_creation() {
        let scraper = JobSpyScraper::new("linkedin");
        assert!(scraper.is_ok());

        let scraper = scraper.unwrap();
        assert_eq!(scraper.name(), "linkedin");
    }

    #[test]
    fn test_invalid_source() {
        let scraper = JobSpyScraper::new("invalid_source");
        assert!(scraper.is_err());
    }

    #[test]
    fn test_python_detection() {
        let python = JobSpyScraper::detect_python_exe();
        assert!(python == "python" || python == "python3");
    }

    #[tokio::test]
    async fn test_parse_jobspy_results() {
        let scraper = JobSpyScraper::new("linkedin").unwrap();

        let json_str = r#"[
            {
                "title": "Software Engineer",
                "company": "Acme Inc",
                "location": "San Francisco, CA",
                "description": "Great opportunity",
                "job_url": "https://example.com/job/123",
                "date_posted": "2024-01-15",
                "compensation": "$100k-$150k",
                "job_type": "full-time",
                "is_remote": true
            }
        ]"#;

        let json_value: Value = serde_json::from_str(json_str).unwrap();
        let jobs = scraper.parse_jobspy_results(&json_value).unwrap();

        assert_eq!(jobs.len(), 1);
        assert_eq!(jobs[0].title, "Software Engineer");
        assert_eq!(jobs[0].company, "Acme Inc");
        assert_eq!(jobs[0].source, "linkedin");
        assert!(jobs[0].is_remote());
    }

    #[test]
    fn test_build_python_script() {
        let scraper = JobSpyScraper::new("linkedin").unwrap();
        let filters = SearchFilters::builder()
            .keywords("rust developer")
            .location("Remote")
            .build();
        let filters_json = serde_json::to_string(&filters).unwrap();

        let script = scraper.build_python_script(&filters_json, 50);

        assert!(script.contains("from jobspy import scrape_jobs"));
        assert!(script.contains("linkedin"));
        assert!(script.contains("50"));
    }
}
