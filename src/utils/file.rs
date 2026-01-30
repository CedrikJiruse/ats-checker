//! File operation utilities.

use crate::error::{AtsError, Result};
use std::path::{Path, PathBuf};

/// Maximum path length for Windows (260 characters for legacy, 32,767 for extended).
const WINDOWS_MAX_PATH: usize = 260;

/// Maximum reasonable path length for all platforms.
const MAX_REASONABLE_PATH: usize = 4096;

/// Ensure a directory exists.
///
/// # Errors
///
/// Returns an error if the directory cannot be created.
pub fn ensure_directory(path: impl AsRef<Path>) -> Result<()> {
    std::fs::create_dir_all(path.as_ref())?;
    Ok(())
}

/// Atomic write to a file.
///
/// # Errors
///
/// Returns an error if the temporary file cannot be written or renamed.
pub fn atomic_write(path: impl AsRef<Path>, content: &str) -> Result<()> {
    let path = path.as_ref();
    let temp_path = path.with_extension("tmp");
    std::fs::write(&temp_path, content)?;
    std::fs::rename(&temp_path, path)?;
    Ok(())
}

/// List files with specific extensions in a directory.
///
/// # Arguments
///
/// * `dir` - Directory to search
/// * `extensions` - Slice of file extensions to match (without leading dot)
///
/// # Returns
///
/// Returns a vector of paths to matching files, sorted alphabetically.
///
/// # Errors
///
/// Returns an error if the directory cannot be read.
///
/// # Example
///
/// ```no_run
/// use ats_checker::utils::file::list_files_with_extension;
///
/// let files = list_files_with_extension("/path/to/dir", &["txt", "pdf"])?;
/// for file in files {
///     println!("Found: {}", file.display());
/// }
/// # Ok::<(), ats_checker::error::AtsError>(())
/// ```
pub fn list_files_with_extension(
    dir: impl AsRef<Path>,
    extensions: &[&str],
) -> Result<Vec<PathBuf>> {
    let dir = dir.as_ref();

    if !dir.exists() {
        return Ok(Vec::new());
    }

    if !dir.is_dir() {
        return Err(AtsError::InputValidation {
            message: format!("{} is not a directory", dir.display()),
        });
    }

    let mut files = Vec::new();

    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();

        if !path.is_file() {
            continue;
        }

        if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
            let ext_lower = ext.to_lowercase();
            if extensions.iter().any(|&e| e.to_lowercase() == ext_lower) {
                files.push(path);
            }
        }
    }

    // Sort for deterministic ordering
    files.sort();

    Ok(files)
}

