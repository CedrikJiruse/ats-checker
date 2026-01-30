//! Integration tests for output generation.

mod common;

use ats_checker::output::{OutputData, OutputGenerator};
use ats_checker::scoring::ScoreReport;
use common::*;
use serde_json::json;
use std::collections::HashMap;

#[test]
fn test_output_generator_creation() {
    let temp_dir = create_temp_dir();

    // Generator should be created successfully without panicking
    let _generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "json".to_string(),
        "{resume_name}/{timestamp}".to_string(),
    );
}

#[test]
fn test_generate_outputs_json_format() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "json".to_string(),
        "{resume_name}".to_string(),
    );

    let resume = sample_resume_json();

    let score_report = ScoreReport {
        kind: "resume".to_string(),
        total: 85.0,
        categories: vec![],
        meta: HashMap::new(),
    };

    let output_data = OutputData {
        resume_name: "John_Doe".to_string(),
        job_title: Some("SWE".to_string()),
        enhanced_resume: resume,
        scores: Some(score_report),
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);

    assert!(result.is_ok());
    let output_path = result.unwrap();

    // Output directory should exist
    assert!(output_path.exists());

    // JSON file should exist
    let json_file = output_path.join("John_Doe_SWE_enhanced.json");
    assert!(json_file.exists());

    // TXT file should exist
    let txt_file = output_path.join("John_Doe_SWE_enhanced.txt");
    assert!(txt_file.exists());

    // Scores file should exist
    let scores_file = output_path.join("scores.toml");
    assert!(scores_file.exists());
}

#[test]
fn test_generate_outputs_toml_format() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "toml".to_string(),
        "{resume_name}".to_string(),
    );

    let resume = sample_resume_json();

    let score_report = ScoreReport {
        kind: "resume".to_string(),
        total: 78.5,
        categories: vec![],
        meta: HashMap::new(),
    };

    let output_data = OutputData {
        resume_name: "Jane_Smith".to_string(),
        job_title: Some("DevOps".to_string()),
        enhanced_resume: resume,
        scores: Some(score_report),
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);

    assert!(result.is_ok());
    let output_path = result.unwrap();

    // TOML file should exist
    let toml_file = output_path.join("Jane_Smith_DevOps_enhanced.toml");
    assert!(toml_file.exists());

    // TXT file should exist (always generated)
    let txt_file = output_path.join("Jane_Smith_DevOps_enhanced.txt");
    assert!(txt_file.exists());
}

#[test]
fn test_generate_outputs_both_formats() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "both".to_string(),
        "output".to_string(),
    );

    let resume = json!({
        "personal_info": {
            "name": "Test User"
        }
    });

    let score_report = ScoreReport {
        kind: "resume".to_string(),
        total: 90.0,
        categories: vec![],
        meta: HashMap::new(),
    };

    let output_data = OutputData {
        resume_name: "Test_User".to_string(),
        job_title: Some("Engineer".to_string()),
        enhanced_resume: resume,
        scores: Some(score_report),
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);

    assert!(result.is_ok());
    let output_path = result.unwrap();

    // Both JSON and TOML should exist
    let json_file = output_path.join("Test_User_Engineer_enhanced.json");
    let toml_file = output_path.join("Test_User_Engineer_enhanced.toml");

    assert!(json_file.exists());
    assert!(toml_file.exists());
}

use ats_checker::utils::file::sanitize_filename;

#[test]
fn test_sanitize_filename_helper() {
    // Test the sanitize_filename function directly
    assert_eq!(sanitize_filename("file<name>.txt"), "file_name_.txt");
    assert_eq!(sanitize_filename("path/to/file"), "path_to_file");
    assert_eq!(sanitize_filename("  spaces  "), "spaces");
}

#[test]
fn test_output_path_with_all_placeholders() {
    let temp_dir = create_temp_dir();

    // Test pattern with all placeholders
    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "json".to_string(),
        "{resume_name}/{job_title}/{timestamp}".to_string(),
    );

    let resume = sample_resume_json();
    let output_data = OutputData {
        resume_name: "Alice_Johnson".to_string(),
        job_title: Some("Data_Scientist".to_string()),
        enhanced_resume: resume,
        scores: None,
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);
    assert!(result.is_ok());
    let output_path = result.unwrap();

    // Path should contain all substituted placeholders
    let path_str = output_path.to_string_lossy();
    assert!(path_str.contains("Alice_Johnson"));
    assert!(path_str.contains("Data_Scientist"));
    // Timestamp format is YYYYMMDD_HHMMSS, should match pattern
    assert!(output_path.exists());
}

