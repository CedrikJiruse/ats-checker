//! Scoring module for resume, job, and match scoring.
//!
//! This module provides multi-dimensional scoring for resumes, job postings,
//! and the match between them. All scoring is deterministic and does not
//! call external services.
//!
//! # Scoring Categories
//!
//! ## Resume Score (0-100)
//! - **completeness**: Has required fields (name, email, experience, etc.)
//! - **`skills_quality`**: Quality and quantity of skills listed
//! - **`experience_quality`**: Quality of experience bullets (action verbs, quantification)
//! - **impact**: Quantification and outcome-focused language
//!
//! ## Job Score (0-100)
//! - **completeness**: Has required fields (title, company, description, etc.)
//! - **clarity**: Description length and structure
//! - **`compensation_transparency`**: Salary information present
//! - **`link_quality`**: Valid URL present
//!
//! ## Match Score (0-100)
//! - **`keyword_overlap`**: Keywords from job found in resume
//! - **`skills_overlap`**: Skills from resume found in job description
//! - **`role_alignment`**: Job title matches resume titles
//!
//! # Example
//!
//! ```rust,no_run
//! use ats_checker::scoring;
//! use serde_json::json;
//!
//! # fn main() -> Result<(), Box<dyn std::error::Error>> {
//! let resume = json!({
//!     "personal_info": {"name": "John Doe", "email": "john@example.com"},
//!     "experience": [{"title": "Engineer", "description": ["Built systems"]}],
//!     "skills": ["Rust", "Python"]
//! });
//!
//! let report = scoring::score_resume(&resume, Some("config/scoring_weights.toml"))?;
//! println!("Resume score: {}", report.total);
//! # Ok(())
//! # }
//! ```

use crate::error::Result;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::Path;

// -------------------------
// Data Structures
// -------------------------

/// A single category score with details.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ScoreCategoryResult {
    /// Category name (e.g., "completeness", "`skills_quality`")
    pub name: String,
    /// Score for this category (0-100)
    pub score: f64,
    /// Normalized weight for this category (0-1)
    pub weight: f64,
    /// Additional details about the score
    pub details: HashMap<String, serde_json::Value>,
}

/// A complete score report with category breakdowns.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ScoreReport {
    /// Report kind: "resume", "job", or "match"
    pub kind: String,
    /// Weighted total score (0-100)
    pub total: f64,
    /// Category scores
    pub categories: Vec<ScoreCategoryResult>,
    /// Metadata about the scoring
    pub meta: HashMap<String, serde_json::Value>,
}

