"""
转写器集成测试 - 需要真实环境配置
运行前请确保：
1. 至少配置了一个可用的转写器（如 GROQ_API_KEY）
2. 有测试音频文件
"""

import unittest
import os
from pathlib import Path

from app.transcriber.transcriber_provider import (
    get_transcriber, 
    get_transcriber_with_fallback,
    TranscriberType
)


@unittest.skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "设置 RUN_INTEGRATION_TESTS=1 运行集成测试"
)
class TestTranscriberIntegration(unittest.TestCase):
    """转写器集成测试"""

    @classmethod
    def setUpClass(cls):
        cls.test_audio = Path("tests/fixtures/test_audio.mp3")
        if not cls.test_audio.exists():
            raise unittest.SkipTest("测试音频文件不存在")

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