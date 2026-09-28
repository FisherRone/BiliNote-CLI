import subprocess
from pathlib import Path

import uuid

from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_screenshot(video_path: str, output_dir: str, timestamp: int, index: int) -> str:
    """
    使用 ffmpeg 生成截图，返回生成图片路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"screenshot_{index:03}_{uuid.uuid4()}.jpg"
    output_path = output_dir / filename

    command = [
        "ffmpeg",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(output_path),
        "-y"
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        logger.warning("ffmpeg 截图命令执行失败: %s", result.stderr)

    return str(output_path)
