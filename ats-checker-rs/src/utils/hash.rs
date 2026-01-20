//! File hashing utilities.

use std::path::Path;
use sha2::{Sha256, Digest};
use crate::error::{AtsError, Result};

/// Calculate SHA256 hash of a file.
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
