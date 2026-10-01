"""ProcessConfig 模型测试

重点回归：argparse 未设置的选项值为 None，``ProcessConfig(**vars(args))``
整包构造时不应因 None 抛 ValidationError（pydantic 默认值只在字段
缺失时生效，显式传 None 仍会走类型校验）。
"""

import unittest

from app.models.process_config import ProcessConfig


class NoteFormatDefaultTest(unittest.TestCase):
    def test_none_falls_back_to_markdown(self):
        """argparse 的 --note-format default=None 传入时回退 markdown"""
        self.assertEqual(ProcessConfig(note_format=None).note_format, "markdown")

    def test_absent_uses_default(self):
        self.assertEqual(ProcessConfig().note_format, "markdown")

    def test_explicit_value_preserved(self):
        self.assertEqual(ProcessConfig(note_format="obsidian").note_format, "obsidian")


if __name__ == "__main__":
    unittest.main()
