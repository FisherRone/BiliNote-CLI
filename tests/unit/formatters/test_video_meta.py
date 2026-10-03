"""CanonicalVideoMeta 跨平台元数据归一化测试"""

import unittest

from app.formatters.video_meta import build_video_meta
from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.pipeline_model import PreparedTask
from app.models.transcriber_model import TranscriptResult


def _make_prepared(platform="bilibili", video_id="BV1xx", title="测试标题", raw_info=None):
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
        video_url="https://example.com/v",
        platform=platform,
        gpt_source=GPTSource(segment=[], title=title, tags=""),
        audio_meta=audio_meta,
        transcript=TranscriptResult(language="zh", full_text="", segments=[]),
    )


class TagNormalizationTest(unittest.TestCase):
    def test_list_of_strings(self):
        meta = build_video_meta(_make_prepared(raw_info={"tags": ["A", "B"]}))
        self.assertEqual(meta.tags, ["A", "B"])

    def test_list_of_dicts_bilibili_variant(self):
        meta = build_video_meta(_make_prepared(
            raw_info={"tags": [{"tag": "A"}, {"title": "B"}, "C", {"tag": "A"}]}))
        self.assertEqual(meta.tags, ["A", "B", "C"])

    def test_comma_separated_string_kuaishou(self):
        meta = build_video_meta(_make_prepared(platform="kuaishou",
                                               raw_info={"tags": "游戏, 日常，生活"}))
        self.assertEqual(meta.tags, ["游戏", "日常", "生活"])

    def test_hashtag_string_douyin(self):
        meta = build_video_meta(_make_prepared(platform="douyin",
                                               raw_info={"tags": "今天聊聊AI #人工智能 #科技"}))
        self.assertEqual(meta.tags, ["人工智能", "科技"])

    def test_whitespace_inside_tags_removed(self):
        meta = build_video_meta(_make_prepared(raw_info={
            "tags": ["AI 学习", "科技　生活", " #笔记整理 "]}))
        self.assertEqual(meta.tags, ["AI学习", "科技生活", "笔记整理"])

    def test_digit_only_tags_dropped(self):
        meta = build_video_meta(_make_prepared(raw_info={
            "tags": ["2023", "12 34", "１２３", "  ", "4K", "人工智能"]}))
        self.assertEqual(meta.tags, ["4K", "人工智能"])

    def test_dedup_after_whitespace_removal(self):
        meta = build_video_meta(_make_prepared(raw_info={
            "tags": ["AI 学习", "AI学习"]}))
        self.assertEqual(meta.tags, ["AI学习"])

    def test_empty_tags(self):
        self.assertEqual(build_video_meta(_make_prepared()).tags, [])


class FieldMappingTest(unittest.TestCase):
    def test_bilibili_full_mapping(self):
        meta = build_video_meta(_make_prepared(raw_info={
            "uploader": "某UP主", "description": "简介",
            "view_count": 100, "like_count": 10,
            "coin_count": 5, "favorite_count": 3, "share_count": 2,
            "comment_count": 12345,
        }))
        self.assertEqual(meta.title, "测试标题")
        self.assertEqual(meta.author, "某UP主")
        self.assertEqual(meta.description, "简介")
        self.assertEqual(meta.stats, "100 播放 · 10 点赞 · 5 投币 · 3 收藏 · 2 分享 · 1.2万 评论")
        self.assertEqual(meta.platform, "bilibili")

    def test_stats_skip_missing_comment_count(self):
        meta = build_video_meta(_make_prepared(raw_info={
            "view_count": 100, "like_count": 10}))
        self.assertEqual(meta.stats, "100 播放 · 10 点赞")

    def test_author_prefers_uploader_over_author(self):
        meta = build_video_meta(_make_prepared(
            raw_info={"uploader": "UP主", "author": "作者"}))
        self.assertEqual(meta.author, "UP主")

    def test_description_falls_back_to_caption(self):
        meta = build_video_meta(_make_prepared(
            platform="douyin", raw_info={"caption": "抖音简介"}))
        self.assertEqual(meta.description, "抖音简介")

    def test_title_falls_back_to_raw_info(self):
        meta = build_video_meta(_make_prepared(title="", raw_info={"title": "备用标题"}))
        self.assertEqual(meta.title, "备用标题")

    def test_empty_raw_info_degrades_gracefully(self):
        meta = build_video_meta(_make_prepared(platform="local"))
        self.assertEqual(meta.title, "测试标题")
        self.assertEqual(meta.author, "")
        self.assertEqual(meta.stats, "")
        self.assertEqual(meta.tags, [])
        self.assertEqual(meta.platform, "local")


if __name__ == "__main__":
    unittest.main()
