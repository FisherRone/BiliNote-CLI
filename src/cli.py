#!/usr/bin/env python3
"""BiliNote CLI - 命令行视频笔记生成工具"""

import argparse
import sys
import os
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.note import NoteGenerator
from app.services.batch_processor import BatchProcessor
from app.enmus.note_enums import DownloadQuality
from app.utils.url_parser import extract_video_id, detect_platform
from app.utils.path_helper import get_path_manager
from config.model_config_manager import remove_model, list_available_models, get_model_config, get_default_model, set_default_model


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
    process_parser = subparsers.add_parser('process', help='处理视频生成笔记（支持批量 URL）')
    process_parser.add_argument('video_urls', nargs='+', help='视频链接或本地文件路径（可多个）')
    process_parser.add_argument('--platform', 
                       choices=['bilibili', 'youtube', 'douyin', 'kuaishou', 'local'],
                       help='视频平台（可选，默认自动识别）')
    process_parser.add_argument('--model', default=None, help='模型名称（可选，默认使用配置的默认模型）')
    process_parser.add_argument('--quality', default='medium', 
                       choices=['fast', 'medium', 'slow'],
                       help='音频下载质量')
    process_parser.add_argument('--screenshot', action='store_true', help='在笔记中插入截图')
    process_parser.add_argument('--link', action='store_true', help='在笔记中插入视频跳转链接')
    process_parser.add_argument('--style', default=None, help='笔记风格（学术风、口语风等）')
    process_parser.add_argument('--format', nargs='*', default=[], 
                       choices=['screenshot', 'link'],
                       help='笔记格式选项')
    process_parser.add_argument('--video-understanding', action='store_true',
                       help='启用视频多模态理解')
    process_parser.add_argument('--video-interval', type=int, default=0,
                       help='视频帧截取间隔（秒）')
    process_parser.add_argument('--grid-size', nargs=2, type=int, default=None,
                       help='缩略图网格大小，如 3 3')
    process_parser.add_argument('--extras', default=None, help='额外参数')
    process_parser.add_argument('--output', default=None, help='输出文件路径（单任务时有效）')
    process_parser.add_argument('--output-dir', default=None, help='批量输出目录（多任务时自动创建批次目录）')
    
    # search 子命令 - 搜索视频
    search_parser = subparsers.add_parser('search', help='搜索视频并交互选择批量执行')
    search_parser.add_argument('keyword', help='搜索关键词')
    search_parser.add_argument('--platform', default='bilibili',
                       choices=['bilibili', 'youtube'],
                       help='搜索平台（默认 bilibili）')
    search_parser.add_argument('--model', default=None, help='模型名称')
    search_parser.add_argument('--quality', default='medium', 
                       choices=['fast', 'medium', 'slow'],
                       help='音频下载质量')
    search_parser.add_argument('--screenshot', action='store_true', help='在笔记中插入截图')
    search_parser.add_argument('--link', action='store_true', help='在笔记中插入视频跳转链接')
    search_parser.add_argument('--style', default=None, help='笔记风格')
    search_parser.add_argument('--format', nargs='*', default=[], 
                       choices=['screenshot', 'link'],
                       help='笔记格式选项')
    search_parser.add_argument('--extras', default=None, help='额外参数')
    search_parser.add_argument('--output', default=None, help='输出文件路径')
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


def process_video_cli(args):
    """处理视频生成笔记（支持批量）"""
    video_urls = args.video_urls
    
    # 使用默认模型
    if not args.model:
        args.model = get_default_model()
        if not args.model:
            print('错误: 未配置默认模型，请使用 --model 指定模型或 model-set-default 设置默认模型')
            sys.exit(1)
    
    # 处理 format 参数
    if args.screenshot and 'screenshot' not in args.format:
        args.format.append('screenshot')
    if args.link and 'link' not in args.format:
        args.format.append('link')
    
    # 转换 quality
    quality_map = {
        'fast': DownloadQuality.fast,
        'medium': DownloadQuality.medium,
        'slow': DownloadQuality.slow
    }
    
    # 单任务处理（兼容旧用法）
    if len(video_urls) == 1 and not args.output_dir:
        _process_single(video_urls[0], args, quality_map)
        return
    
    # 批量处理
    _process_batch(video_urls, args, quality_map)


