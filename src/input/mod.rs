//! Input handling module.
//!
//! This module handles loading resumes and job descriptions from the filesystem.
//! It supports multiple file formats (TXT, PDF, DOCX, MD) and provides utilities
//! for file discovery and content extraction.

use crate::error::{AtsError, Result};
use crate::state::StateManager;
use crate::utils::extract::extract_text_from_file;
use crate::utils::hash::calculate_file_hash;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

/// Supported resume file extensions.
const RESUME_EXTENSIONS: &[&str] = &["txt", "pdf", "docx", "md", "tex"];

/// Supported job description file extensions.
const JOB_EXTENSIONS: &[&str] = &["txt", "md"];

/// Input handler for resumes and job descriptions.
pub struct InputHandler {
    resumes_folder: PathBuf,
    jobs_folder: PathBuf,
}

impl InputHandler {
    /// Create a new input handler.
    ///
    /// # Arguments
    ///
    /// * `resumes_folder` - Path to the folder containing resumes
    /// * `jobs_folder` - Path to the folder containing job descriptions
    pub fn new(resumes_folder: impl Into<PathBuf>, jobs_folder: impl Into<PathBuf>) -> Self {
        Self {
            resumes_folder: resumes_folder.into(),
            jobs_folder: jobs_folder.into(),
        }
    }

    /// List all resume files in the resumes folder.
    ///
    /// Returns paths to all files with supported resume extensions.
    pub fn list_resumes(&self) -> Result<Vec<PathBuf>> {
        self.list_files_with_extensions(&self.resumes_folder, RESUME_EXTENSIONS)
    }

    /// List all job description files in the jobs folder.
    ///
    /// Returns paths to all files with supported job extensions.
    pub fn list_job_descriptions(&self) -> Result<Vec<PathBuf>> {
        self.list_files_with_extensions(&self.jobs_folder, JOB_EXTENSIONS)
    }

    /// List all new (unprocessed) resumes.
    ///
    /// Returns paths to resumes that haven't been processed yet according
    /// to the provided state manager.
    pub fn list_new_resumes(&self, state_manager: &StateManager) -> Result<Vec<PathBuf>> {
        let all_resumes = self.list_resumes()?;
        let mut new_resumes = Vec::new();

        for path in all_resumes {
            let hash = calculate_file_hash(&path)?;
            if !state_manager.is_processed(&hash) {
                new_resumes.push(path);
            }
        }

        Ok(new_resumes)
    }

    /// Load the content of a resume file.
    ///
    /// Extracts text from the file using format-specific extraction.
    pub fn load_resume(&self, path: impl AsRef<Path>) -> Result<String> {
        let path = path.as_ref();
        self.validate_file_exists(path)?;

        extract_text_from_file(path).map_err(|e| AtsError::TextExtraction {
            message: format!("Failed to extract text from {}: {}", path.display(), e),
        })
    }

    /// Load the content of a job description file.
    ///
    /// Extracts text from the file.
    pub fn load_job_description(&self, path: impl AsRef<Path>) -> Result<String> {
        let path = path.as_ref();
        self.validate_file_exists(path)?;

        extract_text_from_file(path).map_err(|e| AtsError::TextExtraction {
            message: format!("Failed to extract text from {}: {}", path.display(), e),
        })
    }

    /// Calculate the hash of a resume file.
    ///
    /// Used to check if a resume has been processed before.
    pub fn calculate_resume_hash(&self, path: impl AsRef<Path>) -> Result<String> {
        calculate_file_hash(path)
    }

