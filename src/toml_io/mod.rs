//! TOML I/O module.
//!
//! Provides functions for loading, saving, and manipulating TOML data.
//!
//! # Examples
//!
//! ```rust,no_run
//! use ats_checker::toml_io::{load, dump, merge_toml};
//! use serde_json::json;
//!
//! // Load TOML from file
//! let data = load("config.toml").unwrap();
//!
//! // Save TOML to file
//! dump(&json!({"name": "test"}), "output.toml").unwrap();
//!
//! // Merge two TOML values
//! let base = json!({"a": 1, "nested": {"x": 1}});
//! let overlay = json!({"b": 2, "nested": {"y": 2}});
//! let merged = merge_toml(&base, &overlay);
//! ```

use crate::error::Result;
use serde::de::DeserializeOwned;
use serde::Serialize;
use std::path::Path;

/// Load TOML from a file.
///
/// # Errors
///
/// Returns an error if the file cannot be read or parsed as valid TOML.
pub fn load(path: impl AsRef<Path>) -> Result<serde_json::Value> {
    let content = std::fs::read_to_string(path)?;
    loads(&content)
}

/// Parse TOML from a string.
///
/// # Errors
///
/// Returns an error if the string is not valid TOML or conversion to JSON fails.
pub fn loads(s: &str) -> Result<serde_json::Value> {
    let value: toml::Value = toml::from_str(s)?;
    let json = serde_json::to_value(value)?;
    Ok(json)
}

/// Write TOML to a file.
///
/// # Errors
///
/// Returns an error if serialization to TOML fails or the file cannot be written.
pub fn dump(data: &serde_json::Value, path: impl AsRef<Path>) -> Result<()> {
    let s = dumps(data)?;
    std::fs::write(path, s)?;
    Ok(())
}

/// Serialize TOML to a string.
///
/// # Errors
///
/// Returns an error if the data cannot be converted to TOML format.
pub fn dumps(data: &serde_json::Value) -> Result<String> {
    let toml_value: toml::Value = serde_json::from_value(data.clone())?;
    let s = toml::to_string_pretty(&toml_value).map_err(|e| crate::error::AtsError::TomlParse {
        message: e.to_string(),
        source: None,
    })?;
    Ok(s)
}

/// Load TOML from a file and deserialize directly to a type.
///
/// # Type Parameters
///
/// * `T` - The type to deserialize into. Must implement `DeserializeOwned`.
///
/// # Errors
///
/// Returns an error if the file cannot be read or parsed as valid TOML,
/// or if deserialization into type `T` fails.
///
/// # Example
///
/// ```rust
/// use serde::Deserialize;
/// use ats_checker::toml_io::load_as;
///
/// #[derive(Deserialize, Debug)]
/// struct Config {
///     name: String,
///     value: i32,
/// }
///
/// // let config: Config = load_as("config.toml").unwrap();
/// ```
pub fn load_as<T: DeserializeOwned>(path: impl AsRef<Path>) -> Result<T> {
    let content = std::fs::read_to_string(path)?;
    loads_as(&content)
}

/// Parse TOML from a string and deserialize directly to a type.
///
/// # Type Parameters
///
/// * `T` - The type to deserialize into. Must implement `DeserializeOwned`.
///
/// # Errors
///
/// Returns an error if the string is not valid TOML or deserialization fails.
pub fn loads_as<T: DeserializeOwned>(s: &str) -> Result<T> {
    let value: T = toml::from_str(s)?;
    Ok(value)
}

/// Serialize a value to TOML and write to a file.
///
/// # Type Parameters
///
/// * `T` - The type to serialize. Must implement `Serialize`.
///
/// # Errors
///
/// Returns an error if serialization fails or the file cannot be written.
///
/// # Example
///
/// ```rust
/// use serde::Serialize;
/// use ats_checker::toml_io::dump_as;
///
/// #[derive(Serialize)]
/// struct Config {
///     name: String,
///     value: i32,
/// }
///
/// // let config = Config { name: "test".to_string(), value: 42 };
/// // dump_as(&config, "config.toml").unwrap();
/// ```
pub fn dump_as<T: Serialize>(data: &T, path: impl AsRef<Path>) -> Result<()> {
    let s = dumps_as(data)?;
    std::fs::write(path, s)?;
    Ok(())
}