/// Validate that a path length is within acceptable limits.
///
/// On Windows, warns if path exceeds 260 characters (legacy `MAX_PATH` limit).
/// On other platforms, checks against a reasonable limit of 4096 characters.
///
/// # Arguments
///
/// * `path` - Path to validate
///
/// # Returns
///
/// `Ok(())` if the path length is acceptable, `Err` otherwise.
///
/// # Errors
///
/// Returns an error if the path length exceeds the maximum allowed length.
///
/// # Example
///
/// ```no_run
/// use ats_checker::utils::file::validate_path_length;
/// use std::path::Path;
///
/// validate_path_length(Path::new("/short/path.txt"))?;
/// # Ok::<(), ats_checker::error::AtsError>(())
/// ```
pub fn validate_path_length(path: impl AsRef<Path>) -> Result<()> {
    let path = path.as_ref();
    let path_str = path.to_string_lossy();
    let len = path_str.len();

    #[cfg(windows)]
    {
        if len > WINDOWS_MAX_PATH {
            return Err(AtsError::InputValidation {
                message: format!(
                    "Path exceeds Windows maximum length ({} > {}): {}",
                    len,
                    WINDOWS_MAX_PATH,
                    path.display()
                ),
            });
        }
    }

    // General sanity check for all platforms
    if len > MAX_REASONABLE_PATH {
        return Err(AtsError::InputValidation {
            message: format!(
                "Path exceeds maximum reasonable length ({} > {}): {}",
                len,
                MAX_REASONABLE_PATH,
                path.display()
            ),
        });
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_ensure_directory() {
        let temp = TempDir::new().unwrap();
        let test_dir = temp.path().join("test/nested/dir");

        // Verify directory doesn't exist
        assert!(!test_dir.exists());

        // Create directory
        ensure_directory(&test_dir).unwrap();

        // Verify it was created
        assert!(test_dir.exists());
        assert!(test_dir.is_dir());
    }

    #[test]
    fn test_ensure_directory_existing() {
        let temp = TempDir::new().unwrap();
        let test_dir = temp.path().join("existing");

        // Create directory manually
        std::fs::create_dir(&test_dir).unwrap();

        // Ensure should succeed on existing directory
        let result = ensure_directory(&test_dir);
        assert!(result.is_ok());

        assert!(test_dir.exists());
    }

    #[test]
    fn test_atomic_write() {
        let temp = TempDir::new().unwrap();
        let file_path = temp.path().join("test.txt");

        let content = "Hello, World!";
        atomic_write(&file_path, content).unwrap();

        // Verify file was created and has correct content
        assert!(file_path.exists());
        let read_content = std::fs::read_to_string(&file_path).unwrap();
        assert_eq!(read_content, content);

        // Verify temp file was cleaned up
        let temp_path = file_path.with_extension("tmp");
        assert!(!temp_path.exists());
    }

    #[test]
    fn test_atomic_write_overwrite() {
        let temp = TempDir::new().unwrap();
        let file_path = temp.path().join("test.txt");

        // Write initial content
        atomic_write(&file_path, "Initial content").unwrap();
        assert_eq!(
            std::fs::read_to_string(&file_path).unwrap(),
            "Initial content"
        );

        // Overwrite with new content
        atomic_write(&file_path, "New content").unwrap();
        assert_eq!(std::fs::read_to_string(&file_path).unwrap(), "New content");
    }

    #[test]
    fn test_atomic_write_unicode() {
        let temp = TempDir::new().unwrap();
        let file_path = temp.path().join("unicode.txt");

        let content = "Hello 世界! 🦀";
        atomic_write(&file_path, content).unwrap();

        let read_content = std::fs::read_to_string(&file_path).unwrap();
        assert_eq!(read_content, content);
    }

    #[test]
    fn test_atomic_write_empty() {
        let temp = TempDir::new().unwrap();
        let file_path = temp.path().join("empty.txt");

        atomic_write(&file_path, "").unwrap();

        assert!(file_path.exists());
        let read_content = std::fs::read_to_string(&file_path).unwrap();
        assert_eq!(read_content, "");
    }

    #[test]
    fn test_atomic_write_large_content() {
        let temp = TempDir::new().unwrap();
        let file_path = temp.path().join("large.txt");

        // Create a large string
        let content = "x".repeat(1_000_000);
        atomic_write(&file_path, &content).unwrap();

        let read_content = std::fs::read_to_string(&file_path).unwrap();
        assert_eq!(read_content.len(), content.len());
    }

    #[test]
    fn test_list_files_with_extension() {
        let temp = TempDir::new().unwrap();

        // Create test files
        std::fs::write(temp.path().join("file1.txt"), "content1").unwrap();
        std::fs::write(temp.path().join("file2.txt"), "content2").unwrap();
        std::fs::write(temp.path().join("file3.pdf"), "content3").unwrap();
        std::fs::write(temp.path().join("file4.md"), "content4").unwrap();

        // Test listing .txt files
        let txt_files = list_files_with_extension(temp.path(), &["txt"]).unwrap();
        assert_eq!(txt_files.len(), 2);
        assert!(txt_files
            .iter()
            .any(|f| f.file_name().unwrap() == "file1.txt"));
        assert!(txt_files
            .iter()
            .any(|f| f.file_name().unwrap() == "file2.txt"));

        // Test listing multiple extensions
        let multi_files = list_files_with_extension(temp.path(), &["txt", "pdf"]).unwrap();
        assert_eq!(multi_files.len(), 3);

        // Test case insensitivity
        let upper_files = list_files_with_extension(temp.path(), &["TXT"]).unwrap();
        assert_eq!(upper_files.len(), 2);
    }

    #[test]
    fn test_list_files_with_extension_nonexistent_dir() {
        let files = list_files_with_extension("/nonexistent/path", &["txt"]).unwrap();
        assert!(files.is_empty());
    }

    #[test]
    fn test_list_files_with_extension_not_a_dir() {
        let temp = TempDir::new().unwrap();
        let file_path = temp.path().join("not_a_dir.txt");
        std::fs::write(&file_path, "content").unwrap();

        let result = list_files_with_extension(&file_path, &["txt"]);
        assert!(result.is_err());
    }

    #[test]
    fn test_validate_path_length_short() {
        let temp = TempDir::new().unwrap();
        let short_path = temp.path().join("short.txt");

        // Should succeed for short paths
        assert!(validate_path_length(&short_path).is_ok());
    }

    #[test]
    fn test_validate_path_length_reasonable() {
        // Test with a path that's long but reasonable
        let path = PathBuf::from(
            "/home/user/documents/projects/resumes/2024/january/software_engineer_position.txt",
        );
        assert!(validate_path_length(&path).is_ok());
    }
}
