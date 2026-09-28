#!/usr/bin/env python3
"""BiliNote CLI - 命令行视频笔记生成工具（兼容入口，实现位于 app.cli）"""

import os
import sys

# 添加 src 目录到路径：开发态直接运行本文件时保证 app/config/ffmpeg_helper 可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.cli import main

if __name__ == '__main__':
    main()
