//! JSON schema validation module.

use crate::error::{AtsError, Result};
use jsonschema::Validator;
use serde::{Deserialize, Serialize};

/// Validation result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    /// Whether validation passed.
    pub ok: bool,
    /// Validation errors.
    pub errors: Vec<String>,
    /// Summary message.
    pub summary: String,
}

impl ValidationResult {
    /// Create a successful validation result.
    pub fn success() -> Self {
        Self {
            ok: true,
            errors: vec![],
            summary: "Valid".to_string(),
        }
    }

    /// Create a failed validation result.
    pub fn failure(errors: Vec<String>) -> Self {
        Self {
            ok: false,
            errors,
            summary: "Validation failed".to_string(),
        }
    }
}

/// Check if schema validation is available.
pub fn schema_validation_available() -> bool {
    true
}

/// Validate JSON against a schema.
///
/// # Errors
///
/// Returns an error if the schema cannot be compiled.
pub fn validate_json(
    instance: &serde_json::Value,
    schema: &serde_json::Value,
) -> Result<ValidationResult> {
    // Compile the schema
    let validator = Validator::new(schema)
        .map_err(|e| AtsError::internal(format!("Failed to compile JSON schema: {e}")))?;

    // Validate the instance
    if validator.is_valid(instance) {
        Ok(ValidationResult::success())
    } else {
        // Collect all validation errors
        let errors = validator.validate(instance);
        let error_messages: Vec<String> = match errors {
            Ok(()) => vec![], // This shouldn't happen since is_valid returned false
            Err(error_iter) => error_iter
                .map(|e| format!("{}: {}", e.instance_path, e))
                .collect(),
        };

        Ok(ValidationResult::failure(error_messages))
    }
}
