//! File operation utilities.

use std::path::Path;
use crate::error::Result;

/// Ensure a directory exists.
pub fn ensure_directory(path: impl AsRef<Path>) -> Result<()> {
    std::fs::create_dir_all(path.as_ref())?;
    Ok(())
}

/// Atomic write to a file.
pub fn atomic_write(path: impl AsRef<Path>, content: &str) -> Result<()> {
    let path = path.as_ref();
    let temp_path = path.with_extension("tmp");
    std::fs::write(&temp_path, content)?;
    std::fs::rename(&temp_path, path)?;
    Ok(())
}
