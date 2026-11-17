"""UP 主可靠性分析的数据模型。

设计要点：标题是唯一判据。统计指标（品类分布、互动率）实测会对判断
产生误导 —— B站分区粒度太粗，多品类横评号往往同属一个分区，
"品类集中度" 算出来恒为 0，反而让模型误判为垂类深度号。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class VideoTitle:
    """一条视频的标题证据"""

    title: str
    order: str          # 该标题来自哪个排序: pubdate / view
    play: int = 0

    @property
    def tag(self) -> str:
        return "最近" if self.order == "pubdate" else "热门"


@dataclass
class CreatorProfile:
    """单个 UP 主的历史作品画像（纯采集，不含模型判断）"""

    mid: str
    name: str
    titles: List[VideoTitle] = field(default_factory=list)
    total_submissions: int = 0      # 空间页报告的历史投稿总数
    sample_size: int = 0            # 实际采集到的标题数

    @property
    def is_sufficient(self) -> bool:
        """标题太少时模型无从判断，低于门槛直接标记为证据不足"""
        return self.sample_size >= 8


@dataclass
class FetchFailure:
    """采集失败的 UP 主，单独记录以便上层如实汇报而非静默丢弃"""

    name: str
    mid: str
    reason: str


@dataclass
class CredibilityResult:
    """批量分析的结果"""

    profiles: List[CreatorProfile] = field(default_factory=list)
    failures: List[FetchFailure] = field(default_factory=list)
    analysis: str = ""              # 模型返回的原文
    from_cache: bool = False        # 是否命中缓存

    @property
    def report(self) -> str:
        """人类可读的结果摘要"""
        if self.from_cache:
            head = "（命中缓存，未重新调用模型）\n"
        else:
            head = ""
        lines = [head]
        if self.analysis:
            lines.append(self.analysis)
        if self.failures:
            lines.append("\n以下 UP 主采集失败，未纳入分析：")
            for f in self.failures:
                lines.append(f"  - {f.name} ({f.reason})")
        return "\n".join(lines).strip()