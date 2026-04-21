import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from app.utils.video_helper import generate_screenshot, save_cover_to_static


class TestGenerateScreenshot(unittest.TestCase):
    """测试截图生成功能"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """每个测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_generate_screenshot_calls_ffmpeg(self, mock_run):
        """测试调用 ffmpeg 生成截图"""
        mock_run.return_value = MagicMock(returncode=0)

        output_dir = os.path.join(self.temp_dir, "screenshots")
        result = generate_screenshot("/path/to/video.mp4", output_dir, 60, 1)

        # 验证 ffmpeg 被调用
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "ffmpeg")
        self.assertIn("-ss", call_args)
        self.assertIn("60", call_args)  # timestamp
        self.assertIn("-i", call_args)
        self.assertIn("/path/to/video.mp4", call_args)

    @patch("subprocess.run")
    def test_generate_screenshot_returns_path(self, mock_run):
        """测试返回生成的截图路径"""
        mock_run.return_value = MagicMock(returncode=0)

        output_dir = os.path.join(self.temp_dir, "screenshots")
        result = generate_screenshot("/path/to/video.mp4", output_dir, 120, 5)

        # 验证返回路径包含正确的前缀和扩展名
        self.assertTrue(result.endswith(".jpg"))
        self.assertIn("screenshot_005_", result)

    @patch("subprocess.run")
    def test_generate_screenshot_creates_directory(self, mock_run):
        """测试自动创建输出目录"""
        mock_run.return_value = MagicMock(returncode=0)

        output_dir = os.path.join(self.temp_dir, "new", "nested", "dir")
        self.assertFalse(os.path.exists(output_dir))

        generate_screenshot("/path/to/video.mp4", output_dir, 30, 1)

        self.assertTrue(os.path.exists(output_dir))

    @patch("subprocess.run")
    def test_generate_screenshot_handles_ffmpeg_error(self, mock_run):
        """测试处理 ffmpeg 错误"""
        mock_run.return_value = MagicMock(returncode=1, stderr="ffmpeg error")

        output_dir = os.path.join(self.temp_dir, "screenshots")
        # 不应抛出异常，但会打印错误
        result = generate_screenshot("/path/to/video.mp4", output_dir, 60, 1)

        # 仍然返回路径
        self.assertTrue(result.endswith(".jpg"))


class TestSaveCoverToStatic(unittest.TestCase):
    """测试封面保存功能"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # 创建模拟封面文件
        self.cover_path = os.path.join(self.temp_dir, "test_cover.jpg")
        with open(self.cover_path, "w") as f:
            f.write("fake image data")

    def tearDown(self):
        """每个测试后清理"""
        import shutil
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_cover_copies_file(self):
        """测试复制封面文件到 static 目录"""
        with patch('app.utils.video_helper.BACKEND_BASE_URL', 'http://localhost:8483'):
            result = save_cover_to_static(self.cover_path)

            # 验证文件被复制
            static_path = os.path.join(self.temp_dir, "static", "cover", "test_cover.jpg")
            self.assertTrue(os.path.exists(static_path))

    def test_save_cover_returns_url(self):
        """测试返回可访问的 URL"""
        with patch('app.utils.video_helper.BACKEND_BASE_URL', 'http://localhost:8483'):
            result = save_cover_to_static(self.cover_path)

            # 验证返回 URL 格式
            self.assertIn("http://localhost:8483", result)
            self.assertIn("/static/cover/test_cover.jpg", result)

    def test_save_cover_custom_subfolder(self):
        """测试自定义子目录"""
        with patch('app.utils.video_helper.BACKEND_BASE_URL', 'http://localhost:8483'):
            result = save_cover_to_static(self.cover_path, subfolder="thumbnails")

            # 验证文件在自定义子目录中
            custom_path = os.path.join(self.temp_dir, "static", "thumbnails", "test_cover.jpg")
            self.assertTrue(os.path.exists(custom_path))
            self.assertIn("/static/thumbnails/test_cover.jpg", result)

    def test_save_cover_preserves_filename(self):
        """测试保留原始文件名"""
        with patch('app.utils.video_helper.BACKEND_BASE_URL', 'http://localhost:8483'):
            custom_cover = os.path.join(self.temp_dir, "my_custom_cover.png")
            with open(custom_cover, "w") as f:
                f.write("fake image data")

            result = save_cover_to_static(custom_cover)

            self.assertIn("my_custom_cover.png", result)


if __name__ == "__main__":
    unittest.main()
