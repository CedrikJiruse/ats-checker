//! Core types for job scraping.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Represents a scraped job posting.
///
/// This struct contains all the information about a job posting that was
/// scraped from a job board.
///
/// # Example
///
/// ```rust
/// use ats_checker::scraper::JobPosting;
///
/// let job = JobPosting::new(
///     "Software Engineer",
///     "Acme Inc",
///     "San Francisco, CA",
///     "We are looking for a talented engineer...",
///     "https://example.com/job/123",
///     "linkedin",
/// );
///
/// assert_eq!(job.title, "Software Engineer");
/// ```
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JobPosting {
    /// Job title.
    pub title: String,

    /// Company name.
    pub company: String,

    /// Job location.
    pub location: String,

    /// Full job description.
    pub description: String,

    /// URL to the job posting.
    pub url: String,

    /// Source where the job was found (e.g., "linkedin", "indeed").
    pub source: String,

    /// Date when the job was posted (if available).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub posted_date: Option<String>,

    /// Salary information (if available).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub salary: Option<String>,

    /// Job type (e.g., "full-time", "part-time", "contract").
    #[serde(skip_serializing_if = "Option::is_none")]
    pub job_type: Option<String>,

    /// Whether the job is remote.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub remote: Option<bool>,

    /// Experience level (e.g., "entry", "mid", "senior").
    #[serde(skip_serializing_if = "Option::is_none")]
    pub experience_level: Option<String>,

    /// Timestamp when the job was scraped.
    pub scraped_at: String,

    /// Optional job score (computed separately).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub job_score: Option<f64>,

    /// Additional metadata.
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl JobPosting {
    /// Create a new job posting with required fields.
    pub fn new(
        title: impl Into<String>,
        company: impl Into<String>,
        location: impl Into<String>,
        description: impl Into<String>,
        url: impl Into<String>,
        source: impl Into<String>,
    ) -> Self {
        Self {
            title: title.into(),
            company: company.into(),
            location: location.into(),
            description: description.into(),
            url: url.into(),
            source: source.into(),
            posted_date: None,
            salary: None,
            job_type: None,
            remote: None,
            experience_level: None,
            scraped_at: Utc::now().to_rfc3339(),
            job_score: None,
            metadata: HashMap::new(),
        }
    }

    /// Set the posted date.
    pub fn with_posted_date(mut self, date: impl Into<String>) -> Self {
        self.posted_date = Some(date.into());
        self
    }

    /// Set the salary information.
    pub fn with_salary(mut self, salary: impl Into<String>) -> Self {
        self.salary = Some(salary.into());
        self
    }

    /// Set the job type.
    pub fn with_job_type(mut self, job_type: impl Into<String>) -> Self {
        self.job_type = Some(job_type.into());
        self
    }

    /// Set whether the job is remote.
    pub fn with_remote(mut self, remote: bool) -> Self {
        self.remote = Some(remote);
        self
    }

    /// Set the experience level.
    pub fn with_experience_level(mut self, level: impl Into<String>) -> Self {
        self.experience_level = Some(level.into());
        self
    }

    /// Set the job score.
    pub fn with_score(mut self, score: f64) -> Self {
        self.job_score = Some(score);
        self
    }

    /// Add metadata.
    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }

    /// Check if this job is remote.
    pub fn is_remote(&self) -> bool {
        self.remote.unwrap_or(false)
    }

    /// Get a unique identifier for this job (based on URL hash).
    pub fn id(&self) -> String {
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        hasher.update(self.url.as_bytes());
        hex::encode(&hasher.finalize()[..8])
    }
}

impl Default for JobPosting {
    fn default() -> Self {
        Self::new("", "", "", "", "", "")
    }
}

