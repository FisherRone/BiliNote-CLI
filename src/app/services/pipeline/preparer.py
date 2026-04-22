import logging
from pathlib import Path
from typing import List, Optional, Union

from pydantic import HttpUrl

from app.downloaders.base import Downloader
from app.enmus.exception import NoteErrorEnum
from app.enmus.note_enums import DownloadQuality
from app.enmus.task_status_enums import TaskStatus
from app.exceptions.note import NoteError
from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.pipeline_model import PreparedTask
from app.models.transcriber_model import TranscriptResult
from app.services.cache.task_cache import TaskCache
from app.services.constant import SUPPORT_PLATFORM_MAP
from app.transcriber.base import Transcriber
from app.transcriber.transcriber_provider import get_transcriber_with_fallback
from app.utils.path_helper import get_path_manager
from app.utils.video_reader import VideoReader

logger = logging.getLogger(__name__)
path_manager = get_path_manager()


class TaskPreparer:
    """任务准备阶段：下载、转写、缓存检查、构建 PreparedTask"""

    def __init__(self):
        self.transcriber: Transcriber = get_transcriber_with_fallback()
        self.video_path: Optional[Path] = None
        self.video_img_urls: List[str] = []

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
    ) -> Optional[PreparedTask]:
        if grid_size is None:
            grid_size = []

        try:
            logger.info(f"开始准备任务 (task_id={task_id})")
            TaskCache.update_status(task_id, TaskStatus.PARSING)

            downloader = self._get_downloader(platform)
            markdown_cache_file = TaskCache.get_markdown_cache_file(task_id, output_path)

            # 1. 获取字幕/转写：优先缓存 → 平台字幕 → 音频转写
            transcript = TaskCache.load_transcript(task_id) if task_id else None

            if transcript is None:
                logger.info("尝试获取平台字幕（优先于音频下载）...")
                try:
                    transcript = downloader.download_subtitles(video_url)
                    if transcript and transcript.segments:
                        logger.info(f"成功获取平台字幕，共 {len(transcript.segments)} 段")
                        if task_id:
                            TaskCache.save_transcript(task_id, transcript)
                    else:
                        transcript = None
                        logger.info("平台无可用字幕，将下载音频后转写")
                except Exception as e:
                    logger.warning(f"获取平台字幕失败: {e}，将下载音频后转写")
                    transcript = None

            # 2. 下载音频/视频
            has_transcript = transcript is not None
            need_full_download = not has_transcript or screenshot or video_understanding
            audio_meta = self._download_media(
                downloader=downloader,
                video_url=video_url,
                quality=quality,
                task_id=task_id,
                output_path=output_path,
                screenshot=screenshot,
                video_understanding=video_understanding,
                video_interval=video_interval,
                grid_size=grid_size,
                skip_download=not need_full_download,
            )

            # 3. 如果前面没拿到字幕，走转写流程
            if transcript is None and task_id:
                transcript = self._transcribe_audio(
                    audio_file=audio_meta.file_path,
                    task_id=task_id,
                )

            # 构建 GPTSource
            source = GPTSource(
                title=audio_meta.title,
                segment=transcript.segments if transcript else [],
                tags=audio_meta.raw_info.get("tags", []),
                screenshot=screenshot,
                video_img_urls=self.video_img_urls,
                link=link,
                _format=_format or [],
                style=style,
                extras=extras,
                checkpoint_key=task_id,
            )

            return PreparedTask(
                task_id=task_id,
                video_url=str(video_url),
                platform=platform,
                gpt_source=source,
                audio_meta=audio_meta,
                transcript=transcript,
                video_path=self.video_path,
                video_img_urls=self.video_img_urls or [],
                link=link,
                screenshot=screenshot,
                formats=_format or [],
                output_path=str(markdown_cache_file) if markdown_cache_file else None,
                style=style,
                extras=extras,
            )

        except Exception as exc:
            logger.error(f"准备任务失败 (task_id={task_id})：{exc}", exc_info=True)
            TaskCache.update_status(task_id, TaskStatus.FAILED, message=str(exc))
            return None

    def _get_downloader(self, platform: str) -> Downloader:
        downloader_instance = SUPPORT_PLATFORM_MAP.get(platform)
        if not downloader_instance:
            logger.error(f"不支持的平台：{platform}")
            raise NoteError(
                code=NoteErrorEnum.PLATFORM_NOT_SUPPORTED.code,
                message=NoteErrorEnum.PLATFORM_NOT_SUPPORTED.message,
            )
        logger.info(f"使用下载器：{downloader_instance.__class__}")
        return downloader_instance

    def _download_media(
        self,
        downloader: Downloader,
        video_url: Union[str, HttpUrl],
        quality: DownloadQuality,
        task_id: Optional[str],
        output_path: Optional[str],
        screenshot: bool,
        video_understanding: bool,
        video_interval: int,
        grid_size: List[int],
        skip_download: bool = False,
    ) -> AudioDownloadResult:
        TaskCache.update_status(task_id, TaskStatus.DOWNLOADING)

        download_dir = Path(output_path).parent if output_path else None

        # 已有音频缓存，尝试加载
        if task_id:
            cached = TaskCache.load_audio_meta(task_id)
            if cached:
                return cached

        # 有字幕且不需要截图/视频理解时，只提取元信息不下载文件
        if skip_download:
            logger.info("已有字幕，仅提取视频元信息（不下载音视频）")
            try:
                audio = downloader.download(
                    video_url=video_url,
                    quality=quality,
                    output_dir=str(download_dir) if download_dir else None,
                    need_video=False,
                    skip_download=True,
                )
                if task_id:
                    TaskCache.save_audio_meta(task_id, audio)
                return audio
            except Exception as exc:
                logger.warning(f"元信息提取失败，将尝试完整下载: {exc}")

        # 判断是否需要下载视频
        need_video = screenshot or video_understanding
        if screenshot and not grid_size:
            grid_size = [2, 2]

        frame_interval = video_interval if video_interval and video_interval > 0 else 6
        if need_video:
            try:
                logger.info("开始下载视频")
                video_path_str = downloader.download_video(video_url)
                self.video_path = Path(video_path_str)
                logger.info(f"视频下载完成：{self.video_path}")

                if grid_size:
                    self.video_img_urls = VideoReader(
                        video_path=str(self.video_path),
                        grid_size=tuple(grid_size),
                        frame_interval=frame_interval,
                        unit_width=960,
                        unit_height=540,
                        save_quality=80,
                    ).run()
                else:
                    logger.info("未指定 grid_size，跳过缩略图生成")
            except Exception as exc:
                logger.error(f"视频下载失败：{exc}")
                TaskCache.update_status(task_id, TaskStatus.FAILED, message=str(exc))
                raise

        # 下载音频
        try:
            logger.info("开始下载音频")
            audio = downloader.download(
                video_url=video_url,
                quality=quality,
                output_dir=str(download_dir) if download_dir else None,
                need_video=need_video,
            )
            if task_id:
                TaskCache.save_audio_meta(task_id, audio)
            return audio
        except Exception as exc:
            logger.error(f"音频下载失败：{exc}")
            TaskCache.update_status(task_id, TaskStatus.FAILED, message=str(exc))
            raise

    def _transcribe_audio(
        self,
        audio_file: str,
        task_id: Optional[str],
    ) -> Optional[TranscriptResult]:
        TaskCache.update_status(task_id, TaskStatus.TRANSCRIBING)

        # 再次检查缓存（可能在下载期间其他进程已生成）
        if task_id:
            cached = TaskCache.load_transcript(task_id)
            if cached:
                return cached

        # 调用转写器
        try:
            logger.info("开始转写音频")
            transcript = self.transcriber.transcript(file_path=audio_file)
            if task_id:
                TaskCache.save_transcript(task_id, transcript)
            return transcript
        except Exception as exc:
            logger.error(f"音频转写失败：{exc}")
            TaskCache.update_status(task_id, TaskStatus.FAILED, message=str(exc))
            raise
