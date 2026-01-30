//! Integration tests for recommendations module.

mod common;

use ats_checker::recommendations::generate_recommendations;
use serde_json::json;

#[test]
fn test_generate_recommendations_for_low_scores() {
    let scoring = json!({
        "total": 45.0,
        "categories": [
            {
                "name": "completeness",
                "score": 40.0,
                "weight": 0.25
            },
            {
                "name": "skills_quality",
                "score": 60.0,
                "weight": 0.25
            },
            {
                "name": "experience_quality",
                "score": 50.0,
                "weight": 0.25
            },
            {
                "name": "impact",
                "score": 30.0,
                "weight": 0.25
            }
        ]
    });

    let recommendations = generate_recommendations(&scoring, 5);

    // Should generate recommendations for low-scoring categories
    assert!(!recommendations.is_empty());

    // Should not exceed max limit
    assert!(recommendations.len() <= 5);

    // Check that recommendations have messages
    for rec in &recommendations {
        assert!(!rec.message.is_empty());
    }
}

#[test]
fn test_generate_recommendations_for_high_score() {
    let scoring = json!({
        "total": 92.0,
        "categories": [
            {
                "name": "completeness",
                "score": 90.0,
                "weight": 0.25
            },
            {
                "name": "skills_quality",
                "score": 95.0,
                "weight": 0.25
            },
            {
                "name": "experience_quality",
                "score": 90.0,
                "weight": 0.25
            },
            {
                "name": "impact",
                "score": 93.0,
                "weight": 0.25
            }
        ]
    });

    let recommendations = generate_recommendations(&scoring, 5);

    // Should generate fewer recommendations for high scores
    assert!(recommendations.len() <= 5);
}

#[test]
fn test_generate_recommendations_respects_max_items() {
    let scoring = json!({
        "total": 30.0,
        "categories": [
            {
                "name": "completeness",
                "score": 20.0,
                "weight": 0.25
            },
            {
                "name": "skills_quality",
                "score": 25.0,
                "weight": 0.25
            },
            {
                "name": "experience_quality",
                "score": 35.0,
                "weight": 0.25
            },
            {
                "name": "impact",
                "score": 40.0,
                "weight": 0.25
            }
        ]
    });

    // Request only 2 recommendations
    let recommendations = generate_recommendations(&scoring, 2);

    // Should respect the max limit
    assert!(recommendations.len() <= 2);
}

#[test]
fn test_generate_recommendations_empty_for_perfect_score() {
    let scoring = json!({
        "total": 100.0,
        "categories": [
            {
                "name": "completeness",
                "score": 100.0,
                "weight": 0.25
            },
            {
                "name": "skills_quality",
                "score": 100.0,
                "weight": 0.25
            }
        ]
    });

    let recommendations = generate_recommendations(&scoring, 5);

    // Perfect score should generate no or minimal recommendations
    assert!(recommendations.is_empty() || recommendations.len() <= 1);
}

#[test]
fn test_recommendations_have_valid_structure() {
    let scoring = json!({
        "total": 55.0,
        "categories": [
            {
                "name": "completeness",
                "score": 55.0,
                "weight": 1.0
            }
        ]
    });

    let recommendations = generate_recommendations(&scoring, 3);

    for rec in recommendations {
        // Message should not be empty
        assert!(!rec.message.is_empty());

        // Message should be a complete sentence or phrase
        assert!(rec.message.len() > 10);

        // Reason is optional, but if present should not be empty
        if let Some(reason) = &rec.reason {
            assert!(!reason.is_empty());
        }
    }
}

#[test]
fn test_recommendations_with_missing_categories() {
    let scoring = json!({
        "total": 50.0
        // Missing categories array
    });

    let recommendations = generate_recommendations(&scoring, 5);

    // Should handle gracefully (may return empty or generic recommendations)
    assert!(recommendations.len() <= 5);
}
