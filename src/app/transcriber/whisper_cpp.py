import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from app.decorators.timeit import timeit
from app.models.transcriber_model import TranscriptSegment, TranscriptResult
from app.transcriber.base import Transcriber
from app.config_manager import get_config_manager
from app.utils.logger import get_logger
from app.utils.path_helper import get_path_manager
from app.utils.file_cleanup import cleanup_temp_files

logger = get_logger(__name__)

# 配置管理器实例
_config_manager = get_config_manager()


class WhisperCppTranscriber(Transcriber):
    def __init__(
        self,
        cli_path: str = None,
        model_path: str = None,
    ):
        # 从配置文件读取配置（支持 config.yaml 覆盖）
        config = _config_manager.get_transcriber_config("whisper-cpp")
        self.cli_path = cli_path or config.get("cli_path", "whisper-cli")
        self.model_path = model_path or config.get("model_path", "")

        # 检查 CLI 是否可用
        if not self._is_cli_available():
            raise RuntimeError(
                f"未找到 whisper-cli。请安装 whisper.cpp 并确保其在 PATH 中，"
                f"或通过配置指定路径: transcriber.whisper-cpp.cli_path"
            )

        # 检查模型路径（展开 ~ 为用户主目录）
        self.model_path = os.path.expanduser(self.model_path)
        if not self.model_path or not Path(self.model_path).exists():
            raise RuntimeError(
                f"未找到 Whisper 模型文件: {self.model_path or '未配置'}\n"
                f"请在 config.yaml 中配置模型路径: transcriber.whisper-cpp.model_path"
            )

        logger.info(f"初始化 WhisperCpp 转录器，模型: {self.model_path}")

    def _is_cli_available(self) -> bool:
        """检查 whisper-cli 是否可用"""
        if os.path.isabs(self.cli_path):
            return Path(self.cli_path).exists()
        return shutil.which(self.cli_path) is not None

    @timeit
    def transcript(self, file_path: str) -> TranscriptResult:
        try:
            path_manager = get_path_manager()
            output_prefix = os.path.join(
                path_manager.cache_transcript_dir,
                f"whisper_cpp_{uuid.uuid4().hex[:8]}"
            )

            cmd = [
                self.cli_path,
                "-m", self.model_path,
                "-f", file_path,
                "--output-json",
                "--output-file", output_prefix,
            ]

            logger.info("启动 whisper-cli 转写...")
            proc_result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            if proc_result.returncode != 0:
                raise RuntimeError(f"whisper-cli 退出码: {proc_result.returncode}")

            json_path = f"{output_prefix}.json"
            if not Path(json_path).exists():
                raise RuntimeError(f"whisper-cli 未生成预期的 JSON 文件: {json_path}")

            with open(json_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            # 解析转写结果
            segments = []
            full_text = ""

            for item in raw.get("transcription", []):
                text = item.get("text", "").strip()
                if not text:
                    continue
                full_text += text + " "
                offsets = item.get("offsets", {})
                segments.append(TranscriptSegment(
                    start=offsets.get("from", 0) / 1000.0,
                    end=offsets.get("to", 0) / 1000.0,
                    text=text,
                ))

            transcript_result = TranscriptResult(
                language=raw.get("result", {}).get("language"),
                full_text=full_text.strip(),
                segments=segments,
                raw=raw,
            )

            # 转写完成后清理临时文件
            cleanup_temp_files(file_path)
            return transcript_result

        except Exception as e:
            logger.error(f"WhisperCpp 转写失败: {e}")
            raise
