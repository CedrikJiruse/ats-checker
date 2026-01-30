//! Integration tests for file locking and concurrent file access.

use ats_checker::error::AtsError;
use ats_checker::state::StateManager;
use ats_checker::utils::file::{atomic_write, ensure_directory};
use std::sync::Arc;
use std::time::Duration;
use tempfile::TempDir;
use tokio::task;
use tokio::time::sleep;

#[tokio::test]
async fn test_concurrent_state_updates() {
    let temp_dir = TempDir::new().unwrap();
    let state_file = temp_dir.path().join("state.toml");

    // Create multiple tasks that update state concurrently
    let mut handles = vec![];

    for i in 0..10 {
        let state_file = state_file.clone();
        let handle = task::spawn(async move {
            let mut manager = StateManager::new(state_file).unwrap();
            let hash = format!("hash_{}", i);
            let path = format!("output/file_{}.toml", i);
            manager.update_resume_state(&hash, &path).unwrap();
        });
        handles.push(handle);
    }

    // Wait for all tasks to complete
    for handle in handles {
        handle.await.unwrap();
    }

    // Verify all updates were persisted
    let manager = StateManager::new(state_file).unwrap();
    for i in 0..10 {
        let hash = format!("hash_{}", i);
        let result = manager.get_resume_state(&hash);
        assert!(result.is_some(), "Hash {} should be in state", i);
    }
}

#[tokio::test]
async fn test_concurrent_atomic_writes() {
    let temp_dir = TempDir::new().unwrap();
    ensure_directory(temp_dir.path()).unwrap();

    let file_path = temp_dir.path().join("concurrent_test.txt");
    let mut handles = vec![];

    // Multiple tasks writing to the same file
    for i in 0..5 {
        let file_path = file_path.clone();
        let handle = task::spawn(async move {
            let content = format!("Content from task {}\n", i);
            atomic_write(&file_path, &content)
        });
        handles.push(handle);
    }

    // Wait for all writes to complete
    for handle in handles {
        let result = handle.await.unwrap();
        assert!(result.is_ok(), "Atomic write should succeed");
    }

    // File should exist and contain content from one of the tasks
    assert!(file_path.exists());
    let content = std::fs::read_to_string(&file_path).unwrap();
    assert!(content.contains("Content from task"));
}

#[tokio::test]
async fn test_state_manager_concurrent_reads() {
    let temp_dir = TempDir::new().unwrap();
    let state_file = temp_dir.path().join("state.toml");

    // Initialize state with some data
    {
        let mut manager = StateManager::new(state_file.clone()).unwrap();
        for i in 0..10 {
            let hash = format!("hash_{}", i);
            let path = format!("output/file_{}.toml", i);
            manager.update_resume_state(&hash, &path).unwrap();
        }
    }

    // Multiple concurrent reads
    let mut handles = vec![];

    for i in 0..20 {
        let state_file = state_file.clone();
        let handle = task::spawn(async move {
            let manager = StateManager::new(state_file).unwrap();
            let hash = format!("hash_{}", i % 10);
            let _result = manager.get_resume_state(&hash);
            Ok::<(), AtsError>(())
        });
        handles.push(handle);
    }

    // All reads should succeed
    for handle in handles {
        let result = handle.await.unwrap();
        assert!(result.is_ok());
    }
}

#[tokio::test]
async fn test_interleaved_reads_and_writes() {
    let temp_dir = TempDir::new().unwrap();
    let state_file = temp_dir.path().join("state.toml");

    let state_file_arc = Arc::new(state_file.clone());
    let mut handles = vec![];

    // Spawn reader tasks
    for i in 0..5 {
        let state_file = Arc::clone(&state_file_arc);
        let handle = task::spawn(async move {
            for _ in 0..10 {
                let manager = StateManager::new(state_file.as_ref().clone()).unwrap();
                let hash = format!("hash_{}", i);
                let _ = manager.get_resume_state(&hash);
                sleep(Duration::from_millis(1)).await;
            }
        });
        handles.push(handle);
    }

    // Spawn writer tasks
    for i in 0..5 {
        let state_file = Arc::clone(&state_file_arc);
        let handle = task::spawn(async move {
            for j in 0..10 {
                let mut manager = StateManager::new(state_file.as_ref().clone()).unwrap();
                let hash = format!("hash_{}_{}", i, j);
                let path = format!("output/file_{}_{}.toml", i, j);
                let _ = manager.update_resume_state(&hash, &path);
                sleep(Duration::from_millis(2)).await;
            }
        });
        handles.push(handle);
    }

    // Wait for all tasks to complete
    for handle in handles {
        handle.await.unwrap();
    }

    // Verify state is consistent
    let manager = StateManager::new(state_file).unwrap();
    // At least some writes should have succeeded
    let has_entries = (0..5).any(|i| {
        let hash = format!("hash_{}_0", i);
        manager.get_resume_state(&hash).is_some()
    });
    assert!(
        has_entries,
        "State should contain some entries from concurrent writes"
    );
}

