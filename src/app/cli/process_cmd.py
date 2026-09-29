"""process 子命令：视频笔记生成（单任务串行 / 批量并行）"""

import json
import os
import sys

from app.models.process_config import ProcessConfig
from app.services.batch_processor import AsyncBatchProcessor
from app.services.note import NoteGenerator
from app.utils.path_helper import get_path_manager
from app.utils.url_parser import detect_platform, extract_video_id
from app.config.model_config_manager import get_default_model, get_model_config

from .console import print_note_preview, print_separator, print_success
from .shortcut import _show_shortcut_process_prompt


def _check_model_api_key(model_name: str) -> bool:
    """
    静态预检：校验指定模型的 API Key 是否已配置（不发起网络请求）。
    返回 True 表示 Key 已配置，False 则打印错误提示。
    """
    config = get_model_config(model_name)
    if not config:
        print(f"\n✗ 模型 \"{model_name}\" 的 API Key 未配置")
        print("  使用 bilinote config set <KEY> <value> 配置")
        print("  使用 bilinote check 查看全部状态")
        return False
    return True


def process_video_cli(args):
    """处理视频生成笔记（支持批量 URL 或 JSON）"""
    video_urls = args.video_urls
    json_path = args.json_path

    if not video_urls and not json_path:
        print('错误: 请提供视频链接或使用 --json 指定搜索结果文件')
        sys.exit(1)

    if json_path and video_urls:
        print('错误: 视频链接和 --json 不可同时使用')
        sys.exit(1)

    if json_path:
        video_urls = _load_urls_from_json(json_path, args.index)

    model_name = args.model
    if not model_name:
        model_name = get_default_model()
        if not model_name:
            print('错误: 未配置默认模型，请使用 --model 指定模型或 model-set-default 设置默认模型')
            sys.exit(1)

    if not _check_model_api_key(model_name):
        sys.exit(1)

    cfg = ProcessConfig(**vars(args))

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


def _load_urls_from_json(json_path: str, indices: list[int] | None = None) -> list[str]:
    """从 search 结果 JSON 中读取链接列表"""
    if not os.path.exists(json_path):
        print(f"错误: 文件不存在: {json_path}")
        sys.exit(1)

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {e}")
        sys.exit(1)

    results = data.get("results", [])
    if not results:
        print("错误: JSON 中无搜索结果")
        sys.exit(1)

    if indices:
        index_set = set(indices)
        selected = [r for r in results if r.get("index") in index_set]
        not_found = index_set - {r.get("index") for r in results}
        if not_found:
            print(f"警告: 序号 {sorted(not_found)} 不在搜索结果中")
        if not selected:
            print("错误: 指定的序号无匹配结果")
            sys.exit(1)
        print(f"从 JSON 选择了 {len(selected)} 个视频（共 {len(results)} 条结果）")
        return [r["link"] for r in selected]

    print(f"从 JSON 加载全部 {len(results)} 个视频链接")
    return [r["link"] for r in results]


def _process_tasks(items: list, cfg: ProcessConfig, model_name: str,
                   output_dir: str | None = None, batch_name: str | None = None):
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

        print("开始生成笔记...")
        print(f"平台: {platform}")
        print(f"模型: {model_name}")
        print(f"视频: {url}")
        print_separator("-")

        try:
            note_generator = NoteGenerator()

            # 确定笔记输出路径（CLI 参数 > config.yaml > 默认）
            if output_dir:
                output_dir = os.path.expanduser(os.path.expandvars(output_dir))
                os.makedirs(output_dir, exist_ok=True)
                custom_output_path = os.path.join(output_dir, f"{task_id or 'unknown'}.md")
            else:
                custom_output_path = None

            result = note_generator.generate(
                video_url=url,
                platform=platform,
                cfg=cfg,
                task_id=task_id,
                model_name=model_name,
                output_path=custom_output_path,
            )

            if result and result.markdown:
                # 笔记文件由 AIProcessor 统一落盘，这里只展示真实路径
                output_file = (
                    result.output_path
                    or custom_output_path
                    or get_path_manager().get_note_output_path(task_id or "unknown")
                )

                print_separator(before=True)
                print_success("笔记生成成功！")
                print(f"保存到: {output_file}")
                print_separator(after=True)
                print_note_preview(result.markdown)
                print_separator()
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
