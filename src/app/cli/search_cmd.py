"""search 子命令：搜索视频并保存结果 JSON"""

import json
import os
import re
from datetime import datetime

from .console import format_count, format_duration, print_separator

# 简介仅用于终端展示的截断上限；保存的 JSON 保留全文
_DESC_DISPLAY_LIMIT = 500


def _format_pubdate(pubdate) -> str | None:
    """unix 时间戳 -> YYYY-MM-DD；缺失或非法返回 None"""
    if pubdate is None:
        return None
    try:
        return datetime.fromtimestamp(int(pubdate)).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def _format_description(text) -> str | None:
    """简介压成单行并按展示上限截断"""
    if not text:
        return None
    line = re.sub(r"\s+", " ", str(text)).strip()
    if not line:
        return None
    if len(line) > _DESC_DISPLAY_LIMIT:
        return line[:_DESC_DISPLAY_LIMIT] + "…"
    return line


def _format_tags(tags) -> list:
    if isinstance(tags, str):
        tags = tags.split(",")
    if not tags:
        return []
    return [str(t).strip() for t in tags if str(t).strip()]


def _print_result(index: int, item: dict) -> None:
    """打印单条搜索结果：

    <index>. 作者 - 标题
    发布时间：yyyy-mm-dd  播放量：x  点赞量：x  收藏量：x  时长：x
    简介：...
    标签：a、b、c

    字段缺失则跳过对应片段（YouTube flat 模式下常见）。
    """
    author = (item.get("author") or "").strip()
    title = (item.get("title") or "").strip() or "未知标题"
    label = f"{author} - {title}" if author else title
    print(f"{index}. {label}")

    stats = []
    pubdate = _format_pubdate(item.get("pubdate"))
    if pubdate:
        stats.append(f"发布时间：{pubdate}")
    if item.get("play_count") is not None:
        stats.append(f"播放量：{format_count(item['play_count'])}")
    if item.get("like_count") is not None:
        stats.append(f"点赞量：{format_count(item['like_count'])}")
    if item.get("favorite_count") is not None:
        stats.append(f"收藏量：{format_count(item['favorite_count'])}")
    if item.get("duration") is not None:
        stats.append(f"时长：{format_duration(item['duration'])}")
    if stats:
        print("  ".join(stats))

    description = _format_description(item.get("description"))
    if description:
        print(f"简介：{description}")

    tags = _format_tags(item.get("tags"))
    if tags:
        print("标签：" + "、".join(tags))


def search_videos_cli(args):
    """搜索视频并保存结果为 JSON"""
    from app.services.searcher import search as searcher

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
        _print_result(i, item)

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
