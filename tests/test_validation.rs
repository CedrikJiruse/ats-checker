//! Integration tests for schema validation.

mod common;

use ats_checker::validation::validate_json;
use serde_json::json;

#[test]
fn test_validate_resume_with_valid_structure() {
    let resume = json!({
        "personal_info": {
            "name": "John Doe",
            "email": "john@example.com"
        }
    });

    let schema = json!({
        "type": "object",
        "properties": {
            "personal_info": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                },
                "required": ["name", "email"]
            }
        },
        "required": ["personal_info"]
    });

    let result = validate_json(&resume, &schema);
    assert!(result.is_ok());
    let validation_result = result.unwrap();
    assert!(validation_result.ok);
}

#[test]
fn test_validate_resume_with_missing_fields() {
    let resume = json!({
        "personal_info": {
            "name": "Jane Doe"
        }
        // Missing required email field
    });

    let schema = json!({
        "type": "object",
        "properties": {
            "personal_info": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                },
                "required": ["name", "email"]
            }
        },
        "required": ["personal_info"]
    });

    let result = validate_json(&resume, &schema);
    assert!(result.is_ok());
    let validation_result = result.unwrap();
    // Should fail validation because email is missing
    assert!(!validation_result.ok);
}

#[test]
fn test_validate_resume_with_extra_fields() {
    let resume = json!({
        "personal_info": {
            "name": "Bob Smith",
            "email": "bob@example.com"
        },
        "extra_field": "This shouldn't break validation"
    });

    let schema = json!({
        "type": "object",
        "properties": {
            "personal_info": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                },
                "required": ["name", "email"]
            }
        },
        "required": ["personal_info"]
        // additionalProperties defaults to true, allowing extra fields
    });

    let result = validate_json(&resume, &schema);
    assert!(result.is_ok());
    let validation_result = result.unwrap();
    assert!(validation_result.ok);
}

#[test]
fn test_validate_resume_with_invalid_json_structure() {
    // Not even a valid object - just a string
    let resume = json!("This is not a valid resume structure");

    let schema = json!({
        "type": "object"
    });

    let result = validate_json(&resume, &schema);
    assert!(result.is_ok());
    let validation_result = result.unwrap();
    // Should fail validation because it's a string, not an object
    assert!(!validation_result.ok);
}

#[test]
fn test_validate_resume_with_empty_object() {
    let resume = json!({});

    let schema = json!({
        "type": "object"
    });

    let result = validate_json(&resume, &schema);
    assert!(result.is_ok());
    let validation_result = result.unwrap();
    // Empty object is valid JSON and matches the schema
    assert!(validation_result.ok);
}

#[test]
fn test_validate_resume_with_nested_structure() {
    let resume = json!({
        "personal_info": {
            "name": "Alice Johnson",
            "email": "alice@example.com"
        }
    });

    let schema = json!({
        "type": "object",
        "properties": {
            "personal_info": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                },
                "required": ["name", "email"]
            }
        },
        "required": ["personal_info"]
    });

    let result = validate_json(&resume, &schema);
    assert!(result.is_ok());
    let validation_result = result.unwrap();
    assert!(validation_result.ok);
}
