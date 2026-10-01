"""默认 markdown 格式挂件：与历史版本输出保持一致（来源链接 + 视频信息卡）。"""

from typing import Optional

from app.models.pipeline_model import PreparedTask
from app.utils.note_helper import prepend_source_link, prepend_video_meta


class MarkdownFormatter:
    """默认格式：原样沿用 note_helper 的引用块信息卡逻辑"""

    def decorate(self, markdown: Optional[str], prepared: PreparedTask) -> Optional[str]:
        markdown = prepend_source_link(markdown, prepared.video_url)
        return prepend_video_meta(markdown, prepared.audio_meta.raw_info or {})
