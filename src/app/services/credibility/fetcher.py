"""UP 主历史作品标题采集。

风控要点（均为实测结论，见 dev-docs 或记忆）：
- 决定性变量是 cookie 有无，不是并发数。无 cookie 时降到单线程仍有
  约 5/8 被 412 拦截，因此取不到 cookie 直接放弃，不做无谓重试。
- User.get_videos 内部会先请求 space.bilibili.com/{mid}/dynamic 拿
  w_webid，实际请求数是理论值的 2 倍，w_webid 也不复用。
- B站存在偶发慢响应（实测单次可达 17 秒），不要当成风控降级。
"""

import hashlib
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.utils.logger import get_logger
from app.utils.path_helper import get_path_manager

logger = get_logger(__name__)

# 采集两种排序：最近发布看当前方向，播放最多看代表作
_ORDERS = ("pubdate", "view")

_TAG_RE = re.compile(r"<[^>]+>")


class CookieMissingError(RuntimeError):
    """拿不到 B站 cookie —— 无 cookie 请求会被 412 拦截，不值得重试"""


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _cache_dir() -> Path:
    path = Path(get_path_manager().cache_dir) / "credibility"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path(mid: str) -> Path:
    return _cache_dir() / f"{mid}.json"


def _load_cache(mid: str, ttl_days: int) -> Optional[List]:
    path = _cache_path(mid)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if (time.time() - data.get("fetched_at", 0)) > ttl_days * 86400:
        return None
    return data.get("titles")


def _save_cache(mid: str, name: str, titles: List, total: int) -> None:
    path = _cache_path(mid)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps(
                {"mid": mid, "name": name, "total": total,
                 "fetched_at": time.time(), "titles": titles},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        tmp.replace(path)
    except Exception as e:
        logger.warning(f"写入标题缓存失败 (mid={mid}): {e}")
        tmp.unlink(missing_ok=True)


def _fetch_one_order(cred, mid: str, order: str, retries: int = 3) -> Tuple[str, List, int]:
    """取单个排序下的标题，412 时指数退避重试。返回 (状态, 标题列表, 投稿总数)。"""
    from bilibili_api import sync, user

    order_enum = {
        "pubdate": user.VideoOrder.PUBDATE,
        "view": user.VideoOrder.VIEW,
    }[order]

    last_err = ""
    for attempt in range(retries):
        try:
            data = sync(user.User(mid, credential=cred).get_videos(
                pn=1, ps=30, order=order_enum))
            items = []
            for v in data.get("list", {}).get("vlist", []):
                title = _strip_tags(v.get("title", ""))
                if title:
                    items.append({
                        "title": title,
                        "order": order,
                        "play": v.get("play", 0),
                    })
            # page.count 顺带给出历史投稿总数，避免额外再发一次请求
            return "ok", items, data.get("page", {}).get("count", 0)
        except Exception as e:
            msg = str(e)
            last_err = msg
            # 412 是风控，退避重试有意义；-352/-799 同理
            if any(code in msg for code in ("412", "-352", "-799")) and attempt < retries - 1:
                delay = 2 ** attempt + random.uniform(0, 0.5)
                logger.warning(f"触发风控，{delay:.1f}s 后重试 (mid={mid}, order={order})")
                time.sleep(delay)
                continue
            break
    return "fail", last_err[:200], 0


def fetch_titles(
    name: str,
    mid: str,
    ttl_days: int = 7,
    max_workers: int = 8,
) -> Tuple[List, int, Optional[str]]:
    """采集单个 UP 主的历史作品标题。

    :param name: UP 主名（仅用于日志和缓存可读性）
    :param mid: UP 主 mid
    :param ttl_days: 缓存有效期，过期则重新采集
    :param max_workers: 并发上限；实测 8~16 均稳定，8 更保守
    :return: (标题列表, 历史投稿总数, 失败原因)
             成功时失败原因为 None
    """
    mid = str(mid).strip()
    if not mid.isdigit():
        return [], 0, f"mid 非法: {mid!r}"

    cached = _load_cache(mid, ttl_days)
    if cached is not None:
        logger.info(f"命中标题缓存: {name} ({len(cached)} 条)")
        try:
            data = json.loads(_cache_path(mid).read_text(encoding="utf-8"))
            return cached, data.get("total", 0), None
        except Exception:
            pass

    from app.utils.cookie_helper import get_cookie
    cookie = get_cookie("bilibili")
    if not cookie:
        # 实测：无 cookie 时 412 是随机的，降速无用，快速失败
        raise CookieMissingError(
            "未配置 BILIBILI_COOKIE。匿名请求会被 B站风控随机拦截（实测单线程仍只有 3/8 成功），"
            "请先执行: bilinote config set BILIBILI_COOKIE \"<你的 cookie>\""
        )

    from bilibili_api import user as user_mod
    cred = user_mod.Credential(cookie)

    # 两种排序拆成独立任务并发，避免单个 UP 内的串行等待
    jobs = [(o, m) for o in _ORDERS for m in (mid,)]
    results: Dict[str, List] = {}
    total = 0
    failures = []

    def work(job):
        order, m = job
        return m, order, _fetch_one_order(cred, m, order)

    page_meta: Dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(jobs))) as ex:
        for m, order, (status, payload, count) in ex.map(work, jobs):
            if status == "ok":
                results[order] = payload
                page_meta["total"] = max(page_meta.get("total", 0), count)
            else:
                failures.append(f"{order}={payload}")

    if not results:
        return [], 0, "; ".join(failures) or "未知失败"

    # 去重：同一条视频可能同时出现在两个排序里
    seen, merged = set(), []
    for order in _ORDERS:
        for item in results.get(order, []):
            if item["title"] in seen:
                continue
            seen.add(item["title"])
            merged.append(item)

    total = page_meta.get("total", 0)
    _save_cache(mid, name, merged, total)
    logger.info(f"采集完成: {name} — {len(merged)} 条标题 (历史投稿 {total})")
    return merged, total, None