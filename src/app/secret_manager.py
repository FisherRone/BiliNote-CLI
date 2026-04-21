"""
密钥管理器
使用系统 keyring 安全存储敏感信息（API Key、Cookie等）
"""
import os
from typing import Optional

import keyring

from app.utils.logger import get_logger

logger = get_logger(__name__)

# keyring 服务名
SERVICE_NAME = "bilinote"

# 内存缓存：避免重复访问 keyring 导致多次弹窗
_secret_cache: dict[str, Optional[str]] = {}

# 已知密钥定义：key → 描述
KNOWN_KEYS = {
    # API Keys
    "OPENAI_API_KEY": "OpenAI API Key",
    "DEEPSEEK_API_KEY": "DeepSeek API Key",
    "QWEN_API_KEY": "通义千问 API Key",
    "CLAUDE_API_KEY": "Claude API Key",
    "GEMINI_API_KEY": "Gemini API Key",
    "GROQ_API_KEY": "Groq API Key（用于 LLM 和语音转写）",
    "OLLAMA_API_KEY": "Ollama API Key",
    # Cookies
    "BILIBILI_COOKIE": "B站 Cookie（用于获取字幕和大会员视频）",
    "DOUYIN_COOKIE": "抖音 Cookie（用于下载抖音视频）",
    "KUAISHOU_COOKIE": "快手 Cookie（用于下载快手视频）",
}


def set_secret(key: str, value: str) -> None:
    """存储密钥到 keyring"""
    keyring.set_password(SERVICE_NAME, key, value)
    # 同时更新缓存
    _secret_cache[key] = value
    logger.info(f"已存储密钥: {key}")


def get_secret(key: str) -> Optional[str]:
    """
    获取密钥，优先级：
    1. 系统环境变量（最高优先级，兼容 CI/CD）
    2. 内存缓存（避免重复访问 keyring）
    3. keyring
    """
    # 系统环境变量优先（每次都检查，因为可能动态设置）
    env_val = os.getenv(key)
    if env_val:
        return env_val
    
    # 检查内存缓存
    if key in _secret_cache:
        return _secret_cache[key]
    
    # keyring 回退
    try:
        value = keyring.get_password(SERVICE_NAME, key)
        # 缓存结果（包括 None，避免重复查询不存在的 key）
        _secret_cache[key] = value
        return value
    except Exception as e:
        logger.warning(f"读取 keyring 失败 ({key}): {e}")
        _secret_cache[key] = None
        return None


def delete_secret(key: str) -> bool:
    """删除 keyring 中的密钥"""
    try:
        keyring.delete_password(SERVICE_NAME, key)
        # 同时清除缓存
        _secret_cache.pop(key, None)
        logger.info(f"已删除密钥: {key}")
        return True
    except keyring.errors.PasswordDeleteError:
        logger.warning(f"密钥不存在，无法删除: {key}")
        return False
    except Exception as e:
        logger.error(f"删除密钥失败 ({key}): {e}")
        return False


def list_known_keys() -> dict[str, str]:
    """列出所有已知密钥及其描述"""
    return dict(KNOWN_KEYS)


def clear_secret_cache() -> None:
    """清除密钥缓存（用于测试或重新加载场景）"""
    _secret_cache.clear()
    logger.debug("已清除密钥缓存")


def get_configured_keys() -> list[str]:
    """列出已配置的密钥（在 keyring 或环境变量中存在）"""
    configured = []
    for key in KNOWN_KEYS:
        if get_secret(key) is not None:
            configured.append(key)
    return configured


def mask_value(value: str) -> str:
    """脱敏显示：只显示前4位和后4位，中间用 **** 替代"""
    if not value:
        return ""
    if len(value) <= 12:
        return value[:3] + "****"
    return value[:4] + "****" + value[-4:]

