from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.transcriber_model import TranscriptResult


@dataclass
class PreparedTask:
    """同步准备阶段的输出，供异步 AI 阶段使用"""

    task_id: str
    video_url: str
    platform: str
    gpt_source: GPTSource
    audio_meta: AudioDownloadResult
    transcript: TranscriptResult
    video_path: Optional[Path] = None
    video_img_urls: List[str] = field(default_factory=list)
    link: bool = False
    screenshot: bool = False
    formats: List[str] = field(default_factory=list)
    output_path: Optional[str] = None
    style: Optional[str] = None
    extras: Optional[str] = None
