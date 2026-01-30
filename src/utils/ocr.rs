//! OCR (Optical Character Recognition) utilities.
//!
//! Provides text extraction from images using Tesseract OCR.
//!
//! # Requirements
//!
//! - Tesseract OCR must be installed on the system
//! - The `tesseract` binary must be in the system PATH
//!
//! # Installation
//!
//! ## Windows
//! Download and install from: <https://github.com/UB-Mannheim/tesseract/wiki>
//!
//! ## Linux
//! ```bash
//! sudo apt-get install tesseract-ocr
//! ```
//!
//! ## macOS
//! ```bash
//! brew install tesseract
//! ```

use crate::error::{AtsError, Result};
use std::path::Path;
use std::process::Command;

/// Extract text from an image file using OCR.
///
/// # Arguments
///
/// * `path` - Path to the image file (PNG, JPG, TIFF, etc.)
/// * `language` - Optional language code (e.g., "eng", "spa"). Defaults to "eng"
///
/// # Errors
///
/// Returns an error if:
/// - Tesseract is not installed or not in PATH
/// - The image file cannot be read
/// - OCR processing fails
///
/// # Examples
///
/// ```no_run
/// use ats_checker::utils::ocr::extract_text_from_image;
///
/// let text = extract_text_from_image("resume_scan.png", None)?;
/// println!("Extracted text: {}", text);
/// # Ok::<(), ats_checker::error::AtsError>(())
/// ```
pub fn extract_text_from_image(path: impl AsRef<Path>, language: Option<&str>) -> Result<String> {
    let path = path.as_ref();

    // Verify file exists
    if !path.exists() {
        return Err(AtsError::FileNotFound {
            path: path.to_path_buf(),
        });
    }

    // Verify Tesseract is installed
    check_tesseract_installed()?;

    // Build tesseract command
    let mut cmd = Command::new("tesseract");
    cmd.arg(path.as_os_str());
    cmd.arg("stdout"); // Output to stdout instead of file

    // Set language
    if let Some(lang) = language {
        cmd.arg("-l").arg(lang);
    }

    // Execute tesseract
    let output = cmd.output().map_err(|e| AtsError::Ocr {
        message: format!("Failed to execute Tesseract: {e}"),
    })?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(AtsError::Ocr {
            message: format!("Tesseract failed: {stderr}"),
        });
    }

    let text = String::from_utf8_lossy(&output.stdout).to_string();

    Ok(text.trim().to_string())
}

/// Check if Tesseract is installed and accessible.
///
/// # Errors
///
/// Returns an error if Tesseract is not found in PATH.
pub fn check_tesseract_installed() -> Result<()> {
    let output = Command::new("tesseract")
        .arg("--version")
        .output()
        .map_err(|e| AtsError::TesseractNotFound {
            path: format!(
                "Tesseract OCR not found in PATH: {e}. Please install Tesseract and ensure it's in your PATH."
            ),
        })?;

    if !output.status.success() {
        return Err(AtsError::TesseractNotFound {
            path: "Tesseract is installed but not working correctly".to_string(),
        });
    }

    Ok(())
}

/// Get Tesseract version information.
///
/// # Errors
///
/// Returns an error if Tesseract is not installed.
pub fn get_tesseract_version() -> Result<String> {
    check_tesseract_installed()?;

    let output = Command::new("tesseract")
        .arg("--version")
        .output()
        .map_err(|e| AtsError::Ocr {
            message: format!("Failed to get Tesseract version: {e}"),
        })?;

    let version = String::from_utf8_lossy(&output.stdout).to_string();

    Ok(version.lines().next().unwrap_or("Unknown").to_string())
}

/// Supported image formats for OCR.
pub const SUPPORTED_IMAGE_FORMATS: &[&str] = &["png", "jpg", "jpeg", "tiff", "tif", "bmp"];

/// Check if a file extension is a supported image format.
pub fn is_supported_image_format(extension: &str) -> bool {
    SUPPORTED_IMAGE_FORMATS
        .iter()
        .any(|&ext| ext.eq_ignore_ascii_case(extension))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tesseract_check() {
        // This test will pass if Tesseract is installed, otherwise it will fail gracefully
        let result = check_tesseract_installed();

        if result.is_ok() {
            println!("Tesseract is installed");
        } else {
            println!("Tesseract is not installed (this is OK for CI/CD)");
        }
    }

    #[test]
    fn test_supported_image_formats() {
        assert!(is_supported_image_format("png"));
        assert!(is_supported_image_format("PNG"));
        assert!(is_supported_image_format("jpg"));
        assert!(is_supported_image_format("jpeg"));
        assert!(is_supported_image_format("tiff"));
        assert!(is_supported_image_format("bmp"));

        assert!(!is_supported_image_format("pdf"));
        assert!(!is_supported_image_format("docx"));
        assert!(!is_supported_image_format("txt"));
    }

    #[test]
    fn test_extract_text_nonexistent_file() {
        let result = extract_text_from_image("nonexistent_image.png", None);

        assert!(result.is_err());
        match result.unwrap_err() {
            AtsError::FileNotFound { .. } => {} // Expected
            e => panic!("Expected FileNotFound, got: {e:?}"),
        }
    }

    #[test]
    #[ignore = "Only run when Tesseract is installed"]
    fn test_get_tesseract_version() {
        let result = get_tesseract_version();

        if let Ok(version) = result {
            assert!(!version.is_empty());
            assert!(version.contains("tesseract"));
        }
    }
}