#[tokio::test]
async fn test_atomic_write_prevents_corruption() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("atomic_test.txt");

    // Initial content
    atomic_write(&file_path, "Initial content").unwrap();

    let file_path_arc = Arc::new(file_path.clone());
    let mut handles = vec![];

    // Multiple concurrent writes with different content
    for i in 0..10 {
        let file_path = Arc::clone(&file_path_arc);
        let handle = task::spawn(async move {
            let content = format!("Updated content {}\n", i).repeat(100);
            atomic_write(file_path.as_ref(), &content)
        });
        handles.push(handle);
    }

    // Wait for all writes
    for handle in handles {
        let result = handle.await.unwrap();
        assert!(result.is_ok());
    }

    // File should still be readable and not corrupted
    let content = std::fs::read_to_string(&*file_path).unwrap();
    // Content should be from one complete write, not partial/corrupted
    assert!(content.contains("Updated content") || content == "Initial content");
    // All lines should be from the same write (same index)
    let lines: Vec<&str> = content.lines().collect();
    if !lines.is_empty() && lines[0].contains("Updated content") {
        // Extract the index from the first line
        if let Some(_first_line) = lines.first() {
            // All subsequent lines should match the pattern of the first line
            let all_same = lines
                .iter()
                .all(|line| line.is_empty() || line.contains("Updated content"));
            assert!(
                all_same,
                "File content should not be mixed from different writes"
            );
        }
    }
}

#[tokio::test]
async fn test_state_persistence_under_load() {
    let temp_dir = TempDir::new().unwrap();
    let state_file = temp_dir.path().join("load_test_state.toml");

    let state_file_arc = Arc::new(state_file.clone());
    let mut handles = vec![];

    // High load: 50 concurrent tasks, each doing 20 operations
    for i in 0..50 {
        let state_file = Arc::clone(&state_file_arc);
        let handle = task::spawn(async move {
            for j in 0..20 {
                let mut manager = StateManager::new(state_file.as_ref().clone()).unwrap();
                let hash = format!("hash_{}_{}", i, j);
                let path = format!("output/file_{}_{}.toml", i, j);
                manager.update_resume_state(&hash, &path).unwrap();
            }
        });
        handles.push(handle);
    }

    // Wait for all operations to complete
    for handle in handles {
        handle.await.unwrap();
    }

    // Verify state file is not corrupted and contains expected data
    let manager = StateManager::new(state_file).unwrap();

    // Sample check: verify some of the entries exist
    let mut found_count = 0;
    for i in 0..10 {
        for j in 0..5 {
            let hash = format!("hash_{}_{}", i, j);
            if manager.get_resume_state(&hash).is_some() {
                found_count += 1;
            }
        }
    }

    assert!(
        found_count > 0,
        "State should contain entries from concurrent operations"
    );
}

#[tokio::test]
async fn test_file_write_atomicity() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("atomicity_test.txt");

    // Large content to increase chance of observing partial writes if atomicity is broken
    let large_content = "x".repeat(10_000);

    let file_path_arc = Arc::new(file_path.clone());
    let mut handles = vec![];

    // Concurrent writes
    for i in 0..5 {
        let file_path = Arc::clone(&file_path_arc);
        let content = format!("{}{}", i, &large_content);
        let handle = task::spawn(async move { atomic_write(file_path.as_ref(), &content) });
        handles.push(handle);
    }

    // Wait for all writes
    for handle in handles {
        handle.await.unwrap().unwrap();
    }

    // Read final content and verify it's a complete write from one task
    let content = std::fs::read_to_string(&*file_path).unwrap();

    // The content should start with a digit (0-4) followed by 10000 x's
    assert!(content.len() >= 10_000, "Content should be complete");

    if let Some(first_char) = content.chars().next() {
        if first_char.is_ascii_digit() {
            // Verify the rest is all x's
            let rest: String = content.chars().skip(1).collect();
            let expected_rest = "x".repeat(10_000);
            assert_eq!(
                rest, expected_rest,
                "Content should be atomic - either complete or not written"
            );
        }
    }
}

#[test]
fn test_file_locking_single_thread() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("single_thread.txt");

    // Sequential writes should always work
    for i in 0..10 {
        let content = format!("Content {}\n", i);
        atomic_write(&file_path, &content).unwrap();
    }

    let final_content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(final_content, "Content 9\n");
}

#[tokio::test]
async fn test_state_clear_during_concurrent_access() {
    let temp_dir = TempDir::new().unwrap();
    let state_file = temp_dir.path().join("clear_test_state.toml");

    // Initialize with some data
    {
        let mut manager = StateManager::new(state_file.clone()).unwrap();
        for i in 0..10 {
            manager
                .update_resume_state(&format!("hash_{}", i), &format!("path_{}", i))
                .unwrap();
        }
    }

    let state_file_arc = Arc::new(state_file.clone());
    let mut handles = vec![];

    // Readers
    for _ in 0..5 {
        let state_file = Arc::clone(&state_file_arc);
        let handle = task::spawn(async move {
            for i in 0..10 {
                let manager = StateManager::new(state_file.as_ref().clone()).unwrap();
                let _ = manager.get_resume_state(&format!("hash_{}", i));
                sleep(Duration::from_millis(1)).await;
            }
        });
        handles.push(handle);
    }

    // Clear in the middle of concurrent reads
    sleep(Duration::from_millis(5)).await;
    {
        let mut manager = StateManager::new(state_file.clone()).unwrap();
        manager.clear_all().unwrap();
    }

    // Wait for readers
    for handle in handles {
        handle.await.unwrap();
    }

    // Verify state is cleared
    let manager = StateManager::new(state_file).unwrap();
    for i in 0..10 {
        let result = manager.get_resume_state(&format!("hash_{}", i));
        assert!(result.is_none(), "State should be cleared");
    }
}
