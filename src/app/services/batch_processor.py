"""批量处理器 - 统一管理批量笔记生成任务"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from app.utils.logger import get_logger
from app.utils.path_helper import get_path_manager

logger = get_logger(__name__)


class BatchResult:
    """单个任务的执行结果"""
    def __init__(self, task_id: str, success: bool, message: str = ""):
        self.task_id = task_id
        self.success = success
        self.message = message


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


class AsyncBatchProcessor:
    """
    异步批量处理器：主线程串行准备（下载/转写），AI 阶段提交线程池并行执行。
    无锁设计，依赖缓存机制避免多终端冲突；内置背压控制防止内存堆积。
    """

    def __init__(
        self,
        batch_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        max_ai_workers: int = 3,
    ):
        self.batch_name = batch_name
        self.custom_output_dir = output_dir
        self.max_ai_workers = max_ai_workers
        self.max_pending = max_ai_workers * 2
        self.batch_dir: Optional[Path] = None
        self.results: List[BatchResult] = []

        if output_dir:
            self.batch_dir = Path(output_dir)
            self.batch_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"使用自定义输出目录: {self.batch_dir}")
        else:
            self.batch_dir = self._create_batch_dir(batch_name)

    def _create_batch_dir(self, batch_name: Optional[str] = None) -> Path:
        """创建批次目录"""
        path_manager = get_path_manager()
        base_dir = Path(path_manager.output_notes_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if batch_name:
            slug = _slugify(batch_name)
            dir_name = f"search[{slug}]_{timestamp}"
        else:
            dir_name = f"batch_{timestamp}"

        batch_dir = base_dir / dir_name
        batch_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建批次目录: {batch_dir}")
        return batch_dir

    def get_output_path(self, task_id: str, ext: str = ".md") -> str:
        """获取指定 task_id 的输出路径"""
        return str(self.batch_dir / f"{task_id}{ext}")

    def process(
        self,
        items: List[Tuple[str, str, str, str]],
        prepare_func: Callable[[str, str, str, str], Any],
        ai_func: Callable[[Any], bool],
        model_name: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        批量异步处理任务

        :param items: 任务列表，每项为 (url, platform, task_id, title)
        :param prepare_func: 准备函数，接收 (url, platform, task_id, output_path)，返回 prepared_data 或 None
        :param ai_func: AI 处理函数，接收 prepared_data，返回是否成功
        :param model_name: 模型名称，用于头部展示
        :return: (成功数量, 失败数量)
        """
        total = len(items)
        success_count = 0
        fail_count = 0
        task_meta = {}  # task_id -> (1-based 序号, 标题)

        def report(ok: bool, tid: str, msg: str) -> None:
            """打印并记录单个任务结果，序号用任务在列表中的原始序号"""
            nonlocal success_count, fail_count
            idx, title = task_meta.get(tid, (0, tid))
            if ok:
                success_count += 1
                self.results.append(BatchResult(tid, True, msg))
                print(f"  ✓ 任务{idx} 完成: {title} - {tid}")
            else:
                fail_count += 1
                self.results.append(BatchResult(tid, False, msg))
                print(f"  ✗ 任务{idx} 失败: {tid} - {msg}")

        print(f"开始批量处理: {total} 个任务 (AI 并发: {self.max_ai_workers})")
        if model_name:
            print(f"使用模型: {model_name}")
        print()

        with ThreadPoolExecutor(max_workers=self.max_ai_workers) as executor:
            pending = set()

            for idx, (url, platform, task_id, title) in enumerate(items, 1):
                task_meta[task_id] = (idx, title or task_id)
                output_path = self.get_output_path(task_id)

                try:
                    prepared = prepare_func(url, platform, task_id, output_path)
                    if prepared is None:
                        report(False, task_id, "准备阶段失败")
                        continue

                    # 背压控制：待处理任务过多时，等待至少一个完成
                    while len(pending) >= self.max_pending:
                        done, pending = wait(pending, return_when=FIRST_COMPLETED)
                        for future in done:
                            ok, tid, msg = future.result()
                            report(ok, tid, msg)

                    future = executor.submit(
                        self._ai_worker, ai_func, prepared, task_id, output_path
                    )
                    pending.add(future)

                except Exception as e:
                    error_msg = str(e)
                    report(False, task_id, error_msg)
                    logger.error(f"批量处理任务失败 (task_id={task_id}): {e}", exc_info=True)

            # 等待剩余任务全部完成
            for future in pending:
                ok, tid, msg = future.result()
                report(ok, tid, msg)

        # 打印摘要
        print(f"\n{'=' * 60}")
        print("批量处理完成!")
        print(f"  成功: {success_count}")
        print(f"  失败: {fail_count}")
        print(f"  总计: {total}")
        print(f"输出目录: {self.batch_dir}")
        print(f"{'=' * 60}")

        return success_count, fail_count

    @staticmethod
    def _ai_worker(
        ai_func: Callable[[Any], bool],
        prepared: Any,
        task_id: str,
        output_path: str,
    ) -> Tuple[bool, str, str]:
        """AI 任务包装器，捕获异常并返回统一格式结果"""
        try:
            success = ai_func(prepared)
            if success:
                return True, task_id, f"保存至: {output_path}"
            return False, task_id, "AI 处理返回空结果"
        except Exception as e:
            logger.error(f"AI 处理失败 (task_id={task_id}): {e}", exc_info=True)
            return False, task_id, str(e)

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