    /// Get a job description by name or path.
    ///
    /// Searches for a job description file with the given name (with or without extension).
    pub fn find_job_description(&self, name: &str) -> Result<Option<PathBuf>> {
        let all_jobs = self.list_job_descriptions()?;

        // Try exact match first
        for job_path in &all_jobs {
            if let Some(filename) = job_path.file_name().and_then(|n| n.to_str()) {
                if filename == name {
                    return Ok(Some(job_path.clone()));
                }
            }
        }

        // Try match without extension
        for job_path in &all_jobs {
            if let Some(stem) = job_path.file_stem().and_then(|s| s.to_str()) {
                if stem == name {
                    return Ok(Some(job_path.clone()));
                }
            }
        }

        Ok(None)
    }

    /// Get the base name of a resume file (without extension).
    ///
    /// Used for organizing output files.
    pub fn get_resume_basename(&self, path: impl AsRef<Path>) -> String {
        path.as_ref()
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string()
    }

    /// Get the base name of a job description file (without extension).
    pub fn get_job_basename(&self, path: impl AsRef<Path>) -> String {
        path.as_ref()
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string()
    }

    /// Validate that a file exists.
    fn validate_file_exists(&self, path: &Path) -> Result<()> {
        if !path.exists() {
            return Err(AtsError::FileNotFound {
                path: path.to_path_buf(),
            });
        }

        if !path.is_file() {
            return Err(AtsError::InputValidation {
                message: format!("{} is not a file", path.display()),
            });
        }

        Ok(())
    }

    /// List files with specific extensions in a directory.
    fn list_files_with_extensions(&self, dir: &Path, extensions: &[&str]) -> Result<Vec<PathBuf>> {
        if !dir.exists() {
            return Ok(Vec::new());
        }

        if !dir.is_dir() {
            return Err(AtsError::InputValidation {
                message: format!("{} is not a directory", dir.display()),
            });
        }

        let mut files = Vec::new();

        for entry in WalkDir::new(dir)
            .max_depth(1)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();

            if !path.is_file() {
                continue;
            }

            if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                if extensions.contains(&ext.to_lowercase().as_str()) {
                    files.push(path.to_path_buf());
                }
            }
        }

        // Sort by filename for deterministic ordering
        files.sort();

        Ok(files)
    }
}

impl Default for InputHandler {
    fn default() -> Self {
        Self::new("workspace/input_resumes", "workspace/job_descriptions")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_input_handler_creation() {
        let handler = InputHandler::new("/tmp/resumes", "/tmp/jobs");
        assert_eq!(handler.resumes_folder, PathBuf::from("/tmp/resumes"));
        assert_eq!(handler.jobs_folder, PathBuf::from("/tmp/jobs"));
    }

    #[test]
    fn test_list_files_with_extensions() {
        let temp_dir = TempDir::new().unwrap();
        let dir_path = temp_dir.path();

        // Create test files
        fs::write(dir_path.join("resume1.txt"), "content").unwrap();
        fs::write(dir_path.join("resume2.pdf"), "content").unwrap();
        fs::write(dir_path.join("resume3.docx"), "content").unwrap();
        fs::write(dir_path.join("ignored.csv"), "content").unwrap();

        let handler = InputHandler::new(dir_path, dir_path);
        let files = handler
            .list_files_with_extensions(dir_path, RESUME_EXTENSIONS)
            .unwrap();

        assert_eq!(files.len(), 3);
        assert!(files.iter().any(|f| f.ends_with("resume1.txt")));
        assert!(files.iter().any(|f| f.ends_with("resume2.pdf")));
        assert!(files.iter().any(|f| f.ends_with("resume3.docx")));
        assert!(!files.iter().any(|f| f.ends_with("ignored.csv")));
    }

    #[test]
    fn test_get_resume_basename() {
        let handler = InputHandler::default();
        assert_eq!(
            handler.get_resume_basename("/path/to/john_doe.txt"),
            "john_doe"
        );
        assert_eq!(handler.get_resume_basename("/path/to/resume.pdf"), "resume");
    }

    #[test]
    fn test_list_nonexistent_directory() {
        let handler = InputHandler::new("/nonexistent/path", "/nonexistent/path");
        let result = handler.list_resumes();
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), 0);
    }
}