impl ScoreReport {
    /// Convert to a JSON value.
    pub fn as_dict(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

// -------------------------
// Default Weights
// -------------------------

/// Default weights for resume scoring categories.
fn default_resume_weights() -> HashMap<String, f64> {
    let mut weights = HashMap::new();
    weights.insert("completeness".to_string(), 0.30);
    weights.insert("skills_quality".to_string(), 0.20);
    weights.insert("experience_quality".to_string(), 0.30);
    weights.insert("impact".to_string(), 0.20);
    weights
}

/// Default weights for job scoring categories.
fn default_job_weights() -> HashMap<String, f64> {
    let mut weights = HashMap::new();
    weights.insert("completeness".to_string(), 0.35);
    weights.insert("clarity".to_string(), 0.35);
    weights.insert("compensation_transparency".to_string(), 0.15);
    weights.insert("link_quality".to_string(), 0.15);
    weights
}

/// Default weights for match scoring categories.
fn default_match_weights() -> HashMap<String, f64> {
    let mut weights = HashMap::new();
    weights.insert("keyword_overlap".to_string(), 0.45);
    weights.insert("skills_overlap".to_string(), 0.35);
    weights.insert("role_alignment".to_string(), 0.20);
    weights
}

/// Default weights for combining resume and match scores into iteration score.
fn default_overall_iteration_weights() -> HashMap<String, f64> {
    let mut weights = HashMap::new();
    weights.insert("resume".to_string(), 0.45);
    weights.insert("match".to_string(), 0.55);
    weights
}

// -------------------------
// Weight Loading & Normalization
// -------------------------

/// Load scoring weights from a TOML file.
///
/// Expected format:
/// ```toml
/// [resume.weights]
/// completeness = 0.30
/// skills_quality = 0.20
///
/// [job.weights]
/// completeness = 0.35
///
/// [match.weights]
/// keyword_overlap = 0.45
/// ```
pub fn load_scoring_weights(weights_path: Option<&str>) -> HashMap<String, HashMap<String, f64>> {
    let mut all_weights = HashMap::new();
    all_weights.insert("resume".to_string(), default_resume_weights());
    all_weights.insert("job".to_string(), default_job_weights());
    all_weights.insert("match".to_string(), default_match_weights());

    let Some(path) = weights_path else {
        return all_weights;
    };

    if !Path::new(path).exists() {
        return all_weights;
    }

    // Try to load and parse TOML
    let Ok(content) = std::fs::read_to_string(path) else {
        return all_weights;
    };

    let Ok(doc) = toml::from_str::<toml::Value>(&content) else {
        return all_weights;
    };

    // Parse weights for each group
    for group in ["resume", "job", "match"] {
        if let Some(group_table) = doc.get(group).and_then(|v| v.as_table()) {
            // Try [group.weights] first, fallback to [group]
            let weights_table = group_table
                .get("weights")
                .or_else(|| group_table.get("weight"))
                .and_then(|v| v.as_table())
                .unwrap_or(group_table);

            let mut parsed = HashMap::new();
            for (key, value) in weights_table {
                if let Some(weight) = value
                    .as_float()
                    .or_else(|| value.as_integer().map(|i| i as f64))
                {
                    parsed.insert(key.clone(), weight);
                }
            }

            if !parsed.is_empty() {
                if let Some(group_weights) = all_weights.get_mut(group) {
                    group_weights.extend(parsed);
                }
            }
        }
    }

    all_weights
}

/// Load overall iteration weights from TOML file.
pub fn load_overall_iteration_weights(weights_path: Option<&str>) -> HashMap<String, f64> {
    let mut weights = default_overall_iteration_weights();

    let Some(path) = weights_path else {
        return weights;
    };

    if !Path::new(path).exists() {
        return weights;
    }

    let Ok(content) = std::fs::read_to_string(path) else {
        return weights;
    };

    let Ok(doc) = toml::from_str::<toml::Value>(&content) else {
        return weights;
    };

    if let Some(overall) = doc.get("overall").and_then(|v| v.as_table()) {
        let weights_table = overall
            .get("weights")
            .or_else(|| overall.get("weight"))
            .and_then(|v| v.as_table())
            .unwrap_or(overall);

        for key in ["resume", "match"] {
            if let Some(value) = weights_table.get(key) {
                if let Some(weight) = value
                    .as_float()
                    .or_else(|| value.as_integer().map(|i| i as f64))
                {
                    weights.insert(key.to_string(), weight);
                }
            }
        }
    }

    weights
}

/// Normalize weights to sum to 1.0.
///
/// Ignores non-positive weights. If all weights are <= 0, returns 0 for all.
pub fn normalize_weights<S: std::hash::BuildHasher>(
    weights: &HashMap<String, f64, S>,
) -> HashMap<String, f64> {
    let positive: HashMap<String, f64> = weights
        .iter()
        .filter(|(_, &v)| v > 0.0)
        .map(|(k, &v)| (k.clone(), v))
        .collect();

    let sum: f64 = positive.values().sum();

    if sum <= 0.0 {
        return weights.keys().map(|k| (k.clone(), 0.0)).collect();
    }

    weights
        .keys()
        .map(|k| (k.clone(), positive.get(k).copied().unwrap_or(0.0) / sum))
        .collect()
}

/// Compute iteration score from resume and match reports.
///
/// Combines resume quality score and match score into a single score
/// used to drive iterative improvement loops.
pub fn compute_iteration_score(
    resume_report: &ScoreReport,
    match_report: &ScoreReport,
    weights_path: Option<&str>,
) -> (f64, HashMap<String, serde_json::Value>) {
    let raw_weights = load_overall_iteration_weights(weights_path);
    let normalized = normalize_weights(&raw_weights);

    let resume_weight = normalized.get("resume").copied().unwrap_or(0.0);
    let match_weight = normalized.get("match").copied().unwrap_or(0.0);

    // Fallback to mean if no weights configured
    let score = if resume_weight + match_weight <= 0.0 {
        f64::midpoint(resume_report.total, match_report.total)
    } else {
        (resume_report.total * resume_weight) + (match_report.total * match_weight)
    };

    let mut details = HashMap::new();
    details.insert(
        "resume_total".to_string(),
        serde_json::json!(resume_report.total),
    );
    details.insert(
        "match_total".to_string(),
        serde_json::json!(match_report.total),
    );
    details.insert("weights".to_string(), serde_json::json!(normalized));
    details.insert("raw_weights".to_string(), serde_json::json!(raw_weights));

    (clamp(score, 0.0, 100.0), details)
}

// -------------------------
// Resume Scoring
// -------------------------

/// Score a resume across multiple quality categories.
///
/// Returns a `ScoreReport` with weighted total (0-100) and category breakdowns.
///
/// # Errors
///
/// Returns an error if the weights file cannot be loaded or parsed.
pub fn score_resume(resume: &serde_json::Value, weights_path: Option<&str>) -> Result<ScoreReport> {
    let all_weights = load_scoring_weights(weights_path);
    let resume_weights = all_weights
        .get("resume")
        .cloned()
        .unwrap_or_else(default_resume_weights);
    let normalized = normalize_weights(&resume_weights);

    let (completeness_score, completeness_details) = score_resume_completeness(resume);
    let (skills_score, skills_details) = score_resume_skills_quality(resume);
    let (exp_score, exp_details) = score_resume_experience_quality(resume);
    let (impact_score, impact_details) = score_resume_impact(resume);

    let categories = vec![
        ScoreCategoryResult {
            name: "completeness".to_string(),
            score: completeness_score,
            weight: *normalized.get("completeness").unwrap_or(&0.0),
            details: completeness_details,
        },
        ScoreCategoryResult {
            name: "skills_quality".to_string(),
            score: skills_score,
            weight: *normalized.get("skills_quality").unwrap_or(&0.0),
            details: skills_details,
        },
        ScoreCategoryResult {
            name: "experience_quality".to_string(),
            score: exp_score,
            weight: *normalized.get("experience_quality").unwrap_or(&0.0),
            details: exp_details,
        },
        ScoreCategoryResult {
            name: "impact".to_string(),
            score: impact_score,
            weight: *normalized.get("impact").unwrap_or(&0.0),
            details: impact_details,
        },
    ];

    let total = weighted_total(&categories);

    let mut meta = HashMap::new();
    if let Some(path) = weights_path {
        meta.insert(
            "weights_source".to_string(),
            serde_json::json!(std::fs::canonicalize(path).ok()),
        );
    }

    Ok(ScoreReport {
        kind: "resume".to_string(),
        total,
        categories,
        meta,
    })
}

fn score_resume_completeness(
    resume: &serde_json::Value,
) -> (f64, HashMap<String, serde_json::Value>) {
    let personal = resume.get("personal_info").and_then(|v| v.as_object());
    let summary = resume.get("summary").and_then(|v| v.as_str()).unwrap_or("");
    let exp = resume
        .get("experience")
        .and_then(|v| v.as_array())
        .map_or(0, std::vec::Vec::len);
    let edu = resume
        .get("education")
        .and_then(|v| v.as_array())
        .map_or(0, std::vec::Vec::len);
    let skills = resume
        .get("skills")
        .and_then(|v| v.as_array())
        .map_or(0, std::vec::Vec::len);
    let projects = resume
        .get("projects")
        .and_then(|v| v.as_array())
        .map_or(0, std::vec::Vec::len);

    let has_name = personal
        .and_then(|p| p.get("name"))
        .and_then(|v| v.as_str())
        .is_some_and(|s| !s.trim().is_empty());

    let has_email = personal
        .and_then(|p| p.get("email"))
        .and_then(|v| v.as_str())
        .is_some_and(|s| !s.trim().is_empty());

    let has_summary = !summary.trim().is_empty();
    let has_experience = exp > 0;
    let has_education = edu > 0;
    let has_skills = skills > 0;
    let has_projects = projects > 0;

    // Weighted checklist
    let weights = [
        (has_name, 0.10),
        (has_email, 0.10),
        (has_summary, 0.15),
        (has_experience, 0.25),
        (has_education, 0.15),
        (has_skills, 0.20),
        (has_projects, 0.05),
    ];

    let score = weights
        .iter()
        .map(|(check, weight)| if *check { weight } else { &0.0 })
        .sum::<f64>()
        * 100.0;

    let mut details = HashMap::new();
    details.insert("has_name".to_string(), serde_json::json!(has_name));
    details.insert("has_email".to_string(), serde_json::json!(has_email));
    details.insert("has_summary".to_string(), serde_json::json!(has_summary));
    details.insert(
        "has_experience".to_string(),
        serde_json::json!(has_experience),
    );
    details.insert(
        "has_education".to_string(),
        serde_json::json!(has_education),
    );
    details.insert("has_skills".to_string(), serde_json::json!(has_skills));
    details.insert("has_projects".to_string(), serde_json::json!(has_projects));
    details.insert("experience_count".to_string(), serde_json::json!(exp));
    details.insert("education_count".to_string(), serde_json::json!(edu));
    details.insert("skills_count".to_string(), serde_json::json!(skills));
    details.insert("projects_count".to_string(), serde_json::json!(projects));

    (clamp(score, 0.0, 100.0), details)
}

fn score_resume_skills_quality(
    resume: &serde_json::Value,
) -> (f64, HashMap<String, serde_json::Value>) {
    let skills = resume
        .get("skills")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let unique: HashSet<String> = skills.iter().map(|s| s.to_lowercase()).collect();
    let count = unique.len();

    // Heuristics: saturates at 12 skills
    let count_score = 100.0 * (count as f64 / 12.0).min(1.0);

    // Penalize overly long skill strings (likely sentences, not skills)
    let too_long = skills.iter().filter(|s| s.len() > 32).count();
    let long_penalty = (too_long as f64 * 7.5).min(30.0);

    let score = count_score - long_penalty;

    let mut details = HashMap::new();
    details.insert("unique_skill_count".to_string(), serde_json::json!(count));
    details.insert("too_long_skills".to_string(), serde_json::json!(too_long));

    (clamp(score, 0.0, 100.0), details)
}

fn score_resume_experience_quality(
    resume: &serde_json::Value,
) -> (f64, HashMap<String, serde_json::Value>) {
    let empty_vec = vec![];
    let exp = resume
        .get("experience")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty_vec);

    if exp.is_empty() {
        let mut details = HashMap::new();
        details.insert(
            "reason".to_string(),
            serde_json::json!("no_experience_entries"),
        );
        return (0.0, details);
    }

    let mut total_bullets = 0;
    let mut action_bullets = 0;
    let mut quantified_bullets = 0;

    for entry in exp {
        let bullets = extract_bullets(entry.get("description"));
        for bullet in bullets {
            total_bullets += 1;
            if looks_like_action_bullet(&bullet) {
                action_bullets += 1;
            }
            if contains_number(&bullet) {
                quantified_bullets += 1;
            }
        }
    }

    if total_bullets == 0 {
        let mut details = HashMap::new();
        details.insert(
            "reason".to_string(),
            serde_json::json!("experience_without_bullets"),
        );
        return (15.0, details);
    }

    // Scoring: bullet volume (saturates at 10), action verb ratio, quantified ratio
    let vol = (f64::from(total_bullets) / 10.0).min(1.0) * 35.0;
    let action_ratio = f64::from(action_bullets) / f64::from(total_bullets);
    let action = action_ratio * 35.0;
    let quant_ratio = f64::from(quantified_bullets) / f64::from(total_bullets);
    let quant = quant_ratio * 30.0;

    let score = vol + action + quant;

    let mut details = HashMap::new();
    details.insert(
        "total_bullets".to_string(),
        serde_json::json!(total_bullets),
    );
    details.insert(
        "action_bullets".to_string(),
        serde_json::json!(action_bullets),
    );
    details.insert(
        "quantified_bullets".to_string(),
        serde_json::json!(quantified_bullets),
    );
    details.insert("action_ratio".to_string(), serde_json::json!(action_ratio));
    details.insert(
        "quantified_ratio".to_string(),
        serde_json::json!(quant_ratio),
    );

    (clamp(score, 0.0, 100.0), details)
}

fn score_resume_impact(resume: &serde_json::Value) -> (f64, HashMap<String, serde_json::Value>) {
    let empty_vec = vec![];
    let exp = resume
        .get("experience")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty_vec);

