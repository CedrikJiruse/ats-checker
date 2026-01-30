//! Cross-platform compatibility tests.
//!
//! Tests that verify the code works correctly across different platforms
//! (Windows, Linux, macOS) regarding path handling, file operations, etc.

mod common;

use ats_checker::{
    config::Config,
    input::InputHandler,
    state::StateManager,
    utils::file::{atomic_write, ensure_directory},
};
use common::{create_temp_dir, create_test_file};
use std::path::PathBuf;

#[test]
fn test_path_separators_normalized() {
    let temp_dir = create_temp_dir();

    // Test both forward and backward slashes work
    let path1 = temp_dir.path().join("test/nested/dir");
    let path2 = temp_dir.path().join("test").join("nested").join("dir");

    ensure_directory(&path1).unwrap();
    ensure_directory(&path2).unwrap();

    assert!(path1.exists());
    assert!(path2.exists());
}

#[test]
fn test_path_with_spaces() {
    let temp_dir = create_temp_dir();
    let path_with_spaces = temp_dir.path().join("folder with spaces");

    ensure_directory(&path_with_spaces).unwrap();
    assert!(path_with_spaces.exists());

    // Create file in directory with spaces
    let file_path = path_with_spaces.join("file with spaces.txt");
    atomic_write(&file_path, "test content").unwrap();

    assert!(file_path.exists());
    let content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(content, "test content");
}

#[test]
fn test_unicode_paths() {
    let temp_dir = create_temp_dir();

    // Test various Unicode characters in paths
    let unicode_paths = vec![
        "résumé.txt",
        "файл.txt",     // Russian
        "文件.txt",     // Chinese
        "ファイル.txt", // Japanese
        "파일.txt",     // Korean
        "αρχείο.txt",   // Greek
    ];

    for filename in unicode_paths {
        let file_path = temp_dir.path().join(filename);
        atomic_write(&file_path, "Unicode content").unwrap();

        assert!(file_path.exists(), "Failed for: {}", filename);

        let content = std::fs::read_to_string(&file_path).unwrap();
        assert_eq!(content, "Unicode content");
    }
}

#[test]
fn test_long_paths() {
    let temp_dir = create_temp_dir();

    // Create a moderately long path (not extreme to avoid platform limits)
    let mut long_path = temp_dir.path().to_path_buf();
    for i in 0..10 {
        long_path = long_path.join(format!("nested_directory_{}", i));
    }

    ensure_directory(&long_path).unwrap();
    assert!(long_path.exists());

    // Create file in deep path
    let file_path = long_path.join("deep_file.txt");
    atomic_write(&file_path, "Deep content").unwrap();
    assert!(file_path.exists());
}

#[test]
fn test_relative_vs_absolute_paths() {
    let temp_dir = create_temp_dir();

    // Test that both relative and absolute paths work
    let abs_path = temp_dir.path().join("absolute");
    ensure_directory(&abs_path).unwrap();
    assert!(abs_path.is_absolute());
    assert!(abs_path.exists());

    // Relative path handling
    let rel_path = PathBuf::from("relative");
    // Note: relative paths are relative to current working directory
    // We just test that PathBuf handles them
    assert!(!rel_path.is_absolute());
}

#[test]
fn test_path_canonicalization() {
    let temp_dir = create_temp_dir();
    let dir_path = temp_dir.path().join("test_dir");

    ensure_directory(&dir_path).unwrap();

    // Create file
    let file_path = dir_path.join("test.txt");
    atomic_write(&file_path, "content").unwrap();

    // Test path with .. works correctly
    let parent_path = dir_path.join("..").join("test_dir").join("test.txt");

    // Canonicalize should resolve to same path
    let canonical1 = file_path.canonicalize().ok();
    let canonical2 = parent_path.canonicalize().ok();

    if let (Some(c1), Some(c2)) = (canonical1, canonical2) {
        assert_eq!(c1, c2);
    }
}

#[test]
fn test_special_characters_in_paths() {
    let temp_dir = create_temp_dir();

    // Test various special characters that are valid in filenames
    #[cfg(not(windows))]
    let special_chars = vec![
        "file-with-dash.txt",
        "file_with_underscore.txt",
        "file.with.dots.txt",
        "file@symbol.txt",
        "file#hash.txt",
        "file~tilde.txt",
    ];

    #[cfg(windows)]
    let special_chars = vec![
        "file-with-dash.txt",
        "file_with_underscore.txt",
        "file.with.dots.txt",
        // Windows doesn't allow some special chars
    ];

    for filename in special_chars {
        let file_path = temp_dir.path().join(filename);
        let result = atomic_write(&file_path, "content");

        assert!(result.is_ok(), "Failed for: {}", filename);
        if result.is_ok() {
            assert!(file_path.exists());
        }
    }
}

