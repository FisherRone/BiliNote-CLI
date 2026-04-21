"""测试 searcher 模块"""

import sys
import unittest
from unittest.mock import patch, MagicMock

# 在导入 searcher 之前 mock bilibili_api
_mock_bilibili_api = MagicMock()
_mock_bilibili_api.search = MagicMock()
_mock_bilibili_api.search.SearchObjectType = MagicMock()
_mock_bilibili_api.search.OrderVideo = MagicMock()
sys.modules["bilibili_api"] = _mock_bilibili_api

from app.services.searcher import search, _strip_html, _parse_bilibili_duration


class TestStripHtml(unittest.TestCase):
    """测试 HTML 标签移除功能"""

    def test_strip_html_tags(self):
        """移除 HTML 高亮标签"""
        self.assertEqual(_strip_html("<em class='keyword'>Python</em>教程"), "Python教程")
        self.assertEqual(_strip_html("<b>粗体</b>文本"), "粗体文本")
        self.assertEqual(_strip_html("无标签文本"), "无标签文本")

    def test_strip_empty_string(self):
        """处理空字符串"""
        self.assertEqual(_strip_html(""), "")

    def test_strip_nested_tags(self):
        """处理嵌套标签"""
        self.assertEqual(_strip_html("<div><span>内容</span></div>"), "内容")


class TestParseBilibiliDuration(unittest.TestCase):
    """测试 B站时长解析功能"""

    def test_parse_mm_ss_format(self):
        """解析 MM:SS 格式"""
        self.assertEqual(_parse_bilibili_duration("5:14"), 314)  # 5*60 + 14
        self.assertEqual(_parse_bilibili_duration("0:30"), 30)
        self.assertEqual(_parse_bilibili_duration("59:59"), 3599)

    def test_parse_hh_mm_ss_format(self):
        """解析 HH:MM:SS 格式"""
        self.assertEqual(_parse_bilibili_duration("1:30:45"), 5445)  # 1*3600 + 30*60 + 45
        self.assertEqual(_parse_bilibili_duration("2:00:00"), 7200)
        self.assertEqual(_parse_bilibili_duration("0:05:30"), 330)

    def test_parse_long_duration(self):
        """解析超长视频时长"""
        self.assertEqual(_parse_bilibili_duration("2398:14"), 143894)  # 2398*60 + 14

    def test_parse_empty_string(self):
        """处理空字符串"""
        self.assertEqual(_parse_bilibili_duration(""), 0)

    def test_parse_none(self):
        """处理 None 值"""
        self.assertEqual(_parse_bilibili_duration(None), 0)

    def test_parse_invalid_format(self):
        """处理无效格式"""
        self.assertEqual(_parse_bilibili_duration("invalid"), 0)
        self.assertEqual(_parse_bilibili_duration("5"), 0)
        self.assertEqual(_parse_bilibili_duration("1:2:3:4"), 0)

    def test_parse_non_numeric(self):
        """处理非数字内容"""
        self.assertEqual(_parse_bilibili_duration("abc:def"), 0)


class TestSearchBilibili(unittest.TestCase):
    """测试 B站搜索功能"""

    def setUp(self):
        """重置 mock"""
        _mock_bilibili_api.reset_mock()

    def test_search_success(self):
        """成功搜索并解析结果"""
        # 配置 mock 返回值
        _mock_bilibili_api.sync = MagicMock(return_value={
            "result": [
                {
                    "title": "<em class='keyword'>Python</em>教程",
                    "bvid": "BV1xx411c7mD",
                    "play": 10000,
                    "like": 500,
                    "favorites": 200,
                    "duration": "10:30",
                    "author": "UP主A"
                },
                {
                    "title": "Java入门",
                    "bvid": "BV2yy411c7mE",
                    "play": 5000,
                    "like": 300,
                    "favorites": 100,
                    "duration": "1:30:00",
                    "author": "UP主B"
                }
            ]
        })

        from app.services import searcher
        results = searcher._search_bilibili("编程", limit=2)

        self.assertEqual(len(results), 2)
        
        # 验证第一个结果
        self.assertEqual(results[0]["title"], "Python教程")  # HTML 标签已移除
        self.assertEqual(results[0]["link"], "https://www.bilibili.com/video/BV1xx411c7mD")
        self.assertEqual(results[0]["play_count"], 10000)
        self.assertEqual(results[0]["like_count"], 500)
        self.assertEqual(results[0]["favorite_count"], 200)
        self.assertEqual(results[0]["duration"], 630)  # 10*60 + 30
        self.assertEqual(results[0]["author"], "UP主A")
        
        # 验证第二个结果
        self.assertEqual(results[1]["duration"], 5400)  # 1*3600 + 30*60

    def test_search_empty_result(self):
        """搜索结果为空"""
        _mock_bilibili_api.sync = MagicMock(return_value={"result": []})

        from app.services import searcher
        results = searcher._search_bilibili("不存在的关键词", limit=5)

        self.assertEqual(len(results), 0)

    def test_search_api_error(self):
        """API 调用失败"""
        _mock_bilibili_api.sync = MagicMock(side_effect=Exception("网络错误"))

        from app.services import searcher
        results = searcher._search_bilibili("编程", limit=5)

        self.assertEqual(len(results), 0)


