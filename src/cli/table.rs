//! Table formatting utilities for CLI output.
//!
//! Provides functions to format structured data (scores, job listings, resume lists)
//! as nicely formatted tables for terminal display.

use comfy_table::{presets, Attribute, Cell, CellAlignment, Color, ContentArrangement, Table};
use serde_json::Value;

/// Format resume scores as a table.
///
/// # Arguments
///
/// * `scores` - JSON Value containing resume scores
///
/// # Returns
///
/// Formatted table string ready for terminal display.
///
/// # Examples
///
/// ```no_run
/// use ats_checker::cli::table::format_resume_scores;
/// use serde_json::json;
///
/// let scores = json!({
///     "overall": 85.5,
///     "categories": {
///         "completeness": {"score": 90.0, "weight": 0.25},
///         "skills": {"score": 82.0, "weight": 0.30},
///         "experience": {"score": 88.0, "weight": 0.25},
///         "impact": {"score": 80.0, "weight": 0.20}
///     }
/// });
///
/// let table = format_resume_scores(&scores);
/// println!("{}", table);
/// ```
pub fn format_resume_scores(scores: &Value) -> String {
    let mut table = Table::new();
    table
        .load_preset(presets::UTF8_FULL)
        .set_content_arrangement(ContentArrangement::Dynamic)
        .set_header(vec![
            Cell::new("Category")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Score")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Weight")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Weighted")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
        ]);

    // Add overall score
    if let Some(overall) = scores.get("overall").and_then(serde_json::Value::as_f64) {
        table.add_row(vec![
            Cell::new("OVERALL")
                .add_attribute(Attribute::Bold)
                .fg(get_score_color(overall)),
            Cell::new(format!("{overall:.1}"))
                .set_alignment(CellAlignment::Right)
                .fg(get_score_color(overall)),
            Cell::new("-").set_alignment(CellAlignment::Center),
            Cell::new("-").set_alignment(CellAlignment::Center),
        ]);
    }

    // Add category scores
    if let Some(categories) = scores.get("categories").and_then(|v| v.as_object()) {
        for (category, data) in categories {
            let score = data.get("score").and_then(serde_json::Value::as_f64).unwrap_or(0.0);
            let weight = data.get("weight").and_then(serde_json::Value::as_f64).unwrap_or(0.0);
            let weighted = score * weight;

            table.add_row(vec![
                Cell::new(capitalize_category(category)),
                Cell::new(format!("{score:.1}"))
                    .set_alignment(CellAlignment::Right)
                    .fg(get_score_color(score)),
                Cell::new(format!("{:.0}%", weight * 100.0))
                    .set_alignment(CellAlignment::Right),
                Cell::new(format!("{weighted:.1}"))
                    .set_alignment(CellAlignment::Right),
            ]);
        }
    }

    table.to_string()
}

/// Format match scores as a table.
///
/// # Arguments
///
/// * `match_scores` - JSON Value containing match scores
///
/// # Returns
///
/// Formatted table string ready for terminal display.
pub fn format_match_scores(match_scores: &Value) -> String {
    let mut table = Table::new();
    table
        .load_preset(presets::UTF8_FULL)
        .set_content_arrangement(ContentArrangement::Dynamic)
        .set_header(vec![
            Cell::new("Match Category")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Score")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Status")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
        ]);

    // Add overall match score
    if let Some(overall) = match_scores.get("overall").and_then(serde_json::Value::as_f64) {
        table.add_row(vec![
            Cell::new("OVERALL MATCH")
                .add_attribute(Attribute::Bold)
                .fg(get_score_color(overall)),
            Cell::new(format!("{overall:.1}"))
                .set_alignment(CellAlignment::Right)
                .fg(get_score_color(overall)),
            Cell::new(get_score_status(overall))
                .set_alignment(CellAlignment::Center)
                .fg(get_score_color(overall)),
        ]);
    }

    // Add category scores
    if let Some(categories) = match_scores.get("categories").and_then(|v| v.as_object()) {
        for (category, data) in categories {
            let score = if data.is_number() {
                data.as_f64().unwrap_or(0.0)
            } else {
                data.get("score").and_then(serde_json::Value::as_f64).unwrap_or(0.0)
            };

            table.add_row(vec![
                Cell::new(capitalize_category(category)),
                Cell::new(format!("{score:.1}"))
                    .set_alignment(CellAlignment::Right)
                    .fg(get_score_color(score)),
                Cell::new(get_score_status(score))
                    .set_alignment(CellAlignment::Center)
                    .fg(get_score_color(score)),
            ]);
        }
    }

    table.to_string()
}

