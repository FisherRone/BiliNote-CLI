import unittest
from unittest.mock import patch, MagicMock

from app.utils.url_parser import detect_platform, extract_video_id, resolve_bilibili_short_url


class TestDetectPlatform(unittest.TestCase):
    """测试平台检测功能"""

    def test_detect_bilibili(self):
        """检测 B站链接"""
        self.assertEqual(detect_platform("https://www.bilibili.com/video/BV1xx411c7mD"), "bilibili")
        self.assertEqual(detect_platform("https://b23.tv/abc123"), "bilibili")

    def test_detect_youtube(self):
        """检测 YouTube 链接"""
        self.assertEqual(detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "youtube")
        self.assertEqual(detect_platform("https://youtu.be/dQw4w9WgXcQ"), "youtube")

    def test_detect_douyin(self):
        """检测抖音链接"""
        self.assertEqual(detect_platform("https://www.douyin.com/video/1234567890123456789"), "douyin")
        self.assertEqual(detect_platform("https://v.iesdouyin.com/abc123"), "douyin")

    def test_detect_kuaishou(self):
        """检测快手链接"""
        self.assertEqual(detect_platform("https://www.kuaishou.com/short-video/abc123"), "kuaishou")
        self.assertEqual(detect_platform("https://v.gifshow.com/abc123"), "kuaishou")

    @patch("os.path.exists")
    def test_detect_local_file(self, mock_exists):
        """检测本地文件"""
        mock_exists.return_value = True
        self.assertEqual(detect_platform("/path/to/video.mp4"), "local")
        self.assertEqual(detect_platform("./video.mp4"), "local")

    def test_detect_unknown(self):
        """检测未知平台"""
        self.assertIsNone(detect_platform("https://example.com/video/123"))
        self.assertIsNone(detect_platform("not a url"))


class TestExtractVideoId(unittest.TestCase):
    """测试视频 ID 提取功能"""

    def test_extract_bilibili_bv(self):
        """提取 B站 BV 号"""
        self.assertEqual(extract_video_id("https://www.bilibili.com/video/BV1xx411c7mD", "bilibili"), "BV1xx411c7mD")
        self.assertEqual(extract_video_id("https://www.bilibili.com/video/BV1vc411b7Wa/?spm_id_from=333.1007", "bilibili"), "BV1vc411b7Wa")

    @patch("app.utils.url_parser.resolve_bilibili_short_url")
    def test_extract_bilibili_short_url(self, mock_resolve):
        """通过短链接提取 B站 BV 号"""
        mock_resolve.return_value = "https://www.bilibili.com/video/BV1xx411c7mD"
        result = extract_video_id("https://b23.tv/abc123", "bilibili")
        self.assertEqual(result, "BV1xx411c7mD")

    def test_extract_youtube_id(self):
        """提取 YouTube 视频 ID"""
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://youtu.be/dQw4w9WgXcQ", "youtube"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123s", "youtube"), "dQw4w9WgXcQ")

    def test_extract_douyin_id(self):
        """提取抖音视频 ID"""
        self.assertEqual(extract_video_id("https://www.douyin.com/video/1234567890123456789", "douyin"), "1234567890123456789")

    def test_extract_none_for_invalid(self):
        """无效链接返回 None"""
        self.assertIsNone(extract_video_id("https://example.com", "bilibili"))
        self.assertIsNone(extract_video_id("invalid", "youtube"))
        self.assertIsNone(extract_video_id("", "douyin"))


class TestResolveBilibiliShortUrl(unittest.TestCase):
    """测试 B站短链接解析功能"""

    @patch("app.utils.url_parser.requests.head")
    def test_resolve_success(self, mock_head):
        """成功解析短链接"""
        mock_response = MagicMock()
        mock_response.url = "https://www.bilibili.com/video/BV1xx411c7mD"
        mock_head.return_value = mock_response

        result = resolve_bilibili_short_url("https://b23.tv/abc123")
        self.assertEqual(result, "https://www.bilibili.com/video/BV1xx411c7mD")

    @patch("requests.head")
    def test_resolve_failure(self, mock_head):
        """解析失败返回 None"""
        import requests
        mock_head.side_effect = requests.RequestException("Network error")

        result = resolve_bilibili_short_url("https://b23.tv/invalid")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
