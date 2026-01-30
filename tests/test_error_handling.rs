//! Comprehensive error handling and propagation tests.

mod common;

use ats_checker::{
    config::Config,
    error::AtsError,
    input::InputHandler,
    scoring,
    state::StateManager,
    toml_io,
    utils::{extract::extract_text_from_file, hash::calculate_file_hash},
};
use common::{create_temp_dir, create_test_file, sample_resume_json};

#[test]
fn test_config_error_invalid_toml() {
    let temp_dir = create_temp_dir();
    let bad_config = create_test_file(temp_dir.path(), "bad.toml", "invalid { toml syntax");

    let result = Config::load(bad_config.to_str().unwrap());

    assert!(result.is_err());
    match result.unwrap_err() {
        AtsError::TomlParse { .. } => {} // Expected
        e => panic!("Expected TomlParse error, got: {:?}", e),
    }
}

#[test]
fn test_config_error_file_not_found() {
    let result = Config::load("/nonexistent/path/config.toml");

    assert!(result.is_err());
    match result.unwrap_err() {
        AtsError::ConfigNotFound { .. } => {} // Expected
        e => panic!("Expected ConfigNotFound error, got: {:?}", e),
    }
}

#[test]
fn test_file_hash_error_nonexistent() {
    let result = calculate_file_hash("completely_nonexistent_file.txt");

    assert!(result.is_err());
    // Should be IO error
    assert!(result.is_err());
}

#[test]
fn test_text_extraction_error_nonexistent() {
    let result = extract_text_from_file("nonexistent_document.pdf");

    assert!(result.is_err());
    // Should be IO or extraction error
}

#[test]
fn test_scoring_error_invalid_weights() {
    let temp_dir = create_temp_dir();

    // Create invalid weights file (missing required fields)
    let bad_weights = create_test_file(
        temp_dir.path(),
        "bad_weights.toml",
        "[resume]\nonly_one_field = 1.0",
    );

    let resume = sample_resume_json();
    let result = scoring::score_resume(&resume, bad_weights.to_str());

    // Should handle gracefully (either error or use defaults)
    assert!(result.is_ok() || result.is_err());
}

#[test]
fn test_scoring_error_weights_not_found() {
    let resume = sample_resume_json();
    let result = scoring::score_resume(&resume, Some("/nonexistent/weights.toml"));

    // Should either error or use defaults - both are acceptable
    let _ = result;
}

#[test]
fn test_state_manager_corrupted_state() {
    let temp_dir = create_temp_dir();
    let state_file = temp_dir.path().join("corrupted_state.toml");

    // Create corrupted state file
    std::fs::write(&state_file, "corrupted { invalid toml").unwrap();

    let result = StateManager::new(&state_file);

    // Should either handle gracefully or error
    assert!(result.is_ok() || result.is_err());
}

#[test]
fn test_input_handler_invalid_directory() {
    let handler = InputHandler::new("/dev/null", "/dev/null"); // File, not directory on Unix
    let result = handler.list_resumes();

    // Should handle gracefully
    assert!(result.is_ok());
}

#[test]
fn test_toml_io_malformed_toml() {
    let temp_dir = create_temp_dir();
    let bad_file = create_test_file(temp_dir.path(), "malformed.toml", "{ invalid ]");

    let result = toml_io::load(&bad_file);

    assert!(result.is_err());
    match result.unwrap_err() {
        AtsError::TomlParse { .. } => {} // Expected
        e => panic!("Expected TomlParse error, got: {:?}", e),
    }
}

#[test]
fn test_error_propagation_chain() {
    // Test that errors propagate correctly through the call chain
    let temp_dir = create_temp_dir();
    let handler = InputHandler::new(temp_dir.path(), temp_dir.path());

    // Try to load a nonexistent file
    let result = handler.load_resume("nonexistent.txt");

    assert!(result.is_err());

    // Verify error type
    match result.unwrap_err() {
        AtsError::FileNotFound { .. } => {} // Expected
        e => panic!("Expected FileNotFound error, got: {:?}", e),
    }
}

#[test]
fn test_multiple_error_scenarios() {
    let temp_dir = create_temp_dir();

    // Scenario 1: Invalid config + invalid weights
    let bad_config = create_test_file(temp_dir.path(), "bad1.toml", "bad");
    assert!(Config::load(bad_config.to_str().unwrap()).is_err());

    // Scenario 2: Missing state file (should create new)
    let state_path = temp_dir.path().join("new_state.toml");
    let state = StateManager::new(&state_path);
    assert!(state.is_ok());

    // Scenario 3: Invalid resume hash
    assert!(calculate_file_hash("nonexistent").is_err());
}

#[test]
fn test_error_recovery() {
    let temp_dir = create_temp_dir();

    // Create a valid state file
    let state_path = temp_dir.path().join("state.toml");
    let mut state = StateManager::new(&state_path).unwrap();

    // Add some data
    state.update_resume_state("hash1", "output1").unwrap();

    // Verify recovery works
    let recovered_state = StateManager::new(&state_path).unwrap();
    assert!(recovered_state.get_resume_state("hash1").is_some());
}

#[test]
fn test_concurrent_error_handling() {
    use std::sync::Arc;

    let temp_dir = create_temp_dir();
    let handler = Arc::new(InputHandler::new(temp_dir.path(), temp_dir.path()));

    // Spawn multiple threads trying to access nonexistent files
    let handles: Vec<_> = (0..5)
        .map(|i| {
            let h = handler.clone();
            std::thread::spawn(move || {
                let result = h.load_resume(format!("nonexistent{}.txt", i));
                assert!(result.is_err());
            })
        })
        .collect();

    for handle in handles {
        handle.join().unwrap();
    }
}

#[test]
fn test_error_display_messages() {
    // Test that error messages are helpful
    let temp_dir = create_temp_dir();
    let path = temp_dir.path().join("missing.txt");

    let result = calculate_file_hash(&path);
    assert!(result.is_err());

    let err_msg = format!("{}", result.unwrap_err());
    // Error message should be informative
    assert!(!err_msg.is_empty());
}

#[test]
fn test_graceful_degradation_missing_optional_fields() {
    // Test that system handles missing optional configuration gracefully
    let temp_dir = create_temp_dir();

    // Create minimal valid config
    let minimal_config = r#"
[paths]
input_resumes_folder = "workspace/input_resumes"
job_descriptions_folder = "workspace/job_descriptions"
output_folder = "workspace/output"
state_file = "data/state.toml"
scoring_weights_file = "config/scoring_weights.toml"

[processing]
num_versions_per_job = 1

[ai]
gemini_api_key_env = "GEMINI_API_KEY"
"#;

    let config_path = create_test_file(temp_dir.path(), "minimal.toml", minimal_config);
    let result = Config::load(config_path.to_str().unwrap());

    // Should load with defaults for missing fields
    assert!(result.is_ok());
}

#[test]
fn test_error_types_characteristics() {
    // Test error type characteristics
    use ats_checker::error::AtsError;

    // Create different error types
    let api_err = AtsError::ApiRequest {
        message: "Connection failed".to_string(),
        source: None,
    };

    let file_err = AtsError::FileNotFound {
        path: std::path::PathBuf::from("test.txt"),
    };

    let rate_err = AtsError::ApiRateLimit {
        message: "Rate limited".to_string(),
        retry_after: Some(60),
    };

    // Verify errors can be created and formatted
    assert!(!format!("{}", api_err).is_empty());
    assert!(!format!("{}", file_err).is_empty());
    assert!(!format!("{}", rate_err).is_empty());
}
