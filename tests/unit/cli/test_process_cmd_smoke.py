"""CLI process 单任务路径冒烟测试

验证成功路径完整走通（正常返回、展示真实落盘路径），
防止出现被 ``except Exception`` 吞掉的 NameError（如 print_success 未导入）
导致"笔记已生成却报错退出"的回归。

写盘契约：笔记文件由 AIProcessor 统一落盘，CLI 只展示 NoteResult 携带的
真实路径，自身不再写文件。
"""

import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from app.cli import process_cmd
from app.models.process_config import ProcessConfig


class ProcessSingleTaskSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _run(self, markdown, output_path=None):
        """跑通单任务路径，返回 (sys.exit mock, 捕获的 stdout)"""
        fake_result = MagicMock()
        fake_result.markdown = markdown
        fake_result.output_path = output_path

        cfg = ProcessConfig()
        items = [("https://www.bilibili.com/video/BV1xx", "bilibili", "BV1xx", "BV1xx")]

        stdout = io.StringIO()
        with patch.object(process_cmd, "NoteGenerator") as mock_ng, \
                patch("sys.exit") as mock_exit, \
                redirect_stdout(stdout):
            mock_ng.return_value.generate.return_value = fake_result
            process_cmd._process_tasks(items, cfg, "test-model", output_dir=self.tmpdir)
        return mock_exit, stdout.getvalue()

    def test_success_shows_real_path_and_exits_normally(self):
        markdown = "# 测试笔记\n\n正文内容"
        real_path = os.path.join(self.tmpdir, "标题 - UP主 - BV1xx.md")
        mock_exit, out = self._run(markdown, output_path=real_path)

        self.assertIn(real_path, out, "未展示 NoteResult 携带的真实落盘路径")
        mock_exit.assert_not_called()

    def test_success_does_not_write_file_itself(self):
        """写盘点已收敛到 AIProcessor，CLI 不应再自己写文件"""
        real_path = os.path.join(self.tmpdir, "标题 - UP主 - BV1xx.md")
        _, out = self._run("# 笔记", output_path=real_path)

        md_files = [f for f in os.listdir(self.tmpdir) if f.endswith(".md")]
        self.assertEqual(md_files, [], f"CLI 不应写盘，却发现: {md_files}")
        self.assertIn("保存到", out)

    def test_success_without_result_path_uses_fallback(self):
        """NoteResult 未携带路径时回退到 custom_output_path 展示，不崩溃"""
        fallback_path = os.path.join(self.tmpdir, "BV1xx.md")
        mock_exit, out = self._run("# 笔记", output_path=None)

        self.assertIn(fallback_path, out)
        mock_exit.assert_not_called()

    def test_generator_failure_exits_nonzero(self):
        mock_exit, _ = self._run("")  # 空 markdown 视为生成失败

        self.assertFalse(os.path.exists(os.path.join(self.tmpdir, "BV1xx.md")))
        mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