/// Format job rankings as a table.
///
/// # Arguments
///
/// * `jobs` - Vector of job data with scores
/// * `top_n` - Number of top jobs to display (0 for all)
///
/// # Returns
///
/// Formatted table string ready for terminal display.
pub fn format_job_rankings(jobs: &[Value], top_n: usize) -> String {
    let mut table = Table::new();
    table
        .load_preset(presets::UTF8_FULL)
        .set_content_arrangement(ContentArrangement::Dynamic)
        .set_header(vec![
            Cell::new("Rank")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Job Title")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Company")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Match Score")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Location")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
        ]);

    let display_count = if top_n == 0 { jobs.len() } else { top_n.min(jobs.len()) };

    for (rank, job) in jobs.iter().take(display_count).enumerate() {
        let title = job.get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("Unknown");
        let company = job.get("company")
            .and_then(|v| v.as_str())
            .unwrap_or("Unknown");
        let score = job.get("score")
            .or_else(|| job.get("match_score"))
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.0);
        let location = job.get("location")
            .and_then(|v| v.as_str())
            .unwrap_or("Remote");

        table.add_row(vec![
            Cell::new(format!("#{}", rank + 1))
                .set_alignment(CellAlignment::Center),
            Cell::new(truncate_string(title, 40)),
            Cell::new(truncate_string(company, 25)),
            Cell::new(format!("{score:.1}"))
                .set_alignment(CellAlignment::Right)
                .fg(get_score_color(score)),
            Cell::new(truncate_string(location, 20)),
        ]);
    }

    if jobs.len() > display_count {
        table.add_row(vec![
            Cell::new(format!("... {} more jobs", jobs.len() - display_count))
                .add_attribute(Attribute::Italic)
                .fg(Color::DarkGrey),
        ]);
    }

    table.to_string()
}

/// Format resume list as a table.
///
/// # Arguments
///
/// * `resumes` - Vector of resume file paths or names
/// * `with_status` - Optional vector of processing status for each resume
///
/// # Returns
///
/// Formatted table string ready for terminal display.
pub fn format_resume_list(resumes: &[String], with_status: Option<&[String]>) -> String {
    let mut table = Table::new();
    table
        .load_preset(presets::UTF8_FULL)
        .set_content_arrangement(ContentArrangement::Dynamic);

    if with_status.is_some() {
        table.set_header(vec![
            Cell::new("#")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Resume")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Status")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
        ]);
    } else {
        table.set_header(vec![
            Cell::new("#")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Resume")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
        ]);
    }

    for (idx, resume) in resumes.iter().enumerate() {
        let resume_name = std::path::Path::new(resume)
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or(resume);

        if let Some(statuses) = with_status {
            let status = statuses.get(idx).map_or("Unknown", std::string::String::as_str);
            table.add_row(vec![
                Cell::new(format!("{}", idx + 1))
                    .set_alignment(CellAlignment::Right),
                Cell::new(resume_name),
                Cell::new(status)
                    .fg(get_status_color(status)),
            ]);
        } else {
            table.add_row(vec![
                Cell::new(format!("{}", idx + 1))
                    .set_alignment(CellAlignment::Right),
                Cell::new(resume_name),
            ]);
        }
    }

    table.to_string()
}

/// Format recommendations as a table.
///
/// # Arguments
///
/// * `recommendations` - Vector of recommendation strings
///
/// # Returns
///
/// Formatted table string ready for terminal display.
pub fn format_recommendations(recommendations: &[String]) -> String {
    let mut table = Table::new();
    table
        .load_preset(presets::UTF8_FULL)
        .set_content_arrangement(ContentArrangement::Dynamic)
        .set_header(vec![
            Cell::new("#")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
            Cell::new("Recommendation")
                .add_attribute(Attribute::Bold)
                .fg(Color::Cyan),
        ]);

    for (idx, rec) in recommendations.iter().enumerate() {
        table.add_row(vec![
            Cell::new(format!("{}", idx + 1))
                .set_alignment(CellAlignment::Right),
            Cell::new(rec),
        ]);
    }

    table.to_string()
}

// Helper functions

fn get_score_color(score: f64) -> Color {
    if score >= 80.0 {
        Color::Green
    } else if score >= 60.0 {
        Color::Yellow
    } else if score >= 40.0 {
        Color::Magenta
    } else {
        Color::Red
    }
}

fn get_score_status(score: f64) -> &'static str {
    if score >= 80.0 {
        "Excellent"
    } else if score >= 60.0 {
        "Good"
    } else if score >= 40.0 {
        "Fair"
    } else {
        "Poor"
    }
}

