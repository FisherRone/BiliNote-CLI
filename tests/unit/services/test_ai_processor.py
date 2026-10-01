"""AIProcessor._resolve_output_path 的落盘路径规则测试

规则：目录跟随 prepared.output_path 所在目录（用户通过 --output-dir
或批次目录指定的优先）；文件名全平台统一为
"{标题[:50]} - {作者[:20]} - {视频ID}.md"（作者缺失时省略该段，
视频 ID 与标题相同（local 平台）时跳过，标题缺失时回退 task_id 命名）。
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.pipeline_model import PreparedTask
from app.models.transcriber_model import TranscriptResult
from app.services.pipeline.ai_processor import AIProcessor


def _make_prepared(platform="bilibili", output_path=None, raw_info=None,
                   video_id="BV1xx", task_id="BV1xx", title="视频标题"):
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
        task_id=task_id,
        video_url="https://example.com/v",
        platform=platform,
        gpt_source=GPTSource(segment=[], title=title, tags=""),
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

    def test_douyin_gets_unified_name_without_author(self):
        """非 B 站平台同样使用统一命名（作者缺失时省略作者段）"""
        prepared = _make_prepared(platform="douyin", output_path=self._user_path())

        final = AIProcessor._resolve_output_path(prepared)

        self.assertEqual(os.path.dirname(final), self.tmpdir)
        self.assertEqual(os.path.basename(final), "视频标题 - BV1xx.md")

    def test_douyin_with_author_in_raw_info(self):
        prepared = _make_prepared(platform="douyin", output_path=self._user_path(),
                                  raw_info={"author": "抖音作者"})

        self.assertEqual(
            os.path.basename(AIProcessor._resolve_output_path(prepared)),
            "视频标题 - 抖音作者 - BV1xx.md",
        )

    def test_local_skips_duplicate_video_id(self):
        """local 平台 video_id 即文件名（与标题相同），不应重复出现"""
        prepared = _make_prepared(platform="local", video_id="本地视频",
                                  task_id="本地视频", title="本地视频",
                                  output_path=self._user_path())

        self.assertEqual(
            os.path.basename(AIProcessor._resolve_output_path(prepared)),
            "本地视频.md",
        )

    def test_missing_title_falls_back_to_output_path(self):
        prepared = _make_prepared(output_path=self._user_path(), title="")

        self.assertEqual(AIProcessor._resolve_output_path(prepared), self._user_path())

    def test_no_output_path_uses_default_dir(self):
        prepared = _make_prepared(platform="douyin", output_path=None, task_id="xy123")

        with patch("app.utils.path_helper.get_path_manager") as pm:
            pm.return_value.output_notes_dir = self.tmpdir
            final = AIProcessor._resolve_output_path(prepared)

        self.assertEqual(final, os.path.join(self.tmpdir, "视频标题 - BV1xx.md"))

    def test_no_output_path_and_no_title_uses_task_id(self):
        prepared = _make_prepared(platform="douyin", output_path=None,
                                  task_id="xy123", title="")

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
