//! Integration tests for TOML I/O utilities.

mod common;

use ats_checker::toml_io::{dump, dumps, load, loads};
use common::*;
use serde_json::json;

#[test]
fn test_save_and_load_toml() {
    let temp_dir = create_temp_dir();
    let file_path = temp_dir.path().join("test.toml");

    let data = json!({
        "name": "Test",
        "value": 42,
        "enabled": true
    });

    // Save to TOML
    dump(&data, &file_path).expect("Failed to save TOML");

    // Verify file exists
    assert!(file_path.exists());

    // Load back
    let loaded = load(&file_path).expect("Failed to load TOML");

    // Verify data matches
    assert_eq!(loaded, data);
}

#[test]
fn test_load_nonexistent_toml() {
    let temp_dir = create_temp_dir();
    let file_path = temp_dir.path().join("nonexistent.toml");

    let result = load(&file_path);
    assert!(result.is_err());
}

#[test]
fn test_toml_roundtrip_with_complex_data() {
    let temp_dir = create_temp_dir();
    let file_path = temp_dir.path().join("complex.toml");

    let data = json!({
        "strings": ["one", "two", "three"],
        "numbers": [1, 2, 3, 4, 5],
        "nested": {
            "key": "test",
            "value": 42.5
        }
    });

    // Save and load
    dump(&data, &file_path).unwrap();
    let loaded = load(&file_path).unwrap();

    assert_eq!(loaded, data);
}

#[test]
fn test_load_malformed_toml() {
    let temp_dir = create_temp_dir();

    // Create a malformed TOML file
    let malformed = "this is not valid = TOML [[[";
    let file_path = create_test_file(temp_dir.path(), "malformed.toml", malformed);

    // Should return an error
    let result = load(&file_path);
    assert!(result.is_err());
}

#[test]
fn test_loads_and_dumps() {
    let toml_str = r#"
name = "Test"
value = 42
enabled = true
"#;

    // Parse from string
    let parsed = loads(toml_str).expect("Failed to parse TOML string");

    // Verify values
    assert_eq!(parsed["name"], "Test");
    assert_eq!(parsed["value"], 42);
    assert_eq!(parsed["enabled"], true);

    // Convert back to string
    let serialized = dumps(&parsed).expect("Failed to serialize to TOML");

    // Should contain the same keys
    assert!(serialized.contains("name"));
    assert!(serialized.contains("value"));
    assert!(serialized.contains("enabled"));
}
