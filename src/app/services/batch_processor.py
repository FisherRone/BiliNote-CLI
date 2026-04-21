"""批量处理器 - 统一管理批量笔记生成任务"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from app.utils.path_helper import get_path_manager

logger = logging.getLogger(__name__)


class BatchResult:
    """单个任务的执行结果"""
    def __init__(self, task_id: str, success: bool, message: str = ""):
        self.task_id = task_id
        self.success = success
        self.message = message


class BatchProcessor:
    """
    批量处理器：生成批次目录、串行执行、统一错误处理、进度报告
    
    目录命名规则:
    - process 批量: batch_20250420_143052/
    - search 批量: search[关键词]_20250420_143100/
    """
    
    def __init__(self, batch_name: Optional[str] = None, output_dir: Optional[str] = None):
        """
        初始化批量处理器
        
        :param batch_name: 批次名称（如关键词），用于生成目录名
        :param output_dir: 自定义输出目录（可选），优先级高于自动生成的批次目录
        """
        self.batch_name = batch_name
        self.custom_output_dir = output_dir
        self.batch_dir: Optional[Path] = None
        self.results: List[BatchResult] = []
        
        if output_dir:
            # 使用自定义输出目录
            self.batch_dir = Path(output_dir)
            self.batch_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"使用自定义输出目录: {self.batch_dir}")
        else:
            # 自动生成批次目录
            self.batch_dir = self._create_batch_dir(batch_name)
            
    def _create_batch_dir(self, batch_name: Optional[str] = None) -> Path:
        """创建批次目录"""
        path_manager = get_path_manager()
        base_dir = Path(path_manager.output_notes_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if batch_name:
            # 对 batch_name 进行 slug 化处理
            slug = self._slugify(batch_name)
            dir_name = f"search[{slug}]_{timestamp}"
        else:
            dir_name = f"batch_{timestamp}"
            
        batch_dir = base_dir / dir_name
        batch_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建批次目录: {batch_dir}")
        return batch_dir
    
    @staticmethod
    def _slugify(text: str) -> str:
        """
        将文本转换为安全的目录名
        - 移除特殊字符
        - 限制长度
        - 中文保留
        """
        # 替换常见分隔符为空格
        text = text.replace("-", " ").replace("_", " ")
        # 移除危险字符，但保留中文、字母、数字、空格
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', "", text)
        # 合并多个空格
        text = re.sub(r'\s+', " ", text)
        # 去除首尾空格
        text = text.strip()
        # 限制长度（保留前 30 个字符）
        if len(text) > 30:
            text = text[:30]
        return text or "untitled"
    
    def get_output_path(self, task_id: str, ext: str = ".md") -> str:
        """获取指定 task_id 的输出路径"""
        return str(self.batch_dir / f"{task_id}{ext}")
    
    def process(
        self,
        items: List[Tuple[str, str, str]],
        process_func: Callable[[str, str, str, str], bool],
    ) -> Tuple[int, int]:
        """
        批量处理任务
        
        :param items: 任务列表，每项为 (url, platform, task_id, title)
        :param process_func: 处理函数，接收 (url, platform, task_id, output_path)，返回是否成功
        :return: (成功数量, 失败数量)
        """
        total = len(items)
        success_count = 0
        fail_count = 0
        
        print(f"\n{'=' * 60}")
        print(f"开始批量处理: {total} 个任务")
        print(f"输出目录: {self.batch_dir}")
        print(f"{'=' * 60}\n")
        
        for idx, (url, platform, task_id, title) in enumerate(items, 1):
            print(f"[{idx}/{total}] {title or task_id}")
            print("-" * 40)
            
            output_path = self.get_output_path(task_id)
            
            try:
                success = process_func(url, platform, task_id, output_path)
                if success:
                    success_count += 1
                    self.results.append(BatchResult(task_id, True, f"保存至: {output_path}"))
                    print(f"  ✓ 成功")
                else:
                    fail_count += 1
                    self.results.append(BatchResult(task_id, False, "处理失败"))
                    print(f"  ✗ 失败")
            except Exception as e:
                fail_count += 1
                error_msg = str(e)
                self.results.append(BatchResult(task_id, False, error_msg))
                print(f"  ✗ 错误: {error_msg}")
                logger.error(f"批量处理任务失败 (task_id={task_id}): {e}", exc_info=True)
            
            print()
        
        # 打印摘要
        print(f"{'=' * 60}")
        print(f"批量处理完成!")
        print(f"  成功: {success_count}")
        print(f"  失败: {fail_count}")
        print(f"  总计: {total}")
        print(f"输出目录: {self.batch_dir}")
        print(f"{'=' * 60}")
        
        return success_count, fail_count
    
    def get_summary(self) -> dict:
        """获取处理摘要"""
        success = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success)
        return {
            "total": len(self.results),
            "success": success,
            "failed": failed,
            "batch_dir": str(self.batch_dir),
            "results": [
                {"task_id": r.task_id, "success": r.success, "message": r.message}
                for r in self.results
            ]
        }
