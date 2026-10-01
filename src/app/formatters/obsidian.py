"""Obsidian 格式挂件：YAML frontmatter + 一级标题 + LLM 正文。

frontmatter 由代码从视频元数据确定性构建（不依赖 LLM 输出，跨平台
字段缺失时自动省略）；正文顶部统一为单个 `# 视频标题`，原有标题层级
（## 小节）保持不变。
"""

import re
from typing import Optional

import yaml

from app.formatters.video_meta import CanonicalVideoMeta, build_video_meta

_DESCRIPTION_LIMIT = 200


class ObsidianFormatter:
    """输出 Obsidian 笔记：frontmatter 属性 + 单个一级标题"""

    def decorate(self, markdown: Optional[str], prepared) -> Optional[str]:
        if markdown is None:
            return None

        meta = build_video_meta(prepared)
        parts = [_build_frontmatter(meta)]
        if meta.title:
            parts.append(f"# {meta.title}")
        body = _strip_leading_h1(markdown.strip())
        if body:
            parts.append(body)
        return "\n\n".join(parts) + "\n"


def _build_frontmatter(meta: CanonicalVideoMeta) -> str:
    """按示例笔记的字段序构建 frontmatter；空字段省略，保证合法 YAML"""
    fm: dict = {}
    if meta.title:
        fm["title"] = meta.title
    if meta.author:
        fm["author"] = meta.author
    if meta.description:
        fm["description"] = _flatten_description(meta.description)
    if meta.stats:
        fm["data"] = meta.stats
    if meta.tags:
        fm["tags"] = meta.tags
    if meta.source:
        fm["source"] = meta.source
    fm["platform"] = meta.platform
    fm["created"] = meta.created

    dumped = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{dumped.strip()}\n---"


def _flatten_description(text: str) -> str:
    """简介拍平为单行并截断，避免 YAML 多行字符串与 Obsidian 属性面板换行问题"""
    text = re.sub(r"\s*\n\s*", " ", text).strip()
    if len(text) > _DESCRIPTION_LIMIT:
        text = text[:_DESCRIPTION_LIMIT] + "..."
    return text


def _strip_leading_h1(body: str) -> str:
    """去掉正文开头 LLM 自带的一级标题，统一由挂件补 `# 视频标题`；
    正文以 ## 及更低层级开头时原样保留。"""
    lines = body.splitlines()
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx < len(lines) and re.match(r"^#\s+\S", lines[idx].strip()):
        return "\n".join(lines[idx + 1:]).strip()
    return body
