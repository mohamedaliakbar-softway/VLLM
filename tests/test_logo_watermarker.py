"""
Unit tests for Logo Watermarking Feature
Tests the LogoWatermarker service class
"""

import unittest
import base64
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.logo_watermarker import LogoWatermarker


class TestLogoWatermarker(unittest.TestCase):
    """Test suite for LogoWatermarker class"""

    def setUp(self):
        """Set up test fixtures"""
        self.watermarker = LogoWatermarker()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a simple 1x1 PNG in base64 (red pixel)
        self.valid_png_base64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        self.valid_data_url = f"data:image/png;base64,{self.valid_png_base64}"
        
        # Create a test video file (empty for testing)
        self.test_video_path = os.path.join(self.temp_dir, "test_video.mp4")
        with open(self.test_video_path, 'wb') as f:
            f.write(b"fake video data")

    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    # ==================== decode_logo() Tests ====================

    def test_decode_logo_valid_png(self):
        """Test decoding valid PNG data URL"""
        result = self.watermarker.decode_logo(self.valid_data_url)
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.png'))
        
        # Verify file contains image data
        with open(result, 'rb') as f:
            data = f.read()
            self.assertGreater(len(data), 0)
            # PNG files start with specific bytes
            self.assertEqual(data[:4], b'\x89PNG')
        
        # Cleanup
        os.remove(result)

    def test_decode_logo_valid_jpeg(self):
        """Test decoding JPEG data URL"""
        # Minimal JPEG in base64
        jpeg_base64 = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
        data_url = f"data:image/jpeg;base64,{jpeg_base64}"
        
        result = self.watermarker.decode_logo(data_url)
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.png'))
        
        # Cleanup
        os.remove(result)

    def test_decode_logo_invalid_format(self):
        """Test decoding with invalid data URL format"""
        invalid_url = "not a data url"
        
        with self.assertRaises(ValueError):
            self.watermarker.decode_logo(invalid_url)

    def test_decode_logo_invalid_base64(self):
        """Test decoding with invalid base64 data"""
        invalid_url = "data:image/png;base64,invalid!@#$%"
        
        with self.assertRaises(Exception):
            self.watermarker.decode_logo(invalid_url)

    def test_decode_logo_missing_mime_type(self):
        """Test decoding with missing mime type"""
        invalid_url = f"data:;base64,{self.valid_png_base64}"
        
        # Should still work as we extract base64 part
        result = self.watermarker.decode_logo(invalid_url)
        self.assertIsNotNone(result)
        os.remove(result)

    def test_decode_logo_creates_temp_file(self):
        """Test that decoded logo is saved in temp directory"""
        result = self.watermarker.decode_logo(self.valid_data_url)
        
        # Should be in uploads/temp_logos/
        self.assertIn('temp_logos', result)
        # Normalize path for cross-platform
        result_normalized = result.replace('\\', '/')
        self.assertTrue(result_normalized.startswith('uploads/temp_logos/logo_'))
        
        # Cleanup
        os.remove(result)

    # ==================== add_logo_to_video() Tests ====================

    @patch('services.logo_watermarker.ffmpeg')
    def test_add_logo_to_video_success(self, mock_ffmpeg):
        """Test successful logo addition to video"""
        # Mock ffmpeg.probe to return video info
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        # Mock the ffmpeg chain
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        mock_input.run.return_value = None
        
        result = self.watermarker.add_logo_to_video(
            video_path=self.test_video_path,
            logo_data_url=self.valid_data_url,
            position="top_right",
            opacity=0.9,
            padding=20,
            logo_size=80
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('_with_logo.mp4'))
        
        # Verify FFmpeg was called
        mock_ffmpeg.probe.assert_called_once_with(self.test_video_path)
        mock_ffmpeg.input.assert_called()

    @patch('services.logo_watermarker.ffmpeg')
    def test_add_logo_to_video_different_positions(self, mock_ffmpeg):
        """Test logo positioning formulas"""
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        # Mock the ffmpeg chain
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        mock_input.run.return_value = None
        
        positions = {
            'top_right': 'W-w-20:20',
            'top_left': '20:20',
            'bottom_right': 'W-w-20:H-h-20',
            'bottom_left': '20:H-h-20',
            'center': '(W-w)/2:(H-h)/2'
        }
        
        for pos, expected_formula in positions.items():
            self.watermarker.add_logo_to_video(
                video_path=self.test_video_path,
                logo_data_url=self.valid_data_url,
                position=pos,
                opacity=0.9,
                padding=20,
                logo_size=80
            )
            
            # Check filter_complex was called with correct overlay formula
            call_args = str(mock_input.filter_complex.call_args)
            self.assertIn(f'overlay={expected_formula}', call_args)

    @patch('services.logo_watermarker.ffmpeg')
    def test_add_logo_to_video_custom_opacity(self, mock_ffmpeg):
        """Test custom opacity values"""
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        mock_input.run.return_value = None
        
        for opacity in [0.5, 0.7, 0.9, 1.0]:
            self.watermarker.add_logo_to_video(
                video_path=self.test_video_path,
                logo_data_url=self.valid_data_url,
                opacity=opacity
            )
            
            # Check filter contains opacity setting
            call_args = str(mock_input.filter_complex.call_args)
            self.assertIn(f'aa={opacity}', call_args)

    @patch('services.logo_watermarker.ffmpeg')
    def test_add_logo_to_video_custom_size(self, mock_ffmpeg):
        """Test custom logo sizes"""
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        mock_input.run.return_value = None
        
        for size in [50, 80, 100, 150]:
            self.watermarker.add_logo_to_video(
                video_path=self.test_video_path,
                logo_data_url=self.valid_data_url,
                logo_size=size
            )
            
            # Check filter contains scale setting
            call_args = str(mock_input.filter_complex.call_args)
            self.assertIn(f'scale={size}:-1', call_args)

    @patch('services.logo_watermarker.ffmpeg')
    def test_add_logo_to_video_ffmpeg_failure(self, mock_ffmpeg):
        """Test handling of FFmpeg execution failure"""
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        # Mock FFmpeg failure
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        
        # Create a real ffmpeg.Error
        import ffmpeg
        error = ffmpeg.Error('ffmpeg', '', b'FFmpeg error: invalid input')
        mock_input.run.side_effect = error
        
        with self.assertRaises(RuntimeError) as context:
            self.watermarker.add_logo_to_video(
                video_path=self.test_video_path,
                logo_data_url=self.valid_data_url
            )
        
        self.assertIn("Failed to add logo", str(context.exception))

    def test_add_logo_to_video_invalid_video_path(self):
        """Test with non-existent video file"""
        with self.assertRaises(FileNotFoundError):
            self.watermarker.add_logo_to_video(
                video_path="/nonexistent/video.mp4",
                logo_data_url=self.valid_data_url
            )

    @patch('services.logo_watermarker.ffmpeg')
    def test_add_logo_to_video_cleanup_temp_logo(self, mock_ffmpeg):
        """Test that temporary logo file is cleaned up"""
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        mock_input.run.return_value = None
        
        # Get list of files before
        temp_logo_dir = Path("uploads/temp_logos")
        temp_logo_dir.mkdir(parents=True, exist_ok=True)
        files_before = set(temp_logo_dir.glob("*.png"))
        
        self.watermarker.add_logo_to_video(
            video_path=self.test_video_path,
            logo_data_url=self.valid_data_url
        )
        
        # Get list of files after
        files_after = set(temp_logo_dir.glob("*.png"))
        
        # Temp logo should be cleaned up (same or fewer files)
        self.assertLessEqual(len(files_after), len(files_before))

    # ==================== cleanup_temp_logos() Tests ====================

    def test_cleanup_temp_logos_removes_old_files(self):
        """Test cleanup of old temporary logo files"""
        temp_logo_dir = Path("uploads/temp_logos")
        temp_logo_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test files with old timestamps
        old_file = temp_logo_dir / "logo_old.png"
        old_file.write_bytes(b"test")
        
        # Set modification time to 2 hours ago
        import time
        old_time = time.time() - (2 * 3600)
        os.utime(old_file, (old_time, old_time))
        
        # Run cleanup with directory parameter
        LogoWatermarker.cleanup_temp_logos(str(temp_logo_dir))
        
        # Old file should be removed
        self.assertFalse(old_file.exists())

    def test_cleanup_temp_logos_keeps_recent_files(self):
        """Test that recent files are not cleaned up"""
        temp_logo_dir = Path("uploads/temp_logos")
        temp_logo_dir.mkdir(parents=True, exist_ok=True)
        
        # Create recent file
        recent_file = temp_logo_dir / "logo_recent.png"
        recent_file.write_bytes(b"test")
        
        # Run cleanup with directory parameter
        LogoWatermarker.cleanup_temp_logos(str(temp_logo_dir))
        
        # Recent file should still exist
        self.assertTrue(recent_file.exists())
        
        # Cleanup
        recent_file.unlink()

    def test_cleanup_temp_logos_handles_empty_directory(self):
        """Test cleanup with empty directory"""
        temp_logo_dir = Path("uploads/temp_logos_empty")
        temp_logo_dir.mkdir(parents=True, exist_ok=True)
        
        # Should not raise error
        try:
            LogoWatermarker.cleanup_temp_logos(str(temp_logo_dir))
        except Exception as e:
            self.fail(f"cleanup_temp_logos raised exception: {e}")
        
        # Cleanup
        temp_logo_dir.rmdir()

    def test_cleanup_temp_logos_nonexistent_directory(self):
        """Test cleanup with non-existent directory"""
        # Should not raise error
        try:
            LogoWatermarker.cleanup_temp_logos("/nonexistent/directory")
        except Exception as e:
            self.fail(f"cleanup_temp_logos raised exception: {e}")

    # ==================== Integration Tests ====================

    @patch('services.logo_watermarker.ffmpeg')
    def test_full_workflow(self, mock_ffmpeg):
        """Test complete workflow: decode -> add logo -> cleanup"""
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        mock_input.run.return_value = None
        
        # Step 1: Add logo to video
        result = self.watermarker.add_logo_to_video(
            video_path=self.test_video_path,
            logo_data_url=self.valid_data_url,
            position="top_right",
            opacity=0.9,
            padding=20,
            logo_size=80
        )
        
        # Verify output path
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('_with_logo.mp4'))
        
        # Verify FFmpeg was called with correct parameters
        mock_ffmpeg.probe.assert_called_with(self.test_video_path)
        self.assertTrue(mock_input.filter_complex.called)
        self.assertTrue(mock_input.run.called)

    @patch('services.logo_watermarker.ffmpeg')
    def test_multiple_logos_different_videos(self, mock_ffmpeg):
        """Test applying logos to multiple videos"""
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        mock_input.run.return_value = None
        
        # Create multiple test videos
        video_paths = []
        for i in range(3):
            video_path = os.path.join(self.temp_dir, f"test_video_{i}.mp4")
            with open(video_path, 'wb') as f:
                f.write(b"fake video data")
            video_paths.append(video_path)
        
        # Apply logo to each
        results = []
        for video_path in video_paths:
            result = self.watermarker.add_logo_to_video(
                video_path=video_path,
                logo_data_url=self.valid_data_url
            )
            results.append(result)
        
        # Verify all succeeded
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIsNotNone(result)
            self.assertTrue(result.endswith('_with_logo.mp4'))

    # ==================== Edge Cases ====================

    def test_decode_logo_very_large_base64(self):
        """Test handling of very large logo data"""
        # Create a large base64 string (simulating 5MB image)
        large_data = base64.b64encode(b"x" * (5 * 1024 * 1024)).decode('utf-8')
        large_url = f"data:image/png;base64,{large_data}"
        
        # Should handle large data
        result = self.watermarker.decode_logo(large_url)
        self.assertIsNotNone(result)
        
        # Cleanup
        if os.path.exists(result):
            os.remove(result)

    @patch('services.logo_watermarker.ffmpeg')
    def test_add_logo_boundary_values(self, mock_ffmpeg):
        """Test boundary values for parameters"""
        mock_ffmpeg.probe.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.input.return_value = mock_input
        mock_input.filter_complex.return_value = mock_input
        mock_input.output.return_value = mock_input
        mock_input.overwrite_output.return_value = mock_input
        mock_input.run.return_value = None
        
        # Test minimum values
        self.watermarker.add_logo_to_video(
            video_path=self.test_video_path,
            logo_data_url=self.valid_data_url,
            opacity=0.0,
            padding=0,
            logo_size=1
        )
        
        # Test maximum values
        self.watermarker.add_logo_to_video(
            video_path=self.test_video_path,
            logo_data_url=self.valid_data_url,
            opacity=1.0,
            padding=100,
            logo_size=1000
        )
        
        # Test invalid opacity (should raise)
        with self.assertRaises(ValueError):
            self.watermarker.add_logo_to_video(
                video_path=self.test_video_path,
                logo_data_url=self.valid_data_url,
                opacity=1.5
            )
        
        # Test invalid logo_size (should raise)
        with self.assertRaises(ValueError):
            self.watermarker.add_logo_to_video(
                video_path=self.test_video_path,
                logo_data_url=self.valid_data_url,
                logo_size=1001
            )

    def test_decode_logo_special_characters_in_base64(self):
        """Test handling of special characters in base64"""
        # Base64 can contain +, /, =
        special_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ++++/////=========="
        special_url = f"data:image/png;base64,{special_base64}"
        
        try:
            result = self.watermarker.decode_logo(special_url)
            if result and os.path.exists(result):
                os.remove(result)
        except Exception:
            # Invalid base64 should raise exception
            pass


class TestLogoWatermarkerPerformance(unittest.TestCase):
    """Performance tests for LogoWatermarker"""

    def setUp(self):
        self.watermarker = LogoWatermarker()
        self.valid_png_base64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        self.valid_data_url = f"data:image/png;base64,{self.valid_png_base64}"

    def test_decode_performance(self):
        """Test decode_logo performance"""
        import time
        
        start = time.time()
        for i in range(10):
            result = self.watermarker.decode_logo(self.valid_data_url)
            if os.path.exists(result):
                os.remove(result)
        end = time.time()
        
        avg_time = (end - start) / 10
        # Should complete in less than 100ms per decode
        self.assertLess(avg_time, 0.1, f"Decode took {avg_time:.3f}s (expected <0.1s)")


def run_tests():
    """Run all tests and display results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLogoWatermarker))
    suite.addTests(loader.loadTestsFromTestCase(TestLogoWatermarkerPerformance))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
