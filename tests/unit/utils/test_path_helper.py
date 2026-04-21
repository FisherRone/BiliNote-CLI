import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from app.utils.path_helper import get_path_manager, PathManager


class TestPathManager(unittest.TestCase):
    """测试 PathManager 路径管理功能"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        # 重置单例以使用临时目录
        import app.utils.path_helper as ph
        ph._path_manager = None

    def tearDown(self):
        """每个测试后清理临时目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ensure_dir_creates_directory(self):
        """测试 _ensure_dir 创建目录"""
        test_path = os.path.join(self.temp_dir, "test_subdir")
        result = PathManager._ensure_dir(test_path)
        self.assertTrue(os.path.exists(test_path))
        self.assertEqual(result, test_path)

    def test_get_download_path(self):
        """测试获取下载路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_download_path("BV12345")
            expected = os.path.join(pm.downloads_dir, "BV12345.mp3")
            self.assertEqual(path, expected)

    def test_get_download_path_with_custom_ext(self):
        """测试获取自定义扩展名的下载路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_download_path("BV12345", ".mp4")
            expected = os.path.join(pm.downloads_dir, "BV12345.mp4")
            self.assertEqual(path, expected)

    def test_get_transcript_cache_path(self):
        """测试获取转写缓存路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_transcript_cache_path("task_001")
            self.assertTrue(path.endswith("_transcript.json"))
            self.assertIn("task_001", path)
            self.assertIn("transcript", path)

    def test_get_audio_meta_cache_path(self):
        """测试获取音频元信息缓存路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_audio_meta_cache_path("task_001")
            self.assertTrue(path.endswith("_audio.json"))
            self.assertIn("task_001", path)
            self.assertIn("audio_meta", path)

    def test_get_note_output_path(self):
        """测试获取笔记输出路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_note_output_path("task_001")
            expected = os.path.join(pm.output_notes_dir, "task_001.md")
            self.assertEqual(path, expected)

    def test_get_note_output_path_with_custom_ext(self):
        """测试获取自定义扩展名的笔记输出路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_note_output_path("task_001", ".txt")
            expected = os.path.join(pm.output_notes_dir, "task_001.txt")
            self.assertEqual(path, expected)

    def test_get_temp_dir(self):
        """测试获取临时目录"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_temp_dir("task_001")
            self.assertTrue(os.path.exists(path))
            self.assertIn("task_001", path)

    def test_get_temp_dir_with_subdir(self):
        """测试获取带子目录的临时目录"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_temp_dir("task_001", "frames")
            self.assertTrue(os.path.exists(path))
            self.assertIn("task_001_frames", path)

    def test_get_state_file_path(self):
        """测试获取状态文件路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_state_file_path("task_001")
            self.assertTrue(path.endswith(".status.json"))
            self.assertIn("task_001", path)
            self.assertIn("state", path)

    def test_get_metadata_file_path(self):
        """测试获取元数据文件路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_metadata_file_path("task_001")
            self.assertTrue(path.endswith("_metadata.json"))
            self.assertIn("task_001", path)
            self.assertIn("cache", path)

    def test_get_gpt_checkpoint_path(self):
        """测试获取 GPT 检查点路径"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_gpt_checkpoint_path("task_001")
            self.assertTrue(path.endswith(".gpt.checkpoint.json"))
            self.assertIn("task_001", path)

    def test_get_model_dir(self):
        """测试获取模型目录"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_model_dir("whisper")
            self.assertTrue(os.path.exists(path))
            self.assertIn("whisper", path)

    def test_get_model_dir_default(self):
        """测试获取默认模型目录"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            path = pm.get_model_dir()
            self.assertTrue(os.path.exists(path))

    def test_directory_structure(self):
        """测试目录结构完整性"""
        with patch('app.utils.path_helper._BILINOTE_HOME', self.temp_dir):
            pm = PathManager()
            # 验证所有主要目录都已创建
            self.assertTrue(os.path.exists(pm.data_dir))
            self.assertTrue(os.path.exists(pm.downloads_dir))
            self.assertTrue(os.path.exists(pm.cache_dir))
            self.assertTrue(os.path.exists(pm.cache_transcript_dir))
            self.assertTrue(os.path.exists(pm.cache_audio_meta_dir))
            self.assertTrue(os.path.exists(pm.output_dir))
            self.assertTrue(os.path.exists(pm.output_notes_dir))
            self.assertTrue(os.path.exists(pm.temp_dir))
            self.assertTrue(os.path.exists(pm.state_dir))
            self.assertTrue(os.path.exists(pm.resources_dir))
            self.assertTrue(os.path.exists(pm.logs_dir))
            self.assertTrue(os.path.exists(pm.user_config_dir))


class TestPathManagerSingleton(unittest.TestCase):
    """测试 PathManager 单例模式"""

    def test_singleton_returns_same_instance(self):
        """测试单例返回相同实例"""
        import app.utils.path_helper as ph
        # 重置单例
        ph._path_manager = None
        pm1 = get_path_manager()
        pm2 = get_path_manager()
        self.assertIs(pm1, pm2)


if __name__ == "__main__":
    unittest.main()
