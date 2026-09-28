"""macOS 快捷指令：安装/关闭提示子命令与 process 后提示逻辑"""

import os
import subprocess
import sys
from pathlib import Path

_SHORTCUT_MARKER = os.path.join(os.path.expanduser("~"), ".bilinote", ".no_shortcut_prompt")


def _is_macos():
    return sys.platform == "darwin"


def _get_shortcut_path():
    pkg_dir = Path(__file__).resolve().parent
    # 逐级向上查找：兼容 wheel 安装布局与开发态源码布局
    for base in (pkg_dir, pkg_dir.parent, pkg_dir.parent.parent, pkg_dir.parent.parent.parent):
        candidate = base / "BiliNote.shortcut"
        if candidate.exists():
            return str(candidate)
    return str(pkg_dir / "BiliNote.shortcut")  # 默认返回，用于错误提示


def _get_shortcut_help_text():
    return (
        "💡 macOS 快捷指令：从浏览器一键发送视频到 BiliNote\n"
        "   安装: bilinote install-shortcut\n"
        "   使用: 浏览器点击网址栏选择网址 → 菜单栏左上角 [浏览器名称] → 服务 → BiliNote"
    )


def _get_shortcut_process_prompt():
    return (
        _get_shortcut_help_text()
        + "\n   关闭提示: bilinote shortcut-prompt-off\n"
        "   再次查看: bilinote --help"
    )


def _show_shortcut_process_prompt():
    """在 process 命令成功后显示快捷指令提示（macOS 且未关闭）"""
    if not _is_macos():
        return
    if os.path.exists(_SHORTCUT_MARKER):
        return
    print(f"\n{_get_shortcut_process_prompt()}\n")


def install_shortcut_cmd():
    """安装 macOS 快捷指令"""
    if not _is_macos():
        print("快捷指令仅支持 macOS 系统")
        return

    shortcut_path = _get_shortcut_path()
    if not os.path.exists(shortcut_path):
        print(f"错误: 未找到快捷指令文件: {shortcut_path}")
        return

    print("正在打开快捷指令安装窗口...")
    subprocess.run(["open", shortcut_path])
    print("请在弹出的「快捷指令」App 窗口中点击「添加快捷指令」完成安装")
    print()
    print("安装后使用方式: 浏览器点击网址栏选择网址 → 菜单栏左上角 [浏览器名称] → 服务 → BiliNote")


def shortcut_prompt_off_cmd():
    """关闭快捷指令安装提示"""
    os.makedirs(os.path.dirname(_SHORTCUT_MARKER), exist_ok=True)
    Path(_SHORTCUT_MARKER).touch()
    print("已关闭快捷指令安装提示")
    print("如需再次查看: bilinote --help")
