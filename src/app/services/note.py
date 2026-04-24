import logging
from typing import List, Optional, Union

from pydantic import HttpUrl

from app.enmus.note_enums import DownloadQuality
from app.enmus.task_status_enums import TaskStatus
from app.models.notes_model import NoteResult
from app.models.pipeline_model import PreparedTask
from app.services.cache.task_cache import TaskCache
from app.services.pipeline.ai_processor import AIProcessor
from app.services.pipeline.preparer import TaskPreparer
from app.utils.path_helper import get_path_manager
from app.config_manager import get_config_manager

logger = logging.getLogger(__name__)

config_mgr = get_config_manager()
path_manager = get_path_manager()

API_BASE_URL = config_mgr.get("api_base_url", "http://localhost")
BACKEND_PORT = config_mgr.get("backend_port", "8483")

IMAGE_OUTPUT_DIR = path_manager.get_temp_dir("", "screenshots")
IMAGE_BASE_URL = config_mgr.get("image_base_url", "/static/screenshots")


class NoteGenerator:
    """
    NoteGenerator 用于执行视频/音频下载、转写、GPT 生成笔记、插入截图/链接、
    以及将任务信息写入状态文件与数据库等功能。

    当前版本为门面模式，具体逻辑已拆分到 TaskPreparer 和 AIProcessor。
    """

    def __init__(self):
        self.preparer = TaskPreparer()
        self.ai_processor = AIProcessor(IMAGE_OUTPUT_DIR, IMAGE_BASE_URL)
        logger.info("NoteGenerator 初始化完成")

    def generate(
        self,
        video_url: Union[str, HttpUrl],
        platform: str,
        quality: DownloadQuality = DownloadQuality.medium,
        task_id: Optional[str] = None,
        model_name: Optional[str] = None,
        link: bool = False,
        screenshot: bool = False,
        _format: Optional[List[str]] = None,
        style: Optional[str] = None,
        extras: Optional[str] = None,
        output_path: Optional[str] = None,
        video_understanding: bool = False,
        video_interval: int = 0,
        grid_size: Optional[List[int]] = None,
        no_subtitle: bool = False,
    ) -> Optional[NoteResult]:
        """
        主流程：按步骤依次下载、转写、GPT 总结、截图/链接处理、存库、返回 NoteResult。
        """
        try:
            prepared = self.prepare(
                video_url=video_url,
                platform=platform,
                quality=quality,
                task_id=task_id,
                link=link,
                screenshot=screenshot,
                _format=_format,
                style=style,
                extras=extras,
                output_path=output_path,
                video_understanding=video_understanding,
                video_interval=video_interval,
                grid_size=grid_size,
                no_subtitle=no_subtitle,
            )
            if prepared is None:
                return None
            return self.summarize_and_save(prepared, model_name=model_name)
        except Exception as exc:
            logger.error(f"生成笔记流程异常 (task_id={task_id})：{exc}", exc_info=True)
            TaskCache.update_status(task_id, TaskStatus.FAILED, message=str(exc))
            return None

    def prepare(
        self,
        video_url: Union[str, HttpUrl],
        platform: str,
        quality: DownloadQuality = DownloadQuality.medium,
        task_id: Optional[str] = None,
        link: bool = False,
        screenshot: bool = False,
        _format: Optional[List[str]] = None,
        style: Optional[str] = None,
        extras: Optional[str] = None,
        output_path: Optional[str] = None,
        video_understanding: bool = False,
        video_interval: int = 0,
        grid_size: Optional[List[int]] = None,
        no_subtitle: bool = False,
    ) -> Optional[PreparedTask]:
        """
        同步准备阶段：下载、转写、构建 GPTSource。
        批量处理时主线程串行执行此阶段。
        """
        return self.preparer.prepare(
            video_url=video_url,
            platform=platform,
            quality=quality,
            task_id=task_id,
            link=link,
            screenshot=screenshot,
            _format=_format,
            style=style,
            extras=extras,
            output_path=output_path,
            video_understanding=video_understanding,
            video_interval=video_interval,
            grid_size=grid_size,
            no_subtitle=no_subtitle,
        )

    def summarize_and_save(
        self,
        prepared: PreparedTask,
        model_name: Optional[str] = None,
    ) -> Optional[NoteResult]:
        """
        AI 处理 + 后处理 + 保存。可在独立 NoteGenerator 实例中线程安全执行。
        """
        return self.ai_processor.process(prepared, model_name=model_name)

    @staticmethod
    def delete_note(video_id: str, platform: str) -> int:
        """
        删除笔记记录（CLI 工具不需要，保留接口）
        """
        logger.info(f"删除笔记记录 (video_id={video_id}, platform={platform})")
        return 0