#[test]
fn test_output_path_without_job_title() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "toml".to_string(),
        "{resume_name}/{job_title}".to_string(),
    );

    let resume = sample_resume_json();
    let output_data = OutputData {
        resume_name: "Bob_Williams".to_string(),
        job_title: None, // No job title
        enhanced_resume: resume,
        scores: None,
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);
    assert!(result.is_ok());
    let output_path = result.unwrap();

    // Should use "no_job" placeholder
    let path_str = output_path.to_string_lossy();
    assert!(path_str.contains("Bob_Williams"));
    assert!(path_str.contains("no_job"));
}

#[test]
fn test_output_with_unicode_characters() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "json".to_string(),
        "{resume_name}".to_string(),
    );

    // Resume with Unicode characters
    let resume = json!({
        "personal_info": {
            "name": "José García",
            "location": "São Paulo, Brasil"
        },
        "summary": "Software engineer with expertise in AI and ML. Spécialités: データサイエンス, 机器学习"
    });

    let output_data = OutputData {
        resume_name: "Jose_Garcia".to_string(),
        job_title: Some("Engineer".to_string()),
        enhanced_resume: resume,
        scores: None,
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);
    assert!(result.is_ok());
    let output_path = result.unwrap();

    // Files should be created and contain Unicode properly
    let json_file = output_path.join("Jose_Garcia_Engineer_enhanced.json");
    assert!(json_file.exists());

    let content = std::fs::read_to_string(&json_file).unwrap();
    assert!(content.contains("José García"));
    assert!(content.contains("São Paulo"));
    assert!(content.contains("データサイエンス"));
}

#[test]
fn test_output_with_empty_sections() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "toml".to_string(),
        "output".to_string(),
    );

    // Resume with mostly empty sections
    let resume = json!({
        "personal_info": {
            "name": "Empty Test"
        },
        "education": [],
        "work_experience": [],
        "skills": []
    });

    let output_data = OutputData {
        resume_name: "Empty_Test".to_string(),
        job_title: None,
        enhanced_resume: resume,
        scores: None,
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);
    assert!(result.is_ok());

    let output_path = result.unwrap();
    let toml_file = output_path.join("Empty_Test_no_job_enhanced.toml");
    assert!(toml_file.exists());

    // Should still generate valid TOML even with empty sections
    let content = std::fs::read_to_string(&toml_file).unwrap();
    assert!(!content.is_empty());
    assert!(content.contains("personal_info"));
}

#[test]
fn test_manifest_generation() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "both".to_string(),
        "output".to_string(),
    );

    let resume = sample_resume_json();
    let score_report = ScoreReport {
        kind: "resume".to_string(),
        total: 88.5,
        categories: vec![],
        meta: HashMap::new(),
    };

    let recommendations = vec![ats_checker::recommendations::Recommendation {
        message: "Add more technical skills".to_string(),
        reason: Some("Skills section needs improvement".to_string()),
    }];

    let output_data = OutputData {
        resume_name: "Manifest_Test".to_string(),
        job_title: Some("Developer".to_string()),
        enhanced_resume: resume,
        scores: Some(score_report),
        recommendations,
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);
    assert!(result.is_ok());
    let output_path = result.unwrap();

    // Manifest file should exist
    let manifest_file = output_path.join("manifest.toml");
    assert!(manifest_file.exists());

    // Parse manifest and verify contents
    let manifest_content = std::fs::read_to_string(&manifest_file).unwrap();
    assert!(manifest_content.contains("Manifest_Test"));
    assert!(manifest_content.contains("Developer"));
    assert!(manifest_content.contains("88.5"));
    assert!(manifest_content.contains("recommendations_count"));
}

