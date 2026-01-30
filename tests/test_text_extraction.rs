//! Integration tests for text extraction.

mod common;

use ats_checker::utils::extract::extract_text_from_file;
use common::*;

#[test]
fn test_extract_text_from_txt() {
    let temp_dir = create_temp_dir();
    let content = sample_resume_text();

    // Create a text file
    let file_path = create_test_file(temp_dir.path(), "resume.txt", content);

    // Extract text
    let extracted = extract_text_from_file(&file_path).expect("Failed to extract text from TXT");

    // Verify content matches
    assert_eq!(extracted, content);
}

#[test]
fn test_extract_text_from_md() {
    let temp_dir = create_temp_dir();
    let content = "# My Resume\n\n## Experience\n\nSoftware Engineer at Tech Corp";

    // Create a markdown file
    let file_path = create_test_file(temp_dir.path(), "resume.md", content);

    // Extract text
    let extracted = extract_text_from_file(&file_path).expect("Failed to extract text from MD");

    // Verify content matches (markdown is read as plain text)
    assert_eq!(extracted, content);
}

#[test]
fn test_extract_text_from_tex() {
    let temp_dir = create_temp_dir();
    let content = r"\documentclass{article}
\begin{document}
John Doe - Software Engineer
\end{document}";

    // Create a LaTeX file
    let file_path = create_test_file(temp_dir.path(), "resume.tex", content);

    // Extract text
    let extracted = extract_text_from_file(&file_path).expect("Failed to extract text from TEX");

    // Verify content matches (TeX is read as plain text)
    assert_eq!(extracted, content);
}

#[test]
fn test_extract_text_from_nonexistent_file() {
    let temp_dir = create_temp_dir();
    let file_path = temp_dir.path().join("nonexistent.txt");

    // Should return an error
    let result = extract_text_from_file(&file_path);
    assert!(result.is_err());
}

#[test]
fn test_extract_text_handles_utf8() {
    let temp_dir = create_temp_dir();
    let content = "José García\nSoftware Engineer\nEmail: josé@example.com\n日本語テスト";

    let file_path = create_test_file(temp_dir.path(), "resume_utf8.txt", content);

    let extracted = extract_text_from_file(&file_path).expect("Failed to extract UTF-8 text");

    assert_eq!(extracted, content);
}
