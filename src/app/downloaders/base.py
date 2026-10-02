
from abc import ABC, abstractmethod
from typing import Optional, Union

from app.enums.note_enums import DownloadQuality
from app.models.notes_model import AudioDownloadResult
from app.models.transcriber_model import TranscriptResult
QUALITY_MAP = {
    "fast": "32",
    "medium": "64",
    "slow": "128"
}


class Downloader(ABC):
    def __init__(self):
        #TODO 需要修改为可配置
        self.quality = QUALITY_MAP.get('fast')

    @abstractmethod
    def download(self, video_url: str, output_dir: str = None,
                 quality: DownloadQuality = DownloadQuality.fast, need_video: Optional[bool] = False,
                 skip_download: bool = False, quiet: bool = False) -> AudioDownloadResult:
        '''

        :param need_video:
        :param video_url: 资源链接
        :param output_dir: 输出路径 默认根目录data
        :param quality: 音频质量 fast | medium | slow
        :param quiet: 静默下载过程输出（yt-dlp 进度等）
        :return:返回一个 AudioDownloadResult 类
        '''
        pass

    @abstractmethod
    def download_video(self, video_url: str,
                       output_dir: Union[str, None] = None,
                       quiet: bool = False) -> str:
        '''
        下载视频文件，返回视频文件路径
        '''
        pass

    def download_subtitles(self, video_url: str, output_dir: str = None,
                           langs: list = None) -> Optional[TranscriptResult]:
        '''
        尝试获取平台字幕（人工字幕或自动生成字幕）

        :param video_url: 视频链接
        :param output_dir: 输出路径
        :param langs: 优先语言列表，如 ['zh-Hans', 'zh', 'en']
        :return: TranscriptResult 或 None（无字幕时）
        '''
        return None