#[test]
fn test_output_with_complex_nested_data() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "json".to_string(),
        "complex".to_string(),
    );

    // Complex nested resume structure
    let resume = json!({
        "personal_info": {
            "name": "Complex User",
            "contact": {
                "email": "user@example.com",
                "phone": "+1-555-0100",
                "address": {
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94102"
                }
            }
        },
        "work_experience": [
            {
                "company": "Tech Corp",
                "role": "Senior Engineer",
                "duration": "2020-2023",
                "achievements": [
                    "Led team of 5 engineers",
                    "Reduced latency by 40%",
                    "Implemented CI/CD pipeline"
                ],
                "technologies": ["Rust", "Python", "Docker", "Kubernetes"]
            },
            {
                "company": "StartUp Inc",
                "role": "Engineer",
                "duration": "2018-2020",
                "achievements": ["Built MVP", "Scaled to 1M users"],
                "technologies": ["Go", "React", "PostgreSQL"]
            }
        ],
        "certifications": [
            {"name": "AWS Certified", "year": 2022},
            {"name": "Kubernetes Admin", "year": 2021}
        ]
    });

    let mut metadata = HashMap::new();
    metadata.insert("processing_version".to_string(), json!("1.0.0"));
    metadata.insert("ai_model".to_string(), json!("gemini-1.5-flash"));

    let output_data = OutputData {
        resume_name: "Complex_User".to_string(),
        job_title: Some("Senior_Engineer".to_string()),
        enhanced_resume: resume,
        scores: None,
        recommendations: vec![],
        metadata,
    };

    let result = generator.generate(&output_data);
    assert!(result.is_ok());
    let output_path = result.unwrap();

    let json_file = output_path.join("Complex_User_Senior_Engineer_enhanced.json");
    assert!(json_file.exists());

    // Parse and verify structure is preserved
    let content = std::fs::read_to_string(&json_file).unwrap();
    let parsed: serde_json::Value = serde_json::from_str(&content).unwrap();

    // Verify nested structure
    assert_eq!(parsed["personal_info"]["name"], "Complex User");
    assert_eq!(
        parsed["personal_info"]["contact"]["address"]["city"],
        "San Francisco"
    );
    assert_eq!(parsed["work_experience"][0]["company"], "Tech Corp");
    assert_eq!(parsed["work_experience"][0]["technologies"][0], "Rust");
    assert_eq!(parsed["certifications"][0]["name"], "AWS Certified");
}

#[test]
fn test_txt_format_contains_all_sections() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "json".to_string(),
        "txt_test".to_string(),
    );

    let resume = json!({
        "name": "Test User",
        "email": "test@example.com",
        "summary": "Experienced software engineer",
        "experience": [
            {
                "title": "Developer",
                "company": "Company A",
                "dates": "2020-2023",
                "description": "Built amazing software"
            }
        ],
        "education": [
            {
                "degree": "BS Computer Science",
                "school": "University",
                "year": "2019"
            }
        ],
        "skills": ["Rust", "Python", "Go"]
    });

    let output_data = OutputData {
        resume_name: "Test_User".to_string(),
        job_title: Some("Dev".to_string()),
        enhanced_resume: resume,
        scores: None,
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);
    assert!(result.is_ok());
    let output_path = result.unwrap();

    let txt_file = output_path.join("Test_User_Dev_enhanced.txt");
    assert!(txt_file.exists());

    let content = std::fs::read_to_string(&txt_file).unwrap();

    // TXT file should contain formatted sections
    assert!(content.contains("Test User"), "Should contain name");
    assert!(content.contains("test@example.com"), "Should contain email");
    assert!(
        content.contains("Experienced software engineer"),
        "Should contain summary"
    );
    assert!(content.contains("Company A"), "Should contain company");
    assert!(content.contains("Developer"), "Should contain title");
    assert!(content.contains("University"), "Should contain school");
    assert!(
        content.contains("BS Computer Science"),
        "Should contain degree"
    );
}

#[test]
fn test_scores_file_format() {
    let temp_dir = create_temp_dir();

    let generator = OutputGenerator::new(
        temp_dir.path().to_path_buf(),
        "json".to_string(),
        "scores_test".to_string(),
    );

    let resume = sample_resume_json();

    use ats_checker::scoring::ScoreCategoryResult;
    let score_report = ScoreReport {
        kind: "resume".to_string(),
        total: 85.0,
        categories: vec![
            ScoreCategoryResult {
                name: "completeness".to_string(),
                score: 90.0,
                weight: 0.25,
                details: HashMap::new(),
            },
            ScoreCategoryResult {
                name: "skills".to_string(),
                score: 80.0,
                weight: 0.30,
                details: HashMap::new(),
            },
        ],
        meta: HashMap::new(),
    };

    let output_data = OutputData {
        resume_name: "Score_Test".to_string(),
        job_title: Some("Engineer".to_string()),
        enhanced_resume: resume,
        scores: Some(score_report),
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result = generator.generate(&output_data);
    assert!(result.is_ok());
    let output_path = result.unwrap();

    let scores_file = output_path.join("scores.toml");
    assert!(scores_file.exists());

    let content = std::fs::read_to_string(&scores_file).unwrap();

    // Scores file should contain all score information
    assert!(content.contains("resume"));
    assert!(content.contains("85"));
    assert!(content.contains("completeness"));
    assert!(content.contains("skills"));
    assert!(content.contains("90"));
    assert!(content.contains("80"));
}
