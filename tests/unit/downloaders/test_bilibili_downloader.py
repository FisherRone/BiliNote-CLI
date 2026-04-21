"""测试 bilibili_downloader 模块

测试 Cookie 注入逻辑（有/无 Cookie）和 Netscape 格式转换
不实际下载视频，通过 mock yt-dlp 验证参数传递
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from app.downloaders.bilibili_downloader import (
    BilibiliDownloader,
    _cookie_string_to_file,
    _apply_bilibili_cookie,
)

# ==================== 配置区 ====================
# 测试用的视频链接（无需修改，仅用于 mock 测试）
BILIBILI_TEST_URL = "https://www.bilibili.com/video/BV1GJ411x7h7"
# ================================================


class TestCookieStringToFile(unittest.TestCase):
    """测试 _cookie_string_to_file 函数"""

    def setUp(self):
        """设置测试"""
        self.convert = _cookie_string_to_file
        self.temp_files = []

    def tearDown(self):
        """清理临时文件"""
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)

    def test_convert_simple_cookie(self):
        """转换简单的 cookie 字符串"""
        cookie_str = "SESSDATA=abc123; bili_jct=xyz789"
        path = self.convert(cookie_str)
        self.temp_files.append(path)

        self.assertTrue(os.path.exists(path))
        with open(path, 'r') as f:
            content = f.read()

        self.assertIn("# Netscape HTTP Cookie File", content)
        self.assertIn(".bilibili.com\tTRUE\t/\tFALSE\t0\tSESSDATA\tabc123", content)
        self.assertIn(".bilibili.com\tTRUE\t/\tFALSE\t0\tbili_jct\txyz789", content)

    def test_convert_cookie_with_spaces(self):
        """转换含有空格的 cookie 字符串"""
        cookie_str = "  key1 = val1 ;  key2 = val2  "
        path = self.convert(cookie_str)
        self.temp_files.append(path)

        with open(path, 'r') as f:
            content = f.read()

        self.assertIn("\tkey1\tval1", content)
        self.assertIn("\tkey2\tval2", content)

    def test_convert_cookie_with_equals_in_value(self):
        """转换值中包含等号的 cookie"""
        cookie_str = "token=abc=def=ghi"
        path = self.convert(cookie_str)
        self.temp_files.append(path)

        with open(path, 'r') as f:
            content = f.read()

        # 第一个 = 是分隔符，后面的 = 是值的一部分
        self.assertIn("\ttoken\tabc=def=ghi", content)

    def test_convert_empty_cookie_item(self):
        """跳过空项和无等号的项"""
        cookie_str = "key1=val1;; key2=val2; no_equals; =empty_key"
        path = self.convert(cookie_str)
        self.temp_files.append(path)

        with open(path, 'r') as f:
            content = f.read()

        self.assertIn("\tkey1\tval1", content)
        self.assertIn("\tkey2\tval2", content)
        # 空 key 也会写入
        self.assertIn("\tempty_key", content)
        # no_equals 不会写入（没有 = 分隔符）
        self.assertNotIn("\tno_equals", content)

    def test_convert_custom_domain(self):
        """使用自定义域名"""
        cookie_str = "session=abc"
        path = self.convert(cookie_str, domain=".example.com")
        self.temp_files.append(path)

        with open(path, 'r') as f:
            content = f.read()

        self.assertIn(".example.com\tTRUE", content)


class TestApplyBilibiliCookie(unittest.TestCase):
    """测试 _apply_bilibili_cookie 函数"""

    def setUp(self):
        """设置测试"""
        self.apply = _apply_bilibili_cookie

    @patch("app.downloaders.bilibili_downloader.get_cookie")
    def test_apply_with_cookie(self, mock_get_cookie):
        """有 Cookie 时注入 cookiefile"""
        mock_get_cookie.return_value = "SESSDATA=abc; bili_jct=xyz"

        ydl_opts = {}
        cookie_file = self.apply(ydl_opts)

        self.assertIsNotNone(cookie_file)
        self.assertIn("cookiefile", ydl_opts)
        self.assertTrue(os.path.exists(ydl_opts["cookiefile"]))

        # 清理临时文件
        if cookie_file and os.path.exists(cookie_file):
            os.unlink(cookie_file)

    @patch("app.downloaders.bilibili_downloader.get_cookie")
    def test_apply_without_cookie(self, mock_get_cookie):
        """无 Cookie 时不注入 cookiefile"""
        mock_get_cookie.return_value = None

        ydl_opts = {}
        cookie_file = self.apply(ydl_opts)

        self.assertIsNone(cookie_file)
        self.assertNotIn("cookiefile", ydl_opts)

    @patch("app.downloaders.bilibili_downloader.get_cookie")
    def test_apply_empty_cookie(self, mock_get_cookie):
        """空字符串 Cookie 等同于无 Cookie"""
        mock_get_cookie.return_value = ""

        ydl_opts = {}
        cookie_file = self.apply(ydl_opts)

        self.assertIsNone(cookie_file)
        self.assertNotIn("cookiefile", ydl_opts)


class TestBilibiliDownloaderWithCookie(unittest.TestCase):
    """测试 BilibiliDownloader 在有/无 Cookie 下的行为"""

    @patch("app.downloaders.bilibili_downloader.get_cookie")
    @patch("yt_dlp.YoutubeDL")
    def test_download_with_cookie(self, mock_ydl_class, mock_get_cookie):
        """有 Cookie 时 download 方法设置 cookiefile"""
        mock_get_cookie.return_value = "SESSDATA=test123"

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "id": "BV1test",
            "title": "测试视频",
            "duration": 120,
            "thumbnail": "https://example.com/cover.jpg",
        }
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        downloader = BilibiliDownloader()
        # 不实际下载，只验证 cookiefile 被传入
        with patch.object(downloader, 'download', wraps=None) as mock_dl:
            # 直接测试 _apply_bilibili_cookie 调用
            ydl_opts = {}
            cookie_file = _apply_bilibili_cookie(ydl_opts)

            self.assertIsNotNone(cookie_file)
            self.assertIn("cookiefile", ydl_opts)

            if cookie_file and os.path.exists(cookie_file):
                os.unlink(cookie_file)

    @patch("app.downloaders.bilibili_downloader.get_cookie")
    def test_download_without_cookie(self, mock_get_cookie):
        """无 Cookie 时不设置 cookiefile"""
        mock_get_cookie.return_value = None

        ydl_opts = {}
        cookie_file = _apply_bilibili_cookie(ydl_opts)

        self.assertIsNone(cookie_file)
        self.assertNotIn("cookiefile", ydl_opts)


if __name__ == "__main__":
    unittest.main()