    if exp.is_empty() {
        let mut details = HashMap::new();
        details.insert(
            "reason".to_string(),
            serde_json::json!("no_experience_entries"),
        );
        return (0.0, details);
    }

    let mut bullets = Vec::new();
    for entry in exp {
        bullets.extend(extract_bullets(entry.get("description")));
    }

    if bullets.is_empty() {
        let mut details = HashMap::new();
        details.insert("reason".to_string(), serde_json::json!("no_bullets"));
        return (10.0, details);
    }

    let quantified = bullets.iter().filter(|b| contains_number(b)).count();
    let outcome = bullets
        .iter()
        .filter(|b| contains_outcome_language(b))
        .count();
    let strong = bullets
        .iter()
        .filter(|b| {
            looks_like_action_bullet(b) && (contains_number(b) || contains_outcome_language(b))
        })
        .count();

    let n = bullets.len() as f64;
    let quantified_ratio = quantified as f64 / n;
    let outcome_ratio = outcome as f64 / n;
    let strong_ratio = strong as f64 / n;

    let score = (quantified_ratio * 45.0) + (outcome_ratio * 35.0) + (strong_ratio * 20.0);

    let mut details = HashMap::new();
    details.insert("bullets".to_string(), serde_json::json!(bullets.len()));
    details.insert("quantified".to_string(), serde_json::json!(quantified));
    details.insert("outcome".to_string(), serde_json::json!(outcome));
    details.insert("strong".to_string(), serde_json::json!(strong));
    details.insert(
        "quantified_ratio".to_string(),
        serde_json::json!(quantified_ratio),
    );
    details.insert(
        "outcome_ratio".to_string(),
        serde_json::json!(outcome_ratio),
    );
    details.insert("strong_ratio".to_string(), serde_json::json!(strong_ratio));

