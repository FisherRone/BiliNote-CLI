import logging
from pathlib import Path
from typing import List, Optional

from app.utils.note_helper import replace_content_markers
from app.utils.screenshot_marker import extract_screenshot_timestamps
from app.utils.video_helper import generate_screenshot

logger = logging.getLogger(__name__)


class PostProcessor:
    """Markdown 后处理：截图插入、链接替换"""

    def __init__(self, image_output_dir: str, image_base_url: str):
        self.image_output_dir = image_output_dir
        self.image_base_url = image_base_url

    def process(
        self,
        markdown: str,
        formats: List[str],
        video_path: Optional[Path] = None,
        video_id: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> str:
        if "screenshot" in formats and video_path:
            try:
                markdown = self._insert_screenshots(markdown, video_path)
            except Exception as exc:
                logger.warning("截图插入失败，跳过该步骤")

        if "link" in formats and video_id and platform:
            try:
                markdown = replace_content_markers(markdown, video_id=video_id, platform=platform)
            except Exception as e:
                logger.warning(f"链接插入失败，跳过该步骤：{e}")

        return markdown

    def _insert_screenshots(self, markdown: str, video_path: Path) -> str:
        matches = extract_screenshot_timestamps(markdown)
        for idx, (marker, ts) in enumerate(matches):
            try:
                img_path = generate_screenshot(
                    str(video_path), self.image_output_dir, ts, idx
                )
                filename = Path(img_path).name
                img_url = f"{self.image_base_url.rstrip('/')}/{filename}"
                markdown = markdown.replace(marker, f"![]({img_url})", 1)
            except Exception as exc:
                logger.error(f"生成截图失败 (timestamp={ts})：{exc}")
                # 不中断，继续处理其他截图
        return markdown
