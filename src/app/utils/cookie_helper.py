"""
Cookie 工具函数
统一从 keyring 读取各平台的 Cookie
"""
from typing import Optional

from app.secret_manager import get_secret


def get_cookie(platform: str) -> Optional[str]:
    """
    从 keyring 读取指定平台的 Cookie
    
    :param platform: 平台名称 (bilibili, douyin, kuaishou)
    :return: Cookie 字符串或 None
    """
    env_var = f"{platform.upper()}_COOKIE"
    return get_secret(env_var)
