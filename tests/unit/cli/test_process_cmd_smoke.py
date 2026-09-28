"""CLI process 单任务路径冒烟测试

验证成功路径完整走通（笔记落盘、进程正常返回），
防止出现被 ``except Exception`` 吞掉的 NameError（如 print_success 未导入）
导致"笔记已生成却报错退出"的回归。
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# process_cmd 依赖 config.model_config_manager（import 即读配置、触碰 keyring），
# 测试环境用桩模块隔离（与 test_searcher 隔离 bilibili_api 的做法一致）
sys.modules["config.model_config_manager"] = MagicMock()

from app.cli import process_cmd
from app.models.process_config import ProcessConfig


class ProcessSingleTaskSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _run(self, markdown):
        """跑通单任务路径，返回 sys.exit 的 mock 以便断言退出行为"""
        fake_result = MagicMock()
        fake_result.markdown = markdown

        cfg = ProcessConfig()
        items = [("https://www.bilibili.com/video/BV1xx", "bilibili", "BV1xx", "BV1xx")]

        with patch.object(process_cmd, "NoteGenerator") as mock_ng, \
                patch("sys.exit") as mock_exit:
            mock_ng.return_value.generate.return_value = fake_result
            process_cmd._process_tasks(items, cfg, "test-model", output_dir=self.tmpdir)
        return mock_exit

    def test_success_writes_note_and_exits_normally(self):
        markdown = "# 测试笔记\n\n正文内容"
        mock_exit = self._run(markdown)

        note_file = os.path.join(self.tmpdir, "BV1xx.md")
        self.assertTrue(os.path.exists(note_file), "笔记文件未落盘")
        with open(note_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), markdown)
        mock_exit.assert_not_called()

    def test_generator_failure_exits_nonzero(self):
        mock_exit = self._run("")  # 空 markdown 视为生成失败

        note_file = os.path.join(self.tmpdir, "BV1xx.md")
        self.assertFalse(os.path.exists(note_file), "失败时不应写笔记文件")
        mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
