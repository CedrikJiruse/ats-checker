import unittest
import os
import json
from state_manager import StateManager

class TestStateManager(unittest.TestCase):

    def setUp(self):
        """Set up a temporary state file for testing."""
        self.test_state_filepath = "test_processed_resumes_state.json"
        self.state_manager = StateManager(self.test_state_filepath)

    def tearDown(self):
        """Clean up the temporary state file after each test."""
        if os.path.exists(self.test_state_filepath):
            os.remove(self.test_state_filepath)

    def test_initial_state_is_empty(self):
        """Test that the state is empty initially."""
        self.assertEqual(self.state_manager.state, {})

    def test_update_resume_state_adds_entry(self):
        """Test that updating a resume state adds an entry."""
        file_hash = "hash123"
        output_path = "output/resume1.pdf"
        self.state_manager.update_resume_state(file_hash, output_path)
        self.assertEqual(self.state_manager.state, {file_hash: {"output_path": output_path}})
        # Verify it's saved to file
        with open(self.test_state_filepath, "r") as f:
            loaded_state = json.load(f)
        self.assertEqual(loaded_state, {file_hash: {"output_path": output_path}})

    def test_is_processed_returns_true_for_processed_resume(self):
        """Test that is_processed returns True for a processed resume."""
        file_hash = "hash456"
        output_path = "output/resume2.pdf"
        self.state_manager.update_resume_state(file_hash, output_path)
        self.assertTrue(self.state_manager.is_processed(file_hash))

    def test_is_processed_returns_false_for_unprocessed_resume(self):
        """Test that is_processed returns False for an unprocessed resume."""
        file_hash = "hash789"
        self.assertFalse(self.state_manager.is_processed(file_hash))

    def test_get_resume_state_returns_correct_data(self):
        """Test that get_resume_state returns the correct data."""
        file_hash = "hashabc"
        output_path = "output/resume3.pdf"
        self.state_manager.update_resume_state(file_hash, output_path)
        state = self.state_manager.get_resume_state(file_hash)
        self.assertEqual(state, {"output_path": output_path})

    def test_get_resume_state_returns_none_for_non_existent_hash(self):
        """Test that get_resume_state returns None for a non-existent hash."""
        self.assertIsNone(self.state_manager.get_resume_state("nonexistent_hash"))

    def test_state_persists_across_instances(self):
        """Test that state is loaded correctly when a new StateManager is instantiated."""
        file_hash = "hashdef"
        output_path = "output/resume4.pdf"
        self.state_manager.update_resume_state(file_hash, output_path)

        # Create a new instance of StateManager, it should load the saved state
        new_state_manager = StateManager(self.test_state_filepath)
        self.assertTrue(new_state_manager.is_processed(file_hash))
        self.assertEqual(new_state_manager.get_resume_state(file_hash), {"output_path": output_path})

if __name__ == '__main__':
    unittest.main()