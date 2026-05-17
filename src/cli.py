#!/usr/bin/env python3
"""BiliNote CLI - 命令行视频笔记生成工具"""

import argparse
import sys
import os
import json
import subprocess
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.note import NoteGenerator
from app.services.batch_processor import AsyncBatchProcessor
from app.models.process_config import ProcessConfig
from app.utils.url_parser import extract_video_id, detect_platform
from app.utils.path_helper import get_path_manager
from config.model_config_manager import remove_model, list_available_models, get_model_config, get_default_model, set_default_model
from ffmpeg_helper import check_ffmpeg_exists
from app.gpt.provider.OpenAI_compatible_provider import OpenAICompatibleProvider


# ── macOS 快捷指令 ──────────────────────────────────────────────
_SHORTCUT_MARKER = os.path.join(os.path.expanduser("~"), ".bilinote", ".no_shortcut_prompt")


def _is_macos():
    return sys.platform == "darwin"


def _get_shortcut_path():
    pkg_dir = Path(__file__).resolve().parent
    # 安装后路径（wheel force-include 放入 src/）
    in_pkg = pkg_dir / "BiliNote.shortcut"
    if in_pkg.exists():
        return str(in_pkg)
    # 开发时路径（项目根目录）
    in_root = pkg_dir.parent / "BiliNote.shortcut"
    if in_root.exists():
        return str(in_root)
    return str(in_pkg)  # 默认返回，用于错误提示


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
  python cli.py process https://www.bilibili.com/video/BV1xx
  
  # 批量生成笔记
  python cli.py process https://www.bilibili.com/video/BV1xx https://www.bilibili.com/video/BV1xx2

  # 指定模型生成笔记
  python cli.py process https://www.bilibili.com/video/BV1xx --model gpt-4o
  
  # 生成 YouTube 视频笔记并插入截图
  python cli.py process https://youtube.com/watch?v=xxx --screenshot
  
  # 处理本地视频
  python cli.py process ./video.mp4
  
  # 搜索视频并交互选择批量生成笔记
  python cli.py search "关键词" --platform bilibili
  
  # 查看任务状态
  python cli.py status <task_id>
  
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
    process_parser = subparsers.add_parser('process', help='处理视频生成笔记（支持批量 URL）',
                                          parents=[_SHARED_ARGS_PARSER])
    process_parser.add_argument('video_urls', nargs='+', help='视频链接或本地文件路径（可多个）')
    process_parser.add_argument('--platform',
                       choices=['bilibili', 'youtube', 'douyin', 'kuaishou', 'local'],
                       help='视频平台（可选，默认自动识别）')
    process_parser.add_argument('--model', default=None, help='模型名称（可选，默认使用配置的默认模型）')
    process_parser.add_argument('--output-dir', default=None, help='批量输出目录（多任务时自动创建批次目录）')
    
    # search 子命令 - 搜索视频
    search_parser = subparsers.add_parser('search', help='搜索视频并交互选择批量执行',
                                         parents=[_SHARED_ARGS_PARSER])
    search_parser.add_argument('keyword', help='搜索关键词')
    search_parser.add_argument('--platform', default='bilibili',
                       choices=['bilibili', 'youtube'],
                       help='搜索平台（默认 bilibili）')
    search_parser.add_argument('--model', default=None, help='模型名称')
    search_parser.add_argument('--output-dir', default=None, help='批量输出目录')
    
    # status 子命令 - 查询任务状态
    status_parser = subparsers.add_parser('status', help='查询任务状态')
    status_parser.add_argument('task_id', help='任务ID')
    
    # model-list 子命令 - 列出所有模型
    model_list_parser = subparsers.add_parser('model-list', help='列出所有已配置的模型')
        
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


def process_video_cli(args):
    """处理视频生成笔记（支持批量）"""
    video_urls = args.video_urls
    
    # 使用默认模型
    model_name = args.model
    if not model_name:
        model_name = get_default_model()
        if not model_name:
            print('错误: 未配置默认模型，请使用 --model 指定模型或 model-set-default 设置默认模型')
            sys.exit(1)
    
    # 静态预检：API Key 是否存在
    if not _check_model_api_key(model_name):
        sys.exit(1)
    
    # 一键从 argparse namespace 生成 ProcessConfig（quality、format 等自动处理）
    cfg = ProcessConfig(**vars(args))
    
    # 构建任务列表
    items = []
    for url in video_urls:
        platform = args.platform or detect_platform(url)
        if not platform:
            print(f"警告: 无法识别平台，跳过: {url}")
            continue
        task_id = extract_video_id(url, platform)
        items.append((url, platform, task_id, task_id))
    
    _process_tasks(items, cfg, model_name, args.output_dir)
    _show_shortcut_process_prompt()


