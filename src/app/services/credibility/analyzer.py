"""批量分析入口：采集 → 拼装 → 单次 LLM 调用 → 缓存结果。

为什么单次调用而不是逐个：实测 8 个 UP 主的标题合成一份约 1 万 token，
逐个调用会让往返次数和总 token 都翻 8 倍；更重要的是模型能在多个
UP 主之间横向对比（识别出「这几个都是软广号」），孤立分析做不到。
"""

import hashlib
import json
import time
from pathlib import Path
from typing import List, Optional, Tuple

from app.services.credibility import prompt as prompt_mod
from app.services.credibility.assembler import build_evidence
from app.services.credibility.fetcher import CookieMissingError, _cache_dir, fetch_titles
from app.services.credibility.models import (
    CreatorProfile,
    CredibilityResult,
    FetchFailure,
    VideoTitle,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 结果缓存：标题 7 天过期，结论跟着标题一起过期即可
_TTL_DAYS = 7


def _result_path(cache_key: str) -> Path:
    return _cache_dir() / f"analysis_{cache_key}.json"


def _load_result(cache_key: str) -> Optional[str]:
    path = _result_path(cache_key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if (time.time() - data.get("created_at", 0)) > _TTL_DAYS * 86400:
        return None
    return data.get("analysis")


def _save_result(cache_key: str, topic: str, analysis: str, mids: List[str]) -> None:
    path = _result_path(cache_key)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps({"created_at": time.time(), "topic": topic,
                        "mids": mids, "analysis": analysis},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
    except Exception as e:
        logger.warning(f"写入分析结果缓存失败: {e}")
        tmp.unlink(missing_ok=True)


def _call_llm(user_prompt: str, model: str = "") -> str:
    """复用项目现有的 GPT 工厂与模型配置，不另造轮子"""
    from app.config.model_config_manager import get_default_model, get_model_config
    from app.gpt.gpt_factory import GPTFactory
    from app.models.model_config import ModelConfig

    model_name = model or get_default_model()
    model_config = get_model_config(model_name)
    if not model_config:
        raise RuntimeError(f"无法加载模型 '{model_name}' 的配置，请检查 API Key 是否已配置")

    config = ModelConfig(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"],
        model_name=model_config["model_name"],
        provider="openai",
        name=model_name,
    )
    client = GPTFactory().from_config(config)
    return client.ask(user_prompt)


def analyze_credibility(
    creators: List[Tuple[str, str]],
    topic: str = "",
    ttl_days: int = 7,
    max_workers: int = 8,
    use_cache: bool = True,
) -> CredibilityResult:
    """分析一组 UP 主的可靠性。

    :param creators: [(UP主名, mid), ...]
    :param topic: 分析主题，会填入提示词，如「手机选购建议」
    :param ttl_days: 缓存天数
    :param max_workers: 采集并发数，实测 8 稳定
    :param use_cache: 是否复用缓存结论
    :return: CredibilityResult
    """
    if not creators:
        return CredibilityResult(analysis="未提供任何 UP 主")

    # 结论缓存键包含提示词哈希 —— 提示词一改自动失效，不会读到旧结论
    prompt_hash = hashlib.sha256(prompt_mod.CREDIBILITY_PROMPT.encode("utf-8")).hexdigest()[:8]
    mids_key = hashlib.sha256(
        "|".join(sorted(m for _, m in creators)).encode("utf-8")
    ).hexdigest()[:8]
    cache_key = f"{prompt_hash}_{mids_key}"

    profiles: List[CreatorProfile] = []
    failures: List[FetchFailure] = []
    cookie_missing = False

    for name, mid in creators:
        try:
            raw, total, err = fetch_titles(
                name, mid, ttl_days=ttl_days, max_workers=max_workers
            )
        except CookieMissingError as e:
            cookie_missing = True
            logger.error(str(e))
            break
        if err and not raw:
            failures.append(FetchFailure(name=name, mid=str(mid), reason=err))
            continue
        profiles.append(CreatorProfile(
            mid=str(mid),
            name=name,
            titles=[VideoTitle(**t) for t in raw],
            total_submissions=total,
            sample_size=len(raw),
        ))

    if cookie_missing:
        return CredibilityResult(
            profiles=profiles, failures=failures,
            analysis="未配置 B站 Cookie，无法采集 UP 主历史作品。"
                    "请执行 bilinote config set BILIBILI_COOKIE \"<cookie>\" 后重试。",
        )

    if not profiles:
        return CredibilityResult(
            failures=failures,
            analysis="所有 UP 主均采集失败，无法分析。",
        )

    if not prompt_mod.is_prompt_ready():
        return CredibilityResult(
            profiles=profiles, failures=failures,
            analysis="可靠性分析提示词尚未填写。\n"
                    f"请编辑 {__file__.rsplit('/', 1)[0]}/prompt.py 中的 CREDIBILITY_PROMPT。\n"
                    f"当前已采集 {len(profiles)} 个 UP 主共 "
                    f"{sum(p.sample_size for p in profiles)} 条标题，填好提示词后可直接重跑（标题已缓存，不会重新请求）。",
        )

    if use_cache:
        cached = _load_result(cache_key)
        if cached:
            return CredibilityResult(
                profiles=profiles, failures=failures,
                analysis=cached, from_cache=True,
            )

    evidence = build_evidence(profiles)
    user_prompt = prompt_mod.build_user_prompt(topic or "该领域的评测可信度", evidence)

    try:
        analysis = _call_llm(user_prompt)
    except Exception as e:
        logger.error(f"模型调用失败: {e}")
        return CredibilityResult(
            profiles=profiles, failures=failures,
            analysis=f"模型调用失败：{e}",
        )

    _save_result(cache_key, topic, analysis, [p.mid for p in profiles])
    return CredibilityResult(profiles=profiles, failures=failures, analysis=analysis)