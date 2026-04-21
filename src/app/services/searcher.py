"""视频搜索模块

Bilibili: bilibili_api (search.search_by_type)
YouTube: yt-dlp (ytsearch)
"""

import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


def search(keyword: str, platform: str = "bilibili", limit: int = 20) -> List[Dict]:
    """搜索视频

    :param keyword: 搜索关键词
    :param platform: 平台 (bilibili, youtube)
    :param limit: 结果数量上限
    :return: 列表，每项为 {title, link, play_count, like_count, favorite_count, duration, author}
    """
    if platform == "bilibili":
        return _search_bilibili(keyword, limit)
    elif platform == "youtube":
        return _search_youtube(keyword, limit)
    else:
        logger.error("搜索不支持平台: %s", platform)
        return []


def _strip_html(text: str) -> str:
    """移除 B站搜索结果中的 HTML 高亮标签"""
    return re.sub(r'<[^>]+>', '', text)


def _parse_bilibili_duration(duration_str: str) -> int:
    """解析 B站时长字符串为秒数，如 "5:14" -> 314, "1:30:45" -> 5445"""
    if not duration_str:
        return 0
    parts = duration_str.split(":")
    try:
        if len(parts) == 2:
            # MM:SS 格式
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            # HH:MM:SS 格式
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return 0


def _search_bilibili(keyword: str, limit: int = 20) -> List[Dict]:
    """使用 bilibili_api 搜索 B站视频"""
    from bilibili_api import search, sync

    page_size = min(limit, 50)
    pages = (limit + page_size - 1) // page_size
    results = []

    for page in range(1, pages + 1):
        try:
            data = sync(search.search_by_type(
                keyword,
                search_type=search.SearchObjectType.VIDEO,
                order_type=search.OrderVideo.SCORES,
                page=page,
                page_size=page_size,
            ))
        except Exception as e:
            logger.error("B站搜索失败 (page=%d): %s", page, e)
            break

        for v in data.get("result", []):
            results.append({
                "title": _strip_html(v.get("title", "未知标题")),
                "link": f"https://www.bilibili.com/video/{v['bvid']}",
                "play_count": v.get("play"),
                "like_count": v.get("like"),
                "favorite_count": v.get("favorites"),
                "duration": _parse_bilibili_duration(v.get("duration", "")),
                "author": v.get("author"),
            })
            if len(results) >= limit:
                return results

    return results


def _search_youtube(keyword: str, limit: int = 20) -> List[Dict]:
    """使用 yt-dlp 搜索 YouTube 视频"""
    import yt_dlp

    search_url = f"ytsearch{limit}:{keyword}"
    ydl_opts = {"quiet": True, "no_warnings": True}
    results = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_url, download=False)
        for entry in info.get("entries") or []:
            if not entry:
                continue
            results.append({
                "title": entry.get("title", "未知标题"),
                "link": entry.get("webpage_url") or entry.get("url", ""),
                "play_count": entry.get("view_count"),
                "like_count": entry.get("like_count"),
                "favorite_count": entry.get("bookmark_count") or entry.get("favorite_count"),
                "duration": entry.get("duration"),
                "author": entry.get("uploader") or entry.get("channel"),
            })

    return results
