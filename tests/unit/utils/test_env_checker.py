import sys
import types
import unittest

from app.utils.env_checker import is_cuda_available, is_torch_installed


# 安装 stubs 以避免导入依赖
def _install_stubs():
    # 创建一个 mock torch 模块
    torch_mod = types.ModuleType("torch")
    torch_mod.cuda = types.ModuleType("torch.cuda")
    torch_mod.cuda.is_available = lambda: True
    sys.modules["torch"] = torch_mod


class TestIsCudaAvailable(unittest.TestCase):
    """测试 CUDA 可用性检查"""

    def test_cuda_available_when_torch_installed(self):
        """测试 torch 安装且 CUDA 可用时返回 True"""
        _install_stubs()
        result = is_cuda_available()
        self.assertTrue(result)

    def test_cuda_not_available_when_torch_not_installed(self):
        """测试 torch 未安装时返回 False"""
        # 移除 torch 模块
        original_torch = sys.modules.pop("torch", None)
        try:
            result = is_cuda_available()
            self.assertFalse(result)
        finally:
            if original_torch:
                sys.modules["torch"] = original_torch

    def test_cuda_not_available_when_torch_cuda_missing(self):
        """测试 torch 模块缺少 cuda 时会抛出 AttributeError（代码行为）"""
        # 注意：实际代码只捕获 ImportError，不捕获 AttributeError
        # 这个测试验证当 torch 存在但缺少 cuda 时会抛出异常
        original_torch = sys.modules.get("torch")
        mock_torch = types.ModuleType("torch")
        # 不设置 cuda 属性
        sys.modules["torch"] = mock_torch
        try:
            # 由于代码只捕获 ImportError，这里应该抛出 AttributeError
            with self.assertRaises(AttributeError):
                is_cuda_available()
        finally:
            if original_torch:
                sys.modules["torch"] = original_torch
            else:
                del sys.modules["torch"]


class TestIsTorchInstalled(unittest.TestCase):
    """测试 torch 安装检查"""

    def test_torch_installed_returns_true(self):
        """测试 torch 已安装时返回 True"""
        _install_stubs()
        result = is_torch_installed()
        self.assertTrue(result)

    def test_torch_not_installed_returns_false(self):
        """测试 torch 未安装时返回 False"""
        # 移除 torch 模块
        original_torch = sys.modules.pop("torch", None)
        try:
            result = is_torch_installed()
            self.assertFalse(result)
        finally:
            if original_torch:
                sys.modules["torch"] = original_torch


class TestEnvCheckerIntegration(unittest.TestCase):
    """测试环境检查器集成场景"""

    def test_both_functions_with_torch_installed(self):
        """测试 torch 安装时两个函数的行为"""
        _install_stubs()
        self.assertTrue(is_torch_installed())
        self.assertTrue(is_cuda_available())

    def test_both_functions_without_torch(self):
        """测试 torch 未安装时两个函数的行为"""
        original_torch = sys.modules.pop("torch", None)
        try:
            self.assertFalse(is_torch_installed())
            self.assertFalse(is_cuda_available())
        finally:
            if original_torch:
                sys.modules["torch"] = original_torch


if __name__ == "__main__":
    unittest.main()
