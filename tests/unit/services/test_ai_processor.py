"""AIProcessor._resolve_output_path 的落盘路径规则测试

规则：目录跟随 prepared.output_path 所在目录（用户通过 --output-dir
或批次目录指定的优先）；文件名由平台命名规则决定，
B 站为 "{标题} - {UP主} - {BV号}.md"。
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# ai_processor 顶层 import config.model_config_manager（import 即读配置、
# 触碰 keyring），测试环境用桩模块隔离
sys.modules["config.model_config_manager"] = MagicMock()

from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.pipeline_model import PreparedTask
from app.models.transcriber_model import TranscriptResult
from app.services.pipeline.ai_processor import AIProcessor


def _make_prepared(platform="bilibili", output_path=None, raw_info=None,
                   video_id="BV1xx", task_id="BV1xx"):
    audio_meta = AudioDownloadResult(
        file_path="/tmp/a.m4a",
        title="标题",
        duration=1.0,
        cover_url=None,
        platform=platform,
        video_id=video_id,
        raw_info=raw_info if raw_info is not None else {},
    )
    return PreparedTask(
        task_id=task_id,
        video_url="https://example.com/v",
        platform=platform,
        gpt_source=GPTSource(segment=[], title="标题", tags=""),
        audio_meta=audio_meta,
        transcript=TranscriptResult(language="zh", full_text="", segments=[]),
        output_path=output_path,
    )


class ResolveOutputPathTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _user_path(self, name="BV1xx.md"):
        return os.path.join(self.tmpdir, name)

    def test_bilibili_keeps_user_dir_and_uses_friendly_name(self):
        prepared = _make_prepared(
            output_path=self._user_path(),
            raw_info={"uploader": "某UP主", "title": "视频标题"},
        )

        final = AIProcessor._resolve_output_path(prepared)

        self.assertEqual(os.path.dirname(final), self.tmpdir, "用户指定目录被绕过")
        self.assertEqual(os.path.basename(final), "视频标题 - 某UP主 - BV1xx.md")

    def test_bilibili_without_output_path_uses_default_dir(self):
        prepared = _make_prepared(
            output_path=None,
            raw_info={"uploader": "某UP主", "title": "视频标题"},
        )

        with patch("app.utils.path_helper.get_path_manager") as pm:
            pm.return_value.output_notes_dir = self.tmpdir
            final = AIProcessor._resolve_output_path(prepared)

        self.assertEqual(final, os.path.join(self.tmpdir, "视频标题 - 某UP主 - BV1xx.md"))

    def test_non_bilibili_output_path_unchanged(self):
        prepared = _make_prepared(platform="douyin", output_path=self._user_path())

        self.assertEqual(AIProcessor._resolve_output_path(prepared), self._user_path())

    def test_bilibili_missing_meta_falls_back_to_output_path(self):
        prepared = _make_prepared(
            output_path=self._user_path(),
            raw_info={"title": "只有标题"},  # 缺 uploader，友好命名不可用
        )

        self.assertEqual(AIProcessor._resolve_output_path(prepared), self._user_path())

    def test_no_output_path_non_bilibili_uses_default(self):
        prepared = _make_prepared(platform="douyin", output_path=None, task_id="xy123")

        with patch("app.utils.path_helper.get_path_manager") as pm:
            pm.return_value.get_note_output_path.return_value = os.path.join(
                self.tmpdir, "xy123.md"
            )
            final = AIProcessor._resolve_output_path(prepared)

        self.assertEqual(final, os.path.join(self.tmpdir, "xy123.md"))

    def test_long_title_truncated_but_bvid_kept(self):
        prepared = _make_prepared(
            output_path=self._user_path(),
            raw_info={"uploader": "很长的UP主名字" * 10, "title": "超" * 100},
        )

        basename = os.path.basename(AIProcessor._resolve_output_path(prepared))

        self.assertTrue(basename.endswith(" - BV1xx.md"), f"BV号应保留在末尾: {basename}")
        self.assertLessEqual(len(basename.split(" - ")[0]), 50, "标题应被截断")


if __name__ == "__main__":
    unittest.main()
