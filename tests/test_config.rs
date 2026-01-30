//! Integration tests for configuration module.

mod common;

use ats_checker::config::Config;
use common::*;

#[test]
fn test_config_from_toml_string() {
    let toml_str = sample_config_toml();
    let config: Config = toml::from_str(toml_str).expect("Failed to parse config TOML");

    // Verify paths are set
    assert_eq!(
        config.input_resumes_folder.to_str().unwrap(),
        "workspace/input_resumes"
    );
    assert_eq!(
        config.job_descriptions_folder.to_str().unwrap(),
        "workspace/job_descriptions"
    );
    assert_eq!(config.output_folder.to_str().unwrap(), "workspace/output");

    // Verify processing settings
    assert_eq!(config.num_versions_per_job, 1);
    assert!(!config.iterate_until_score_reached);
    assert_eq!(config.max_iterations, 3);
    assert_eq!(config.target_score, 80.0);
    assert_eq!(config.iteration_strategy, "best_of");
}

#[test]
fn test_config_default() {
    let config = Config::default();

    // Verify defaults are sensible
    assert!(config.num_versions_per_job > 0);
    assert!(config.max_iterations > 0);
    assert!(config.target_score > 0.0 && config.target_score <= 100.0);
    assert!(!config.iteration_strategy.is_empty());
}

#[test]
fn test_config_serialization_roundtrip() {
    let config = Config::default();

    // Serialize to TOML
    let toml_string = toml::to_string(&config).expect("Failed to serialize config");

    // Deserialize back
    let deserialized: Config = toml::from_str(&toml_string).expect("Failed to deserialize config");

    // Verify key fields match
    assert_eq!(
        config.num_versions_per_job,
        deserialized.num_versions_per_job
    );
    assert_eq!(config.max_iterations, deserialized.max_iterations);
    assert_eq!(config.target_score, deserialized.target_score);
}

#[test]
fn test_config_with_custom_paths() {
    let temp_dir = create_temp_dir();

    // Create a config with custom paths using struct update syntax
    let config = Config {
        input_resumes_folder: temp_dir.path().join("resumes"),
        output_folder: temp_dir.path().join("output"),
        ..Default::default()
    };

    // Verify paths are set correctly
    assert!(config
        .input_resumes_folder
        .to_str()
        .unwrap()
        .contains("resumes"));
    assert!(config.output_folder.to_str().unwrap().contains("output"));
}