class TestSearchYoutube(unittest.TestCase):
    """测试 YouTube 搜索功能"""

    @patch("yt_dlp.YoutubeDL")
    def test_search_success(self, mock_yt_class):
        """成功搜索 YouTube 视频"""
        mock_ydl = MagicMock()
        mock_yt_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_yt_class.return_value.__exit__ = MagicMock(return_value=False)
        
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "title": "Python Tutorial",
                    "webpage_url": "https://www.youtube.com/watch?v=abc123",
                    "view_count": 100000,
                    "like_count": 5000,
                    "bookmark_count": 1000,
                    "duration": 600,
                    "uploader": "Tech Channel"
                }
            ]
        }
        
        from app.services import searcher
        results = searcher._search_youtube("python tutorial", limit=1)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Python Tutorial")
        self.assertEqual(results[0]["link"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(results[0]["play_count"], 100000)
        self.assertEqual(results[0]["duration"], 600)
        self.assertEqual(results[0]["author"], "Tech Channel")

    @patch("yt_dlp.YoutubeDL")
    def test_search_empty_entries(self, mock_yt_class):
        """搜索结果为空"""
        mock_ydl = MagicMock()
        mock_yt_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_yt_class.return_value.__exit__ = MagicMock(return_value=False)
        
        mock_ydl.extract_info.return_value = {"entries": []}
        
        from app.services import searcher
        results = searcher._search_youtube("不存在的关键词", limit=5)
        
        self.assertEqual(len(results), 0)

    @patch("yt_dlp.YoutubeDL")
    def test_search_with_none_entries(self, mock_yt_class):
        """处理 entries 为 None 的情况"""
        mock_ydl = MagicMock()
        mock_yt_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_yt_class.return_value.__exit__ = MagicMock(return_value=False)
        
        mock_ydl.extract_info.return_value = {"entries": None}
        
        from app.services import searcher
        results = searcher._search_youtube("test", limit=5)
        
        self.assertEqual(len(results), 0)

    @patch("yt_dlp.YoutubeDL")
    def test_search_skip_none_entry(self, mock_yt_class):
        """跳过 None 的 entry"""
        mock_ydl = MagicMock()
        mock_yt_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_yt_class.return_value.__exit__ = MagicMock(return_value=False)
        
        mock_ydl.extract_info.return_value = {
            "entries": [
                None,
                {"title": "Valid Video", "webpage_url": "https://youtube.com/watch?v=xyz", "duration": 300}
            ]
        }
        
        from app.services import searcher
        results = searcher._search_youtube("test", limit=5)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Valid Video")


class TestSearchMainFunction(unittest.TestCase):
    """测试主 search 函数"""

    @patch("app.services.searcher._search_bilibili")
    def test_search_bilibili_platform(self, mock_bilibili):
        """调用 B站搜索"""
        mock_bilibili.return_value = [{"title": "Test"}]
        
        results = search("python", platform="bilibili", limit=5)
        
        mock_bilibili.assert_called_once_with("python", 5)
        self.assertEqual(len(results), 1)

    @patch("app.services.searcher._search_youtube")
    def test_search_youtube_platform(self, mock_youtube):
        """调用 YouTube 搜索"""
        mock_youtube.return_value = [{"title": "Test"}]
        
        results = search("python", platform="youtube", limit=5)
        
        mock_youtube.assert_called_once_with("python", 5)
        self.assertEqual(len(results), 1)

    def test_search_unsupported_platform(self):
        """不支持的平台返回空列表"""
        results = search("python", platform="unsupported", limit=5)
        
        self.assertEqual(len(results), 0)

    def test_search_default_platform(self):
        """默认使用 bilibili 平台"""
        with patch("app.services.searcher._search_bilibili") as mock_bilibili:
            mock_bilibili.return_value = []
            search("python", limit=5)
            mock_bilibili.assert_called_once()


if __name__ == "__main__":
    unittest.main()
