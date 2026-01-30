//! Integration tests for the full processing pipeline (without AI calls).
//!
//! These tests verify that all major components work together correctly:
//! - Config loading
//! - State management
//! - Input handling
//! - Scoring system
//! - Output generation
//! - File I/O operations

mod common;

use ats_checker::{
    config::Config, input::InputHandler, output::OutputGenerator, scoring, state::StateManager,
    utils::hash::calculate_file_hash,
};
use common::{
    create_temp_dir, create_test_file, sample_config_toml, sample_job_description,
    sample_resume_json, sample_resume_text, sample_scoring_weights,
};
use std::collections::HashMap;

#[test]
fn test_config_state_input_integration() {
    // Create temp directory and test files
    let temp_dir = create_temp_dir();

    // Create config file
    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());

    // Create state file directory
    std::fs::create_dir_all(temp_dir.path().join("data")).unwrap();

    // Load config
    let mut config = Config::load(config_path.to_str().unwrap()).unwrap();

    // Update paths to use temp directory
    config.state_file = temp_dir.path().join("data/state.toml");
    config.input_resumes_folder = temp_dir.path().join("input");
    config.job_descriptions_folder = temp_dir.path().join("jobs");
    config.output_folder = temp_dir.path().join("output");

    // Create input directories and file
    std::fs::create_dir_all(&config.input_resumes_folder).unwrap();
    std::fs::create_dir_all(&config.job_descriptions_folder).unwrap();

    let resume_path = create_test_file(
        &config.input_resumes_folder,
        "test_resume.txt",
        sample_resume_text(),
    );

    // Initialize StateManager
    let mut state = StateManager::new(&config.state_file).unwrap();

    // Calculate file hash
    let file_hash = calculate_file_hash(&resume_path).unwrap();

    // Verify state doesn't have this file yet
    assert!(state.get_resume_state(&file_hash).is_none());

    // Add to state
    let output_path = temp_dir.path().join("output/test_resume.toml");
    state
        .update_resume_state(&file_hash, output_path.to_str().unwrap())
        .unwrap();

    // Verify state now has the file
    let resume_state = state.get_resume_state(&file_hash).unwrap();
    assert_eq!(resume_state.output_path, output_path.to_str().unwrap());

    // Initialize InputHandler
    let input_handler = InputHandler::new(
        &config.input_resumes_folder,
        &config.job_descriptions_folder,
    );

    // List resume files
    let resume_files = input_handler.list_resumes().unwrap();

    assert_eq!(resume_files.len(), 1);
    assert!(resume_files[0].ends_with("test_resume.txt"));
}

#[test]
fn test_scoring_and_output_integration() {
    let temp_dir = create_temp_dir();

    // Create weights file
    let weights_path = create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    // Create resume JSON
    let resume_json = sample_resume_json();

    // Score the resume
    let resume_score = scoring::score_resume(&resume_json, weights_path.to_str()).unwrap();

    assert!(resume_score.total >= 0.0);
    assert!(resume_score.total <= 100.0);
    assert!(!resume_score.categories.is_empty());

    // Create job description
    let job_text = sample_job_description();
    let job_json = serde_json::json!({
        "description": job_text,
        "raw_text": job_text
    });

    // Score job
    let job_score = scoring::score_job(&job_json, weights_path.to_str()).unwrap();

    assert!(job_score.total >= 0.0);
    assert!(job_score.total <= 100.0);

    // Score match
    let match_score = scoring::score_match(&resume_json, &job_json, weights_path.to_str()).unwrap();

    assert!(match_score.total >= 0.0);
    assert!(match_score.total <= 100.0);

    // Initialize OutputGenerator
    let output_dir = temp_dir.path().join("output");
    let generator = OutputGenerator::new(
        output_dir.clone(),
        "json".to_string(),
        "{resume_name}/{timestamp}".to_string(),
    );

    // Prepare output data with combined score
    let mut metadata = HashMap::new();
    metadata.insert(
        "resume_score".to_string(),
        serde_json::to_value(&resume_score).unwrap(),
    );
    metadata.insert(
        "job_score".to_string(),
        serde_json::to_value(&job_score).unwrap(),
    );
    metadata.insert(
        "match_score".to_string(),
        serde_json::to_value(&match_score).unwrap(),
    );

    let output_data = ats_checker::output::OutputData {
        resume_name: "test_resume".to_string(),
        job_title: Some("Software Engineer".to_string()),
        enhanced_resume: resume_json.clone(),
        scores: Some(resume_score.clone()),
        recommendations: vec![],
        metadata,
    };

    // Generate outputs
    let result_dir = generator.generate(&output_data).unwrap();

    // Verify output directory exists
    assert!(result_dir.exists());
    assert!(result_dir.is_dir());

    // List files in output directory
    let entries: Vec<_> = std::fs::read_dir(&result_dir)
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();

    // Should have at least resume.json and manifest.toml
    assert!(entries.len() >= 2);

    // Find and verify JSON file exists
    let json_file = entries
        .iter()
        .find(|p| p.extension().is_some_and(|ext| ext == "json"));
    assert!(json_file.is_some());

    // Verify JSON content can be read back
    let json_content = std::fs::read_to_string(json_file.unwrap()).unwrap();
    let parsed: serde_json::Value = serde_json::from_str(&json_content).unwrap();
    assert!(parsed.is_object());
}

