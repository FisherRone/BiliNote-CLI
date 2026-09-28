"""
转写器集成测试 - 需要真实环境配置

标记为 ``integration``：默认被排除（CI 用 ``-m "not integration"``），
本地显式运行::

    uv run pytest -m integration

运行前请确保：
1. 至少配置了一个可用的转写器（如 GROQ_API_KEY）
2. tests/fixtures/test_audio.mp3 存在
"""

import unittest
import os
from pathlib import Path

import pytest

from app.transcriber.transcriber_provider import (
    get_transcriber,
    get_transcriber_with_fallback,
    TranscriberType
)


@pytest.mark.integration
class TestTranscriberIntegration(unittest.TestCase):
    """转写器集成测试"""

    @classmethod
    def setUpClass(cls):
        cls.test_audio = Path("tests/fixtures/test_audio.mp3")
        if not cls.test_audio.exists():
            raise unittest.SkipTest("测试音频文件不存在（tests/fixtures/test_audio.mp3）")

    def test_groq_transcription(self):
        """测试 Groq 转写（需要 GROQ_API_KEY）"""
        if not os.getenv("GROQ_API_KEY"):
            self.skipTest("未配置 GROQ_API_KEY")

        transcriber = get_transcriber(TranscriberType.GROQ)
        result = transcriber.transcript(str(self.test_audio))

        self.assertIsNotNone(result)
        self.assertTrue(len(result.segments) > 0)
        self.assertTrue(len(result.full_text) > 0)

    def test_fallback_with_real_transcribers(self):
        """测试真实 fallback 场景"""
        fallback = get_transcriber_with_fallback()
        result = fallback.transcript(str(self.test_audio))

        self.assertIsNotNone(result)
        self.assertTrue(len(result.segments) > 0)


if __name__ == "__main__":
    unittest.main()