fn get_status_color(status: &str) -> Color {
    match status.to_lowercase().as_str() {
        "processed" | "completed" | "done" => Color::Green,
        "processing" | "in progress" => Color::Yellow,
        "pending" | "queued" => Color::Cyan,
        "error" | "failed" => Color::Red,
        _ => Color::White,
    }
}

fn capitalize_category(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => {
            let rest: String = chars.collect();
            format!("{}{}", first.to_uppercase(), rest.replace('_', " "))
        }
    }
}

fn truncate_string(s: &str, max_len: usize) -> String {
    if s.len() <= max_len {
        s.to_string()
    } else {
        format!("{}...", &s[..max_len.saturating_sub(3)])
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_format_resume_scores() {
        let scores = json!({
            "overall": 85.5,
            "categories": {
                "completeness": {"score": 90.0, "weight": 0.25},
                "skills": {"score": 82.0, "weight": 0.30},
            }
        });

        let table = format_resume_scores(&scores);
        assert!(table.contains("OVERALL"));
        assert!(table.contains("85.5"));
        assert!(table.contains("Completeness"));
        assert!(table.contains("Skills"));
    }

    #[test]
    fn test_format_match_scores() {
        let scores = json!({
            "overall": 75.0,
            "categories": {
                "keyword_overlap": 80.0,
                "skills_match": 70.0,
            }
        });

        let table = format_match_scores(&scores);
        assert!(table.contains("75.0"));
        assert!(table.contains("Keyword overlap"));
        assert!(table.contains("Skills match"));
    }

    #[test]
    fn test_format_job_rankings() {
        let jobs = vec![
            json!({
                "title": "Software Engineer",
                "company": "Tech Corp",
                "score": 85.0,
                "location": "Remote"
            }),
            json!({
                "title": "Senior Developer",
                "company": "StartUp Inc",
                "match_score": 78.5,
                "location": "San Francisco"
            }),
        ];

        let table = format_job_rankings(&jobs, 0);
        assert!(table.contains("#1"));
        assert!(table.contains("#2"));
        assert!(table.contains("Software Engineer"));
        assert!(table.contains("Senior Developer"));
    }

    #[test]
    fn test_format_job_rankings_top_n() {
        let jobs = vec![
            json!({"title": "Job 1", "company": "Co 1", "score": 90.0}),
            json!({"title": "Job 2", "company": "Co 2", "score": 85.0}),
            json!({"title": "Job 3", "company": "Co 3", "score": 80.0}),
        ];

        let table = format_job_rankings(&jobs, 2);
        assert!(table.contains("#1"));
        assert!(table.contains("#2"));
        assert!(table.contains("1 more jobs"));
    }

    #[test]
    fn test_format_resume_list() {
        let resumes = vec![
            "resume1.txt".to_string(),
            "resume2.pdf".to_string(),
        ];

        let table = format_resume_list(&resumes, None);
        assert!(table.contains("resume1"));
        assert!(table.contains("resume2"));
    }

    #[test]
    fn test_format_resume_list_with_status() {
        let resumes = vec![
            "resume1.txt".to_string(),
            "resume2.pdf".to_string(),
        ];
        let statuses = vec!["Processed".to_string(), "Pending".to_string()];

        let table = format_resume_list(&resumes, Some(&statuses));
        assert!(table.contains("Processed"));
        assert!(table.contains("Pending"));
    }

    #[test]
    fn test_format_recommendations() {
        let recommendations = vec![
            "Add more technical skills".to_string(),
            "Include quantifiable achievements".to_string(),
        ];

        let table = format_recommendations(&recommendations);
        assert!(table.contains("Add more technical skills"));
        assert!(table.contains("Include quantifiable achievements"));
    }

    #[test]
    fn test_get_score_color() {
        assert_eq!(get_score_color(90.0), Color::Green);
        assert_eq!(get_score_color(70.0), Color::Yellow);
        assert_eq!(get_score_color(50.0), Color::Magenta);
        assert_eq!(get_score_color(30.0), Color::Red);
    }

    #[test]
    fn test_get_score_status() {
        assert_eq!(get_score_status(85.0), "Excellent");
        assert_eq!(get_score_status(65.0), "Good");
        assert_eq!(get_score_status(45.0), "Fair");
        assert_eq!(get_score_status(25.0), "Poor");
    }

    #[test]
    fn test_capitalize_category() {
        assert_eq!(capitalize_category("completeness"), "Completeness");
        assert_eq!(capitalize_category("skills_match"), "Skills match");
        assert_eq!(capitalize_category("keyword_overlap"), "Keyword overlap");
    }

    #[test]
    fn test_truncate_string() {
        assert_eq!(truncate_string("short", 10), "short");
        assert_eq!(
            truncate_string("this is a very long string that needs truncation", 20),
            "this is a very lo..."
        );
    }
}
