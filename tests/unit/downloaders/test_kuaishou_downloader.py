"""测试 kuaishou_downloader 模块

测试 Cookie 读取逻辑（有/无 Cookie）和链接提取
不实际下载视频，通过 mock 验证参数传递
"""

import os
import unittest
from unittest.mock import patch, MagicMock

# ==================== 配置区 ====================
# 测试用的视频链接（无需修改，仅用于 mock 测试）
KUAISHOU_TEST_URL = "https://v.kuaishou.com/2vBqX74"
# ================================================


class TestKuaiShouExtractLink(unittest.TestCase):
    """测试 KuaiShou._extract_kuaishou_link 方法"""

    def setUp(self):
        from app.downloaders.kuaishou_helper.kuaishou import KuaiShou
        self.ks = KuaiShou()

    def test_extract_link_from_text(self):
        """从文本中提取快手链接"""
        text = '看视频 https://v.kuaishou.com/2vBqX74 更多内容'
        url = self.ks._extract_kuaishou_link(text)
        self.assertEqual(url, "https://v.kuaishou.com/2vBqX74")

    def test_extract_link_pure_url(self):
        """纯 URL 输入"""
        text = "https://v.kuaishou.com/abc123"
        url = self.ks._extract_kuaishou_link(text)
        self.assertEqual(url, "https://v.kuaishou.com/abc123")


class TestKuaiShouTempCookies(unittest.TestCase):
    """测试 KuaiShou.get_temp_cookies 的 Cookie 读取逻辑"""

    @patch("app.downloaders.kuaishou_helper.kuaishou.get_cookie")
    def test_get_cookies_from_env(self, mock_get_cookie):
        """有 KUAISHOU_COOKIE 环境变量时直接返回"""
        mock_get_cookie.return_value = "did=abc123; kpf=PC_WEB"

        from app.downloaders.kuaishou_helper.kuaishou import KuaiShou
        ks = KuaiShou()
        cookies = ks.get_temp_cookies()

        self.assertEqual(cookies, "did=abc123; kpf=PC_WEB")
        mock_get_cookie.assert_called_with("kuaishou")

    @patch("requests.get")
    @patch("app.downloaders.kuaishou_helper.kuaishou.get_cookie")
    def test_get_cookies_fallback_to_web(self, mock_get_cookie, mock_requests_get):
        """无 KUAISHOU_COOKIE 时从网页获取临时 Cookie"""
        mock_get_cookie.return_value = None

        mock_response = MagicMock()
        mock_response.cookies.get_dict.return_value = {
            "did": "web_temp_id",
            "kpn": "KUAISHOU_VISION",
        }
        mock_requests_get.return_value = mock_response

        from app.downloaders.kuaishou_helper.kuaishou import KuaiShou
        ks = KuaiShou()
        cookies = ks.get_temp_cookies()

        # 应该从网页获取并拼接成 cookie 字符串
        self.assertIn("did=web_temp_id", cookies)
        self.assertIn("kpn=KUAISHOU_VISION", cookies)
        mock_requests_get.assert_called_once()

    @patch("app.downloaders.kuaishou_helper.kuaishou.get_cookie")
    def test_env_cookie_takes_priority(self, mock_get_cookie):
        """环境变量 Cookie 优先于网页获取"""
        mock_get_cookie.return_value = "env_cookie=from_env"

        from app.downloaders.kuaishou_helper.kuaishou import KuaiShou
        ks = KuaiShou()
        cookies = ks.get_temp_cookies()

        # 应返回环境变量的 Cookie，不调用网页
        self.assertEqual(cookies, "env_cookie=from_env")


class TestKuaiShouRunWithCookie(unittest.TestCase):
    """测试 KuaiShou.run 在有/无 Cookie 下的行为"""

    @patch("app.downloaders.kuaishou_helper.kuaishou.get_cookie")
    @patch("requests.post")
    @patch("requests.get")
    def test_run_with_env_cookie(self, mock_get, mock_post, mock_get_cookie):
        """有环境变量 Cookie 时使用它"""
        mock_get_cookie.return_value = "did=from_env; kpf=PC_WEB"

        # mock 第一个 requests.get（获取 photo_id 时的重定向）
        mock_redirect_resp = MagicMock()
        mock_redirect_resp.url = "https://www.kuaishou.com/short-video/abc123"
        mock_get.return_value = mock_redirect_resp

        # mock requests.post（获取视频详情）
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            "data": {"visionVideoDetail": {"status": 1}}
        }
        mock_post.return_value = mock_post_resp

        from app.downloaders.kuaishou_helper.kuaishou import KuaiShou
        ks = KuaiShou()
        result = ks.run("https://v.kuaishou.com/2vBqX74 测试视频")

        # Cookie 应该来自环境变量
        self.assertEqual(ks.header["Cookie"], "did=from_env; kpf=PC_WEB")
        mock_get_cookie.assert_called_with("kuaishou")

    @patch("app.downloaders.kuaishou_helper.kuaishou.get_cookie")
    def test_run_without_cookie_uses_temp(self, mock_get_cookie):
        """无环境变量 Cookie 时使用临时获取的 Cookie"""
        mock_get_cookie.return_value = ""

        from app.downloaders.kuaishou_helper.kuaishou import KuaiShou
        ks = KuaiShou()

        # mock get_temp_cookies 返回临时 Cookie
        with patch.object(ks, 'get_temp_cookies', return_value="temp=cookie"):
            with patch.object(ks, '_extract_kuaishou_link', return_value="https://v.kuaishou.com/test"):
                with patch.object(ks, 'get_photo_id', return_value="photo123"):
                    with patch.object(ks, 'get_video_details', return_value={"data": {"test": 1}}):
                        result = ks.run("https://v.kuaishou.com/test 测试")
                        self.assertEqual(ks.header["Cookie"], "temp=cookie")


if __name__ == "__main__":
    unittest.main()
