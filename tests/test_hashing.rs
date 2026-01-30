//! Integration tests for file hashing.

mod common;

use ats_checker::utils::hash::calculate_file_hash;
use common::*;

#[test]
fn test_hash_calculation_basic() {
    let temp_dir = create_temp_dir();
    let content = "Hello, world!";
    let file_path = create_test_file(temp_dir.path(), "test.txt", content);

    let hash = calculate_file_hash(&file_path)
        .expect("Failed to calculate hash");

    // Hash should be a 64-character hex string (SHA256)
    assert_eq!(hash.len(), 64);
    assert!(hash.chars().all(|c| c.is_ascii_hexdigit()));
}

#[test]
fn test_hash_consistency() {
    let temp_dir = create_temp_dir();
    let content = "Consistent content for hashing";
    let file_path = create_test_file(temp_dir.path(), "test.txt", content);

    // Calculate hash multiple times
    let hash1 = calculate_file_hash(&file_path).unwrap();
    let hash2 = calculate_file_hash(&file_path).unwrap();
    let hash3 = calculate_file_hash(&file_path).unwrap();

    // All hashes should be identical
    assert_eq!(hash1, hash2);
    assert_eq!(hash2, hash3);
}

#[test]
fn test_different_content_different_hash() {
    let temp_dir = create_temp_dir();

    let file1 = create_test_file(temp_dir.path(), "file1.txt", "Content A");
    let file2 = create_test_file(temp_dir.path(), "file2.txt", "Content B");

    let hash1 = calculate_file_hash(&file1).unwrap();
    let hash2 = calculate_file_hash(&file2).unwrap();

    // Different content should produce different hashes
    assert_ne!(hash1, hash2);
}

#[test]
fn test_hash_large_file() {
    let temp_dir = create_temp_dir();

    // Create a large file (1 MB)
    let content = "x".repeat(1_000_000);
    let file_path = create_test_file(temp_dir.path(), "large.txt", &content);

    // Should successfully hash large file
    let hash = calculate_file_hash(&file_path)
        .expect("Failed to hash large file");

    assert_eq!(hash.len(), 64);
}

#[test]
fn test_hash_empty_file() {
    let temp_dir = create_temp_dir();
    let file_path = create_test_file(temp_dir.path(), "empty.txt", "");

    // Should successfully hash empty file
    let hash = calculate_file_hash(&file_path)
        .expect("Failed to hash empty file");

    assert_eq!(hash.len(), 64);

    // Empty file should have a specific hash
    // SHA256 of empty string is e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    assert_eq!(hash, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
}

#[test]
fn test_hash_nonexistent_file() {
    let temp_dir = create_temp_dir();
    let file_path = temp_dir.path().join("nonexistent.txt");

    // Should return an error
    let result = calculate_file_hash(&file_path);
    assert!(result.is_err());
}

#[test]
fn test_hash_unicode_content() {
    let temp_dir = create_temp_dir();
    let content = "Hello 世界 🌍 مرحبا";
    let file_path = create_test_file(temp_dir.path(), "unicode.txt", content);

    let hash = calculate_file_hash(&file_path)
        .expect("Failed to hash file with unicode");

    assert_eq!(hash.len(), 64);
}