    (clamp(score, 0.0, 100.0), details)
}

// -------------------------
// Job Scoring
// -------------------------

/// Score a job posting across multiple quality categories.
///
/// # Errors
///
/// Returns an error if the weights file cannot be loaded or parsed.
pub fn score_job(job: &serde_json::Value, weights_path: Option<&str>) -> Result<ScoreReport> {
    let all_weights = load_scoring_weights(weights_path);
    let job_weights = all_weights
        .get("job")
        .cloned()
        .unwrap_or_else(default_job_weights);
    let normalized = normalize_weights(&job_weights);

    let (completeness_score, completeness_details) = score_job_completeness(job);
    let (clarity_score, clarity_details) = score_job_clarity(job);
    let (comp_score, comp_details) = score_job_compensation(job);
    let (link_score, link_details) = score_job_link_quality(job);

    let categories = vec![
        ScoreCategoryResult {
            name: "completeness".to_string(),
            score: completeness_score,
            weight: *normalized.get("completeness").unwrap_or(&0.0),
            details: completeness_details,
        },
        ScoreCategoryResult {
            name: "clarity".to_string(),
            score: clarity_score,
            weight: *normalized.get("clarity").unwrap_or(&0.0),
            details: clarity_details,
        },
        ScoreCategoryResult {
            name: "compensation_transparency".to_string(),
            score: comp_score,
            weight: *normalized.get("compensation_transparency").unwrap_or(&0.0),
            details: comp_details,
        },
        ScoreCategoryResult {
            name: "link_quality".to_string(),
            score: link_score,
            weight: *normalized.get("link_quality").unwrap_or(&0.0),
            details: link_details,
        },
    ];

    let total = weighted_total(&categories);

    let mut meta = HashMap::new();
    if let Some(path) = weights_path {
        meta.insert(
            "weights_source".to_string(),
            serde_json::json!(std::fs::canonicalize(path).ok()),
        );
    }

    Ok(ScoreReport {
        kind: "job".to_string(),
        total,
        categories,
        meta,
    })
}

