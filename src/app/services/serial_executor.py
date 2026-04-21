import threading
from typing import Callable


class SerialTaskExecutor:
    """串行任务执行器，确保所有提交的任务严格按顺序逐个执行。"""

    def __init__(self):
        self._lock = threading.Lock()

    def run(self, func: Callable):
        """提交一个任务并阻塞等待其执行完成。

        :param func: 无参数的可调用对象
        """
        with self._lock:
            return func()
