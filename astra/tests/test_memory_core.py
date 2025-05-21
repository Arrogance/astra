import unittest
import os
# Adjust the import path if necessary based on how tests are run (e.g., from project root)
# This assumes tests might be run from the root directory of the project.
from astra.memory.core import Core 

# Define a temporary database file for testing
TEST_DB_FILE = "test_astra_memory.db"

class TestCoreTagFragment(unittest.TestCase):

    def setUp(self):
        # Initialize Core with a temporary database for each test
        # This ensures that if Core's __init__ has side effects (like creating a DB),
        # they are isolated to the test.
        self.core_instance = Core(db_file=TEST_DB_FILE)
        # Ensure a clean state by removing the test DB if it exists from a previous run
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)
        # Re-initialize to create the DB for the current test
        self.core_instance = Core(db_file=TEST_DB_FILE)


    def tearDown(self):
        # Clean up the temporary database file after each test
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)

    def test_tag_fragment_with_emotions(self):
        """Test that tag_fragment returns the first emotion when emotions are present."""
        self.assertEqual(self.core_instance.tag_fragment("some text", ["ansiedad", "culpa"]), "ansiedad")
        self.assertEqual(self.core_instance.tag_fragment("other text", ["duelo"]), "duelo")
        self.assertEqual(self.core_instance.tag_fragment("text with one emotion", ["alegria"]), "alegria")

    def test_tag_fragment_without_emotions(self):
        """Test that tag_fragment returns 'reflexión' when no emotions are present."""
        self.assertEqual(self.core_instance.tag_fragment("some text", []), "reflexión")

    def test_tag_fragment_with_empty_string_as_first_emotion(self):
        """Test that tag_fragment returns an empty string if it's the first emotion."""
        # This behavior depends on the requirements: should an empty string tag be allowed?
        # Assuming current logic: if it's in the list, it's returned.
        self.assertEqual(self.core_instance.tag_fragment("some text", ["", "culpa"]), "")

    def test_tag_fragment_with_none_in_emotions_list(self):
        """Test behavior if None is in the emotions list (should ideally be filtered before)."""
        # This assumes that the list contains strings as per type hint List[str]
        # If None could be passed, this test might fail or function might need adjustment
        # For now, assuming valid string inputs or type error from caller.
        # Let's test with a valid list first, then consider edge cases if they arise.
        # This test case might be redundant if type hinting is strictly followed by callers.
        # self.assertEqual(self.core_instance.tag_fragment("text with None", [None, "alegria"]), None) # Example if None was possible
        pass # Placeholder if we stick to List[str]

if __name__ == '__main__':
    # This allows running the tests directly from the command line
    unittest.main()
