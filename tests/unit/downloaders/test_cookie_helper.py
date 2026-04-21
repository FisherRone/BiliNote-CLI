"""测试 cookie_helper 模块"""

import os
import unittest
from unittest.mock import patch

from app.utils.cookie_helper import get_cookie


class TestGetCookie(unittest.TestCase):
    """测试 get_cookie 函数"""

    def test_get_bilibili_cookie(self):
        """读取 BILIBILI_COOKIE"""
        with patch('app.utils.cookie_helper.get_secret', return_value="SESSDATA=abc; bili_jct=xyz"):
            result = get_cookie("bilibili")
            self.assertEqual(result, "SESSDATA=abc; bili_jct=xyz")

    def test_get_douyin_cookie(self):
        """读取 DOUYIN_COOKIE"""
        with patch('app.utils.cookie_helper.get_secret', return_value="ttwid=123; sessionid=456"):
            result = get_cookie("douyin")
            self.assertEqual(result, "ttwid=123; sessionid=456")

    def test_get_kuaishou_cookie(self):
        """读取 KUAISHOU_COOKIE"""
        with patch('app.utils.cookie_helper.get_secret', return_value="did=abc; kpf=PC_WEB"):
            result = get_cookie("kuaishou")
            self.assertEqual(result, "did=abc; kpf=PC_WEB")

    def test_get_cookie_not_set(self):
        """密钥未设置时返回 None"""
        with patch('app.utils.cookie_helper.get_secret', return_value=None):
            self.assertIsNone(get_cookie("bilibili"))
            self.assertIsNone(get_cookie("douyin"))
            self.assertIsNone(get_cookie("kuaishou"))

    def test_get_cookie_platform_case_insensitive(self):
        """平台名大小写不敏感"""
        with patch('app.utils.cookie_helper.get_secret', return_value="test_val"):
            self.assertEqual(get_cookie("bilibili"), "test_val")
            self.assertEqual(get_cookie("Bilibili"), "test_val")
            self.assertEqual(get_cookie("BILIBILI"), "test_val")


if __name__ == "__main__":
    unittest.main()
