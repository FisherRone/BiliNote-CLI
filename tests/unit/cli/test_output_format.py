"""输出格式测试：极简模式（--quiet）、批量任务行、search 结果行

对应输出改版设计：
- 极简模式仅用于直接给 URL 的单视频处理；--json 是批量模式，两者不交互
- 批量输出：头部（任务数/AI 并发/模型）+ 统一 ✓/✗ 任务行 + 尾部统计
- search 结果行：作者 - 标题 / 指标行 / 简介 / 标签，字段缺失跳过片段
"""

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from app.cli import main as cli_main
from app.cli import process_cmd, search_cmd
from app.models.process_config import ProcessConfig
from app.services.batch_processor import AsyncBatchProcessor


def _run_func(func, *args, **kwargs):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        result = func(*args, **kwargs)
    return result, stdout.getvalue()


class QuietModeOutputTest(unittest.TestCase):
    """单任务 --quiet：只打印成功/标题/保存路径三类信息"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.url = "https://www.bilibili.com/video/BV1xx"
        self.items = [(self.url, "bilibili", "BV1xx", "BV1xx")]

    def _run(self, quiet, audio_title="视频标题"):
        real_path = os.path.join(self.tmpdir, "视频标题 - UP主 - BV1xx.md")
        fake_result = MagicMock()
        fake_result.markdown = "# 笔记\n\n" + "正文" * 300
        fake_result.output_path = real_path
        fake_result.audio_meta.title = audio_title

        stdout = io.StringIO()
        with patch.object(process_cmd, "NoteGenerator") as mock_ng, \
                patch("sys.exit") as mock_exit, \
                redirect_stdout(stdout):
            mock_ng.return_value.generate.return_value = fake_result
            process_cmd._process_tasks(self.items, ProcessConfig(), "test-model",
                                       output_dir=self.tmpdir, quiet=quiet)
        return mock_exit, stdout.getvalue()

    def test_quiet_prints_minimal_lines(self):
        _, out = self._run(quiet=True)

        self.assertIn("✓ 笔记生成成功！", out)
        self.assertIn("标题：视频标题", out)
        self.assertIn("保存到:", out)
        # 原链接行已移除
        self.assertNotIn("原链接", out)
        # 过程输出全部抑制
        self.assertNotIn("开始生成笔记", out)
        self.assertNotIn("平台:", out)
        self.assertNotIn("更多内容请查看文件", out)  # 笔记预览已抑制

    def test_quiet_title_falls_back_to_task_id(self):
        _, out = self._run(quiet=True, audio_title=None)
        self.assertIn("标题：BV1xx", out)

    def test_non_quiet_keeps_preview(self):
        _, out = self._run(quiet=False)

        self.assertIn("开始生成笔记", out)
        self.assertIn("更多内容请查看文件", out)
        self.assertIn("保存到", out)


class QuietWiringTest(unittest.TestCase):
    """--quiet 参数经 argparse 整条入口的接线：仅直接 URL 单视频生效"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _run_cli(self, argv_extra):
        fake_result = MagicMock()
        fake_result.markdown = "# 笔记"
        fake_result.output_path = os.path.join(self.tmpdir, "BV1xx.md")
        fake_result.audio_meta.title = "Q标题"

        fake_cm = MagicMock()
        fake_cm.get.return_value = ""

        stdout = io.StringIO()
        with patch.object(process_cmd, "NoteGenerator") as mock_ng, \
                patch.object(process_cmd, "get_default_model", return_value="test-model"), \
                patch.object(process_cmd, "get_model_config", return_value={"api_key": "sk-test"}), \
                patch.object(process_cmd, "get_config_manager", return_value=fake_cm), \
                patch("app.config_manager.get_config_manager", return_value=fake_cm), \
                patch.object(process_cmd, "_show_shortcut_process_prompt"), \
                patch("sys.exit") as mock_exit, \
                patch("sys.argv", ["bilinote", "process", *argv_extra]), \
                redirect_stdout(stdout):
            mock_ng.return_value.generate.return_value = fake_result
            cli_main()
        self._generate_mock = mock_ng.return_value.generate
        return mock_exit, stdout.getvalue()

    def test_quiet_flag_takes_effect_for_direct_url(self):
        _, out = self._run_cli(["https://www.bilibili.com/video/BV1xx", "--quiet"])

        self.assertIn("标题：Q标题", out)
        self.assertNotIn("开始生成笔记", out)

    def test_quiet_flag_propagates_to_config(self):
        """--quiet 需传入 ProcessConfig.quiet，供静默 yt-dlp 下载进度"""
        _, out = self._run_cli(["https://www.bilibili.com/video/BV1xx", "--quiet"])

        generate = self._generate_mock
        self.assertTrue(generate.call_args.kwargs["cfg"].quiet)

    def test_quiet_not_propagated_in_batch_mode(self):
        """--json 批量模式下 quiet 不生效，下载进度保持正常输出"""
        json_path = os.path.join(self.tmpdir, "result.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"results": [{"index": 1,
                                    "link": "https://www.bilibili.com/video/BV1xx"}]}, f)

        _, out = self._run_cli(["--json", json_path, "--quiet"])

        self.assertIn("从 JSON 加载全部 1 个视频链接", out)
        self.assertIn("开始生成笔记", out)  # 走了常规单任务输出，quiet 未生效
        generate = self._generate_mock
        self.assertFalse(generate.call_args.kwargs["cfg"].quiet)