def _process_single(video_url: str, args, quality_map: dict):
    """处理单个视频"""
    # 自动识别平台
    platform = args.platform
    if not platform:
        platform = detect_platform(video_url)
        if not platform:
            print('错误: 无法自动识别平台，请使用 --platform 手动指定')
            sys.exit(1)
        print(f"自动识别平台: {platform}")
    
    print(f"使用默认模型: {args.model}")
    
    try:
        print(f"开始生成笔记...")
        print(f"平台: {platform}")
        print(f"模型: {args.model}")
        print(f"视频: {video_url}")
        print("-" * 60)
        
        note_generator = NoteGenerator()
        path_manager = get_path_manager()
        
        # 提取 task_id 用于缓存和文件命名
        task_id = extract_video_id(video_url, platform)
        
        result = note_generator.generate(
            video_url=video_url,
            platform=platform,
            quality=quality_map[args.quality],
            task_id=task_id,
            model_name=args.model,
            link=args.link,
            screenshot=args.screenshot,
            _format=args.format,
            style=args.style,
            extras=args.extras,
            output_path=args.output,
            video_understanding=args.video_understanding,
            video_interval=args.video_interval,
            grid_size=args.grid_size,
        )
        
        if result and result.markdown:
            task_id = task_id or "unknown"
            
            # 保存到文件
            output_file = args.output or path_manager.get_note_output_path(task_id)
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


def _process_batch(video_urls: list, args, quality_map: dict):
    """批量处理视频"""
    print(f"批量处理 {len(video_urls)} 个视频...")
    print(f"使用模型: {args.model}")
    
    # 准备任务列表
    items = []
    for url in video_urls:
        # 自动识别平台
        platform = args.platform or detect_platform(url)
        if not platform:
            print(f"警告: 无法识别平台，跳过: {url}")
            continue
        task_id = extract_video_id(url, platform)
        items.append((url, platform, task_id, task_id))
    
    if not items:
        print("没有有效的视频链接")
        sys.exit(1)
    
    # 创建批量处理器
    batch_processor = BatchProcessor(output_dir=args.output_dir)
    note_generator = NoteGenerator()
    
    def process_func(url: str, platform: str, task_id: str, output_path: str) -> bool:
        """单个任务处理函数"""
        try:
            result = note_generator.generate(
                video_url=url,
                platform=platform,
                quality=quality_map[args.quality],
                task_id=task_id,
                model_name=args.model,
                link=args.link,
                screenshot=args.screenshot,
                _format=args.format,
                style=args.style,
                extras=args.extras,
                output_path=output_path,
                video_understanding=args.video_understanding,
                video_interval=args.video_interval,
                grid_size=args.grid_size,
            )
            
            if result and result.markdown:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.markdown)
                return True
            return False
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return False
    
    # 执行批量处理
    success_count, fail_count = batch_processor.process(items, process_func)
    
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

    # 5. 使用 BatchProcessor 批量执行
    quality_map = {
        'fast': DownloadQuality.fast,
        'medium': DownloadQuality.medium,
        'slow': DownloadQuality.slow
    }
    
    # 准备任务列表: (url, platform, task_id, title)
    task_items = []
    for item in selected:
        url = item['link']
        detected_platform = detect_platform(url) or platform
        task_id = extract_video_id(url, detected_platform)
        title = item.get('title', task_id)
        task_items.append((url, detected_platform, task_id, title))
    
    # 创建批量处理器（使用关键词作为批次名称）
    batch_processor = BatchProcessor(batch_name=keyword, output_dir=args.output_dir)
    note_generator = NoteGenerator()
    
    def process_func(url: str, platform: str, task_id: str, output_path: str) -> bool:
        """单个任务处理函数"""
        try:
            result = note_generator.generate(
                video_url=url,
                platform=platform,
                quality=quality_map[args.quality],
                task_id=task_id,
                model_name=model_name,
                link=args.link,
                screenshot=args.screenshot,
                _format=args.format,
                style=args.style,
                extras=args.extras,
                output_path=output_path,
            )
            if result and result.markdown:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.markdown)
                return True
            return False
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return False
    
    # 执行批量处理
    success_count, fail_count = batch_processor.process(task_items, process_func)
    
    if fail_count > 0:
        sys.exit(1)


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