fn score_job_completeness(job: &serde_json::Value) -> (f64, HashMap<String, serde_json::Value>) {
    let title = safe_str(job.get("title")).trim().to_string();
    let company = safe_str(job.get("company")).trim().to_string();
    let location = safe_str(job.get("location")).trim().to_string();
    let description = safe_str(job.get("description")).trim().to_string();
    let url = safe_str(job.get("url")).trim().to_string();

    let has_title = !title.is_empty() && title.to_lowercase() != "unknown";
    let has_company = !company.is_empty() && company.to_lowercase() != "unknown";
    let has_location = !location.is_empty() && location.to_lowercase() != "unknown";
    let has_description = description.len() >= 200; // Signal of real posting
    let has_url = !url.is_empty();

    let weights = [
        (has_title, 0.20),
        (has_company, 0.20),
        (has_location, 0.15),
        (has_description, 0.35),
        (has_url, 0.10),
    ];

    let score = weights
        .iter()
        .map(|(check, weight)| if *check { weight } else { &0.0 })
        .sum::<f64>()
        * 100.0;

    let mut details = HashMap::new();
    details.insert("has_title".to_string(), serde_json::json!(has_title));
    details.insert("has_company".to_string(), serde_json::json!(has_company));
    details.insert("has_location".to_string(), serde_json::json!(has_location));
    details.insert(
        "has_description".to_string(),
        serde_json::json!(has_description),
    );
    details.insert("has_url".to_string(), serde_json::json!(has_url));
    details.insert(
        "description_length".to_string(),
        serde_json::json!(description.len()),
    );

    (clamp(score, 0.0, 100.0), details)
}

fn score_job_clarity(job: &serde_json::Value) -> (f64, HashMap<String, serde_json::Value>) {
    let desc = safe_str(job.get("description")).trim().to_string();

    if desc.is_empty() {
        let mut details = HashMap::new();
        details.insert(
            "reason".to_string(),
            serde_json::json!("missing_description"),
        );
        return (0.0, details);
    }

    // Length-based (saturates around 1200 chars)
    let length_score = 100.0 * (desc.len() as f64 / 1200.0).min(1.0);

    // Section markers
    let section_markers = [
        "requirements",
        "responsibilities",
        "qualifications",
        "what you will",
        "benefits",
        "nice to have",
        "about you",
        "about the role",
    ];
    let desc_lower = desc.to_lowercase();
    let section_hits = section_markers
        .iter()
        .filter(|&&m| desc_lower.contains(m))
        .count();

    let section_score = (section_hits as f64 / 4.0).min(1.0) * 100.0;

    // Blend: more weight on length
    let score = (length_score * 0.65) + (section_score * 0.35);

    let mut details = HashMap::new();
    details.insert(
        "description_length".to_string(),
        serde_json::json!(desc.len()),
    );
    details.insert("section_hits".to_string(), serde_json::json!(section_hits));

    (clamp(score, 0.0, 100.0), details)
}

fn score_job_compensation(job: &serde_json::Value) -> (f64, HashMap<String, serde_json::Value>) {
    let salary = job
        .get("salary")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim();

    let has_salary = !salary.is_empty();

    let mut details = HashMap::new();
    details.insert("has_salary".to_string(), serde_json::json!(has_salary));

    if has_salary {
        (100.0, details)
    } else {
        (0.0, details)
    }
}

fn score_job_link_quality(job: &serde_json::Value) -> (f64, HashMap<String, serde_json::Value>) {
    let url = safe_str(job.get("url")).trim().to_string();

    if url.is_empty() {
        let mut details = HashMap::new();
        details.insert("reason".to_string(), serde_json::json!("missing_url"));
        return (0.0, details);
    }

    let looks_http = url.starts_with("http://") || url.starts_with("https://");

    let mut details = HashMap::new();
    details.insert("url".to_string(), serde_json::json!(url));
    details.insert("looks_http".to_string(), serde_json::json!(looks_http));

    if looks_http {
        (100.0, details)
    } else {
        (30.0, details)
    }
}

// -------------------------
// Match Scoring
// -------------------------

