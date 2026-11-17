"""把采集到的标题拼装成给模型看的证据块。

这一步完全是本地字符串处理，不发请求、不消耗 token。
拼装目标是「模型一眼能看出模式」：按 UP 主分组、按时间标注来源、
保留标题原文不做删减 —— 品类漂移和模板化用词只有看原文才抓得住。
"""

from typing import Dict, List

from app.services.credibility.models import CreatorProfile

# 证据条数上限：实测 30 条足够看出品类与标题模式，再多收益递减且徒增 token
MAX_TITLES_PER_CREATOR = 30

# 每类排序（最近发布 / 播放最多）各取一半
_PER_ORDER_LIMIT = MAX_TITLES_PER_CREATOR // 2


def _pick_count(profile: CreatorProfile) -> int:
    """实际会写进证据块的标题条数"""
    return sum(
        min(len([t for t in profile.titles if t.order == order]), _PER_ORDER_LIMIT)
        for order in ("pubdate", "view")
    )


def build_evidence(profiles: List[CreatorProfile]) -> str:
    """把所有 UP 主的标题拼成一份证据块。

    一次性拼完交给模型单次调用 —— 既省 token 又省往返，
    而且模型能在多个 UP 主之间横向对比，
    这是逐个分析做不到的。
    """
    blocks = []

    for idx, p in enumerate(profiles, 1):
        lines = [f"### UP主 {idx}：{p.name}"]

        # 采集到多少 ≠ 送进证据多少，如实说明避免模型误判证据量
        used = _pick_count(p)
        if p.total_submissions:
            lines.append(f"历史投稿总数：{p.total_submissions}")
        lines.append(f"已提供标题样本：{used} 条")
        if used < p.sample_size:
            lines.append(f"（另有 {p.sample_size - used} 条同类标题未列出）")
        if not p.is_sufficient:
            lines.append(
                f"⚠️ 仅采集到 {p.sample_size} 条标题，证据不足，"
                f"请在结论中标注为「无法判断」而非猜测"
            )

        lines.append("")
        # 最近发布在前，反映当前方向；热门在后，反映代表作
        for order, label in (("pubdate", "最近发布"), ("view", "播放最多")):
            picked = [t for t in p.titles if t.order == order][:_PER_ORDER_LIMIT]
            if not picked:
                continue
            lines.append(f"【{label}】")
            for t in picked:
                lines.append(f"- {t.title}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def build_report_context(profiles: List[CreatorProfile]) -> str:
    """给上层展示用的极简上下文，不含标题全文"""
    rows = []
    for p in profiles:
        rows.append(
            f"- {p.name} (mid={p.mid})：采集 {p.sample_size} 条标题"
            + (f"，历史投稿 {p.total_submissions} 部" if p.total_submissions else "")
        )
    return "\n".join(rows)