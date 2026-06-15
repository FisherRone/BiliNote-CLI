"""
Cookie 工具函数
统一从 keyring 读取各平台的 Cookie
"""
from typing import Optional, Tuple

import httpx

from app.secret_manager import get_secret


def get_cookie(platform: str) -> Optional[str]:
    """
    从 keyring 读取指定平台的 Cookie
    
    :param platform: 平台名称 (bilibili, douyin, kuaishou)
    :return: Cookie 字符串或 None
    """
    env_var = f"{platform.upper()}_COOKIE"
    return get_secret(env_var)


def check_bilibili_cookie(cookie_str: str) -> Tuple[bool, str]:
    """
    检查 Bilibili cookie 有效性

    通过请求 B站 nav 接口判断 cookie 是否有效。

    :param cookie_str: 完整的 cookie 字符串
    :return: (是否有效, 描述信息)
    """
    try:
        resp = httpx.get(
            "https://api.bilibili.com/x/web-interface/nav",
            headers={
                "Cookie": cookie_str,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com",
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
            uname = data["data"].get("uname", "")
            vip_type = data["data"].get("vipType", 0)
            vip_label = {0: "无大会员", 1: "月度大会员", 2: "年度大会员"}.get(vip_type, "未知")
            return True, f"有效（{uname}，{vip_label}）"
        else:
            message = data.get("message", "未知错误")
            return False, f"无效（{message}）"
    except httpx.TimeoutException:
        return False, "无效（请求超时）"
    except Exception as e:
        return False, f"无效（{e}）"
