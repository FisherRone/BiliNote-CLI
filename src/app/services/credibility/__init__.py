"""UP 主可靠性分析。

用途：搜索工具拿到一批 UP 主后，判断其在特定领域上的评测可信度。
判断依据是历史作品标题 —— 实测统计指标（品类分布、互动率）会误导，
因为 B站分区粒度太粗，多品类横评号往往同属一个分区。

典型用法::

    from app.services.credibility import analyze_credibility

    result = analyze_credibility(
        creators=[("万物测评侦探社", "3546961447750141"), ("大米评测", "8372353")],
        topic="手机选购建议",
    )
    print(result.report)
"""

from app.services.credibility.analyzer import analyze_credibility
from app.services.credibility.models import (
    CreatorProfile,
    CredibilityResult,
    FetchFailure,
    VideoTitle,
)

__all__ = [
    "analyze_credibility",
    "CreatorProfile",
    "CredibilityResult",
    "FetchFailure",
    "VideoTitle",
]