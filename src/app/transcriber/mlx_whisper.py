import mlx_whisper
from pathlib import Path
import os
import platform
from huggingface_hub import snapshot_download

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


class MLXWhisperTranscriber(Transcriber):
    def __init__(
            self,
            model_size: str = None
    ):
        # 检查平台
        if platform.system() != "Darwin":
            raise RuntimeError("MLX Whisper 仅支持 Apple 平台")
        
        # 从配置文件读取配置（支持 config.yaml 覆盖）
        config = _config_manager.get_transcriber_config("mlx-whisper")
        self.model_size = model_size or config.get("model_size", "base")
        self.model_name = f"mlx-community/whisper-{self.model_size}-mlx"
        self.model_path = None
        
        # 设置模型路径
        path_manager = get_path_manager()
        self.model_path = os.path.join(path_manager.get_model_dir("mlx-whisper"), self.model_name)
        # 检查并下载模型
        if not Path(self.model_path).exists():
            logger.info(f"模型 {self.model_name} 不存在，开始下载...")
            snapshot_download(
                self.model_name,
                local_dir=self.model_path,
                local_dir_use_symlinks=False,
            )
            logger.info("模型下载完成")
        
        logger.info(f"初始化 MLX Whisper 转录器，模型：{self.model_name}")

    @timeit
    def transcript(self, file_path: str) -> TranscriptResult:
        try:
            # 使用 MLX Whisper 进行转录
            result = mlx_whisper.transcribe(
                file_path,
                path_or_hf_repo=f"{self.model_name}"
            )
            
            # 转换为标准格式
            segments = []
            full_text = ""
            
            for segment in result["segments"]:
                text = segment["text"].strip()
                full_text += text + " "
                segments.append(TranscriptSegment(
                    start=segment["start"],
                    end=segment["end"],
                    text=text
                ))
            
            transcript_result = TranscriptResult(
                language=result.get("language", "unknown"),
                full_text=full_text.strip(),
                segments=segments,
                raw=result
            )
            
            # 转写完成后清理临时文件
            cleanup_temp_files(file_path)
            return transcript_result
            
        except Exception as e:
            logger.error(f"MLX Whisper 转写失败：{e}")
            raise e

 