/// Filters for job searches.
///
/// Use the builder pattern to construct filters:
///
/// ```rust
/// use ats_checker::scraper::SearchFilters;
///
/// let filters = SearchFilters::builder()
///     .keywords("rust developer")
///     .location("Remote")
///     .remote_only(true)
///     .experience_level(vec!["mid", "senior"])
///     .build();
/// ```
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct SearchFilters {
    /// Keywords to search for.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub keywords: Option<String>,

    /// Location filter.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub location: Option<String>,

    /// Job types to filter by.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub job_type: Option<Vec<String>>,

    /// Whether to only include remote jobs.
    #[serde(default)]
    pub remote_only: bool,

    /// Experience levels to filter by.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub experience_level: Option<Vec<String>>,

    /// Minimum salary filter.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub salary_min: Option<i32>,

    /// Maximum age of job postings (e.g., "24h", "7d", "30d").
    #[serde(skip_serializing_if = "Option::is_none")]
    pub date_posted: Option<String>,

    /// Country code for location filtering.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub country: Option<String>,

    /// Distance from location in miles.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub distance_miles: Option<i32>,
}

impl SearchFilters {
    /// Create a new empty search filters.
    pub fn new() -> Self {
        Self::default()
    }

    /// Create a builder for constructing search filters.
    pub fn builder() -> SearchFiltersBuilder {
        SearchFiltersBuilder::default()
    }

    /// Check if any filters are set.
    pub fn is_empty(&self) -> bool {
        self.keywords.is_none()
            && self.location.is_none()
            && self.job_type.is_none()
            && !self.remote_only
            && self.experience_level.is_none()
            && self.salary_min.is_none()
            && self.date_posted.is_none()
    }
}

/// Builder for [`SearchFilters`].
#[derive(Debug, Clone, Default)]
pub struct SearchFiltersBuilder {
    filters: SearchFilters,
}

impl SearchFiltersBuilder {
    /// Set the keywords to search for.
    pub fn keywords(mut self, keywords: impl Into<String>) -> Self {
        self.filters.keywords = Some(keywords.into());
        self
    }

    /// Set the location filter.
    pub fn location(mut self, location: impl Into<String>) -> Self {
        self.filters.location = Some(location.into());
        self
    }

    /// Set the job types to filter by.
    pub fn job_type(mut self, job_types: Vec<impl Into<String>>) -> Self {
        self.filters.job_type = Some(job_types.into_iter().map(Into::into).collect());
        self
    }

    /// Set whether to only include remote jobs.
    pub fn remote_only(mut self, remote: bool) -> Self {
        self.filters.remote_only = remote;
        self
    }

    /// Set the experience levels to filter by.
    pub fn experience_level(mut self, levels: Vec<impl Into<String>>) -> Self {
        self.filters.experience_level = Some(levels.into_iter().map(Into::into).collect());
        self
    }

    /// Set the minimum salary filter.
    pub fn salary_min(mut self, salary: i32) -> Self {
        self.filters.salary_min = Some(salary);
        self
    }

    /// Set the date posted filter.
    pub fn date_posted(mut self, date_posted: impl Into<String>) -> Self {
        self.filters.date_posted = Some(date_posted.into());
        self
    }

    /// Set the country code.
    pub fn country(mut self, country: impl Into<String>) -> Self {
        self.filters.country = Some(country.into());
        self
    }

    /// Set the distance from location.
    pub fn distance_miles(mut self, distance: i32) -> Self {
        self.filters.distance_miles = Some(distance);
        self
    }

    /// Build the search filters.
    pub fn build(self) -> SearchFilters {
        self.filters
    }
}

/// A saved job search configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SavedSearch {
    /// Name of the saved search.
    pub name: String,

    /// Search filters.
    pub filters: SearchFilters,

    /// Sources to search.
    pub sources: Vec<String>,

    /// Maximum number of results.
    #[serde(default = "default_max_results")]
    pub max_results: i32,

    /// When the search was created.
    pub created_at: String,

    /// When the search was last run.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_run: Option<String>,
}

fn default_max_results() -> i32 {
    50
}

impl SavedSearch {
    /// Create a new saved search.
    pub fn new(name: impl Into<String>, filters: SearchFilters, sources: Vec<String>) -> Self {
        Self {
            name: name.into(),
            filters,
            sources,
            max_results: 50,
            created_at: Utc::now().to_rfc3339(),
            last_run: None,
        }
    }

    /// Set the maximum number of results.
    pub fn with_max_results(mut self, max: i32) -> Self {
        self.max_results = max;
        self
    }

