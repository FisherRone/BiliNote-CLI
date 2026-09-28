"""search 子命令：搜索视频并保存结果 JSON"""

import json
import os
import re

from .console import print_separator


def _format_count(n):
    """格式化数量，使用中文单位（无、k、w），最多3位有效数字"""
    if n is None:
        return None
    if n >= 10000:
        return f"{n / 10000:.3g}w"
    if n >= 1000:
        return f"{n / 1000:.3g}k"
    return str(n)


def _format_duration(seconds):
    """格式化视频时长，如 "1h30min", "7min", "45s"""
    if seconds is None:
        return None
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return None

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        if minutes > 0:
            return f"{hours}h{minutes}min"
        return f"{hours}h"
    elif minutes > 0:
        return f"{minutes}min"
    else:
        return f"{secs}s"


def search_videos_cli(args):
    """搜索视频并保存结果为 JSON"""
    from app.services.searcher import search as searcher
    from datetime import datetime

    platform = args.platform or "bilibili"
    keyword = args.keyword

    print(f"搜索: {keyword}  平台: {platform}")
    print_separator("-")

    items = searcher(keyword, platform=platform, limit=args.limit)
    if not items:
        print("未找到相关视频")
        return

    print(f"搜索到 {len(items)} 条结果：\n")
    for i, item in enumerate(items, 1):
        parts = [f"{i}. {item['title']}"]
        stats = []
        if item.get('play_count') is not None:
            stats.append(f"播放量：{_format_count(item['play_count'])}")
        if item.get('like_count') is not None:
            stats.append(f"点赞量：{_format_count(item['like_count'])}")
        if item.get('favorite_count') is not None:
            stats.append(f"收藏量：{_format_count(item['favorite_count'])}")
        if item.get('duration') is not None:
            stats.append(f"时长：{_format_duration(item['duration'])}")
        if stats:
            parts.append("  ".join(stats))
        print("  ".join(parts))

    search_result = {
        "meta": {
            "keyword": keyword,
            "platform": platform,
            "searched_at": datetime.now().isoformat(timespec="seconds"),
        },
        "results": [
            {"index": i + 1, **item}
            for i, item in enumerate(items)
        ],
    }

    output_dir = args.output_dir or os.path.join(
        os.path.expanduser("~"), ".bilinote", "output", "search_result"
    )
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    safe_keyword = re.sub(r'[^\w\s\u4e00-\u9fff]', '', keyword).strip().replace(' ', '_')[:30]
    filename = f"{timestamp}_{safe_keyword}.json"
    json_path = os.path.join(output_dir, filename)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(search_result, f, ensure_ascii=False, indent=2)

    print(f"\n搜索结果已保存至: {json_path}")
    print(f"\n使用 process 命令处理搜索结果：")
    print(f"  bilinote process --json \"{json_path}\"")
    print(f"  bilinote process --json \"{json_path}\" --index 1 2 3")
