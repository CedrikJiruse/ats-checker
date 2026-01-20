//! TOML I/O module.

use std::path::Path;
use crate::error::Result;

/// Load TOML from a file.
pub fn load(path: impl AsRef<Path>) -> Result<serde_json::Value> {
    let content = std::fs::read_to_string(path)?;
    loads(&content)
}

/// Parse TOML from a string.
pub fn loads(s: &str) -> Result<serde_json::Value> {
    let value: toml::Value = toml::from_str(s)?;
    let json = serde_json::to_value(value)?;
    Ok(json)
}

/// Write TOML to a file.
pub fn dump(data: &serde_json::Value, path: impl AsRef<Path>) -> Result<()> {
    let s = dumps(data)?;
    std::fs::write(path, s)?;
    Ok(())
}

/// Serialize TOML to a string.
pub fn dumps(data: &serde_json::Value) -> Result<String> {
    let toml_value: toml::Value = serde_json::from_value(data.clone())?;
    let s = toml::to_string_pretty(&toml_value).map_err(|e| {
        crate::error::AtsError::TomlParse {
            message: e.to_string(),
            source: None,
        }
    })?;
    Ok(s)
}
