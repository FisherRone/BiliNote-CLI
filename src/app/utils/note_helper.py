import re


def prepend_source_link(markdown: str | None, source_url: str) -> str | None:
    """
    在笔记开头添加来源链接；若首个非空行已包含来源链接，则更新该行并避免重复。
    """
    if markdown is None:
        return None

    source = (source_url or "").strip()
    if not source:
        return markdown

    header = f"> 来源链接：{source}"
    lines = markdown.splitlines()
    first_non_empty_idx = None
    for idx, line in enumerate(lines):
        if line.strip():
            first_non_empty_idx = idx
            break

    if first_non_empty_idx is not None:
        first_line = lines[first_non_empty_idx].strip()
        if first_line.startswith("> 来源链接：") or first_line.startswith("来源链接："):
            lines[first_non_empty_idx] = header
            return "\n".join(lines)

    if markdown.strip():
        return f"{header}\n\n{markdown}"
    return header


def replace_content_markers(markdown: str, video_id: str, platform: str = 'bilibili') -> str:
    """
    替换 *Content-04:16*、Content-04:16 或 Content-[04:16] 为超链接，跳转到对应平台视频的时间位置
    """
    # 匹配三种形式：*Content-04:16*、Content-04:16、Content-[04:16]
    pattern = r"(?:\*?)Content-(?:\[(\d{2}):(\d{2})\]|(\d{2}):(\d{2}))"

    safe_video_id = video_id

    def replacer(match):
        mm = match.group(1) or match.group(3)
        ss = match.group(2) or match.group(4)
        total_seconds = int(mm) * 60 + int(ss)

        if platform == 'bilibili':
            video_id = video_id.replace("_p", "?p=")
            url = f"https://www.bilibili.com/video/{video_id}&t={total_seconds}"
            parsed_video_id = safe_video_id.replace("_p", "?p=")
            url = f"https://www.bilibili.com/video/{parsed_video_id}&t={total_seconds}"
        elif platform == 'youtube':
            url = f"https://www.youtube.com/watch?v={video_id}&t={total_seconds}s"
            url = f"https://www.youtube.com/watch?v={safe_video_id}&t={total_seconds}s"
        elif platform == 'douyin':
            url = f"https://www.douyin.com/video/{video_id}"
            url = f"https://www.douyin.com/video/{safe_video_id}"
            return f"[原片 @ {mm}:{ss}]({url})"
        else:
            return f"({mm}:{ss})"

        return f"[原片 @ {mm}:{ss}]({url})"

    return re.sub(pattern, replacer, markdown)


def prepend_video_meta(markdown: str | None, raw_info: dict) -> str | None:
    """在笔记开头插入视频信息卡片（UP主、标题、简介、数据、标签）"""
    if markdown is None or not raw_info:
        return markdown

    title = raw_info.get("title", "")
    uploader = raw_info.get("uploader", "")
    description = raw_info.get("description", "")
    view_count = raw_info.get("view_count")
    like_count = raw_info.get("like_count")
    coin_count = raw_info.get("coin_count")
    favorite_count = raw_info.get("favorite_count")
    share_count = raw_info.get("share_count")
    tags = raw_info.get("tags") or []

    if description and len(description) > 200:
        description = description[:200] + "..."

    from app.utils.bilibili_meta import format_number

    stats_parts = []
    if view_count is not None:
        stats_parts.append(f"{format_number(view_count)} 播放")
    if like_count is not None:
        stats_parts.append(f"{format_number(like_count)} 点赞")
    if coin_count is not None:
        stats_parts.append(f"{format_number(coin_count)} 投币")
    if favorite_count is not None:
        stats_parts.append(f"{format_number(favorite_count)} 收藏")
    stats_str = " · ".join(stats_parts) if stats_parts else ""

    tag_names = []
    for t in tags:
        if isinstance(t, dict):
            name = t.get("tag") or t.get("title", "")
            if name:
                tag_names.append(name)
        elif isinstance(t, str):
            tag_names.append(t)
    tags_str = "、".join(tag_names) if tag_names else ""

    lines = []
    if uploader:
        lines.append(f"> **UP主**：{uploader}")
    if title:
        lines.append(f"> **标题**：{title}")
    if description:
        lines.append(f"> **简介**：{description}")
    if stats_str:
        lines.append(f"> **数据**：{stats_str}")
    if tags_str:
        lines.append(f"> **标签**：{tags_str}")

    if not lines:
        return markdown

    meta_block = "\n".join(lines) + "\n\n---\n\n"
    return meta_block + markdown


def append_top_comments(markdown: str | None, comments: list) -> str | None:
    """在笔记末尾追加热门评论区（引用块格式）"""
    if markdown is None or not comments:
        return markdown

    blocks = []
    for c in comments:
        message = c.message
        if len(message) > 80:
            message = message[:80] + "..."
        # 将评论内部的换行符替换为 "\n>"，确保每行都有引用前缀
        message = message.replace("\n", "\n>")
        block = f">{c.uname}（LV{c.level}）：\n>{message}\n>👍 {c.like_count}"
        blocks.append(block)

    comments_section = "\n\n## 评论\n\n" + "\n\n".join(blocks)
    return markdown + comments_section