def _process_tasks(items: list, cfg: ProcessConfig, model_name: str, output_dir: str | None = None, batch_name: str | None = None):
    """统一任务处理入口
    
    单任务：同步串行执行（保留笔记预览打印）
    多任务：主线程串行准备 + 线程池并行 AI 处理
    """
    if not items:
        print("没有有效的视频链接")
        sys.exit(1)
    
    # ── 单任务：同步串行 ──
    if len(items) == 1:
        url, platform, task_id, title = items[0]
        
        print(f"开始生成笔记...")
        print(f"平台: {platform}")
        print(f"模型: {model_name}")
        print(f"视频: {url}")
        print("-" * 60)
        
        try:
            note_generator = NoteGenerator()
            result = note_generator.generate(
                video_url=url,
                platform=platform,
                cfg=cfg,
                task_id=task_id,
                model_name=model_name,
            )
            
            if result and result.markdown:
                task_id = task_id or "unknown"
                path_manager = get_path_manager()
                output_file = path_manager.get_note_output_path(task_id)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result.markdown)
                
                print(f"\n{'='*60}")
                print(f"✓ 笔记生成成功！")
                print(f"保存到: {output_file}")
                print(f"{'='*60}\n")
                print(result.markdown[:500])
                if len(result.markdown) > 500:
                    print(f"\n... (更多内容请查看文件)")
                print(f"\n{'='*60}")
            else:
                print("\n✗ 笔记生成失败，请检查日志")
                sys.exit(1)
                
        except Exception as e:
            print(f"\n✗ 错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        return
    
    # ── 多任务：异步并行 ──
    print(f"批量处理 {len(items)} 个视频...")
    print(f"使用模型: {model_name}")
    
    batch_processor = AsyncBatchProcessor(batch_name=batch_name, output_dir=output_dir)
    note_generator = NoteGenerator()
    
    def prepare_func(url: str, platform: str, task_id: str, output_path: str):
        """同步准备阶段：下载、转写"""
        try:
            return note_generator.prepare(
                video_url=url,
                platform=platform,
                cfg=cfg,
                task_id=task_id,
                output_path=output_path,
            )
        except Exception as e:
            print(f"  ✗ 准备错误: {e}")
            return None
    
    def ai_func(prepared) -> bool:
        """异步 AI 阶段：每个 worker 线程使用独立 NoteGenerator 实例"""
        try:
            worker = NoteGenerator()
            result = worker.summarize_and_save(prepared, model_name=model_name)
            return result is not None and result.markdown
        except Exception as e:
            print(f"  ✗ AI 错误: {e}")
            return False
    
    # 执行异步批量处理
    success_count, fail_count = batch_processor.process(items, prepare_func, ai_func)
    
    if fail_count > 0:
        sys.exit(1)


def _format_count(n):
    """格式化数量，使用中文单位（无、k、w），最多3位有效数字"""
    if n is None:
        return None
    if n >= 10000:
        return f"{n / 10000:.3g}w"
    if n >= 1000:
        return f"{n / 1000:.3g}k"
    return str(n)


def _format_duration(seconds):
    """格式化视频时长，如 "1h30min", "7min", "45s"""
    if seconds is None:
        return None
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return None
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        if minutes > 0:
            return f"{hours}h{minutes}min"
        return f"{hours}h"
    elif minutes > 0:
        return f"{minutes}min"
    else:
        return f"{secs}s"


def search_videos_cli(args):
    """搜索视频 → 交互选择 → 串行批量生成笔记"""
    from app.services.searcher import search as searcher

    platform = args.platform or "bilibili"
    keyword = args.keyword

    print(f"搜索: {keyword}  平台: {platform}")
    print("-" * 60)

    # 1. 搜索
    items = searcher(keyword, platform=platform)
    if not items:
        print("未找到相关视频")
        return

    # 2. 展示结果
    print(f"搜索到 {len(items)} 条结果：\n")
    for i, item in enumerate(items, 1):
        parts = [f"{i}. {item['title']}"]
        stats = []
        if item.get('play_count') is not None:
            stats.append(f"播放量：{_format_count(item['play_count'])}")
        if item.get('like_count') is not None:
            stats.append(f"点赞量：{_format_count(item['like_count'])}")
        if item.get('favorite_count') is not None:
            stats.append(f"收藏量：{_format_count(item['favorite_count'])}")
        if item.get('duration') is not None:
            stats.append(f"时长：{_format_duration(item['duration'])}")
        if stats:
            parts.append("  ".join(stats))
        print("  ".join(parts))

    # 3. 交互选择
    print(f"\n输入序号列表（如 1 2 4）以执行，q 退出：")
    user_input = input("> ").strip()
    if user_input.lower() == 'q':
        print("退出")
        return

    try:
        indices = [int(x) for x in user_input.split()]
        selected = [items[i - 1] for i in indices if 1 <= i <= len(items)]
    except (ValueError, IndexError):
        print("输入格式错误")
        return

    if not selected:
        print("未选择任何视频")
        return

    # 4. 默认模型
    model_name = args.model or get_default_model()
    if not model_name:
        print("未配置默认模型，请先 --model-set-default")
        return

    # 静态预检：API Key 是否存在
    if not _check_model_api_key(model_name):
        return

    # 5. 准备任务列表并统一处理
    cfg = ProcessConfig(**vars(args))
    
    task_items = []
    for item in selected:
        url = item['link']
        detected_platform = detect_platform(url) or platform
        task_id = extract_video_id(url, detected_platform)
        title = item.get('title', task_id)
        task_items.append((url, detected_platform, task_id, title))
    
    _process_tasks(task_items, cfg, model_name, args.output_dir, batch_name=keyword)


def list_models():
    """列出所有已配置的模型"""
    import logging
    # 临时抑制警告日志
    logging.getLogger('config.model_config_manager').setLevel(logging.ERROR)
    
    models = list_available_models()
    default_model = get_default_model()
    print(f"\n已配置的模型 ({len(models)} 个):")
    print("-" * 60)
    for model_id in models:
        config = get_model_config(model_id)
        is_default = model_id == default_model
        marker = "★" if is_default else "✓"
        default_tag = " (默认)" if is_default else ""
        if config:
            print(f"  {marker} {model_id:20s} -> {config['model_name']}{default_tag}")
        else:
            print(f"  {marker} {model_id:20s} (未配置 API Key){default_tag}")
    print()


def set_default_model_cli(model_id: str):
    """通过 CLI 设置默认模型"""
    if set_default_model(model_id):
        print(f"\n✓ 已设置默认模型: {model_id}")
    else:
        print(f"\n✗ 设置默认模型失败: {model_id}")
    print()


def remove_model_cli(model_id: str):
    """通过 CLI 删除模型"""
    if remove_model(model_id):
        print(f"\n✓ 已删除模型: {model_id}")
    else:
        print(f"\n✗ 删除模型失败: {model_id}")
    print()


def config_cli(args):
    """配置管理命令"""
    from app.secret_manager import set_secret, get_secret, delete_secret, list_known_keys, get_configured_keys, mask_value
    from app.config_manager import get_config_manager
    
    if not args.config_action:
        print('请指定配置操作: set, get, delete, list')
        print('示例: bilinote config set DEEPSEEK_API_KEY sk-xxx')
        return
    
    if args.config_action == 'set':
        set_secret(args.key, args.value)
        print(f"✓ 已设置密钥: {args.key}")
    
    elif args.config_action == 'get':
        value = get_secret(args.key)
        if value:
            print(f"{args.key} = {mask_value(value)}")
        else:
            print(f"✗ 密钥 {args.key} 未配置")
    
    elif args.config_action == 'delete':
        if delete_secret(args.key):
            print(f"✓ 已删除密钥: {args.key}")
        else:
            print(f"✗ 密钥 {args.key} 不存在或删除失败")
    
    elif args.config_action == 'list':
        known = list_known_keys()
        configured = get_configured_keys()
        print(f"\n密钥配置状态 ({len(configured)}/{len(known)} 已配置):\n")
        for key, desc in known.items():
            status = "✓ 已配置" if key in configured else "✗ 未配置"
            print(f"  {status}  {key:25s}  {desc}")
        print(f"\n使用 bilinote config set <KEY> <VALUE> 设置密钥")
    


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


def _check_model_api_key(model_name: str) -> bool:
    """
    静态预检：校验指定模型的 API Key 是否已配置（不发起网络请求）。
    返回 True 表示 Key 已配置，False 则打印错误提示。
    """
    config = get_model_config(model_name)
    if not config:
        print(f"\n✗ 模型 \"{model_name}\" 的 API Key 未配置")
        print(f"  使用 bilinote config set <KEY> <value> 配置")
        print(f"  使用 bilinote check 查看全部状态")
        return False
    return True


def check_cmd():
    """环境诊断：ffmpeg / API Key / Cookie / LLM 连通性"""
    import logging
    # 抑制 get_model_config 的 WARNING 日志（check 命令自行报告状态）
    logging.getLogger('config.model_config_manager').setLevel(logging.ERROR)

    print("\n环境检查结果\n" + "=" * 50)

    # ── 1. ffmpeg ──────────────────────────────────────
    if check_ffmpeg_exists():
        print("  ✓ ffmpeg    已安装")
    else:
        print("  ✗ ffmpeg    未安装")
        print("    👉 下载：https://ffmpeg.org/download.html")
        print("    💡 自定义路径：在 config.yaml 中设置 ffmpeg_bin_path")
    print()

    # ── 2. API Key 配置状态 ───────────────────────────
    from app.secret_manager import list_known_keys, get_configured_keys, get_secret
    known = list_known_keys()
    configured = get_configured_keys()

    print(f"API Key 配置状态 (仅 LLM 相关):\n")
    llm_key_names = {"OPENAI_API_KEY", "DEEPSEEK_API_KEY", "QWEN_API_KEY",
                     "CLAUDE_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "OLLAMA_API_KEY"}
    for key, desc in known.items():
        if key not in llm_key_names:
            continue
        status = "✓ 已配置" if key in configured else "✗ 未配置"
        print(f"  {status}  {key:25s}  {desc}")

    # ── 3. Cookie 配置状态 ───────────────────────────
    print(f"Cookie 配置状态:\n")
    cookie_keys = {"BILIBILI_COOKIE": "B站", "DOUYIN_COOKIE": "抖音", "KUAISHOU_COOKIE": "快手"}
    for key, label in cookie_keys.items():
        cookie_value = get_secret(key)
        if cookie_value:
            has_sessdata = "SESSDATA" in cookie_value if key == "BILIBILI_COOKIE" else None
            if key == "BILIBILI_COOKIE" and has_sessdata:
                print(f"  ✓ 已配置  {key:25s}  {label}（含 SESSDATA）")
            elif key == "BILIBILI_COOKIE" and not has_sessdata:
                print(f"  ⚠ 已配置  {key:25s}  {label}（缺少 SESSDATA，可能无法获取字幕）")
            else:
                print(f"  ✓ 已配置  {key:25s}  {label}")
        else:
            print(f"  ✗ 未配置  {key:25s}  {label}")
    print()

    # ── 4. LLM 连通性测试 ─────────────────────────────
    from config.model_config_manager import MODELS
    print(f"LLM 连通性测试（仅检查已配置 Key 的模型）:\n")
    tested = 0
    for model_id in sorted(MODELS.keys()):
        config = get_model_config(model_id)
        if not config:
            continue
        tested += 1
        model_name = config["model_name"]
        base_url = config["base_url"]
        api_key = config["api_key"]
        success, error = OpenAICompatibleProvider.test_connection(
            api_key=api_key, base_url=base_url, model_name=model_name
        )
        if success:
            print(f"  ✓ {model_id:20s} → 连通正常")
        else:
            short_err = error[:80] + ("..." if len(error) > 80 else "")
            print(f"  ✗ {model_id:20s} → 不可达")
            print(f"    {short_err}")

    if tested == 0:
        print("  (没有已配置 API Key 的模型)\n")
        print(f"  使用 bilinote config set <KEY> <value> 配置 API Key")

    print(f"\n{'=' * 50}")
    print(f"使用 bilinote check 随时复查环境状态\n")


def show_task_status(task_id: str):
    """查询任务状态"""
    path_manager = get_path_manager()
    status_path = path_manager.get_state_file_path(task_id)
    result_path = path_manager.get_note_output_path(task_id, ".json")
    
    if os.path.exists(status_path):
        with open(status_path, 'r', encoding='utf-8') as f:
            status = json.load(f)
        print(f"任务状态: {status.get('status')}")
        if status.get('message'):
            print(f"消息: {status.get('message')}")
    
    if os.path.exists(result_path):
        print(f"\n✓ 任务已完成，结果已保存")
        with open(result_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        print(f"Markdown 长度: {len(result.get('markdown', ''))} 字符")
    else:
        print(f"\n任务结果未找到")


if __name__ == '__main__':
    main()
