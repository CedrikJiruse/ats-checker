//! State management module.
//!
//! Tracks processed resumes by content hash to avoid reprocessing.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::error::{AtsError, Result};

/// State entry for a processed resume.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResumeState {
    /// Path to the generated output.
    pub output_path: String,
}

/// Manages persistent state for processed resumes.
///
/// Stores a mapping of file hash -> output metadata in TOML format.
pub struct StateManager {
    /// Path to the state file.
    state_filepath: PathBuf,
    /// In-memory state.
    state: HashMap<String, ResumeState>,
}

impl StateManager {
    /// Create a new state manager.
    ///
    /// Loads existing state from the file if it exists.
    pub fn new(state_filepath: impl AsRef<Path>) -> Result<Self> {
        let state_filepath = state_filepath.as_ref().to_path_buf();
        let state = Self::load_state(&state_filepath)?;

        Ok(Self {
            state_filepath,
            state,
        })
    }

    /// Get the state for a resume by its hash.
    pub fn get_resume_state(&self, file_hash: &str) -> Option<&ResumeState> {
        self.state.get(file_hash)
    }

    /// Update the state for a processed resume.
    pub fn update_resume_state(&mut self, file_hash: &str, output_path: &str) -> Result<()> {
        self.state.insert(
            file_hash.to_string(),
            ResumeState {
                output_path: output_path.to_string(),
            },
        );
        self.save_state()
    }

    /// Check if a resume has been processed.
    pub fn is_processed(&self, file_hash: &str) -> bool {
        self.state.contains_key(file_hash)
    }

    /// Remove state for a resume.
    pub fn remove_state(&mut self, file_hash: &str) -> Result<()> {
        self.state.remove(file_hash);
        self.save_state()
    }

    /// Clear all state.
    pub fn clear_all(&mut self) -> Result<()> {
        self.state.clear();
        self.save_state()
    }

    /// List all stored hashes.
    pub fn list_all_hashes(&self) -> Vec<&str> {
        self.state.keys().map(String::as_str).collect()
    }

    /// Get the number of processed resumes.
    pub fn count(&self) -> usize {
        self.state.len()
    }

    /// Load state from file.
    fn load_state(path: &Path) -> Result<HashMap<String, ResumeState>> {
        if !path.exists() {
            // Try legacy JSON migration
            let json_path = path.with_extension("json");
            if json_path.exists() {
                log::info!("Migrating legacy JSON state from {:?}", json_path);
                return Self::load_legacy_json(&json_path);
            }
            return Ok(HashMap::new());
        }

        let content = std::fs::read_to_string(path)?;
        let wrapper: StateWrapper = toml::from_str(&content)?;
        Ok(wrapper.resumes)
    }

    /// Load legacy JSON state file.
    fn load_legacy_json(path: &Path) -> Result<HashMap<String, ResumeState>> {
        let content = std::fs::read_to_string(path)?;
        let state: HashMap<String, ResumeState> = serde_json::from_str(&content)?;
        Ok(state)
    }

    /// Save state to file.
    fn save_state(&self) -> Result<()> {
        // Ensure parent directory exists
        if let Some(parent) = self.state_filepath.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let wrapper = StateWrapper {
            resumes: self.state.clone(),
        };

        let toml_str = toml::to_string_pretty(&wrapper).map_err(|e| {
            AtsError::TomlParse {
                message: e.to_string(),
                source: None,
            }
        })?;

        // Atomic write
        let temp_path = self.state_filepath.with_extension("tmp");
        std::fs::write(&temp_path, toml_str)?;
        std::fs::rename(&temp_path, &self.state_filepath)?;

        log::debug!("State saved to {:?}", self.state_filepath);
        Ok(())
    }
}

#[derive(Debug, Serialize, Deserialize)]
struct StateWrapper {
    #[serde(default)]
    resumes: HashMap<String, ResumeState>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_state_manager_new() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("state.toml");

        let manager = StateManager::new(&path).unwrap();
        assert_eq!(manager.count(), 0);
    }

    #[test]
    fn test_update_and_get() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("state.toml");

        let mut manager = StateManager::new(&path).unwrap();
        manager.update_resume_state("abc123", "output/file.txt").unwrap();

        assert!(manager.is_processed("abc123"));
        let state = manager.get_resume_state("abc123").unwrap();
        assert_eq!(state.output_path, "output/file.txt");
    }

    #[test]
    fn test_persistence() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("state.toml");

        {
            let mut manager = StateManager::new(&path).unwrap();
            manager.update_resume_state("hash1", "path1").unwrap();
        }

        let manager = StateManager::new(&path).unwrap();
        assert!(manager.is_processed("hash1"));
    }

    #[test]
    fn test_remove_state() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("state.toml");

        let mut manager = StateManager::new(&path).unwrap();
        manager.update_resume_state("hash", "path").unwrap();
        assert!(manager.is_processed("hash"));

        manager.remove_state("hash").unwrap();
        assert!(!manager.is_processed("hash"));
    }
}
