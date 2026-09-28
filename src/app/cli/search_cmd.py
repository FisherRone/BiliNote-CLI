"""search 子命令：搜索视频并保存结果 JSON"""

import json
import os
import re

from .console import format_count, format_duration, print_separator


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
            stats.append(f"播放量：{format_count(item['play_count'])}")
        if item.get('like_count') is not None:
            stats.append(f"点赞量：{format_count(item['like_count'])}")
        if item.get('favorite_count') is not None:
            stats.append(f"收藏量：{format_count(item['favorite_count'])}")
        if item.get('duration') is not None:
            stats.append(f"时长：{format_duration(item['duration'])}")
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
    print("\n使用 process 命令处理搜索结果：")
    print(f"  bilinote process --json \"{json_path}\"")
    print(f"  bilinote process --json \"{json_path}\" --index 1 2 3")
