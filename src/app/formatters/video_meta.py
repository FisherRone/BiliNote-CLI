"""跨平台视频元数据归一化。

各下载器把平台元数据塞进 AudioDownloadResult.raw_info（自由 dict），
字段名与完整度参差：B 站是 yt-dlp 全量信息，抖音/快手只有 caption
和拼接的标签字符串。这里统一收敛为 CanonicalVideoMeta，供输出格式
挂件（obsidian frontmatter、文件命名）消费；字段缺失时优雅降级，
不假设 B 站字段必然存在。
"""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import List

# 与 note_helper.prepend_video_meta 保持一致的数据展示口径
_STAT_LABELS = (
    ("view_count", "播放"),
    ("like_count", "点赞"),
    ("coin_count", "投币"),
    ("favorite_count", "收藏"),
    ("share_count", "分享"),
    ("comment_count", "评论"),
)


@dataclass
class CanonicalVideoMeta:
    """归一化后的视频元数据（字段缺失时为空值，由消费方决定是否展示）"""

    title: str = ""
    author: str = ""
    description: str = ""
    stats: str = ""                      # 形如 "7520 播放 · 245 点赞"
    tags: List[str] = field(default_factory=list)
    source: str = ""                     # 来源链接；本地文件为路径
    platform: str = ""
    created: str = ""                    # 笔记生成日期 YYYY-MM-DD


def build_video_meta(prepared) -> CanonicalVideoMeta:
    """从 PreparedTask 构建归一化元数据，任何平台都不会抛异常"""
    audio_meta = prepared.audio_meta
    raw = audio_meta.raw_info or {}
    return CanonicalVideoMeta(
        title=_clean(audio_meta.title) or _clean(raw.get("title")),
        author=_clean(raw.get("uploader")) or _clean(raw.get("author")),
        description=_clean(raw.get("description")) or _clean(raw.get("caption")),
        stats=_build_stats(raw),
        tags=_normalize_tags(raw.get("tags")),
        source=(prepared.video_url or "").strip(),
        platform=prepared.platform or _clean(audio_meta.platform),
        created=date.today().isoformat(),
    )


def _clean(value) -> str:
    return str(value).strip() if value else ""


def _build_stats(raw: dict) -> str:
    from app.utils.bilibili_meta import format_number

    parts = []
    for key, label in _STAT_LABELS:
        value = raw.get(key)
        if value is not None:
            parts.append(f"{format_number(value)} {label}")
    return " · ".join(parts)


def _normalize_tags(raw) -> List[str]:
    """兼容三种形态：list[str]（yt-dlp）、list[dict]（B 站部分版本）、
    拼接字符串（抖音 caption+标签、快手逗号串）。
    tag 内部的空白字符（含空格、全角空格）全部去除——Obsidian 标签
    不允许空格；清理后只剩数字或为空的 tag 直接剔除。去重保序。"""
    if not raw:
        return []
    if isinstance(raw, str):
        candidates = _split_tag_string(raw)
    else:
        candidates = [
            str(item.get("tag") or item.get("title") or "") if isinstance(item, dict) else str(item)
            for item in raw
        ]

    seen, tags = set(), []
    for name in candidates:
        name = re.sub(r"\s+", "", name).lstrip("#")
        if not name or name.isdigit() or name in seen:
            continue
        seen.add(name)
        tags.append(name)
    return tags


def _split_tag_string(text: str) -> List[str]:
    # 抖音把 caption 和标签名直接拼成一串：优先提取 "#话题" 形式，
    # 提取不到再按常见分隔符切分
    if "#" in text:
        found = re.findall(r"#([^\s#,，、]+)", text)
        if found:
            return found
    return re.split(r"[,，、\s]+", text)
