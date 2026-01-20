//! Saved search management.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use crate::error::{AtsError, Result};
use crate::scraper::SavedSearch;

/// Manages saved job searches.
pub struct SavedSearchManager {
    /// Path to the saved searches file.
    file_path: PathBuf,
    /// In-memory cache of saved searches.
    searches: HashMap<String, SavedSearch>,
}

impl SavedSearchManager {
    /// Create a new saved search manager.
    ///
    /// Loads existing saved searches from the file if it exists.
    pub fn new(file_path: impl AsRef<Path>) -> Result<Self> {
        let file_path = file_path.as_ref().to_path_buf();
        let searches = if file_path.exists() {
            Self::load_from_file(&file_path)?
        } else {
            HashMap::new()
        };

        Ok(Self { file_path, searches })
    }

    /// Save a search configuration.
    pub fn save(&mut self, search: SavedSearch) -> Result<()> {
        self.searches.insert(search.name.clone(), search);
        self.persist()
    }

    /// Get a saved search by name.
    pub fn get(&self, name: &str) -> Option<&SavedSearch> {
        self.searches.get(name)
    }

    /// Get a mutable reference to a saved search.
    pub fn get_mut(&mut self, name: &str) -> Option<&mut SavedSearch> {
        self.searches.get_mut(name)
    }

    /// List all saved search names.
    pub fn list(&self) -> Vec<&str> {
        self.searches.keys().map(String::as_str).collect()
    }

    /// Delete a saved search.
    pub fn delete(&mut self, name: &str) -> Result<()> {
        self.searches.remove(name);
        self.persist()
    }

    /// Update the last run timestamp for a search.
    pub fn update_last_run(&mut self, name: &str) -> Result<()> {
        if let Some(search) = self.searches.get_mut(name) {
            search.update_last_run();
            self.persist()?;
        }
        Ok(())
    }

    /// Check if a search exists.
    pub fn exists(&self, name: &str) -> bool {
        self.searches.contains_key(name)
    }

    /// Get the number of saved searches.
    pub fn count(&self) -> usize {
        self.searches.len()
    }

    /// Persist searches to disk.
    fn persist(&self) -> Result<()> {
        // Ensure parent directory exists
        if let Some(parent) = self.file_path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let wrapper = SavedSearchesWrapper {
            searches: self.searches.clone(),
        };

        let toml_str = toml::to_string_pretty(&wrapper).map_err(|e| {
            AtsError::TomlParse {
                message: e.to_string(),
                source: None,
            }
        })?;

        // Atomic write
        let temp_path = self.file_path.with_extension("tmp");
        std::fs::write(&temp_path, toml_str)?;
        std::fs::rename(&temp_path, &self.file_path)?;

        Ok(())
    }

    /// Load saved searches from a file.
    fn load_from_file(path: &Path) -> Result<HashMap<String, SavedSearch>> {
        let content = std::fs::read_to_string(path)?;
        let wrapper: SavedSearchesWrapper = toml::from_str(&content)?;
        Ok(wrapper.searches)
    }
}

use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct SavedSearchesWrapper {
    #[serde(default)]
    searches: HashMap<String, SavedSearch>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::scraper::SearchFilters;
    use tempfile::tempdir;

    #[test]
    fn test_saved_search_manager_new() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("searches.toml");

        let manager = SavedSearchManager::new(&path).unwrap();
        assert_eq!(manager.count(), 0);
        assert!(manager.list().is_empty());
    }

    #[test]
    fn test_save_and_get() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("searches.toml");

        let mut manager = SavedSearchManager::new(&path).unwrap();

        let filters = SearchFilters::builder().keywords("rust").build();
        let search = SavedSearch::new("rust-jobs", filters, vec!["linkedin".to_string()]);

        manager.save(search).unwrap();

        assert!(manager.exists("rust-jobs"));
        let retrieved = manager.get("rust-jobs").unwrap();
        assert_eq!(retrieved.name, "rust-jobs");
    }

    #[test]
    fn test_persistence() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("searches.toml");

        {
            let mut manager = SavedSearchManager::new(&path).unwrap();
            let filters = SearchFilters::builder().keywords("python").build();
            let search = SavedSearch::new("python-jobs", filters, vec!["indeed".to_string()]);
            manager.save(search).unwrap();
        }

        // Load again and verify
        let manager = SavedSearchManager::new(&path).unwrap();
        assert!(manager.exists("python-jobs"));
    }

    #[test]
    fn test_delete() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("searches.toml");

        let mut manager = SavedSearchManager::new(&path).unwrap();
        let filters = SearchFilters::default();
        let search = SavedSearch::new("temp", filters, vec![]);
        manager.save(search).unwrap();

        assert!(manager.exists("temp"));
        manager.delete("temp").unwrap();
        assert!(!manager.exists("temp"));
    }
}
