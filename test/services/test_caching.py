import unittest
import os
import shutil
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services import material
from app.models.schema import MaterialInfo, VideoAspect
from app.utils import utils

class TestCachingAndResolution(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for cache_videos testing
        self.temp_dir = tempfile.mkdtemp()
        self.original_storage_dir = utils.storage_dir
        
        # Mock storage_dir to return our temp_dir and handle path creation
        def mock_storage_dir(sub_dir="", create=False):
            d = os.path.join(self.temp_dir, sub_dir) if sub_dir else self.temp_dir
            if create and not os.path.exists(d):
                os.makedirs(d)
            return d
            
        utils.storage_dir = mock_storage_dir

    def tearDown(self):
        # Restore storage_dir
        utils.storage_dir = self.original_storage_dir
        # Remove temp directory
        shutil.rmtree(self.temp_dir)

    def test_safe_filename(self):
        self.assertEqual(material._safe_filename("Motivation & Success"), "motivation_success")
        self.assertEqual(material._safe_filename("Động lực cuộc sống"), "dong_luc_cuoc_song")
        self.assertEqual(material._safe_filename("2K-video-search!"), "2k_video_search")

    def test_save_video_naming(self):
        from unittest.mock import patch, MagicMock
        
        # Mock requests.get response
        mock_response = MagicMock()
        mock_response.content = b"fake mp4 content"
        mock_response.iter_content.return_value = [b"fake mp4 content"]
        
        with patch('app.services.material.requests.get') as mock_get, \
             patch('app.services.material.VideoFileClip') as mock_clip_class:
            
            mock_get.return_value = mock_response
            
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30.0
            mock_clip_class.return_value = mock_clip

            # Call save_video with a remote URL and search_term
            cache_dir = utils.storage_dir("cache_videos", create=True)
            saved_path = material.save_video("https://example.com/video.mp4", save_dir=cache_dir, search_term="Động lực")
            
            self.assertTrue(os.path.exists(saved_path))
            filename = os.path.basename(saved_path)
            self.assertTrue(filename.startswith("dong_luc_"))
            self.assertTrue(filename.endswith(".mp4"))

    def test_get_cached_videos_by_term_finds_file(self):
        cache_dir = utils.storage_dir("cache_videos", create=True)
        # Create a mock file in cache_videos directory
        video_name = f"{material._safe_filename('motivation')}_12345.mp4"
        video_path = os.path.join(cache_dir, video_name)
        
        from unittest.mock import MagicMock, patch
        
        with patch('app.services.material.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value.__enter__.return_value = mock_clip
            
            with open(video_path, "wb") as f:
                f.write(b"fake data")
                
            local_items = material.get_cached_videos_by_term("motivation", minimum_duration=5)
            self.assertEqual(len(local_items), 1)
            self.assertEqual(local_items[0].search_term, "motivation")
            self.assertEqual(local_items[0].duration, 10)
            self.assertEqual(local_items[0].provider, "local_cache")

    def test_video_aspect_mode_schema(self):
        from app.models.schema import VideoParams
        params = VideoParams(video_subject="test")
        self.assertEqual(params.video_aspect_mode, "fit")
        self.assertFalse(params.fixed_subtitle_width)
        
        params_crop = VideoParams(video_subject="test", video_aspect_mode="crop", fixed_subtitle_width=True)
        self.assertEqual(params_crop.video_aspect_mode, "crop")
        self.assertTrue(params_crop.fixed_subtitle_width)

if __name__ == '__main__':
    unittest.main()
