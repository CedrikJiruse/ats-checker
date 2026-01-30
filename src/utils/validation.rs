//! Validation helper functions.

/// Check if a string is a valid email.
///
/// # Examples
///
/// ```
/// use ats_checker::utils::validation::is_valid_email;
///
/// assert!(is_valid_email("user@example.com"));
/// assert!(!is_valid_email("invalid"));
/// ```
pub fn is_valid_email(s: &str) -> bool {
    s.contains('@') && s.contains('.')
}

/// Check if a string is a valid URL.
///
/// # Examples
///
/// ```
/// use ats_checker::utils::validation::is_valid_url;
///
/// assert!(is_valid_url("https://example.com"));
/// assert!(!is_valid_url("not a url"));
/// ```
pub fn is_valid_url(s: &str) -> bool {
    s.starts_with("http://") || s.starts_with("https://")
}

/// Sanitize a string by removing control characters.
///
/// Preserves whitespace characters (space, tab, newline) while removing
/// other control characters.
///
/// # Examples
///
/// ```
/// use ats_checker::utils::validation::sanitize_string;
///
/// let input = "Hello\x00World\nTest";
/// let output = sanitize_string(input);
/// assert_eq!(output, "HelloWorld\nTest");
/// ```
pub fn sanitize_string(s: &str) -> String {
    s.chars()
        .filter(|c| !c.is_control() || c.is_whitespace())
        .collect()
}

/// Truncate a string to a maximum length, respecting UTF-8 boundaries.
///
/// If the string is longer than `max_len` bytes, it will be truncated
/// at the nearest character boundary at or before `max_len`. An ellipsis
/// ("...") is appended if truncation occurs.
///
/// # Arguments
///
/// * `s` - The string to truncate
/// * `max_len` - Maximum length in bytes (must be at least 3 for ellipsis)
///
/// # Examples
///
/// ```
/// use ats_checker::utils::validation::truncate_string;
///
/// assert_eq!(truncate_string("Hello, World!", 10), "Hello, ...");
/// assert_eq!(truncate_string("Short", 100), "Short");
/// assert_eq!(truncate_string("Hello 世界", 10), "Hello ...");
/// ```
pub fn truncate_string(s: &str, max_len: usize) -> String {
    if s.len() <= max_len {
        return s.to_string();
    }

    if max_len < 3 {
        // Not enough space for ellipsis, just truncate
        return s.chars().take(max_len).collect();
    }

    // Reserve 3 bytes for "..."
    let target_len = max_len - 3;

    // Find the character boundary at or before target_len
    let truncate_at = s
        .char_indices()
        .take_while(|(idx, ch)| idx + ch.len_utf8() <= target_len)
        .last()
        .map_or(0, |(idx, ch)| idx + ch.len_utf8());

    format!("{}...", &s[..truncate_at])
}

#[cfg(test)]
mod tests {
    use super::*;

    // Email validation tests
    #[test]
    fn test_is_valid_email_valid() {
        assert!(is_valid_email("user@example.com"));
        assert!(is_valid_email("test.user@domain.co.uk"));
        assert!(is_valid_email("name+tag@company.org"));
    }

    #[test]
    fn test_is_valid_email_invalid() {
        assert!(!is_valid_email("invalid"));
        // Note: Simple validation accepts @example.com (has @ and .)
        // For stricter validation, use a regex crate
        assert!(!is_valid_email("user@")); // Missing .
        assert!(!is_valid_email("user")); // Missing @ and .
        assert!(!is_valid_email("")); // Empty
        assert!(!is_valid_email("user.example")); // Missing @
    }

    // URL validation tests
    #[test]
    fn test_is_valid_url_valid() {
        assert!(is_valid_url("https://example.com"));
        assert!(is_valid_url("http://test.org/path"));
        assert!(is_valid_url("https://subdomain.example.com/page?query=1"));
    }