/// Score the match between a resume and a job posting.
///
/// # Errors
///
/// Returns an error if the weights file cannot be loaded or parsed.
pub fn score_match(
    resume: &serde_json::Value,
    job: &serde_json::Value,
    weights_path: Option<&str>,
) -> Result<ScoreReport> {
    let all_weights = load_scoring_weights(weights_path);
    let match_weights = all_weights
        .get("match")
        .cloned()
        .unwrap_or_else(default_match_weights);
    let normalized = normalize_weights(&match_weights);

    let (keyword_score, keyword_details) = score_match_keyword_overlap(resume, job);
    let (skills_score, skills_details) = score_match_skills_overlap(resume, job);
    let (role_score, role_details) = score_match_role_alignment(resume, job);

    let categories = vec![
        ScoreCategoryResult {
            name: "keyword_overlap".to_string(),
            score: keyword_score,
            weight: *normalized.get("keyword_overlap").unwrap_or(&0.0),
            details: keyword_details,
        },
        ScoreCategoryResult {
            name: "skills_overlap".to_string(),
            score: skills_score,
            weight: *normalized.get("skills_overlap").unwrap_or(&0.0),
            details: skills_details,
        },
        ScoreCategoryResult {
            name: "role_alignment".to_string(),
            score: role_score,
            weight: *normalized.get("role_alignment").unwrap_or(&0.0),
            details: role_details,
        },
    ];

    let total = weighted_total(&categories);

    let mut meta = HashMap::new();
    if let Some(path) = weights_path {
        meta.insert(
            "weights_source".to_string(),
            serde_json::json!(std::fs::canonicalize(path).ok()),
        );
    }

    Ok(ScoreReport {
        kind: "match".to_string(),
        total,
        categories,
        meta,
    })
}

fn score_match_keyword_overlap(
    resume: &serde_json::Value,
    job: &serde_json::Value,
) -> (f64, HashMap<String, serde_json::Value>) {
    let job_text = [
        safe_str(job.get("title")),
        safe_str(job.get("description")),
        safe_str(job.get("company")),
        safe_str(job.get("location")),
    ]
    .join(" ");

    let resume_text = resume_as_text(resume);

    let job_tokens = extract_keywords(&job_text);
    let resume_tokens = extract_keywords(&resume_text);

    if job_tokens.is_empty() {
        let mut details = HashMap::new();
        details.insert("reason".to_string(), serde_json::json!("job_has_no_tokens"));
        return (0.0, details);
    }

    let overlap: HashSet<_> = job_tokens.intersection(&resume_tokens).collect();
    let missing: HashSet<_> = job_tokens.difference(&resume_tokens).collect();

    let ratio = overlap.len() as f64 / job_tokens.len() as f64;

    // sqrt makes it easier to get decent scores on large job token sets
    let score = 100.0 * ratio.sqrt();

    let mut details = HashMap::new();
    details.insert(
        "job_token_count".to_string(),
        serde_json::json!(job_tokens.len()),
    );
    details.insert(
        "resume_token_count".to_string(),
        serde_json::json!(resume_tokens.len()),
    );
    details.insert(
        "overlap_count".to_string(),
        serde_json::json!(overlap.len()),
    );
    details.insert(
        "missing_count".to_string(),
        serde_json::json!(missing.len()),
    );
    details.insert("overlap_ratio".to_string(), serde_json::json!(ratio));

    let sample_overlap: Vec<String> = overlap.iter().take(20).map(|s| (*s).clone()).collect();
    let sample_missing: Vec<String> = missing.iter().take(20).map(|s| (*s).clone()).collect();
    details.insert(
        "sample_overlap".to_string(),
        serde_json::json!(sample_overlap),
    );
    details.insert(
        "sample_missing".to_string(),
        serde_json::json!(sample_missing),
    );

    (clamp(score, 0.0, 100.0), details)
}

fn score_match_skills_overlap(
    resume: &serde_json::Value,
    job: &serde_json::Value,
) -> (f64, HashMap<String, serde_json::Value>) {
    let skills = resume
        .get("skills")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.trim().to_lowercase())
                .filter(|s| !s.is_empty())
                .collect::<HashSet<String>>()
        })
        .unwrap_or_default();

    if skills.is_empty() {
        let mut details = HashMap::new();
        details.insert(
            "reason".to_string(),
            serde_json::json!("resume_has_no_skills"),
        );
        return (0.0, details);
    }

    let job_text = [safe_str(job.get("title")), safe_str(job.get("description"))].join(" ");
    let job_tokens = extract_keywords(&job_text);

    let mut matched = HashSet::new();
    for skill in &skills {
        let skill_tokens = extract_keywords(skill);
        if skill_tokens.is_empty() {
            continue;
        }

        // Single-token skill: exact match
        if skill_tokens.len() == 1 {
            if job_tokens.contains(skill_tokens.iter().next().unwrap()) {
                matched.insert(skill.clone());
            }
        } else {
            // Multi-token skill: require 60%+ tokens present
            let hits = skill_tokens
                .iter()
                .filter(|t| job_tokens.contains(*t))
                .count();
            if hits as f64 / skill_tokens.len() as f64 >= 0.6 {
                matched.insert(skill.clone());
            }
        }
    }

    let ratio = matched.len() as f64 / skills.len() as f64;
    let score = 100.0 * ratio;

    let mut details = HashMap::new();
    details.insert(
        "resume_skill_count".to_string(),
        serde_json::json!(skills.len()),
    );
    details.insert(
        "matched_skill_count".to_string(),
        serde_json::json!(matched.len()),
    );
    details.insert("match_ratio".to_string(), serde_json::json!(ratio));

    let sample_matched: Vec<String> = matched.iter().take(20).cloned().collect();
    details.insert(
        "sample_matched_skills".to_string(),
        serde_json::json!(sample_matched),
    );

    (clamp(score, 0.0, 100.0), details)
}