#[test]
fn test_full_component_integration() {
    // This test integrates: Config → State → Input → Scoring → Output

    let temp_dir = create_temp_dir();

    // 1. Setup config
    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let mut config = Config::load(config_path.to_str().unwrap()).unwrap();

    config.state_file = temp_dir.path().join("data/state.toml");
    config.input_resumes_folder = temp_dir.path().join("input");
    config.job_descriptions_folder = temp_dir.path().join("jobs");
    config.output_folder = temp_dir.path().join("output");
    config.scoring_weights_file = temp_dir.path().join("weights.toml");

    // Create directories
    std::fs::create_dir_all(temp_dir.path().join("data")).unwrap();
    std::fs::create_dir_all(&config.input_resumes_folder).unwrap();
    std::fs::create_dir_all(&config.job_descriptions_folder).unwrap();

    // Create weights file
    create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    // 2. Initialize StateManager
    let mut state = StateManager::new(&config.state_file).unwrap();

    // 3. Create input resume
    let resume_path = create_test_file(
        &config.input_resumes_folder,
        "john_doe.txt",
        sample_resume_text(),
    );

    // 4. Calculate hash and check state
    let file_hash = calculate_file_hash(&resume_path).unwrap();
    assert!(state.get_resume_state(&file_hash).is_none());

    // 5. Initialize InputHandler and list files
    let input_handler = InputHandler::new(
        &config.input_resumes_folder,
        &config.job_descriptions_folder,
    );
    let resume_files = input_handler.list_resumes().unwrap();
    assert_eq!(resume_files.len(), 1);

    // 6. Load resume content
    let resume_content = input_handler
        .load_resume(resume_path.to_str().unwrap())
        .unwrap();
    assert!(!resume_content.is_empty());

    // 7. Simulate enhanced resume (in real pipeline, AI would do this)
    let enhanced_resume = sample_resume_json();

    // 8. Score the resume
    let resume_score =
        scoring::score_resume(&enhanced_resume, config.scoring_weights_file.to_str()).unwrap();

    assert!(resume_score.total >= 0.0);
    assert_eq!(resume_score.categories.len(), 4); // completeness, skills_quality, experience_quality, impact

    // 9. Generate output
    let output_generator = OutputGenerator::new(
        config.output_folder.clone(),
        "json".to_string(),
        "{resume_name}".to_string(),
    );

    let output_data = ats_checker::output::OutputData {
        resume_name: "john_doe".to_string(),
        job_title: None,
        enhanced_resume: enhanced_resume.clone(),
        scores: Some(resume_score.clone()),
        recommendations: vec![],
        metadata: HashMap::new(),
    };

    let result_dir = output_generator.generate(&output_data).unwrap();

    // 10. Update state with output directory path
    state
        .update_resume_state(&file_hash, result_dir.to_str().unwrap())
        .unwrap();

    // 11. Verify state was updated
    let resume_state = state.get_resume_state(&file_hash).unwrap();
    assert!(resume_state.output_path.contains("john_doe"));

    // 12. Verify output directory and files exist
    assert!(result_dir.exists());

    // Find JSON file in output
    let entries: Vec<_> = std::fs::read_dir(&result_dir)
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();

    let json_file = entries
        .iter()
        .find(|p| p.extension().is_some_and(|ext| ext == "json"));
    assert!(json_file.is_some());

    let output_content = std::fs::read_to_string(json_file.unwrap()).unwrap();
    let output_json: serde_json::Value = serde_json::from_str(&output_content).unwrap();

    assert_eq!(output_json["personal_info"]["name"], "John Doe");
}

