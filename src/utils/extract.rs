//! Text extraction from various file formats.
//!
//! This module provides functions to extract text from various file formats including:
//! - Plain text files (.txt, .md, .tex)
//! - PDF documents (.pdf)
//! - Microsoft Word documents (.docx)
//!
//! # Example
//!
//! ```no_run
//! use ats_checker::utils::extract::extract_text_from_file;
//!
//! let text = extract_text_from_file("resume.pdf").expect("Failed to extract text");
//! println!("Extracted text: {}", text);
//! ```

use crate::error::{AtsError, Result};
use std::path::Path;

/// Extract text from a file (TXT, PDF, DOCX, etc.).
///
/// Automatically detects the file type based on extension and uses the appropriate
/// extraction method.
///
/// # Supported Formats
///
/// - `.txt`, `.md`, `.tex` - Plain text files
/// - `.pdf` - PDF documents
/// - `.docx` - Microsoft Word documents
///
/// # Errors
///
/// Returns an error if:
/// - The file cannot be read
/// - The format is not supported
/// - The file is corrupted or malformed
///
/// # Example
///
/// ```no_run
/// use ats_checker::utils::extract::extract_text_from_file;
///
/// let text = extract_text_from_file("document.pdf")?;
/// # Ok::<(), ats_checker::error::AtsError>(())
/// ```
pub fn extract_text_from_file(path: impl AsRef<Path>) -> Result<String> {
    let path = path.as_ref();
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");

    match ext.to_lowercase().as_str() {
        "txt" | "md" | "tex" => extract_text_file(path),
        "pdf" => extract_pdf(path),
        "docx" => extract_docx(path),
        _ => extract_text_file(path), // Fallback to plain text
    }
}

/// Extract text from plain text files.
fn extract_text_file(path: &Path) -> Result<String> {
    std::fs::read_to_string(path).map_err(|e| AtsError::Io {
        message: format!("Failed to read text file: {}", path.display()),
        source: e,
    })
}

/// Extract text from PDF files.
///
/// # Errors
///
/// Returns an error if:
/// - The PDF file cannot be read
/// - The PDF is encrypted (encrypted PDFs not supported)
/// - The PDF is corrupted
fn extract_pdf(path: &Path) -> Result<String> {
    use pdf_extract::extract_text_from_mem;

    // Extract text from the PDF
    let bytes = std::fs::read(path).map_err(|e| AtsError::Io {
        message: format!("Failed to read PDF file: {}", path.display()),
        source: e,
    })?;

    let text = extract_text_from_mem(&bytes).map_err(|e| AtsError::PdfExtraction {
        message: format!("Failed to extract text from PDF: {e}"),
    })?;

    Ok(normalize_text(&text))
}

/// Normalize extracted text.
///
/// Performs the following normalizations:
/// - Removes excessive whitespace (multiple spaces/tabs become single space)
/// - Normalizes line endings to Unix style (\n)
/// - Removes leading/trailing whitespace from each line
/// - Removes empty lines at start and end
///
/// # Arguments
///
/// * `text` - The text to normalize
///
/// # Returns
///
/// Normalized text string
///
/// # Example
///
/// ```
/// use ats_checker::utils::extract::normalize_text;
///
/// let text = "Hello   world\r\n\t\tTest  ";
/// let normalized = normalize_text(text);
/// assert_eq!(normalized, "Hello world\nTest");
/// ```
pub fn normalize_text(text: &str) -> String {
    // Normalize line endings to \n
    let text = text.replace("\r\n", "\n").replace('\r', "\n");

    // Process each line
    let lines: Vec<String> = text
        .lines()
        .map(|line| {
            // Replace tabs and multiple spaces with single space
            let line = line.replace('\t', " ");
            // Collapse multiple spaces into one
            let line = line.split_whitespace().collect::<Vec<_>>().join(" ");
            line
        })
        .filter(|line| !line.is_empty())
        .collect();

    lines.join("\n")
}

/// Remove excessive whitespace from text.
///
/// Replaces multiple consecutive whitespace characters with a single space.
///
/// # Arguments
///
/// * `text` - The text to process
///
/// # Returns
///
/// Text with normalized whitespace
///
/// # Example
///
/// ```
/// use ats_checker::utils::extract::remove_excessive_whitespace;
///
/// let text = "Hello    world   test";
/// let result = remove_excessive_whitespace(text);
/// assert_eq!(result, "Hello world test");
/// ```
pub fn remove_excessive_whitespace(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Extract text from DOCX files.
///
/// # Errors
///
/// Returns an error if:
/// - The DOCX file cannot be read
/// - The DOCX is corrupted or malformed
fn extract_docx(path: &Path) -> Result<String> {
    use docx_rs::{read_docx, DocumentChild, ParagraphChild, RunChild};
    use std::fs::File;
    use std::io::Read;

    // Open and read the file
    let mut file = File::open(path).map_err(|e| AtsError::Io {
        message: format!("Failed to open DOCX file: {}", path.display()),
        source: e,
    })?;

    let mut buf = Vec::new();
    file.read_to_end(&mut buf).map_err(|e| AtsError::Io {
        message: format!("Failed to read DOCX file: {}", path.display()),
        source: e,
    })?;

    // Parse the DOCX file
    let docx = read_docx(&buf).map_err(|e| AtsError::DocxExtraction {
        message: format!("Failed to parse DOCX: {e}"),
    })?;

    // Extract text from all paragraphs (simplified - only handles paragraphs with runs)
    let mut text = String::new();
    for child in &docx.document.children {
        if let DocumentChild::Paragraph(p) = child {
            for run in &p.children {
                if let ParagraphChild::Run(r) = run {
                    for run_child in &r.children {
                        if let RunChild::Text(t) = run_child {
                            text.push_str(&t.text);
                        }
                    }
                }
            }
            text.push('\n');
        }
    }

    Ok(text)
}
