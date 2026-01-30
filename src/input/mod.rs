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

/// Supported resume file extensions (including OCR image formats).
const RESUME_EXTENSIONS: &[&str] = &[
    "txt", "pdf", "docx", "md", "tex", "png", "jpg", "jpeg", "tiff", "tif", "bmp",
];

/// Supported job description file extensions.
const JOB_EXTENSIONS: &[&str] = &["txt", "md"];

/// OCR image file extensions.
const OCR_EXTENSIONS: &[&str] = &["png", "jpg", "jpeg", "tiff", "tif", "bmp"];

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
    ///
    /// # Errors
    ///
    /// Returns an error if the directory cannot be read.
    pub fn list_resumes(&self) -> Result<Vec<PathBuf>> {
        self.list_files_with_extensions(&self.resumes_folder, RESUME_EXTENSIONS)
    }

    /// List all job description files in the jobs folder.
    ///
    /// Returns paths to all files with supported job extensions.
    ///
    /// # Errors
    ///
    /// Returns an error if the directory cannot be read.
    pub fn list_job_descriptions(&self) -> Result<Vec<PathBuf>> {
        self.list_files_with_extensions(&self.jobs_folder, JOB_EXTENSIONS)
    }

    /// List all new (unprocessed) resumes.
    ///
    /// Returns paths to resumes that haven't been processed yet according
    /// to the provided state manager.
    ///
    /// # Errors
    ///
    /// Returns an error if the directory cannot be read or file hashes cannot be calculated.
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
    ///
    /// # Errors
    ///
    /// Returns an error if the file cannot be read or text cannot be extracted.
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
    ///
    /// # Errors
    ///
    /// Returns an error if the file cannot be read or text cannot be extracted.
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
    ///
    /// # Errors
    ///
    /// Returns an error if the file cannot be read.
    pub fn calculate_resume_hash(&self, path: impl AsRef<Path>) -> Result<String> {
        calculate_file_hash(path)
    }

    /// Get a job description by name or path.
    ///
    /// Searches for a job description file with the given name (with or without extension).
    ///
    /// # Errors
    ///
    /// Returns an error if the directory cannot be read.
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

    /// Check if a file is an OCR image (requires Tesseract).
    pub fn is_ocr_file(path: impl AsRef<Path>) -> bool {
        if let Some(ext) = path.as_ref().extension().and_then(|e| e.to_str()) {
            OCR_EXTENSIONS.contains(&ext.to_lowercase().as_str())
        } else {
            false
        }
    }

    /// Interactive resume selection with full UX.
    ///
    /// Displays a numbered list of available resumes and prompts the user
    /// to select one. Returns the selected resume path.
    ///
    /// # Errors
    ///
    /// Returns an error if no resumes are found or the user makes an invalid selection.
    pub fn select_resume_interactive(&self) -> Result<Option<PathBuf>> {
        let resumes = self.list_resumes()?;

        if resumes.is_empty() {
            println!("No resumes found in {}", self.resumes_folder.display());
            return Ok(None);
        }

        println!("\nAvailable resumes:");
        println!("{}", "-".repeat(60));
        for (i, path) in resumes.iter().enumerate() {
            let filename = path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("unknown");
            let is_ocr = Self::is_ocr_file(path);
            let ocr_indicator = if is_ocr { " [OCR]" } else { "" };
            println!("  {}. {}{}", i + 1, filename, ocr_indicator);
        }
        println!("  0. Cancel");
        println!("{}", "-".repeat(60));

        print!("\nSelect resume (0-{}): ", resumes.len());
        std::io::Write::flush(&mut std::io::stdout()).ok();

        let mut input = String::new();
        std::io::stdin().read_line(&mut input).ok();

        match input.trim().parse::<usize>() {
            Ok(0) => Ok(None),
            Ok(n) if n <= resumes.len() => Ok(Some(resumes[n - 1].clone())),
            _ => {
                println!("Invalid selection.");
                Ok(None)
            }
        }
    }

    /// Interactive job description selection with full UX.
    ///
    /// Displays a numbered list of available job descriptions and prompts
    /// the user to select one. Returns the selected job path.
    ///
    /// # Errors
    ///
    /// Returns an error if no job descriptions are found or the user makes an invalid selection.
    pub fn select_job_description_interactive(&self) -> Result<Option<PathBuf>> {
        let jobs = self.list_job_descriptions()?;

        if jobs.is_empty() {
            println!(
                "No job descriptions found in {}",
                self.jobs_folder.display()
            );
            return Ok(None);
        }

        println!("\nAvailable job descriptions:");
        println!("{}", "-".repeat(60));
        for (i, path) in jobs.iter().enumerate() {
            let filename = path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("unknown");
            println!("  {}. {}", i + 1, filename);
        }
        println!("  0. Cancel");
        println!("{}", "-".repeat(60));

        print!("\nSelect job description (0-{}): ", jobs.len());
        std::io::Write::flush(&mut std::io::stdout()).ok();

        let mut input = String::new();
        std::io::stdin().read_line(&mut input).ok();

        match input.trim().parse::<usize>() {
            Ok(0) => Ok(None),
            Ok(n) if n <= jobs.len() => Ok(Some(jobs[n - 1].clone())),
            _ => {
                println!("Invalid selection.");
                Ok(None)
            }
        }
    }

    /// Select multiple resumes with multi-select support.
    ///
    /// Displays a numbered list and allows the user to select multiple
    /// resumes by entering comma-separated numbers or ranges (e.g., "1,3,5-7").
    /// Also supports "all" to select all resumes.
    ///
    /// # Errors
    ///
    /// Returns an error if no resumes are found or parsing fails.
    pub fn select_multiple_resumes(&self) -> Result<Vec<PathBuf>> {
        let resumes = self.list_resumes()?;

        if resumes.is_empty() {
            println!("No resumes found in {}", self.resumes_folder.display());
            return Ok(Vec::new());
        }

        println!("\nAvailable resumes:");
        println!("{}", "-".repeat(60));
        for (i, path) in resumes.iter().enumerate() {
            let filename = path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("unknown");
            let is_ocr = Self::is_ocr_file(path);
            let ocr_indicator = if is_ocr { " [OCR]" } else { "" };
            println!("  {}. {}{}", i + 1, filename, ocr_indicator);
        }
        println!("{}", "-".repeat(60));
        println!("Enter selection (e.g., '1,3,5' or '1-5' or 'all'), or '0' to cancel:");

        print!("Selection: ");
        std::io::Write::flush(&mut std::io::stdout()).ok();

        let mut input = String::new();
        std::io::stdin().read_line(&mut input).ok();
        let input = input.trim();

        if input == "0" || input.is_empty() {
            return Ok(Vec::new());
        }

        if input.to_lowercase() == "all" {
            return Ok(resumes);
        }

        let mut selected = Vec::new();
        let parts: Vec<&str> = input.split(',').collect();

        for part in parts {
            let part = part.trim();
            if part.contains('-') {
                // Range selection (e.g., "1-5")
                let range_parts: Vec<&str> = part.split('-').collect();
                if range_parts.len() == 2 {
                    if let (Ok(start), Ok(end)) = (
                        range_parts[0].trim().parse::<usize>(),
                        range_parts[1].trim().parse::<usize>(),
                    ) {
                        for i in start..=end {
                            if i > 0 && i <= resumes.len() {
                                selected.push(resumes[i - 1].clone());
                            }
                        }
                    }
                }
            } else if let Ok(n) = part.parse::<usize>() {
                if n > 0 && n <= resumes.len() {
                    selected.push(resumes[n - 1].clone());
                }
            }
        }

        // Remove duplicates while preserving order
        let mut unique = Vec::new();
        for path in selected {
            if !unique.contains(&path) {
                unique.push(path);
            }
        }

        Ok(unique)
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
            .filter_map(std::result::Result::ok)
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

    #[test]
    fn test_list_resumes() {
        let temp_dir = TempDir::new().unwrap();
        let resumes_path = temp_dir.path().join("resumes");
        fs::create_dir(&resumes_path).unwrap();

        // Create test resume files
        fs::write(resumes_path.join("resume1.txt"), "Resume 1").unwrap();
        fs::write(resumes_path.join("resume2.pdf"), "Resume 2").unwrap();
        fs::write(resumes_path.join("resume3.md"), "Resume 3").unwrap();

        let handler = InputHandler::new(&resumes_path, temp_dir.path());
        let resumes = handler.list_resumes().unwrap();

        assert_eq!(resumes.len(), 3);
    }

    #[test]
    fn test_list_job_descriptions() {
        let temp_dir = TempDir::new().unwrap();
        let jobs_path = temp_dir.path().join("jobs");
        fs::create_dir(&jobs_path).unwrap();

        // Create test job files
        fs::write(jobs_path.join("job1.txt"), "Job 1").unwrap();
        fs::write(jobs_path.join("job2.md"), "Job 2").unwrap();

        let handler = InputHandler::new(temp_dir.path(), &jobs_path);
        let jobs = handler.list_job_descriptions().unwrap();

        assert_eq!(jobs.len(), 2);
    }

    #[test]
    fn test_load_resume() {
        let temp_dir = TempDir::new().unwrap();
        let resume_path = temp_dir.path().join("test.txt");
        let content = "Test resume content";
        fs::write(&resume_path, content).unwrap();

        let handler = InputHandler::new(temp_dir.path(), temp_dir.path());
        let loaded = handler.load_resume(&resume_path).unwrap();

        assert_eq!(loaded, content);
    }

    #[test]
    fn test_load_resume_nonexistent() {
        let temp_dir = TempDir::new().unwrap();
        let handler = InputHandler::new(temp_dir.path(), temp_dir.path());
        let result = handler.load_resume("nonexistent.txt");

        assert!(result.is_err());
    }

    #[test]
    fn test_load_job_description() {
        let temp_dir = TempDir::new().unwrap();
        let job_path = temp_dir.path().join("job.txt");
        let content = "Test job description";
        fs::write(&job_path, content).unwrap();

        let handler = InputHandler::new(temp_dir.path(), temp_dir.path());
        let loaded = handler.load_job_description(&job_path).unwrap();

        assert_eq!(loaded, content);
    }

    #[test]
    fn test_calculate_resume_hash() {
        let temp_dir = TempDir::new().unwrap();
        let resume_path = temp_dir.path().join("resume.txt");
        fs::write(&resume_path, "Test content").unwrap();

        let handler = InputHandler::new(temp_dir.path(), temp_dir.path());
        let hash1 = handler.calculate_resume_hash(&resume_path).unwrap();
        let hash2 = handler.calculate_resume_hash(&resume_path).unwrap();

        // Same file should produce same hash
        assert_eq!(hash1, hash2);
        assert!(!hash1.is_empty());
    }

    #[test]
    fn test_find_job_description_exact_match() {
        let temp_dir = TempDir::new().unwrap();
        let jobs_path = temp_dir.path().join("jobs");
        fs::create_dir(&jobs_path).unwrap();

        fs::write(jobs_path.join("software_engineer.txt"), "Job content").unwrap();

        let handler = InputHandler::new(temp_dir.path(), &jobs_path);
        let found = handler
            .find_job_description("software_engineer.txt")
            .unwrap();

        assert!(found.is_some());
        assert!(found.unwrap().ends_with("software_engineer.txt"));
    }

    #[test]
    fn test_find_job_description_stem_match() {
        let temp_dir = TempDir::new().unwrap();
        let jobs_path = temp_dir.path().join("jobs");
        fs::create_dir(&jobs_path).unwrap();

        fs::write(jobs_path.join("backend_dev.txt"), "Job content").unwrap();

        let handler = InputHandler::new(temp_dir.path(), &jobs_path);
        let found = handler.find_job_description("backend_dev").unwrap();

        assert!(found.is_some());
        assert!(found.unwrap().ends_with("backend_dev.txt"));
    }

    #[test]
    fn test_find_job_description_not_found() {
        let temp_dir = TempDir::new().unwrap();
        let jobs_path = temp_dir.path().join("jobs");
        fs::create_dir(&jobs_path).unwrap();

        let handler = InputHandler::new(temp_dir.path(), &jobs_path);
        let found = handler.find_job_description("nonexistent").unwrap();

        assert!(found.is_none());
    }

    #[test]
    fn test_validate_file_exists() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("test.txt");
        fs::write(&file_path, "content").unwrap();

        let handler = InputHandler::new(temp_dir.path(), temp_dir.path());
        let result = handler.validate_file_exists(&file_path);

        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_file_nonexistent() {
        let temp_dir = TempDir::new().unwrap();
        let handler = InputHandler::new(temp_dir.path(), temp_dir.path());
        let nonexistent = temp_dir.path().join("nonexistent.txt");
        let result = handler.validate_file_exists(&nonexistent);

        assert!(result.is_err());
    }

    #[test]
    fn test_validate_file_is_directory() {
        let temp_dir = TempDir::new().unwrap();
        let dir_path = temp_dir.path().join("testdir");
        fs::create_dir(&dir_path).unwrap();

        let handler = InputHandler::new(temp_dir.path(), temp_dir.path());
        let result = handler.validate_file_exists(&dir_path);

        assert!(result.is_err());
    }

    #[test]
    fn test_is_ocr_file() {
        assert!(InputHandler::is_ocr_file("resume.png"));
        assert!(InputHandler::is_ocr_file("resume.jpg"));
        assert!(InputHandler::is_ocr_file("resume.jpeg"));
        assert!(InputHandler::is_ocr_file("resume.tiff"));
        assert!(InputHandler::is_ocr_file("resume.tif"));
        assert!(InputHandler::is_ocr_file("resume.bmp"));
        assert!(!InputHandler::is_ocr_file("resume.txt"));
        assert!(!InputHandler::is_ocr_file("resume.pdf"));
        assert!(!InputHandler::is_ocr_file("resume.docx"));
    }

    #[test]
    fn test_list_resumes_with_ocr_files() {
        let temp_dir = TempDir::new().unwrap();
        let resumes_path = temp_dir.path().join("resumes");
        fs::create_dir(&resumes_path).unwrap();

        // Create test resume files including OCR images
        fs::write(resumes_path.join("resume1.txt"), "Resume 1").unwrap();
        fs::write(resumes_path.join("resume2.pdf"), "Resume 2").unwrap();
        fs::write(resumes_path.join("resume3.png"), "PNG content").unwrap();
        fs::write(resumes_path.join("resume4.jpg"), "JPG content").unwrap();

        let handler = InputHandler::new(&resumes_path, temp_dir.path());
        let resumes = handler.list_resumes().unwrap();

        assert_eq!(resumes.len(), 4);
        assert!(resumes.iter().any(|f| f.ends_with("resume1.txt")));
        assert!(resumes.iter().any(|f| f.ends_with("resume2.pdf")));
        assert!(resumes.iter().any(|f| f.ends_with("resume3.png")));
        assert!(resumes.iter().any(|f| f.ends_with("resume4.jpg")));
    }
}
