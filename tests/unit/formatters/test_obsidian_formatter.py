"""ObsidianFormatter 单元测试

验证 frontmatter 构建（跨平台元数据降级、YAML 转义）、
一级标题规范化，以及 markdown=None 透传契约。
"""

import re
import unittest
from datetime import date

import yaml

from app.formatters.obsidian import ObsidianFormatter
from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.pipeline_model import PreparedTask
from app.models.transcriber_model import TranscriptResult


def _make_prepared(platform="bilibili", video_id="BV1xx", title="测试标题",
                   raw_info=None, video_url="https://www.bilibili.com/video/BV1xx"):
    audio_meta = AudioDownloadResult(
        file_path="/tmp/a.m4a",
        title=title,
        duration=1.0,
        cover_url=None,
        platform=platform,
        video_id=video_id,
        raw_info=raw_info if raw_info is not None else {},
    )
    return PreparedTask(
        task_id=video_id,
        video_url=video_url,
        platform=platform,
        gpt_source=GPTSource(segment=[], title=title, tags=""),
        audio_meta=audio_meta,
        transcript=TranscriptResult(language="zh", full_text="", segments=[]),
    )


def _parse_frontmatter(markdown: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", markdown, re.S)
    assert match, f"frontmatter 格式不合法:\n{markdown}"
    return yaml.safe_load(match.group(1))


class ObsidianFrontmatterTest(unittest.TestCase):
    def setUp(self):
        self.formatter = ObsidianFormatter()

    def test_bilibili_full_frontmatter_fields(self):
        prepared = _make_prepared(raw_info={
            "uploader": "某UP主",
            "description": "这是简介",
            "view_count": 7520,
            "like_count": 245,
            "tags": ["TED", "自我成长", "心理健康"],
        })
        result = self.formatter.decorate("# 测试标题\n\n正文", prepared)

        fm = _parse_frontmatter(result)
        self.assertEqual(fm["title"], "测试标题")
        self.assertEqual(fm["author"], "某UP主")
        self.assertEqual(fm["description"], "这是简介")
        self.assertEqual(fm["data"], "7520 播放 · 245 点赞")
        self.assertEqual(fm["tags"], ["TED", "自我成长", "心理健康"])
        self.assertEqual(fm["source"], "https://www.bilibili.com/video/BV1xx")
        self.assertEqual(fm["platform"], "bilibili")
        self.assertEqual(fm["created"], date.today().isoformat())

    def test_stats_use_wan_format(self):
        prepared = _make_prepared(raw_info={"view_count": 12345, "like_count": 678})
        fm = _parse_frontmatter(self.formatter.decorate("正文", prepared))
        self.assertEqual(fm["data"], "1.2万 播放 · 678 点赞")

    def test_yaml_escapes_colon_and_quotes_in_title(self):
        tricky_title = '视频: "上"集与下半场'
        prepared = _make_prepared(title=tricky_title)
        result = self.formatter.decorate("正文", prepared)

        fm = _parse_frontmatter(result)
        self.assertEqual(fm["title"], tricky_title)

    def test_description_flattened_and_truncated(self):
        long_desc = "第一行\n第二行\n" * 50
        prepared = _make_prepared(raw_info={"description": long_desc})
        fm = _parse_frontmatter(self.formatter.decorate("正文", prepared))

        self.assertNotIn("\n", fm["description"])
        self.assertTrue(fm["description"].endswith("..."))
        self.assertLessEqual(len(fm["description"]), 210)

    def test_empty_fields_omitted(self):
        # local 平台只有标题和路径
        prepared = _make_prepared(platform="local", video_id="本地视频",
                                  title="本地视频", video_url="/tmp/v.mp4")
        result = self.formatter.decorate("正文", prepared)

        fm = _parse_frontmatter(result)
        self.assertEqual(fm["platform"], "local")
        for absent in ("author", "description", "data", "tags"):
            self.assertNotIn(absent, fm)
        self.assertEqual(fm["source"], "/tmp/v.mp4")

    def test_douyin_metadata_degradation(self):
        prepared = _make_prepared(platform="douyin", video_id="7345678901234567",
                                  video_url="https://www.douyin.com/video/7345678901234567",
                                  raw_info={
                                      "tags": "今天聊聊AI #人工智能 #科技",
                                      "author": "某创作者",
                                      "description": "今天聊聊AI",
                                      "view_count": 12345,
                                      "like_count": 678,
                                  })
        fm = _parse_frontmatter(self.formatter.decorate("正文", prepared))

        self.assertEqual(fm["author"], "某创作者")
        self.assertEqual(fm["tags"], ["人工智能", "科技"])
        self.assertEqual(fm["data"], "1.2万 播放 · 678 点赞")


class ObsidianBodyTest(unittest.TestCase):
    def setUp(self):
        self.formatter = ObsidianFormatter()

    def test_leading_h1_replaced_by_canonical_title(self):
        prepared = _make_prepared()
        result = self.formatter.decorate("# 模型自己写的标题\n\n正文内容", prepared)

        self.assertIn("\n\n# 测试标题\n\n正文内容", result)
        self.assertNotIn("模型自己写的标题", result)

    def test_h2_sections_preserved(self):
        prepared = _make_prepared()
        result = self.formatter.decorate("## 第一个小节\n\n- 要点", prepared)

        self.assertIn("# 测试标题\n\n## 第一个小节", result)

    def test_body_whitespace_stripped(self):
        prepared = _make_prepared()
        result = self.formatter.decorate("\n\n  正文  \n\n", prepared)

        self.assertTrue(result.endswith("# 测试标题\n\n正文\n"))

    def test_none_markdown_passthrough(self):
        prepared = _make_prepared()
        self.assertIsNone(self.formatter.decorate(None, prepared))


if __name__ == "__main__":
    unittest.main()