class BatchOutputFormatTest(unittest.TestCase):
    """批量输出：头部两行 + 统一任务行 + 尾部统计"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _make_items(self, n):
        return [(f"https://www.bilibili.com/video/BV{i}", "bilibili", f"BV{i}", f"标题{i}")
                for i in range(1, n + 1)]

    def _prepare_ok(self, url, platform, task_id, output_path):
        return {"task_id": task_id}

    def test_full_output(self):
        processor = AsyncBatchProcessor(output_dir=self.tmpdir)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            success, fail = processor.process(self._make_items(3), self._prepare_ok,
                                              lambda p: True, model_name="deepseek-chat")
        out = stdout.getvalue()

        self.assertEqual((success, fail), (3, 0))
        self.assertIn("开始批量处理: 3 个任务 (AI 并发: 3)", out)
        self.assertIn("使用模型: deepseek-chat", out)
        self.assertIn("  ✓ 任务1 完成: 标题1 - BV1", out)
        self.assertIn("  ✓ 任务3 完成: 标题3 - BV3", out)
        self.assertIn("批量处理完成!", out)
        self.assertIn("  成功: 3", out)
        self.assertIn(f"输出目录: {self.tmpdir}", out)
        # 过程噪音已移除
        self.assertNotIn("准备:", out)
        self.assertNotIn("提交 AI", out)
        self.assertNotIn("等待剩余", out)
        # 头部不再打印输出目录（尾部已有）
        self.assertLess(out.index("使用模型"), out.index("输出目录:"))

    def test_failure_lines_carry_error_text(self):
        processor = AsyncBatchProcessor(output_dir=self.tmpdir)

        def prepare(url, platform, task_id, output_path):
            if task_id == "BV1":
                return None  # 准备失败
            if task_id == "BV2":
                raise RuntimeError("下载失败")  # 准备抛异常
            return {"task_id": task_id}

        def ai(prepared):
            if prepared["task_id"] == "BV3":
                return False  # AI 返回空结果
            return True

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            success, fail = processor.process(self._make_items(4), prepare, ai,
                                              model_name="deepseek-chat")
        out = stdout.getvalue()

        self.assertEqual((success, fail), (1, 3))
        self.assertIn("  ✗ 任务1 失败: BV1 - 准备阶段失败", out)
        self.assertIn("  ✗ 任务2 失败: BV2 - 下载失败", out)
        self.assertIn("  ✗ 任务3 失败: BV3 - AI 处理返回空结果", out)
        self.assertIn("  ✓ 任务4 完成: 标题4 - BV4", out)
        self.assertIn("  失败: 3", out)

    def test_model_line_omitted_when_not_provided(self):
        processor = AsyncBatchProcessor(output_dir=self.tmpdir)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            processor.process(self._make_items(1), self._prepare_ok, lambda p: True)
        out = stdout.getvalue()

        self.assertIn("开始批量处理: 1 个任务", out)
        self.assertNotIn("使用模型:", out)


class SearchResultLineTest(unittest.TestCase):
    """search 结果行格式：作者 - 标题 / 指标行 / 简介 / 标签"""

    def test_bilibili_full_line(self):
        item = {
            "title": "视频标题", "author": "UP主A",
            "play_count": 34000, "like_count": 120, "favorite_count": 45,
            "duration": 420, "pubdate": 1759335000,
            "description": "第一行\n\n第二行", "tags": ["编程", "Python"],
        }
        _, out = _run_func(search_cmd._print_result, 1, item)

        self.assertIn("1. UP主A - 视频标题", out)
        self.assertIn("发布时间：", out)
        self.assertIn("播放量：3.4w", out)
        self.assertIn("点赞量：120", out)
        self.assertIn("收藏量：45", out)
        self.assertIn("时长：7min", out)
        self.assertIn("简介：第一行 第二行", out)  # 多行压成单行
        self.assertIn("标签：编程、Python", out)

    def test_missing_fields_skip_segments(self):
        """YouTube flat 模式：pubdate/description/tags 缺失时跳过对应片段"""
        item = {"title": "YT Video", "play_count": None, "duration": None}
        _, out = _run_func(search_cmd._print_result, 2, item)

        self.assertIn("2. YT Video", out)  # 无作者时退化为仅标题
        self.assertNotIn("发布时间", out)
        self.assertNotIn("播放量", out)
        self.assertNotIn("简介", out)
        self.assertNotIn("标签", out)

    def test_description_truncated_at_limit(self):
        long_desc = "字" * 600
        self.assertEqual(len(search_cmd._format_description(long_desc)), 501)  # 500 字 + …
        self.assertTrue(search_cmd._format_description(long_desc).endswith("…"))
        self.assertEqual(search_cmd._format_description("短简介"), "短简介")
        self.assertIsNone(search_cmd._format_description(None))
        self.assertIsNone(search_cmd._format_description("   \n  "))

    def test_pubdate_formatting(self):
        from datetime import datetime
        ts = 1759335000
        expected = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")  # 避免时区相关的硬编码
        self.assertEqual(search_cmd._format_pubdate(ts), expected)
        self.assertEqual(search_cmd._format_pubdate(str(ts)), expected)
        self.assertIsNone(search_cmd._format_pubdate(None))
        self.assertIsNone(search_cmd._format_pubdate("not-a-number"))

    def test_tags_normalization(self):
        self.assertEqual(search_cmd._format_tags("a,b , c"), ["a", "b", "c"])
        self.assertEqual(search_cmd._format_tags(["x", "", " y "]), ["x", "y"])
        self.assertEqual(search_cmd._format_tags(None), [])


class FormatCountTest(unittest.TestCase):
    """format_count 数字人性化"""

    def setUp(self):
        from app.cli.console import format_count
        self.format_count = format_count

    def test_basic_units(self):
        self.assertEqual(self.format_count(45), "45")
        self.assertEqual(self.format_count(120), "120")
        self.assertEqual(self.format_count(3400), "3.4k")
        self.assertEqual(self.format_count(34000), "3.4w")
        self.assertEqual(self.format_count(558000), "55.8w")

    def test_large_numbers_no_scientific_notation(self):
        """回归：万位数值 >=1000 时 %.3g 曾退化成 2.04e+03w"""
        self.assertEqual(self.format_count(20400000), "2040w")
        self.assertEqual(self.format_count(102040000), "10204w")
        self.assertEqual(self.format_count(1000000), "100w")

    def test_none(self):
        self.assertIsNone(self.format_count(None))


if __name__ == "__main__":
    unittest.main()
