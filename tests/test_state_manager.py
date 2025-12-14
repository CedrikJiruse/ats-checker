import os
import unittest

from state_manager import StateManager


class TestStateManagerToml(unittest.TestCase):
    def setUp(self):
        # Use a unique TOML state file per test run
        self.test_state_filepath = "test_processed_resumes_state.toml"
        # Ensure clean slate
        if os.path.exists(self.test_state_filepath):
            os.remove(self.test_state_filepath)

        # Also clean potential legacy JSON sibling used by migration logic
        legacy_json = os.path.splitext(self.test_state_filepath)[0] + ".json"
        if os.path.exists(legacy_json):
            os.remove(legacy_json)

        self.state_manager = StateManager(self.test_state_filepath)

    def tearDown(self):
        if os.path.exists(self.test_state_filepath):
            os.remove(self.test_state_filepath)

        legacy_json = os.path.splitext(self.test_state_filepath)[0] + ".json"
        if os.path.exists(legacy_json):
            os.remove(legacy_json)

    def test_initial_state_is_empty(self):
        """State should start empty when no state file exists."""
        self.assertEqual(self.state_manager.state, {})

    def test_update_resume_state_adds_entry_and_persists_to_toml(self):
        """Updating a resume state should add an entry and persist as TOML."""
        file_hash = "hash123"
        output_path = "output/resume1_enhanced.toml"

        self.state_manager.update_resume_state(file_hash, output_path)

        self.assertEqual(
            self.state_manager.state,
            {file_hash: {"output_path": output_path}},
        )
        self.assertTrue(os.path.exists(self.test_state_filepath))

        # Validate the TOML file contains the expected table/key.
        # We avoid depending on external TOML libraries here; instead do a simple string check.
        with open(self.test_state_filepath, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(f"[resumes.{file_hash}]", content)
        self.assertIn(f'output_path = "{output_path}"', content)

    def test_is_processed_returns_true_for_processed_resume(self):
        """is_processed should return True after update."""
        file_hash = "hash456"
        output_path = "output/resume2_enhanced.toml"

        self.state_manager.update_resume_state(file_hash, output_path)
        self.assertTrue(self.state_manager.is_processed(file_hash))

    def test_is_processed_returns_false_for_unprocessed_resume(self):
        """is_processed should return False for unknown hashes."""
        self.assertFalse(self.state_manager.is_processed("hash789"))

    def test_get_resume_state_returns_correct_data(self):
        """get_resume_state should return the stored metadata dict."""
        file_hash = "hashabc"
        output_path = "output/resume3_enhanced.toml"

        self.state_manager.update_resume_state(file_hash, output_path)
        state = self.state_manager.get_resume_state(file_hash)

        self.assertEqual(state, {"output_path": output_path})

    def test_get_resume_state_returns_none_for_non_existent_hash(self):
        """get_resume_state should return None when absent."""
        self.assertIsNone(self.state_manager.get_resume_state("nonexistent_hash"))

    def test_state_persists_across_instances_toml(self):
        """State should reload correctly from TOML when a new instance is created."""
        file_hash = "hashdef"
        output_path = "output/resume4_enhanced.toml"

        self.state_manager.update_resume_state(file_hash, output_path)

        new_state_manager = StateManager(self.test_state_filepath)
        self.assertTrue(new_state_manager.is_processed(file_hash))
        self.assertEqual(
            new_state_manager.get_resume_state(file_hash),
            {"output_path": output_path},
        )

    def test_migrates_legacy_json_when_toml_missing(self):
        """
        If the TOML file is missing but a legacy JSON file exists (same basename),
        StateManager should load the JSON and migrate to TOML.
        """
        # Ensure TOML does not exist
        if os.path.exists(self.test_state_filepath):
            os.remove(self.test_state_filepath)

        legacy_json_path = os.path.splitext(self.test_state_filepath)[0] + ".json"
        legacy_state = {"hashlegacy": {"output_path": "output/legacy.json"}}

        # Write legacy JSON
        import json

        with open(legacy_json_path, "w", encoding="utf-8") as f:
            json.dump(legacy_state, f, indent=2)

        # Create manager: should migrate
        sm = StateManager(self.test_state_filepath)

        self.assertTrue(sm.is_processed("hashlegacy"))
        self.assertEqual(
            sm.get_resume_state("hashlegacy"), {"output_path": "output/legacy.json"}
        )
        self.assertTrue(os.path.exists(self.test_state_filepath))

        # Verify TOML contains migrated entry
        with open(self.test_state_filepath, "r", encoding="utf-8") as f:
            toml_text = f.read()
        self.assertIn("[resumes.hashlegacy]", toml_text)
        self.assertIn('output_path = "output/legacy.json"', toml_text)


if __name__ == "__main__":
    unittest.main()
