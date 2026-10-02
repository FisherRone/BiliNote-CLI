"""BiliNote CLI 命令入口：parser 装配 + 子命令分发

实现按职责拆分至同包各模块。
"""

import argparse
import sys

from .check_cmd import check_cmd, show_task_status
from .config_cmds import config_cli
from .model_cmds import list_models, remove_model_cli, set_default_model_cli
from .process_cmd import process_video_cli
from .search_cmd import search_videos_cli
from .shortcut import (
    _get_shortcut_help_text,
    _is_macos,
    install_shortcut_cmd,
    shortcut_prompt_off_cmd,
)


def _add_process_args(parser: argparse.ArgumentParser) -> None:
    """为 process / search 子命令添加共享参数"""
    parser.add_argument('--quality', default='medium',
                        choices=['fast', 'medium', 'slow'],
                        help='音频下载质量')
    parser.add_argument('--screenshot', action='store_true', help='在笔记中插入截图')
    parser.add_argument('--link', action='store_true', help='在笔记中插入视频跳转链接')
    parser.add_argument('--style', default=None, help='笔记风格（学术风、口语风等）')
    parser.add_argument('--format', nargs='*', default=[],
                        choices=['screenshot', 'link'],
                        help='笔记格式选项')
    parser.add_argument('--video-understanding', action='store_true',
                        help='启用视频多模态理解')
    parser.add_argument('--video-interval', type=int, default=0,
                        help='视频帧截取间隔（秒）')
    parser.add_argument('--grid-size', nargs=2, type=int, default=None,
                        help='缩略图网格大小，如 3 3')
    parser.add_argument('--no-subtitle', action='store_true',
                        help='禁用平台字幕，强制下载音频并转写')
    parser.add_argument('--extras', default=None, help='额外参数')


_SHARED_ARGS_PARSER = argparse.ArgumentParser(add_help=False)
_add_process_args(_SHARED_ARGS_PARSER)


