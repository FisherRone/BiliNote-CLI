import os
from app.utils.logger import get_logger
from app.utils.path_helper import get_path_manager

logger = get_logger(__name__)


def cleanup_temp_files(file_path: str) -> None:
    """
    清理转写完成后的临时文件
    只删除 downloads/ 目录中的临时音视频文件
    不会影响 cache/ 和 output/ 目录中的缓存文件
    
    :param file_path: 临时文件的完整路径
    """
    logger.info(f"开始清理临时文件：{file_path}")
    
    if not os.path.exists(file_path):
        logger.warning(f"路径不存在：{file_path}")
        return

    # 只清理 downloads 目录中的文件
    path_manager = get_path_manager()
    downloads_dir = path_manager.downloads_dir
    
    # 确保文件在 downloads 目录中
    if not file_path.startswith(downloads_dir):
        logger.warning(f"文件不在 downloads 目录中，跳过清理：{file_path}")
        return

    # 删除指定的临时文件
    try:
        os.remove(file_path)
        logger.info(f"删除临时文件：{file_path}")
    except Exception as e:
        logger.error(f"删除失败：{file_path}，原因：{e}")