fn score_match_role_alignment(
    resume: &serde_json::Value,
    job: &serde_json::Value,
) -> (f64, HashMap<String, serde_json::Value>) {
    let job_title = safe_str(job.get("title")).trim().to_string();

    if job_title.is_empty() {
        let mut details = HashMap::new();
        details.insert("reason".to_string(), serde_json::json!("missing_job_title"));
        return (0.0, details);
    }

    let empty_vec = vec![];
    let exp = resume
        .get("experience")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty_vec);

    let mut titles = Vec::new();
    for entry in exp.iter().take(3) {
        // Recent roles
        if let Some(title) = entry.get("title").and_then(|v| v.as_str()) {
            let title = title.trim();
            if !title.is_empty() {
                titles.push(title.to_string());
            }
        }
    }

    if titles.is_empty() {
        let mut details = HashMap::new();
        details.insert(
            "reason".to_string(),
            serde_json::json!("missing_resume_titles"),
        );
        return (25.0, details); // Don't hard-zero
    }

    let job_toks = extract_keywords(&job_title);

    if job_toks.is_empty() {
        let mut details = HashMap::new();
        details.insert(
            "reason".to_string(),
            serde_json::json!("job_title_no_tokens"),
        );
        return (0.0, details);
    }

    let mut best = 0.0;
    let mut best_title = String::new();

    for title in &titles {
        let rt = extract_keywords(title);
        if rt.is_empty() {
            continue;
        }

        let overlap = job_toks.intersection(&rt).count() as f64 / job_toks.len() as f64;
        if overlap > best {
            best = overlap;
            best_title.clone_from(title);
        }
    }

    let score = 100.0 * best.sqrt();

    let mut details = HashMap::new();
    details.insert("job_title".to_string(), serde_json::json!(job_title));
    details.insert(
        "best_resume_title".to_string(),
        serde_json::json!(best_title),
    );
    details.insert("best_overlap_ratio".to_string(), serde_json::json!(best));

    (clamp(score, 0.0, 100.0), details)
}

// -------------------------
// Utility Functions
// -------------------------

fn weighted_total(categories: &[ScoreCategoryResult]) -> f64 {
    let total_weight: f64 = categories.iter().map(|c| c.weight).sum();

    if total_weight <= 0.0 {
        // No weights configured: unweighted mean
        if categories.is_empty() {
            return 0.0;
        }
        return clamp(
            categories.iter().map(|c| c.score).sum::<f64>() / categories.len() as f64,
            0.0,
            100.0,
        );
    }

    let acc: f64 = categories.iter().map(|c| c.score * c.weight).sum();
    clamp(acc / total_weight.max(1e-12), 0.0, 100.0)
}

fn clamp(x: f64, lo: f64, hi: f64) -> f64 {
    if x.is_nan() || x.is_infinite() {
        return lo;
    }
    x.max(lo).min(hi)
}

fn safe_str(value: Option<&serde_json::Value>) -> String {
    value.and_then(|v| v.as_str()).unwrap_or("").to_string()
}