/// Serialize a value to a TOML string.
///
/// # Type Parameters
///
/// * `T` - The type to serialize. Must implement `Serialize`.
///
/// # Errors
///
/// Returns an error if serialization to TOML fails.
pub fn dumps_as<T: Serialize>(data: &T) -> Result<String> {
    let s = toml::to_string_pretty(data).map_err(|e| crate::error::AtsError::TomlParse {
        message: e.to_string(),
        source: None,
    })?;
    Ok(s)
}

/// Deep merge two TOML values.
///
/// Merges `overlay` into `base`, with `overlay` values taking precedence.
/// For objects/structs, fields are recursively merged.
/// For arrays and primitive values, overlay completely replaces base.
///
/// # Arguments
///
/// * `base` - The base TOML value
/// * `overlay` - The overlay value that takes precedence
///
/// # Returns
///
/// A new merged TOML value
///
/// # Example
///
/// ```rust
/// use ats_checker::toml_io::merge_toml;
/// use serde_json::json;
///
/// let base = json!({
///     "name": "base",
///     "settings": {
///         "debug": false,
///         "timeout": 30
///     }
/// });
///
/// let overlay = json!({
///     "settings": {
///         "debug": true
///     },
///     "extra": "value"
/// });
///
/// let merged = merge_toml(&base, &overlay);
/// assert_eq!(merged["name"], "base");
/// assert_eq!(merged["settings"]["debug"], true);
/// assert_eq!(merged["settings"]["timeout"], 30);
/// assert_eq!(merged["extra"], "value");
/// ```
pub fn merge_toml(base: &serde_json::Value, overlay: &serde_json::Value) -> serde_json::Value {
    match (base, overlay) {
        // Both are objects - recursively merge
        (serde_json::Value::Object(base_map), serde_json::Value::Object(overlay_map)) => {
            let mut result = base_map.clone();
            for (key, overlay_value) in overlay_map {
                let merged_value = if let Some(base_value) = result.get(key) {
                    merge_toml(base_value, overlay_value)
                } else {
                    overlay_value.clone()
                };
                result.insert(key.clone(), merged_value);
            }
            serde_json::Value::Object(result)
        }
        // Overlay is null - keep base
        (_, serde_json::Value::Null) => base.clone(),
        // Otherwise overlay takes precedence
        _ => overlay.clone(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::{Deserialize, Serialize};
    use serde_json::json;
    use tempfile::TempDir;

    #[derive(Debug, Serialize, Deserialize, PartialEq)]
    struct TestConfig {
        name: String,
        value: i32,
        enabled: bool,
    }

    #[derive(Debug, Serialize, Deserialize, PartialEq)]
    struct NestedConfig {
        name: String,
        settings: Settings,
    }

    #[derive(Debug, Serialize, Deserialize, PartialEq)]
    struct Settings {
        debug: bool,
        timeout: i32,
    }

    #[test]
    fn test_loads_as_basic() {
        let toml_str = r#"
name = "test"
value = 42
enabled = true
"#;

        let config: TestConfig = loads_as(toml_str).unwrap();
        assert_eq!(config.name, "test");
        assert_eq!(config.value, 42);
        assert!(config.enabled);
    }

    #[test]
    fn test_loads_as_nested() {
        let toml_str = r#"
name = "nested"
[settings]
debug = false
timeout = 30
"#;

        let config: NestedConfig = loads_as(toml_str).unwrap();
        assert_eq!(config.name, "nested");
        assert!(!config.settings.debug);
        assert_eq!(config.settings.timeout, 30);
    }

    #[test]
    fn test_dumps_as_basic() {
        let config = TestConfig {
            name: "test".to_string(),
            value: 42,
            enabled: true,
        };

        let toml_str = dumps_as(&config).unwrap();
        assert!(toml_str.contains("name = \"test\""));
        assert!(toml_str.contains("value = 42"));
        assert!(toml_str.contains("enabled = true"));
    }

    #[test]
    fn test_dumps_as_nested() {
        let config = NestedConfig {
            name: "nested".to_string(),
            settings: Settings {
                debug: true,
                timeout: 60,
            },
        };

        let toml_str = dumps_as(&config).unwrap();
        assert!(toml_str.contains("name = \"nested\""));
        assert!(toml_str.contains("[settings]"));
        assert!(toml_str.contains("debug = true"));
        assert!(toml_str.contains("timeout = 60"));
    }

    #[test]
    fn test_load_as_and_dump_as_roundtrip() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("test_config.toml");

        let original = TestConfig {
            name: "roundtrip".to_string(),
            value: 123,
            enabled: false,
        };

        // Write to file
        dump_as(&original, &file_path).unwrap();

        // Read back
        let loaded: TestConfig = load_as(&file_path).unwrap();

        assert_eq!(original, loaded);
    }

    #[test]
    fn test_merge_toml_simple() {
        let base = json!({"a": 1, "b": 2});
        let overlay = json!({"b": 3, "c": 4});

        let merged = merge_toml(&base, &overlay);

        assert_eq!(merged["a"], 1);
        assert_eq!(merged["b"], 3); // overlay takes precedence
        assert_eq!(merged["c"], 4);
    }

    #[test]
    fn test_merge_toml_nested() {
        let base = json!({
            "name": "base",
            "settings": {
                "debug": false,
                "timeout": 30,
                "extra": "keep"
            }
        });

        let overlay = json!({
            "settings": {
                "debug": true
            },
            "new_field": "value"
        });

        let merged = merge_toml(&base, &overlay);

        assert_eq!(merged["name"], "base");
        assert_eq!(merged["settings"]["debug"], true); // overlay takes precedence
        assert_eq!(merged["settings"]["timeout"], 30); // base value kept
        assert_eq!(merged["settings"]["extra"], "keep"); // base value kept
        assert_eq!(merged["new_field"], "value");
    }

    #[test]
    fn test_merge_toml_deeply_nested() {
        let base = json!({
            "level1": {
                "level2": {
                    "level3": {
                        "value": "base"
                    }
                }
            }
        });

        let overlay = json!({
            "level1": {
                "level2": {
                    "level3": {
                        "new_value": "overlay"
                    }
                }
            }
        });

        let merged = merge_toml(&base, &overlay);

        assert_eq!(merged["level1"]["level2"]["level3"]["value"], "base");
        assert_eq!(merged["level1"]["level2"]["level3"]["new_value"], "overlay");
    }

    #[test]
    fn test_merge_toml_with_arrays() {
        let base = json!({"items": [1, 2, 3]});
        let overlay = json!({"items": [4, 5]});

        let merged = merge_toml(&base, &overlay);

        // Arrays should be replaced, not merged
        assert_eq!(merged["items"], json!([4, 5]));
    }

    #[test]
    fn test_merge_toml_with_null() {
        let base = json!({"a": 1, "b": 2});
        let overlay = json!({"b": null});

        let merged = merge_toml(&base, &overlay);

        // Null overlay should keep base value
        assert_eq!(merged["a"], 1);
        assert_eq!(merged["b"], 2);
    }

    #[test]
    fn test_merge_toml_empty_objects() {
        let base = json!({});
        let overlay = json!({"new": "value"});

        let merged = merge_toml(&base, &overlay);

        assert_eq!(merged["new"], "value");
    }

    #[test]
    fn test_merge_toml_both_empty() {
        let base = json!({});
        let overlay = json!({});

        let merged = merge_toml(&base, &overlay);

        assert!(merged.as_object().unwrap().is_empty());
    }

    #[test]
    fn test_loads_as_error_invalid_toml() {
        let invalid_toml = "not valid toml [[[";
        let result: Result<TestConfig> = loads_as(invalid_toml);
        assert!(result.is_err());
    }

    #[test]
    fn test_roundtrip_with_merge() {
        let temp_dir = TempDir::new().unwrap();
        let base_path = temp_dir.path().join("base.toml");
        let overlay_path = temp_dir.path().join("overlay.toml");

        // Create base config
        let base = json!({
            "name": "app",
            "settings": {
                "debug": false,
                "timeout": 30
            }
        });
        dump(&base, &base_path).unwrap();

        // Create overlay config
        let overlay = json!({
            "settings": {
                "debug": true
            }
        });
        dump(&overlay, &overlay_path).unwrap();

        // Load and merge
        let base_loaded = load(&base_path).unwrap();
        let overlay_loaded = load(&overlay_path).unwrap();
        let merged = merge_toml(&base_loaded, &overlay_loaded);

        // Verify merged result
        assert_eq!(merged["name"], "app");
        assert_eq!(merged["settings"]["debug"], true);
        assert_eq!(merged["settings"]["timeout"], 30);
    }
}
