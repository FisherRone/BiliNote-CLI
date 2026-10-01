"""MarkdownFormatter 回归契约测试：默认输出必须与历史逻辑逐字节一致。

历史逻辑 = prepend_source_link + prepend_video_meta（ai_processor 迁移前
的硬编码顺序），这里以 note_helper 的直接调用结果作为期望基准。
"""

import unittest

from app.formatters.markdown import MarkdownFormatter
from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.pipeline_model import PreparedTask
from app.models.transcriber_model import TranscriptResult
from app.utils.note_helper import prepend_source_link, prepend_video_meta


def _make_prepared(raw_info, video_url="https://www.bilibili.com/video/BV1xx"):
    audio_meta = AudioDownloadResult(
        file_path="/tmp/a.m4a",
        title="标题",
        duration=1.0,
        cover_url=None,
        platform="bilibili",
        video_id="BV1xx",
        raw_info=raw_info,
    )
    return PreparedTask(
        task_id="BV1xx",
        video_url=video_url,
        platform="bilibili",
        gpt_source=GPTSource(segment=[], title="标题", tags=""),
        audio_meta=audio_meta,
        transcript=TranscriptResult(language="zh", full_text="", segments=[]),
    )


class MarkdownFormatterRegressionTest(unittest.TestCase):
    def setUp(self):
        self.formatter = MarkdownFormatter()

    def test_output_equals_legacy_pipeline_with_full_meta(self):
        markdown = "# 笔记\n\n正文"
        raw_info = {"title": "标题", "uploader": "某UP主", "description": "简介",
                    "view_count": 100, "tags": ["A"]}
        prepared = _make_prepared(raw_info)

        expected = prepend_video_meta(prepend_source_link(markdown, prepared.video_url), raw_info)
        self.assertEqual(self.formatter.decorate(markdown, prepared), expected)

    def test_output_equals_legacy_pipeline_with_empty_meta(self):
        markdown = "# 笔记"
        prepared = _make_prepared({})

        expected = prepend_video_meta(prepend_source_link(markdown, prepared.video_url), {})
        self.assertEqual(self.formatter.decorate(markdown, prepared), expected)

    def test_output_equals_legacy_pipeline_without_url(self):
        markdown = "# 笔记"
        prepared = _make_prepared({"uploader": "某UP主"}, video_url="")
        raw_info = prepared.audio_meta.raw_info

        expected = prepend_video_meta(prepend_source_link(markdown, ""), raw_info)
        self.assertEqual(self.formatter.decorate(markdown, prepared), expected)

    def test_none_markdown_passthrough(self):
        prepared = _make_prepared({})
        self.assertIsNone(self.formatter.decorate(None, prepared))


if __name__ == "__main__":
    unittest.main()