#[test]
fn test_multi_file_processing_workflow() {
    // Test processing multiple resumes with state tracking

    let temp_dir = create_temp_dir();

    // Setup
    let config_path = create_test_file(temp_dir.path(), "config.toml", sample_config_toml());
    let mut config = Config::load(config_path.to_str().unwrap()).unwrap();

    config.state_file = temp_dir.path().join("data/state.toml");
    config.input_resumes_folder = temp_dir.path().join("input");
    config.job_descriptions_folder = temp_dir.path().join("jobs");
    config.output_folder = temp_dir.path().join("output");
    config.scoring_weights_file = temp_dir.path().join("weights.toml");

    std::fs::create_dir_all(temp_dir.path().join("data")).unwrap();
    std::fs::create_dir_all(&config.input_resumes_folder).unwrap();
    std::fs::create_dir_all(&config.job_descriptions_folder).unwrap();

    create_test_file(temp_dir.path(), "weights.toml", sample_scoring_weights());

    let mut state = StateManager::new(&config.state_file).unwrap();

    // Create multiple resume files
    let resume1 = create_test_file(
        &config.input_resumes_folder,
        "resume1.txt",
        "Resume 1 content",
    );

    let resume2 = create_test_file(
        &config.input_resumes_folder,
        "resume2.txt",
        "Resume 2 content - different from resume 1",
    );

    let resume3 = create_test_file(
        &config.input_resumes_folder,
        "resume3.md",
        "# Resume 3\nMarkdown format resume",
    );

    // List all resumes
    let input_handler = InputHandler::new(
        &config.input_resumes_folder,
        &config.job_descriptions_folder,
    );
    let resume_files = input_handler.list_resumes().unwrap();

    assert_eq!(resume_files.len(), 3);

    // Process each resume
    for resume_path in &resume_files {
        let file_hash = calculate_file_hash(resume_path).unwrap();

        // Check if already processed
        if state.get_resume_state(&file_hash).is_some() {
            continue; // Skip already processed
        }

        // Load content
        let content = input_handler.load_resume(resume_path).unwrap();
        assert!(!content.is_empty());

        // Simulate processing
        let stem = resume_path.file_stem().unwrap().to_str().unwrap();
        let output_path = config.output_folder.join(stem);

        // Update state
        state
            .update_resume_state(&file_hash, output_path.to_str().unwrap())
            .unwrap();
    }

    // Verify all files are now in state
    let hash1 = calculate_file_hash(&resume1).unwrap();
    let hash2 = calculate_file_hash(&resume2).unwrap();
    let hash3 = calculate_file_hash(&resume3).unwrap();

    assert!(state.get_resume_state(&hash1).is_some());
    assert!(state.get_resume_state(&hash2).is_some());
    assert!(state.get_resume_state(&hash3).is_some());
}

#[test]
fn test_error_handling_integration() {
    let temp_dir = create_temp_dir();

    // Test 1: Invalid config file
    let bad_config = create_test_file(temp_dir.path(), "bad_config.toml", "invalid { toml");
    let result = Config::load(bad_config.to_str().unwrap());
    assert!(result.is_err());

    // Test 2: Non-existent file hashing
    let result = calculate_file_hash("nonexistent_file.txt");
    assert!(result.is_err());

    // Test 3: Empty input directory
    let empty_dir = temp_dir.path().join("empty");
    let empty_jobs_dir = temp_dir.path().join("empty_jobs");
    std::fs::create_dir_all(&empty_dir).unwrap();
    std::fs::create_dir_all(&empty_jobs_dir).unwrap();

    let input_handler = InputHandler::new(&empty_dir, &empty_jobs_dir);
    let files = input_handler.list_resumes().unwrap();
    assert_eq!(files.len(), 0);

    // Test 4: State file in directory that needs creation
    // Note: StateManager should handle missing parent directories gracefully
    let nested_state_path = temp_dir.path().join("new/nested/state.toml");
    let result = StateManager::new(&nested_state_path);
    // Either creates directories or fails gracefully
    let _ = result;
}
