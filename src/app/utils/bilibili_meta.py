"""Bilibili 视频元信息与评论获取工具

提供从 yt_dlp raw_info 提取视频元数据、以及通过 bilibili_api 获取热门评论的功能。
"""

from dataclasses import dataclass
from typing import List

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BilibiliComment:
    uname: str
    level: int
    message: str
    like_count: int


def fetch_top_comments(video_id: str, n: int = 10) -> List[BilibiliComment]:
    """获取 B 站视频按点赞排序的前 n 条评论。

    :param video_id: BV 号，如 "BV1GJ411x7h7"
    :param n: 返回评论数量上限
    :return: 评论列表；获取失败时返回空列表
    """
    try:
        from bilibili_api import comment, sync
        from bilibili_api.video import bvid2aid

        aid = bvid2aid(video_id)
        data = sync(comment.get_comments(
            aid,
            comment.CommentResourceType.VIDEO,
            order=comment.OrderType.LIKE,
            page_index=1,
        ))

        replies = data.get("replies") or []
        results = []
        for c in replies[:n]:
            member = c.get("member", {})
            content = c.get("content", {})
            results.append(BilibiliComment(
                uname=member.get("uname", "未知用户"),
                level=member.get("level_info", {}).get("current_level", 0),
                message=content.get("message", ""),
                like_count=c.get("like", 0),
            ))
        return results
    except Exception as e:
        logger.warning(f"获取 B 站评论失败 (video_id={video_id}): {e}")
        return []


def format_number(n) -> str:
    """将整数格式化为人类可读形式，如 12345 -> '1.2万'"""
    if n is None:
        return "0"
    try:
        n = int(n)
    except (ValueError, TypeError):
        return str(n)
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


def sanitize_filename(name: str) -> str:
    """替换文件名中的非法字符，使其可安全用作文件名"""
    import re
    name = re.sub(r'[/\\:*?"<>|]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name
