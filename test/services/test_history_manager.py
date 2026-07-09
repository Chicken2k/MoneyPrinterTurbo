import unittest
import os
import shutil
from app.services import history_manager
from app.utils import utils

class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        # Backup existing file if any
        self.history_file = history_manager.get_history_file_path()
        self.backup_file = self.history_file + ".bak"
        if os.path.exists(self.history_file):
            shutil.copyfile(self.history_file, self.backup_file)
            os.remove(self.history_file)

    def tearDown(self):
        # Restore backup if any
        if os.path.exists(self.history_file):
            os.remove(self.history_file)
        if os.path.exists(self.backup_file):
            shutil.copyfile(self.backup_file, self.history_file)
            os.remove(self.backup_file)

    def test_save_and_load_history(self):
        history_manager.save_script_to_history("test_id_1", "Test Subject", "This is a test script content.")
        history = history_manager.load_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["task_id"], "test_id_1")
        self.assertEqual(history[0]["script"], "This is a test script content.")

        # Test duplicate avoidance
        history_manager.save_script_to_history("test_id_1", "Test Subject", "This is a test script content.")
        history = history_manager.load_history()
        self.assertEqual(len(history), 1)

    def test_get_recent_scripts(self):
        history_manager.save_script_to_history("test_1", "Subj 1", "Script one")
        history_manager.save_script_to_history("test_2", "Subj 2", "Script two")
        recent = history_manager.get_recent_scripts(limit=2)
        self.assertEqual(len(recent), 2)
        # Order should be newest first
        self.assertEqual(recent[0], "Script two")
        self.assertEqual(recent[1], "Script one")

    def test_similarity_check(self):
        history_manager.save_script_to_history("test_1", "Subject", "Cuộc sống có những lúc thăng trầm, hãy luôn vững tin.")
        
        # Test exact match
        too_similar, _, ratio = history_manager.is_too_similar("Cuộc sống có những lúc thăng trầm, hãy luôn vững tin.")
        self.assertTrue(too_similar)
        self.assertGreaterEqual(ratio, 0.95)

        # Test slight variation (should still be similar)
        too_similar, _, ratio = history_manager.is_too_similar("Cuộc sống có những lúc thăng trầm! Hãy luôn luôn vững tin nhé.")
        self.assertTrue(too_similar)
        self.assertGreaterEqual(ratio, 0.80)

        # Test different text
        too_similar, _, ratio = history_manager.is_too_similar("Hãy làm việc chăm chỉ mỗi ngày để gặt hái thành công.")
        self.assertFalse(too_similar)
        self.assertLess(ratio, 0.50)

if __name__ == '__main__':
    unittest.main()