fn extract_bullets(description: Option<&serde_json::Value>) -> Vec<String> {
    match description {
        Some(serde_json::Value::String(s)) => s
            .lines()
            .map(|l| l.trim().to_string())
            .filter(|l| !l.is_empty())
            .collect(),
        Some(serde_json::Value::Array(arr)) => arr
            .iter()
            .filter_map(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect(),
        _ => vec![],
    }
}

fn resume_as_text(resume: &serde_json::Value) -> String {
    let mut parts = Vec::new();

    // Personal info
    if let Some(personal) = resume.get("personal_info").and_then(|v| v.as_object()) {
        parts.push(safe_str(personal.get("name")));
        parts.push(safe_str(personal.get("headline")));
        parts.push(safe_str(personal.get("location")));
    }

    // Summary
    parts.push(safe_str(resume.get("summary")));

    // Skills
    if let Some(skills) = resume.get("skills").and_then(|v| v.as_array()) {
        for skill in skills {
            parts.push(safe_str(Some(skill)));
        }
    }

    // Experience
    if let Some(exp) = resume.get("experience").and_then(|v| v.as_array()) {
        for entry in exp {
            if let Some(obj) = entry.as_object() {
                parts.push(safe_str(obj.get("title")));
                parts.push(safe_str(obj.get("company")));
                parts.push(safe_str(obj.get("location")));

                for bullet in extract_bullets(obj.get("description")) {
                    parts.push(bullet);
                }
            }
        }
    }

    // Education
    if let Some(edu) = resume.get("education").and_then(|v| v.as_array()) {
        for entry in edu {
            if let Some(obj) = entry.as_object() {
                parts.push(safe_str(obj.get("degree")));
                parts.push(safe_str(obj.get("institution")));
            }
        }
    }

    // Projects
    if let Some(proj) = resume.get("projects").and_then(|v| v.as_array()) {
        for entry in proj {
            if let Some(obj) = entry.as_object() {
                parts.push(safe_str(obj.get("name")));
                parts.push(safe_str(obj.get("description")));
                parts.push(safe_str(obj.get("link")));
            }
        }
    }

    parts
        .into_iter()
        .filter(|p| !p.trim().is_empty())
        .collect::<Vec<_>>()
        .join("\n")
}

fn extract_keywords(text: &str) -> HashSet<String> {
    // Split on non-alphanumeric (but keep + and #)
    let tokens: Vec<&str> = text
        .split(|c: char| !c.is_alphanumeric() && c != '+' && c != '#')
        .filter(|t| !t.is_empty())
        .collect();

    let stopwords = stopwords();
    let mut keywords = HashSet::new();

    for token in tokens {
        let lower = token.to_lowercase();

        if stopwords.iter().any(|&sw| sw == lower) {
            continue;
        }

        // Filter out very short tokens except known technical terms
        if lower.len() <= 2 {
            if matches!(
                lower.as_str(),
                "c" | "go" | "ai" | "ml" | "ui" | "ux" | "qa" | "c#" | "c++"
            ) {
                keywords.insert(lower);
            }
            continue;
        }

        keywords.insert(lower);
    }

    keywords
}

fn looks_like_action_bullet(bullet: &str) -> bool {
    let b = bullet.trim().to_lowercase();
    if b.is_empty() {
        return false;
    }

    let first_word = b.split_whitespace().next().unwrap_or("");

    if action_verbs().contains(&first_word) {
        return true;
    }

    for verb in action_verbs() {
        if b.starts_with(&format!("{verb} ")) {
            return true;
        }
    }

    false
}

fn contains_number(s: &str) -> bool {
    // Match digits with optional decimal and % sign
    s.chars().any(char::is_numeric)
}

fn contains_outcome_language(s: &str) -> bool {
    let lower = s.to_lowercase();
    outcome_markers()
        .iter()
        .any(|&marker| lower.contains(marker))
}

fn stopwords() -> &'static [&'static str] {
    &[
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have", "he",
        "in", "is", "it", "its", "of", "on", "or", "that", "the", "their", "they", "this", "to",
        "was", "were", "will", "with", "you", "your", "we", "our", "us",
    ]
}

fn action_verbs() -> &'static [&'static str] {
    &[
        "built",
        "created",
        "designed",
        "developed",
        "delivered",
        "implemented",
        "improved",
        "increased",
        "reduced",
        "optimized",
        "automated",
        "led",
        "managed",
        "owned",
        "shipped",
        "launched",
        "migrated",
        "refactored",
        "collaborated",
        "analyzed",
        "architected",
        "tested",
        "deployed",
    ]
}

fn outcome_markers() -> &'static [&'static str] {
    &[
        "improved",
        "increased",
        "reduced",
        "decreased",
        "accelerated",
        "saved",
        "cut",
        "boosted",
        "grew",
        "optimized",
        "revenue",
        "cost",
        "latency",
        "throughput",
        "uptime",
        "performance",
        "efficiency",
        "scalability",
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_normalize_weights() {
        let mut weights = HashMap::new();
        weights.insert("a".to_string(), 1.0);
        weights.insert("b".to_string(), 2.0);
        weights.insert("c".to_string(), 1.0);

        let normalized = normalize_weights(&weights);

        assert_eq!(*normalized.get("a").unwrap(), 0.25);
        assert_eq!(*normalized.get("b").unwrap(), 0.5);
        assert_eq!(*normalized.get("c").unwrap(), 0.25);
    }

    #[test]
    fn test_score_resume_completeness() {
        let resume = json!({
            "personal_info": {"name": "John Doe", "email": "john@example.com"},
            "summary": "Software engineer with 5 years of experience",
            "experience": [{"title": "Engineer"}],
            "education": [{"degree": "BS"}],
            "skills": ["Rust", "Python"]
        });

        let (score, _details) = score_resume_completeness(&resume);
        assert!(score > 70.0); // Should have high score with all fields
    }

    #[test]
    fn test_extract_keywords() {
        let text = "Rust developer with C++ and Python experience";
        let keywords = extract_keywords(text);

        assert!(keywords.contains("rust"));
        assert!(keywords.contains("developer"));
        assert!(keywords.contains("c++"));
        assert!(keywords.contains("python"));
        assert!(keywords.contains("experience"));
        assert!(!keywords.contains("with")); // stopword
    }

    #[test]
    fn test_looks_like_action_bullet() {
        assert!(looks_like_action_bullet("Built a scalable system"));
        assert!(looks_like_action_bullet("Implemented new features"));
        assert!(!looks_like_action_bullet("Responsible for the project"));
    }

    #[test]
    fn test_contains_number() {
        assert!(contains_number("Improved performance by 50%"));
        assert!(contains_number("Processed 1000 requests"));
        assert!(!contains_number("No numbers here"));
    }
}
