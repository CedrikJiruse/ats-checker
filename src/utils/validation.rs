//! Validation helper functions.

/// Check if a string is a valid email.
pub fn is_valid_email(s: &str) -> bool {
    s.contains('@') && s.contains('.')
}

/// Check if a string is a valid URL.
pub fn is_valid_url(s: &str) -> bool {
    s.starts_with("http://") || s.starts_with("https://")
}

/// Sanitize a string by removing control characters.
pub fn sanitize_string(s: &str) -> String {
    s.chars()
        .filter(|c| !c.is_control() || c.is_whitespace())
        .collect()
}
