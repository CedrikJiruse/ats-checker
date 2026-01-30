//! Recommendation generation module.

use serde::{Deserialize, Serialize};

/// A recommendation for resume improvement.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recommendation {
    /// Recommendation message.
    pub message: String,
    /// Optional reason.
    pub reason: Option<String>,
}

impl Recommendation {
    /// Create a new recommendation.
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            reason: None,
        }
    }

    /// Add a reason.
    #[must_use]
    pub fn with_reason(mut self, reason: impl Into<String>) -> Self {
        self.reason = Some(reason.into());
        self
    }
}

/// Generate recommendations from a scoring payload.
pub fn generate_recommendations(
    scoring: &serde_json::Value,
    max_items: usize,
) -> Vec<Recommendation> {
    let mut recommendations = Vec::new();

    // Extract total score and categories from the scoring payload
    let total_score = scoring.get("total").and_then(serde_json::Value::as_f64).unwrap_or(0.0);
    let categories = scoring.get("categories").and_then(|v| v.as_array());

    // If overall score is low, add general recommendation
    if total_score < 50.0 {
        recommendations.push(
            Recommendation::new("Resume needs significant improvement to meet ATS standards")
                .with_reason(format!("Overall score is {total_score:.1}%, which is below the 50% threshold"))
        );
    } else if total_score < 70.0 {
        recommendations.push(
            Recommendation::new("Resume could be improved to better match job requirements")
                .with_reason(format!("Overall score is {total_score:.1}%, aiming for 70%+ is recommended"))
        );
    }

    // Analyze each category
    if let Some(cats) = categories {
        for cat in cats {
            let name = cat.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let score = cat.get("score").and_then(serde_json::Value::as_f64).unwrap_or(0.0);
            let details = cat.get("details");

            // Generate recommendations for low-scoring categories
            if score < 50.0 {
                match name {
                    "completeness" => {
                        recommendations.push(
                            Recommendation::new("Add missing resume sections")
                                .with_reason("Completeness score is low. Ensure you have: contact info, summary, experience, skills, and education sections")
                        );
                    }
                    "skills_quality" => {
                        recommendations.push(
                            Recommendation::new("Improve skills section")
                                .with_reason("Add more relevant technical skills and tools. Include proficiency levels where applicable")
                        );
                    }
                    "experience_quality" => {
                        recommendations.push(
                            Recommendation::new("Enhance work experience descriptions")
                                .with_reason("Use action verbs, quantify achievements, and highlight impact in your experience bullet points")
                        );
                    }
                    "impact" => {
                        recommendations.push(
                            Recommendation::new("Add more quantifiable achievements")
                                .with_reason("Include numbers, metrics, and concrete results (e.g., 'Increased revenue by 25%', 'Reduced processing time by 40%')")
                        );
                    }
                    "keyword_overlap" => {
                        if let Some(d) = details {
                            if let Some(missing_keywords) = d.get("missing_keywords").and_then(|v| v.as_array()) {
                                if !missing_keywords.is_empty() {
                                    let keywords: Vec<String> = missing_keywords
                                        .iter()
                                        .filter_map(|v| v.as_str().map(String::from))
                                        .take(5)
                                        .collect();
                                    recommendations.push(
                                        Recommendation::new("Include more job-specific keywords")
                                            .with_reason(format!("Missing important keywords: {}", keywords.join(", ")))
                                    );
                                }
                            }
                        }
                    }
                    "skills_overlap" => {
                        recommendations.push(
                            Recommendation::new("Add skills mentioned in job description")
                                .with_reason("Your resume is missing several skills listed in the job requirements")
                        );
                    }
                    "role_alignment" => {
                        recommendations.push(
                            Recommendation::new("Better align your job titles with the target role")
                                .with_reason("Your experience titles don't closely match the job title. Consider highlighting transferable responsibilities")
                        );
                    }
                    _ => {}
                }
            } else if score < 70.0 {
                // Moderate scores - give lighter recommendations
                match name {
                    "impact" => {
                        recommendations.push(
                            Recommendation::new("Consider adding more quantifiable metrics to strengthen your impact")
                        );
                    }
                    "keyword_overlap" => {
                        recommendations.push(
                            Recommendation::new("Review job description for additional keywords to include")
                        );
                    }
                    _ => {}
                }
            }
        }
    }

    // Limit to max_items
    recommendations.truncate(max_items);

    recommendations
}
