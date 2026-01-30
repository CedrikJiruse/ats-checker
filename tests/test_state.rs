//! Integration tests for state management.

mod common;

use ats_checker::state::StateManager;
use common::*;

#[test]
fn test_state_manager_new_with_nonexistent_file() {
    let temp_dir = create_temp_dir();
    let state_file = temp_dir.path().join("state.toml");

    // Create state manager with nonexistent file
    let manager = StateManager::new(state_file.clone())
        .expect("Failed to create state manager");

    // State file won't exist until first save
    // But manager should work fine
    assert!(!manager.is_processed("nonexistent_hash"));
}

#[test]
fn test_state_manager_update_and_retrieve() {
    let temp_dir = create_temp_dir();
    let state_file = temp_dir.path().join("state.toml");

    let mut manager = StateManager::new(state_file.clone())
        .expect("Failed to create state manager");

    // Update state with a resume hash
    let hash = "abc123def456";
    let output_path = "/path/to/output.json";

    manager.update_resume_state(hash, output_path)
        .expect("Failed to update state");

    // Should now be marked as processed
    assert!(manager.is_processed(hash));

    // Should be able to retrieve the state
    let state = manager.get_resume_state(hash)
        .expect("State should exist");
    assert_eq!(state.output_path, output_path);
}

#[test]
fn test_state_manager_persistence() {
    let temp_dir = create_temp_dir();
    let state_file = temp_dir.path().join("state.toml");

    // Create manager and add some state
    {
        let mut manager = StateManager::new(state_file.clone())
            .expect("Failed to create state manager");

        manager.update_resume_state("hash1", "/output1.json")
            .expect("Failed to update state");
        manager.update_resume_state("hash2", "/output2.json")
            .expect("Failed to update state");
    }

    // Create a new manager from the same file
    let manager = StateManager::new(state_file)
        .expect("Failed to load state manager");

    // Both hashes should still be present
    assert!(manager.is_processed("hash1"));
    assert!(manager.is_processed("hash2"));

    // Verify output paths
    assert_eq!(manager.get_resume_state("hash1").unwrap().output_path, "/output1.json");
    assert_eq!(manager.get_resume_state("hash2").unwrap().output_path, "/output2.json");
}

#[test]
fn test_state_manager_remove() {
    let temp_dir = create_temp_dir();
    let state_file = temp_dir.path().join("state.toml");

    let mut manager = StateManager::new(state_file)
        .expect("Failed to create state manager");

    // Add a state entry
    manager.update_resume_state("hash1", "/output1.json")
        .expect("Failed to update state");
    assert!(manager.is_processed("hash1"));

    // Remove it
    manager.remove_state("hash1")
        .expect("Failed to remove state");
    assert!(!manager.is_processed("hash1"));
}

#[test]
fn test_state_manager_clear_all() {
    let temp_dir = create_temp_dir();
    let state_file = temp_dir.path().join("state.toml");

    let mut manager = StateManager::new(state_file)
        .expect("Failed to create state manager");

    // Add multiple entries
    manager.update_resume_state("hash1", "/output1.json").unwrap();
    manager.update_resume_state("hash2", "/output2.json").unwrap();
    manager.update_resume_state("hash3", "/output3.json").unwrap();

    assert_eq!(manager.count(), 3);

    // Clear all
    manager.clear_all().expect("Failed to clear state");
    assert_eq!(manager.count(), 0);
    assert!(!manager.is_processed("hash1"));
    assert!(!manager.is_processed("hash2"));
    assert!(!manager.is_processed("hash3"));
}