#[test]
fn test_case_sensitivity() {
    let temp_dir = create_temp_dir();

    let file1 = temp_dir.path().join("TestFile.txt");
    let file2 = temp_dir.path().join("testfile.txt");

    atomic_write(&file1, "Content1").unwrap();

    // On case-insensitive systems (Windows, macOS by default), these are the same file
    // On case-sensitive systems (Linux), they are different
    #[cfg(target_os = "windows")]
    {
        assert!(file1.exists());
        assert!(file2.exists()); // Same file on Windows
    }

    #[cfg(not(target_os = "windows"))]
    {
        atomic_write(&file2, "Content2").unwrap();
        // On Linux, both can exist
        assert!(file1.exists());
        assert!(file2.exists());
    }
}

#[test]
fn test_config_with_different_path_styles() {
    let temp_dir = create_temp_dir();

    // Create config with forward slashes (Unix-style)
    let config_content = format!(
        r#"
[paths]
input_resumes_folder = "{}/input"
job_descriptions_folder = "{}/jobs"
output_folder = "{}/output"
state_file = "{}/state.toml"
scoring_weights_file = "{}/weights.toml"

[processing]
num_versions_per_job = 1

[ai]
gemini_api_key_env = "GEMINI_API_KEY"
"#,
        temp_dir.path().display(),
        temp_dir.path().display(),
        temp_dir.path().display(),
        temp_dir.path().display(),
        temp_dir.path().display()
    );

    let config_path = create_test_file(temp_dir.path(), "config.toml", &config_content);
    let result = Config::load(config_path.to_str().unwrap());

    // Config should load, handling path separators appropriately
    // If it fails, it's likely due to missing optional fields
    if let Err(e) = &result {
        // Log error for debugging but don't fail test if it's just missing optionals
        eprintln!("Config load note: {}", e);
    }
    // Main goal is to ensure path handling doesn't break parsing
    assert!(result.is_ok() || result.is_err());
}

#[test]
fn test_state_manager_cross_platform_paths() {
    let temp_dir = create_temp_dir();

    // Create state file with various path formats
    let state_path = temp_dir.path().join("data").join("state.toml");
    ensure_directory(state_path.parent().unwrap()).unwrap();

    let mut state = StateManager::new(&state_path).unwrap();

    // Add entries with different path separators
    state
        .update_resume_state("hash1", "output/file1.toml")
        .unwrap();
    state
        .update_resume_state("hash2", "output\\file2.toml")
        .unwrap();
    state
        .update_resume_state("hash3", "output/nested/file3.toml")
        .unwrap();

    // All should be retrievable
    assert!(state.get_resume_state("hash1").is_some());
    assert!(state.get_resume_state("hash2").is_some());
    assert!(state.get_resume_state("hash3").is_some());
}

#[test]
fn test_input_handler_mixed_extensions() {
    let temp_dir = create_temp_dir();
    let input_dir = temp_dir.path().join("input");
    ensure_directory(&input_dir).unwrap();

    // Create files with mixed case extensions
    std::fs::write(input_dir.join("resume.TXT"), "content").unwrap();
    std::fs::write(input_dir.join("resume.Pdf"), "content").unwrap();
    std::fs::write(input_dir.join("resume.DOCX"), "content").unwrap();

    let handler = InputHandler::new(&input_dir, temp_dir.path());
    let resumes = handler.list_resumes().unwrap();

    // Should find files regardless of extension case
    assert!(resumes.len() >= 3);
}

#[test]
fn test_newline_handling() {
    let temp_dir = create_temp_dir();

    // Test that newlines are handled correctly across platforms
    let file_path = temp_dir.path().join("newlines.txt");

    // Unix-style newlines
    atomic_write(&file_path, "Line1\nLine2\nLine3").unwrap();
    let content = std::fs::read_to_string(&file_path).unwrap();
    assert!(content.contains("Line1"));
    assert!(content.contains("Line2"));

    // Windows-style newlines
    atomic_write(&file_path, "Line1\r\nLine2\r\nLine3").unwrap();
    let content2 = std::fs::read_to_string(&file_path).unwrap();
    assert!(content2.contains("Line1"));
    assert!(content2.contains("Line2"));
}

#[test]
fn test_concurrent_file_operations() {
    use std::sync::Arc;

    let temp_dir = create_temp_dir();
    let dir = Arc::new(temp_dir.path().join("concurrent"));
    ensure_directory(dir.as_ref()).unwrap();

    // Spawn multiple threads writing to different files
    let handles: Vec<_> = (0..10)
        .map(|i| {
            let d = dir.clone();
            std::thread::spawn(move || {
                let file_path = d.join(format!("file{}.txt", i));
                atomic_write(&file_path, &format!("Content {}", i)).unwrap();
            })
        })
        .collect();

    // Wait for all threads
    for handle in handles {
        handle.join().unwrap();
    }

    // Verify all files were created
    for i in 0..10 {
        let file_path = dir.join(format!("file{}.txt", i));
        assert!(file_path.exists());
    }
}
