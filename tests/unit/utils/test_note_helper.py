import unittest

from app.utils.note_helper import prepend_source_link, prepend_video_meta


class TestNoteHelper(unittest.TestCase):
    def test_prepend_source_link_adds_header_at_top(self):
        source_url = "https://www.bilibili.com/video/BV1xx411c7mD"
        markdown = "## 标题\n\n内容"

        result = prepend_source_link(markdown, source_url)

        self.assertTrue(result.startswith(f"> 来源链接：{source_url}\n\n"))
        self.assertIn("## 标题", result)

    def test_prepend_source_link_does_not_duplicate_when_header_exists(self):
        source_url = "https://www.youtube.com/watch?v=abc123"
        markdown = f"> 来源链接：{source_url}\n\n## 标题\n\n内容"

        result = prepend_source_link(markdown, source_url)

        self.assertEqual(result, markdown)


class TestPrependVideoMeta(unittest.TestCase):
    def test_comment_count_shown_in_stats_line(self):
        raw_info = {
            "title": "测试标题", "uploader": "某UP主",
            "view_count": 7520, "like_count": 245,
            "share_count": 30, "comment_count": 12345,
        }

        result = prepend_video_meta("## 标题\n\n内容", raw_info)

        self.assertIn("> **数据**：7520 播放 · 245 点赞 · 30 分享 · 1.2万 评论", result)

    def test_missing_comment_count_not_shown(self):
        raw_info = {"title": "测试标题", "view_count": 100, "like_count": 10}

        result = prepend_video_meta("## 标题\n\n内容", raw_info)

        self.assertIn("> **数据**：100 播放 · 10 点赞", result)
        self.assertNotIn("评论", result)


if __name__ == "__main__":
    unittest.main()
