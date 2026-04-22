import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Union

from app.enmus.task_status_enums import TaskStatus
from app.models.audio_model import AudioDownloadResult
from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.utils.path_helper import get_path_manager

logger = logging.getLogger(__name__)
path_manager = get_path_manager()


class TaskCache:
    """统一处理任务相关的文件缓存：状态、音频元信息、转写结果、元数据"""

    @staticmethod
    def update_status(
        task_id: Optional[str], status: Union[str, TaskStatus], message: Optional[str] = None
    ) -> None:
        if not task_id:
            return

        status_file = Path(path_manager.get_state_file_path(task_id))
        logger.debug(f"写入状态文件: {status_file} 当前状态: {status}")
        data = {"status": status.value if isinstance(status, TaskStatus) else status}
        if message:
            data["message"] = message

        try:
            temp_file = status_file.with_suffix(".tmp")
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_file.replace(status_file)
            logger.debug(f"状态文件写入成功: {status_file}")
        except Exception as e:
            logger.error(f"写入状态文件失败 (task_id={task_id})：{e}")
            try:
                with status_file.open("w", encoding="utf-8") as f:
                    f.write(f"Error writing status: {str(e)}")
            except:
                logger.error(f"写入错误  {e}")

    @staticmethod
    def load_transcript(task_id: str) -> Optional[TranscriptResult]:
        cache_file = Path(path_manager.get_transcript_cache_path(task_id))
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            segments = [TranscriptSegment(**seg) for seg in data.get("segments", [])]
            result = TranscriptResult(
                language=data.get("language"),
                full_text=data["full_text"],
                segments=segments,
            )
            logger.info(f"已从缓存加载转写结果，共 {len(segments)} 段")
            return result
        except Exception as e:
            logger.warning(f"加载转写缓存失败: {e}")
            return None

    @staticmethod
    def save_transcript(task_id: str, transcript: TranscriptResult) -> None:
        cache_file = Path(path_manager.get_transcript_cache_path(task_id))
        cache_file.write_text(
            json.dumps(asdict(transcript), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"转写结果已缓存 ({cache_file})")

    @staticmethod
    def load_audio_meta(task_id: str) -> Optional[AudioDownloadResult]:
        cache_file = Path(path_manager.get_audio_meta_cache_path(task_id))
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return AudioDownloadResult(**data)
        except Exception as e:
            logger.warning(f"读取音频缓存失败：{e}")
            return None

    @staticmethod
    def save_audio_meta(task_id: str, audio_meta: AudioDownloadResult) -> None:
        cache_file = Path(path_manager.get_audio_meta_cache_path(task_id))
        cache_file.write_text(
            json.dumps(asdict(audio_meta), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"音频元信息已缓存 ({cache_file})")

    @staticmethod
    def save_metadata(video_id: str, platform: str, task_id: str) -> None:
        try:
            metadata = {
                "video_id": video_id,
                "platform": platform,
                "task_id": task_id,
            }
            metadata_file = Path(path_manager.get_metadata_file_path(task_id))
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.info(
                f"已保存任务元数据 (video_id={video_id}, platform={platform}, task_id={task_id})"
            )
        except Exception as e:
            logger.error(f"保存任务元数据失败：{e}")

    @staticmethod
    def get_markdown_cache_file(
        task_id: Optional[str], output_path: Optional[str] = None
    ) -> Optional[Path]:
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        if task_id:
            return Path(path_manager.get_note_output_path(task_id))
        return None
