import logging
import sys
from pathlib import Path

# 导入 path_helper 获取日志目录
from app.utils.path_helper import get_path_manager

# 日志目录（使用 path_helper 确保在项目根目录）
_path_manager = get_path_manager()
LOG_DIR = Path(_path_manager.logs_dir)
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 控制台输出（仅 WARNING 及以上，INFO 级别只写日志文件）
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(formatter)

# 文件输出
file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
file_handler.setFormatter(formatter)

# 获取日志器

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.propagate = False
    return logger
