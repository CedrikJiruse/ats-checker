//! File hashing utilities.

use crate::error::Result;
use sha2::{Digest, Sha256};
use std::path::Path;

/// Calculate SHA256 hash of a file.
///
/// # Errors
///
/// Returns an error if the file cannot be opened or read.
///
/// # Examples
///
/// ```no_run
/// use ats_checker::utils::hash::calculate_file_hash;
/// use std::path::Path;
///
/// let hash = calculate_file_hash(Path::new("file.txt")).unwrap();
/// assert_eq!(hash.len(), 64); // SHA256 is 64 hex characters
/// ```
pub fn calculate_file_hash(path: impl AsRef<Path>) -> Result<String> {
    use std::io::Read;

    let path = path.as_ref();
    let mut file = std::fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 8192];

    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }

    Ok(hex::encode(hasher.finalize()))
}

/// Calculate SHA256 hash of a string.
///
/// # Examples
///
/// ```
/// use ats_checker::utils::hash::calculate_string_hash;
///
/// let hash = calculate_string_hash("hello world");
/// assert_eq!(hash.len(), 64); // SHA256 is 64 hex characters
/// assert_eq!(hash, "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9");
/// ```
pub fn calculate_string_hash(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    hex::encode(hasher.finalize())
}

/// Calculate SHA256 hash of byte slice.
///
/// # Examples
///
/// ```
/// use ats_checker::utils::hash::calculate_bytes_hash;
///
/// let data = b"hello world";
/// let hash = calculate_bytes_hash(data);
/// assert_eq!(hash.len(), 64); // SHA256 is 64 hex characters
/// assert_eq!(hash, "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9");
/// ```
pub fn calculate_bytes_hash(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex::encode(hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_hash_consistency() {
        let mut file = NamedTempFile::new().unwrap();
        file.write_all(b"test content").unwrap();

        let hash1 = calculate_file_hash(file.path()).unwrap();
        let hash2 = calculate_file_hash(file.path()).unwrap();

        assert_eq!(hash1, hash2);
        assert_eq!(hash1.len(), 64); // SHA256 produces 64 hex chars
    }
}