    /// Update the last run timestamp.
    pub fn update_last_run(&mut self) {
        self.last_run = Some(Utc::now().to_rfc3339());
    }
}

/// Job sources supported by the scraper.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum JobSource {
    /// LinkedIn Jobs
    LinkedIn,
    /// Indeed
    Indeed,
    /// Glassdoor
    Glassdoor,
    /// Google Jobs
    Google,
    /// ZipRecruiter
    ZipRecruiter,
}

impl JobSource {
    /// Get all available job sources.
    pub fn all() -> &'static [JobSource] {
        &[
            JobSource::LinkedIn,
            JobSource::Indeed,
            JobSource::Glassdoor,
            JobSource::Google,
            JobSource::ZipRecruiter,
        ]
    }

    /// Get the string name of this source.
    pub fn as_str(&self) -> &'static str {
        match self {
            JobSource::LinkedIn => "linkedin",
            JobSource::Indeed => "indeed",
            JobSource::Glassdoor => "glassdoor",
            JobSource::Google => "google",
            JobSource::ZipRecruiter => "ziprecruiter",
        }
    }
}

impl std::fmt::Display for JobSource {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl std::str::FromStr for JobSource {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "linkedin" => Ok(JobSource::LinkedIn),
            "indeed" => Ok(JobSource::Indeed),
            "glassdoor" => Ok(JobSource::Glassdoor),
            "google" => Ok(JobSource::Google),
            "ziprecruiter" => Ok(JobSource::ZipRecruiter),
            _ => Err(format!("Unknown job source: {}", s)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_job_posting_creation() {
        let job = JobPosting::new(
            "Software Engineer",
            "Acme Inc",
            "San Francisco, CA",
            "Job description here",
            "https://example.com/job/123",
            "linkedin",
        );

        assert_eq!(job.title, "Software Engineer");
        assert_eq!(job.company, "Acme Inc");
        assert_eq!(job.source, "linkedin");
        assert!(!job.scraped_at.is_empty());
    }

    #[test]
    fn test_job_posting_builder_pattern() {
        let job = JobPosting::new("Engineer", "Company", "Location", "Desc", "url", "indeed")
            .with_salary("$100k-$150k")
            .with_remote(true)
            .with_job_type("full-time")
            .with_experience_level("senior");

        assert_eq!(job.salary, Some("$100k-$150k".to_string()));
        assert!(job.is_remote());
        assert_eq!(job.job_type, Some("full-time".to_string()));
        assert_eq!(job.experience_level, Some("senior".to_string()));
    }

    #[test]
    fn test_search_filters_builder() {
        let filters = SearchFilters::builder()
            .keywords("rust developer")
            .location("San Francisco")
            .remote_only(true)
            .salary_min(100000)
            .build();

        assert_eq!(filters.keywords, Some("rust developer".to_string()));
        assert_eq!(filters.location, Some("San Francisco".to_string()));
        assert!(filters.remote_only);
        assert_eq!(filters.salary_min, Some(100000));
    }

    #[test]
    fn test_search_filters_is_empty() {
        let empty = SearchFilters::new();
        assert!(empty.is_empty());

        let with_keywords = SearchFilters::builder().keywords("test").build();
        assert!(!with_keywords.is_empty());
    }

    #[test]
    fn test_job_source_parsing() {
        assert_eq!(
            "linkedin".parse::<JobSource>().unwrap(),
            JobSource::LinkedIn
        );
        assert_eq!("INDEED".parse::<JobSource>().unwrap(), JobSource::Indeed);
        assert!("unknown".parse::<JobSource>().is_err());
    }

    #[test]
    fn test_saved_search() {
        let filters = SearchFilters::builder().keywords("test").build();
        let search = SavedSearch::new("My Search", filters, vec!["linkedin".to_string()]);

        assert_eq!(search.name, "My Search");
        assert_eq!(search.max_results, 50);
        assert!(search.last_run.is_none());
    }

    #[test]
    fn test_job_posting_serialization() {
        let job = JobPosting::new("Title", "Company", "Location", "Desc", "url", "source");
        let json = serde_json::to_string(&job).unwrap();
        let parsed: JobPosting = serde_json::from_str(&json).unwrap();
        assert_eq!(job.title, parsed.title);
    }
}
