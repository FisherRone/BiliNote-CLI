"""
转写器 Fallback 机制测试
测试策略：使用 Mock 隔离外部依赖，验证 fallback 逻辑正确性
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.transcriber.transcriber_provider import (
    FallbackTranscriber,
    get_transcriber_with_fallback,
    _get_fallback_order,
    get_transcriber,
    TranscriberType,
)
from app.models.transcriber_model import TranscriptResult, TranscriptSegment


class TestFallbackOrder(unittest.TestCase):
    """测试 fallback 顺序生成逻辑"""

    def test_default_fallback_order(self):
        """测试默认 fallback 顺序（从 transcriber.json 读取）"""
        with patch('app.transcriber.transcriber_provider.config_manager') as mock_cm:
            mock_cm.get_fallback_priority.return_value = ["bcut", "kuaishou", "whisper-cpp","groq"]
            mock_cm.get.return_value = None  # 无用户首选配置
            
            order = _get_fallback_order()
            
            self.assertEqual(len(order), 4)
            self.assertEqual(order[0], TranscriberType.BCUT)
            self.assertEqual(order[1], TranscriberType.KUAISHOU)
    
    def test_preferred_type_first(self):
        """测试用户首选转写器被置顶"""
        with patch('app.transcriber.transcriber_provider.config_manager') as mock_cm:
            mock_cm.get_fallback_priority.return_value = ["groq", "bcut", "kuaishou"]
            mock_cm.get.return_value = "kuaishou"  # 用户首选快手
            
            order = _get_fallback_order()
            
            self.assertEqual(order[0], TranscriberType.KUAISHOU)
            # 确保原位置被移除，不会重复
            self.assertEqual(order.count(TranscriberType.KUAISHOU), 1)
    
    def test_invalid_transcriber_skipped(self):
        """测试配置中的无效转写器类型被跳过"""
        with patch('app.transcriber.transcriber_provider.config_manager') as mock_cm:
            mock_cm.get_fallback_priority.return_value = ["groq", "invalid_type", "bcut"]
            mock_cm.get.return_value = None
            
            order = _get_fallback_order()
            
            self.assertNotIn("invalid_type", [t.value for t in order])
            self.assertEqual(len(order), 2)


class TestFallbackTranscriber(unittest.TestCase):
    """测试 FallbackTranscriber 核心逻辑"""

    def setUp(self):
        self.mock_audio_file = "/tmp/test_audio.mp3"
        self.mock_result = TranscriptResult(
            language="zh",
            full_text="测试文本",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="测试文本")]
        )

    @patch('app.transcriber.transcriber_provider._get_fallback_order')
    @patch('app.transcriber.transcriber_provider.get_transcriber')
    def test_first_transcriber_success(self, mock_get, mock_order):
        """测试第一个转写器成功时直接返回"""
        mock_order.return_value = [TranscriberType.GROQ, TranscriberType.BCUT]
        
        mock_transcriber = Mock()
        mock_transcriber.transcript.return_value = self.mock_result
        mock_get.return_value = mock_transcriber
        
        fallback = FallbackTranscriber()
        result = fallback.transcript(self.mock_audio_file)
        
        self.assertEqual(result, self.mock_result)
        mock_get.assert_called_once_with(TranscriberType.GROQ)
        mock_transcriber.transcript.assert_called_once_with(self.mock_audio_file)

    @patch('app.transcriber.transcriber_provider._get_fallback_order')
    @patch('app.transcriber.transcriber_provider.get_transcriber')
    def test_fallback_to_second_on_failure(self, mock_get, mock_order):
        """测试第一个失败时 fallback 到第二个"""
        mock_order.return_value = [TranscriberType.GROQ, TranscriberType.BCUT]
        
        # 第一个失败，第二个成功
        mock_groq = Mock()
        mock_groq.transcript.side_effect = Exception("API 错误")
        
        mock_bcut = Mock()
        mock_bcut.transcript.return_value = self.mock_result
        
        mock_get.side_effect = [mock_groq, mock_bcut]
        
        fallback = FallbackTranscriber()
        result = fallback.transcript(self.mock_audio_file)
        
        self.assertEqual(result, self.mock_result)
        self.assertEqual(mock_get.call_count, 2)

    @patch('app.transcriber.transcriber_provider._get_fallback_order')
    @patch('app.transcriber.transcriber_provider.get_transcriber')
    def test_fallback_to_third_on_both_fail(self, mock_get, mock_order):
        """测试前两个都失败时 fallback 到第三个"""
        mock_order.return_value = [
            TranscriberType.GROQ, 
            TranscriberType.BCUT, 
            TranscriberType.KUAISHOU
        ]
        
        mock_groq = Mock()
        mock_groq.transcript.side_effect = Exception("Groq 失败")
        
        mock_bcut = Mock()
        mock_bcut.transcript.side_effect = Exception("Bcut 失败")
        
        mock_kuaishou = Mock()
        mock_kuaishou.transcript.return_value = self.mock_result
        
        mock_get.side_effect = [mock_groq, mock_bcut, mock_kuaishou]
        
        fallback = FallbackTranscriber()
        result = fallback.transcript(self.mock_audio_file)
        
        self.assertEqual(result, self.mock_result)
        self.assertEqual(mock_get.call_count, 3)

    @patch('app.transcriber.transcriber_provider._get_fallback_order')
    @patch('app.transcriber.transcriber_provider.get_transcriber')
    def test_all_failed_raises_error(self, mock_get, mock_order):
        """测试所有转写器都失败时抛出 RuntimeError"""
        mock_order.return_value = [TranscriberType.GROQ, TranscriberType.BCUT]
        
        mock_transcriber = Mock()
        mock_transcriber.transcript.side_effect = Exception("全部失败")
        mock_get.return_value = mock_transcriber
        
        fallback = FallbackTranscriber()
        
        with self.assertRaises(RuntimeError) as ctx:
            fallback.transcript(self.mock_audio_file)
        
        self.assertIn("所有转写器失败", str(ctx.exception))
        self.assertIn("groq", str(ctx.exception))
        self.assertIn("bcut", str(ctx.exception))

    @patch('app.transcriber.transcriber_provider._get_fallback_order')
    @patch('app.transcriber.transcriber_provider.get_transcriber')
    def test_empty_result_triggers_fallback(self, mock_get, mock_order):
        """测试返回空结果时也会触发 fallback"""
        mock_order.return_value = [TranscriberType.GROQ, TranscriberType.BCUT]
        
        # 第一个返回空结果，第二个成功
        mock_groq = Mock()
        mock_groq.transcript.return_value = TranscriptResult(
            language="zh", full_text="", segments=[]
        )
        
        mock_bcut = Mock()
        mock_bcut.transcript.return_value = self.mock_result
        
        mock_get.side_effect = [mock_groq, mock_bcut]
        
        fallback = FallbackTranscriber()
        result = fallback.transcript(self.mock_audio_file)
        
        self.assertEqual(result, self.mock_result)
        self.assertEqual(mock_get.call_count, 2)

    def test_factory_function(self):
        """测试 get_transcriber_with_fallback 工厂函数"""
        result = get_transcriber_with_fallback()
        self.assertIsInstance(result, FallbackTranscriber)


class TestGetTranscriber(unittest.TestCase):
    """测试单个转写器获取逻辑"""

    @patch('app.transcriber.transcriber_provider.config_manager')
    @patch('app.transcriber.transcriber_provider._init_transcriber')
    def test_get_groq_transcriber(self, mock_init, mock_cm):
        """测试获取 Groq 转写器"""
        mock_cm.get_transcriber_config.return_value = {
            "api_key": "test_key",
            "base_url": "https://api.groq.com"
        }
        
        mock_instance = Mock()
        mock_init.return_value = mock_instance
        
        result = get_transcriber(TranscriberType.GROQ)
        
        self.assertEqual(result, mock_instance)
        mock_init.assert_called_once()

    def test_get_unknown_transcriber_raises(self):
        """测试获取未知转写器类型时抛出 ValueError"""
        # 使用一个不在 TRANSCRIBER_CLASSES 中的类型
        with self.assertRaises(ValueError) as ctx:
            get_transcriber("unknown_type")  # type: ignore
        
        self.assertIn("未知的转录器类型", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()