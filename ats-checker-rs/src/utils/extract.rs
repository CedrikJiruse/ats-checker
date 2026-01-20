//! Text extraction from various file formats.

use std::path::Path;
use crate::error::{AtsError, Result};

/// Extract text from a file (TXT, PDF, DOCX, etc.).
pub fn extract_text_from_file(path: impl AsRef<Path>) -> Result<String> {
    let path = path.as_ref();
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");

    match ext.to_lowercase().as_str() {
        "txt" | "md" | "tex" => extract_text_file(path),
        "pdf" => extract_pdf(path),
        _ => extract_text_file(path), // Fallback
    }
}

fn extract_text_file(path: &Path) -> Result<String> {
    Ok(std::fs::read_to_string(path)?)
}

fn extract_pdf(path: &Path) -> Result<String> {
    // TODO: Implement PDF extraction using pdf-extract
    Err(AtsError::NotSupported {
        message: "PDF extraction not yet implemented".to_string(),
    })
}
