import hashlib
import logging
import os

logger = logging.getLogger(__name__)

def calculate_file_hash(filepath: str) -> str:
    """
    Calculates the SHA256 hash of a file's content.

    Args:
        filepath: The path to the file.

    Returns:
        The SHA256 hash of the file content as a hexadecimal string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there's an error reading the file.
    """
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        raise FileNotFoundError(f"File not found: {filepath}")

    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            # Read and update hash string in chunks
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        logger.debug(f"Successfully calculated hash for {filepath}")
        return sha256_hash.hexdigest()
    except IOError as e:
        logger.error(f"Error reading file {filepath} for hashing: {e}")
        raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    # Example usage:
    # Create a dummy file for testing
    test_file_path = "test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test file content.")

    try:
        file_hash = calculate_file_hash(test_file_path)
        logger.info(f"Hash of {test_file_path}: {file_hash}")

        # Modify the file and check the new hash
        with open(test_file_path, "a") as f:
            f.write(" Appended new content.")

        new_file_hash = calculate_file_hash(test_file_path)
        logger.info(f"Hash of modified {test_file_path}: {new_file_hash}")

        # Test non-existent file
        try:
            calculate_file_hash("non_existent_file.txt")
        except FileNotFoundError:
            logger.info("Caught expected FileNotFoundError for non_existent_file.txt")

    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)