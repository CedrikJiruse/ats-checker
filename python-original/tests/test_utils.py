import unittest
import os
from utils import calculate_file_hash

class TestUtils(unittest.TestCase):

    def setUp(self):
        """Create a dummy file for testing before each test."""
        self.test_file_path = "test_hash_file.txt"
        with open(self.test_file_path, "w") as f:
            f.write("Initial content for hashing.")

    def tearDown(self):
        """Remove the dummy file after each test."""
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)

    def test_calculate_file_hash_consistent(self):
        """Test that the hash is consistent for the same file content."""
        hash1 = calculate_file_hash(self.test_file_path)
        hash2 = calculate_file_hash(self.test_file_path)
        self.assertEqual(hash1, hash2)

    def test_calculate_file_hash_changes_on_modification(self):
        """Test that the hash changes when the file content is modified."""
        initial_hash = calculate_file_hash(self.test_file_path)

        with open(self.test_file_path, "a") as f:
            f.write("Appended new content.")

        modified_hash = calculate_file_hash(self.test_file_path)
        self.assertNotEqual(initial_hash, modified_hash)

    def test_calculate_file_hash_empty_file(self):
        """Test hashing an empty file."""
        empty_file_path = "empty_file.txt"
        with open(empty_file_path, "w") as f:
            pass
        empty_hash = calculate_file_hash(empty_file_path)
        self.assertEqual(empty_hash, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") # SHA256 of an empty string
        os.remove(empty_file_path)

    def test_calculate_file_hash_non_existent_file(self):
        """Test hashing a non-existent file raises an error."""
        with self.assertRaises(FileNotFoundError):
            calculate_file_hash("non_existent_file.txt")

if __name__ == '__main__':
    unittest.main()