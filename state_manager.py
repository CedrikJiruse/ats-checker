import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, state_filepath: str = "processed_resumes_state.json"):
        self.state_filepath = state_filepath
        self.state: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads the state from the JSON file."""
        if os.path.exists(self.state_filepath):
            try:
                with open(self.state_filepath, "r") as f:
                    state_data = json.load(f)
                logger.info(f"Loaded state from {self.state_filepath}")
                return state_data
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding state file {self.state_filepath}: {e}")
                return {}
            except IOError as e:
                logger.error(f"Error reading state file {self.state_filepath}: {e}")
                return {}
        logger.info(f"No existing state file found at {self.state_filepath}. Starting with empty state.")
        return {}

    def _save_state(self) -> None:
        """Saves the current state to the JSON file."""
        try:
            with open(self.state_filepath, "w") as f:
                json.dump(self.state, f, indent=4)
            logger.debug(f"State saved to {self.state_filepath}")
        except IOError as e:
            logger.error(f"Error writing state to file {self.state_filepath}: {e}")

    def get_resume_state(self, file_hash: str) -> Dict[str, Any] | None:
        """
        Retrieves the state for a given resume hash.

        Args:
            file_hash: The SHA256 hash of the resume file.

        Returns:
            A dictionary containing the resume's state (e.g., output_path)
            or None if not found.
        """
        return self.state.get(file_hash)

    def update_resume_state(self, file_hash: str, output_path: str) -> None:
        """
        Updates the state for a processed resume.

        Args:
            file_hash: The SHA256 hash of the resume file.
            output_path: The path where the generated PDF resume is saved.
        """
        self.state[file_hash] = {"output_path": output_path}
        self._save_state()
        logger.info(f"Updated state for hash {file_hash} with output path {output_path}")

    def is_processed(self, file_hash: str) -> bool:
        """
        Checks if a resume with the given hash has already been processed.

        Args:
            file_hash: The SHA256 hash of the resume file.

        Returns:
            True if the resume has been processed, False otherwise.
        """
        return file_hash in self.state

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Example usage:
    state_manager = StateManager("test_state.json")

    # Test adding a new resume
    hash1 = "a1b2c3d4e5f6"
    output_path1 = "output/resume1.pdf"
    if not state_manager.is_processed(hash1):
        logger.info(f"Resume with hash {hash1} not processed. Processing...")
        state_manager.update_resume_state(hash1, output_path1)
        logger.info(f"State updated for {hash1}.")
    else:
        logger.info(f"Resume with hash {hash1} already processed. Output: {state_manager.get_resume_state(hash1)['output_path']}")

    # Test processing the same resume again
    if not state_manager.is_processed(hash1):
        logger.info(f"Resume with hash {hash1} not processed. Processing...")
        state_manager.update_resume_state(hash1, output_path1)
        logger.info(f"State updated for {hash1}.")
    else:
        logger.info(f"Resume with hash {hash1} already processed. Output: {state_manager.get_resume_state(hash1)['output_path']}")

    # Test adding another new resume
    hash2 = "f6e5d4c3b2a1"
    output_path2 = "output/resume2.pdf"
    if not state_manager.is_processed(hash2):
        logger.info(f"Resume with hash {hash2} not processed. Processing...")
        state_manager.update_resume_state(hash2, output_path2)
        logger.info(f"State updated for {hash2}.")
    else:
        logger.info(f"Resume with hash {hash2} already processed. Output: {state_manager.get_resume_state(hash2)['output_path']}")

    # Clean up test state file
    if os.path.exists("test_state.json"):
        os.remove("test_state.json")