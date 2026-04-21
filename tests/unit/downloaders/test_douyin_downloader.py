"""测试 douyin_downloader 模块

测试 Cookie 注入逻辑（有/无 Cookie）
不实际下载视频，通过 mock 验证参数传递
"""

import os
import unittest
from unittest.mock import patch, MagicMock

# ==================== 配置区 ====================
# 测试用的视频链接（无需修改，仅用于 mock 测试）
DOUYIN_TEST_URL = "https://v.douyin.com/iRNBho5M"
# ================================================


class TestDouyinDownloaderCookie(unittest.TestCase):
    """测试 DouyinDownloader 的 Cookie 注入"""

    @patch("app.downloaders.douyin_downloader.get_cookie")
    def test_init_with_cookie(self, mock_get_cookie):
        """有 Cookie 时初始化设置到 headers"""
        mock_get_cookie.return_value = "ttwid=abc123; sessionid=xyz789"

        from app.downloaders.douyin_downloader import DouyinDownloader
        downloader = DouyinDownloader()

        self.assertEqual(downloader.headers_config["Cookie"], "ttwid=abc123; sessionid=xyz789")
        mock_get_cookie.assert_called_with("douyin")

    @patch("app.downloaders.douyin_downloader.get_cookie")
    def test_init_without_cookie(self, mock_get_cookie):
        """无 Cookie 时 headers 中 Cookie 为 None"""
        mock_get_cookie.return_value = None

        from app.downloaders.douyin_downloader import DouyinDownloader
        downloader = DouyinDownloader()

        self.assertIsNone(downloader.headers_config["Cookie"])
        mock_get_cookie.assert_called_with("douyin")

    @patch("app.downloaders.douyin_downloader.get_cookie")
    def test_init_with_empty_cookie(self, mock_get_cookie):
        """空字符串 Cookie"""
        mock_get_cookie.return_value = ""

        from app.downloaders.douyin_downloader import DouyinDownloader
        downloader = DouyinDownloader()

        self.assertEqual(downloader.headers_config["Cookie"], "")

    @patch("app.downloaders.douyin_downloader.get_cookie")
    def test_headers_other_fields_preserved(self, mock_get_cookie):
        """Cookie 注入不影响其他 headers 字段"""
        mock_get_cookie.return_value = "test_cookie"

        from app.downloaders.douyin_downloader import DouyinDownloader
        downloader = DouyinDownloader()

        # 验证其他 headers 仍然存在
        self.assertIn("User-Agent", downloader.headers_config)
        self.assertIn("Referer", downloader.headers_config)
        self.assertEqual(downloader.headers_config["Cookie"], "test_cookie")


class TestDouyinDownloaderFindUrl(unittest.TestCase):
    """测试 DouyinDownloader.find_url 静态方法"""

    def setUp(self):
        from app.downloaders.douyin_downloader import DouyinDownloader
        self.find_url = DouyinDownloader.find_url

    def test_find_url_from_text(self):
        """从文本中提取抖音链接"""
        text = '7.43 11/16 好视频 https://v.douyin.com/iRNBho5M 复制此链接'
        urls = self.find_url(text)
        self.assertTrue(len(urls) > 0)
        self.assertIn("https://v.douyin.com/iRNBho5M", urls[0])

    def test_find_url_no_url(self):
        """文本中无链接时返回空列表"""
        text = "这是一段没有链接的文字"
        urls = self.find_url(text)
        self.assertEqual(len(urls), 0)

    def test_find_url_multiple_urls(self):
        """提取多个链接"""
        text = "视频1 https://v.douyin.com/abc 和视频2 https://v.douyin.com/def"
        urls = self.find_url(text)
        self.assertEqual(len(urls), 2)


if __name__ == "__main__":
    unittest.main()