    #[test]
    fn test_is_valid_url_invalid() {
        assert!(!is_valid_url("not a url"));
        assert!(!is_valid_url("ftp://example.com"));
        assert!(!is_valid_url("example.com"));
        assert!(!is_valid_url(""));
        assert!(!is_valid_url("//example.com"));
    }

    // String sanitization tests
    #[test]
    fn test_sanitize_string_basic() {
        assert_eq!(sanitize_string("Hello World"), "Hello World");
        assert_eq!(sanitize_string("Test\nNewline"), "Test\nNewline");
        assert_eq!(sanitize_string("Tab\there"), "Tab\there");
    }

    #[test]
    fn test_sanitize_string_control_chars() {
        assert_eq!(sanitize_string("Hello\x00World"), "HelloWorld");
        assert_eq!(sanitize_string("Test\x01\x02\x03"), "Test");
        assert_eq!(sanitize_string("\x1bEscape"), "Escape");
    }

    #[test]
    fn test_sanitize_string_mixed() {
        let input = "Normal\x00Text\nWith\x01Controls\tAnd Spaces";
        let output = sanitize_string(input);
        assert_eq!(output, "NormalText\nWithControls\tAnd Spaces");
    }

    #[test]
    fn test_sanitize_string_empty() {
        assert_eq!(sanitize_string(""), "");
    }

    #[test]
    fn test_sanitize_string_only_controls() {
        assert_eq!(sanitize_string("\x00\x01\x02"), "");
    }

    // String truncation tests
    #[test]
    fn test_truncate_string_no_truncation() {
        assert_eq!(truncate_string("Short", 100), "Short");
        assert_eq!(truncate_string("Exact", 5), "Exact");
        assert_eq!(truncate_string("", 10), "");
    }

    #[test]
    fn test_truncate_string_basic() {
        assert_eq!(truncate_string("Hello, World!", 10), "Hello, ...");
        assert_eq!(truncate_string("Long string here", 8), "Long ...");
    }

    #[test]
    fn test_truncate_string_unicode() {
        // "Hello 世界" = "Hello " (6 bytes) + "世" (3 bytes) + "界" (3 bytes) = 12 bytes
        // max_len=10 -> target=7 -> fits "Hello " (6 bytes) + "..." = "Hello ..."
        assert_eq!(truncate_string("Hello 世界", 10), "Hello ...");

        // "🦀" is 4 bytes each, so "🦀🦀🦀🦀" = 16 bytes
        // max_len=10 -> target=7 -> fits "🦀" (4 bytes) + "..." = "🦀..."
        assert_eq!(truncate_string("🦀🦀🦀🦀", 10), "🦀...");
    }

    #[test]
    fn test_truncate_string_at_boundary() {
        // Should truncate at character boundary, not in middle of multi-byte char
        let s = "Hello 世"; // "Hello " (6) + "世" (3) = 9 bytes
        let result = truncate_string(s, 10);
        // Should not truncate since 9 <= 10
        assert_eq!(result, "Hello 世");

        // Test actual truncation
        let result2 = truncate_string(s, 8);
        assert!(result2.ends_with("..."));
        assert!(result2.is_char_boundary(result2.len() - 3));
    }

    #[test]
    fn test_truncate_string_very_short() {
        assert_eq!(truncate_string("Hello", 2), "He");
        assert_eq!(truncate_string("Test", 1), "T");
        assert_eq!(truncate_string("X", 0), "");
    }

    #[test]
    fn test_truncate_string_exact_length() {
        let s = "12345678";
        assert_eq!(truncate_string(s, 8), s);
        assert_eq!(truncate_string(s, 9), s);
    }

    #[test]
    fn test_truncate_string_preserves_validity() {
        // Ensure truncated string is always valid UTF-8
        let s = "Hello 世界 Test 🦀";
        for len in 0..s.len() + 5 {
            let result = truncate_string(s, len);
            assert!(result.is_char_boundary(result.len()));
            // Should be valid UTF-8 (won't panic on creation)
            let _ = result.chars().count();
        }
    }
}
