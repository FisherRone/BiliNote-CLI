"""笔记输出格式化挂件。

在 AIProcessor 落盘前对 LLM 生成的正文做最后一层包装：
- markdown：默认格式，保留原有的来源链接 + 视频信息卡（引用块）
- obsidian：YAML frontmatter + 一级标题，可直接放进 Obsidian 库

挂件不参与提示词组装，LLM 正文与 --style/--format/--extras 完全解耦；
frontmatter 等结构化内容由代码从视频元数据确定性构建。
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.formatters.markdown import MarkdownFormatter
from app.formatters.obsidian import ObsidianFormatter
from app.models.pipeline_model import PreparedTask
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NoteFormatter(ABC):
    """笔记格式化挂件接口：对 LLM 正文做落盘前的包装"""

    @abstractmethod
    def decorate(self, markdown: Optional[str], prepared: PreparedTask) -> Optional[str]:
        """包装正文；返回 None 时透传（与输入约定一致）"""


_FORMATTERS = {
    "markdown": MarkdownFormatter(),
    "obsidian": ObsidianFormatter(),
}


def get_formatter(note_format: Optional[str]) -> NoteFormatter:
    """按名称获取格式化挂件；未知名称回退到默认 markdown 并告警"""
    fmt = (note_format or "markdown").strip().lower()
    formatter = _FORMATTERS.get(fmt)
    if formatter is None:
        logger.warning(f"未知笔记格式 '{note_format}'，回退到 markdown")
        return _FORMATTERS["markdown"]
    return formatter