def main():
    # 首次运行时确保默认 config.yaml 存在
    from app.config_manager import get_config_manager
    get_config_manager().ensure_default_config()

    parser = argparse.ArgumentParser(
        description='BiliNote CLI - AI 视频笔记生成工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 生成 B站视频笔记（自动识别平台，使用默认模型）
  bilinote process https://www.bilibili.com/video/BV1xx

  # 批量生成笔记
  bilinote process https://www.bilibili.com/video/BV1xx https://www.bilibili.com/video/BV1xx2

  # 指定模型生成笔记
  bilinote process https://www.bilibili.com/video/BV1xx --model gpt-4o

  # 生成 YouTube 视频笔记并插入截图
  bilinote process https://youtube.com/watch?v=xxx --screenshot

  # 生成 Obsidian 格式笔记（frontmatter 属性 + 一级标题）
  bilinote process https://www.bilibili.com/video/BV1xx --note-format obsidian

  # 处理本地视频
  bilinote process ./video.mp4

  # 搜索视频并保存结果
  bilinote search "关键词" --platform bilibili

  # 从搜索结果处理全部视频
  bilinote process --json ~/.bilinote/output/search_result/xxx.json

  # 从搜索结果选择指定序号处理
  bilinote process --json ~/.bilinote/output/search_result/xxx.json --index 1 2 3

  # 查看任务状态
  bilinote status <task_id>

  # 列出所有可用模型（★ 表示默认模型）
  bilinote model-list

  # 设置默认模型
  bilinote model-set-default gpt-4o

  #  删除模型
  bilinote model-remove my-model

  # 配置密钥（存入系统 keyring）
  bilinote config set DEEPSEEK_API_KEY sk-xxx
  bilinote config set BILIBILI_COOKIE "SESSDATA=xxx; bili_jct=xxx;"

  # 查看密钥配置状态
  bilinote config list


  # 自定义模型：手动编辑 ~/.bilinote/config/models.json
  # 非敏感配置：编辑 ~/.bilinote/config.yaml
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # process 子命令 - 处理视频生成笔记
    process_parser = subparsers.add_parser('process', help='处理视频生成笔记（支持批量 URL 或 JSON）',
                                          parents=[_SHARED_ARGS_PARSER])
    process_parser.add_argument('video_urls', nargs='*', default=[],
                       help='视频链接或本地文件路径（可多个，与 --json 二选一）')
    process_parser.add_argument('--json', dest='json_path', default=None,
                       help='从 search 结果 JSON 文件读取链接')
    process_parser.add_argument('--index', nargs='+', type=int, default=None,
                       help='指定 JSON 中要处理的视频序号（如 --index 1 2 3）')
    process_parser.add_argument('--platform',
                       choices=['bilibili', 'youtube', 'douyin', 'kuaishou', 'local'],
                       help='视频平台（可选，默认自动识别）')
    process_parser.add_argument('--model', default=None, help='模型名称（可选，默认使用配置的默认模型）')
    process_parser.add_argument('--note-format', default=None,
                       choices=['markdown', 'obsidian'],
                       help='笔记输出格式（默认取 config.yaml 的 output.note_format，再回退 markdown）')
    process_parser.add_argument('--output-dir', default=None, help='笔记输出目录（留空则使用默认路径）')
    process_parser.add_argument('--quiet', action='store_true',
                       help='极简输出（仅单视频处理生效：只打印标题、链接和保存路径）')

    # search 子命令 - 搜索视频
    search_parser = subparsers.add_parser('search', help='搜索视频并保存结果为 JSON')
    search_parser.add_argument('keyword', help='搜索关键词')
    search_parser.add_argument('--platform', default='bilibili',
                       choices=['bilibili', 'youtube'],
                       help='搜索平台（默认 bilibili）')
    search_parser.add_argument('--output-dir', default=None,
                       help='搜索结果保存目录（默认 ~/.bilinote/output/search_result）')
    search_parser.add_argument('--limit', type=int, default=20,
                       help='搜索结果数量上限（默认 20）')

    # status 子命令 - 查询任务状态
    status_parser = subparsers.add_parser('status', help='查询任务状态')
    status_parser.add_argument('task_id', help='任务ID')

    # model-list 子命令 - 列出所有模型
    subparsers.add_parser('model-list', help='列出所有已配置的模型')

    # model-set-default 子命令 - 设置默认模型
    model_set_default_parser = subparsers.add_parser('model-set-default', help='设置默认模型')
    model_set_default_parser.add_argument('model_id', help='模型ID')

    # model-remove 子命令 - 删除模型
    model_remove_parser = subparsers.add_parser('model-remove', help='删除自定义模型')
    model_remove_parser.add_argument('model_id', help='模型ID')

    # config 子命令 - 管理密钥和配置
    config_parser = subparsers.add_parser('config', help='管理密钥和配置')
    config_subparsers = config_parser.add_subparsers(dest='config_action', help='配置操作')

    # config set
    config_set_parser = config_subparsers.add_parser('set', help='设置密钥（存入系统 keyring）')
    config_set_parser.add_argument('key', help='密钥名称（如 DEEPSEEK_API_KEY、BILIBILI_COOKIE）')
    config_set_parser.add_argument('value', help='密钥值')

    # config get
    config_get_parser = config_subparsers.add_parser('get', help='查看密钥（脱敏显示）')
    config_get_parser.add_argument('key', help='密钥名称')

    # config delete
    config_delete_parser = config_subparsers.add_parser('delete', help='删除密钥')
    config_delete_parser.add_argument('key', help='密钥名称')

    # config list
    config_subparsers.add_parser('list', help='列出所有已知密钥及配置状态')

    # install-shortcut 子命令（仅 macOS）
    subparsers.add_parser('install-shortcut', help='安装 macOS 快捷指令（从浏览器一键发送视频）')

    # shortcut-prompt-off 子命令
    subparsers.add_parser('shortcut-prompt-off', help='关闭快捷指令安装提示')

    # check 子命令 - 环境诊断
    subparsers.add_parser('check', help='环境检查（ffmpeg、API Key、Cookie、LLM 连通性）')

    # macOS: 在帮助信息中添加快捷指令提示
    if _is_macos():
        parser.epilog += "\n" + _get_shortcut_help_text()


    args = parser.parse_args()

    # 如果没有指定命令，显示帮助
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 搜索子命令
    if args.command == 'search':
        search_videos_cli(args)
        return

    # 处理视频子命令
    if args.command == 'process':
        process_video_cli(args)
        return

    # 查询任务状态
    if args.command == 'status':
        show_task_status(args.task_id)
        return

    # 模型管理子命令
    if args.command == 'model-list':
        list_models()
        return

    if args.command == 'model-set-default':
        set_default_model_cli(args.model_id)
        return

    if args.command == 'model-remove':
        remove_model_cli(args.model_id)
        return

    # 配置管理子命令
    if args.command == 'config':
        config_cli(args)
        return

    # 环境检查子命令
    if args.command == 'check':
        check_cmd()
        return

    # 快捷指令子命令
    if args.command == 'install-shortcut':
        install_shortcut_cmd()
        return

    if args.command == 'shortcut-prompt-off':
        shortcut_prompt_off_cmd()
        return
