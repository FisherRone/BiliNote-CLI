"""check / status 子命令：环境诊断与任务状态查询"""

import json
import os

from app.gpt.provider.OpenAI_compatible_provider import OpenAICompatibleProvider
from app.utils.path_helper import get_path_manager
from config.model_config_manager import get_model_config
from ffmpeg_helper import check_ffmpeg_exists

from .console import print_separator


def check_cmd():
    """环境诊断：ffmpeg / API Key / Cookie / LLM 连通性"""
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
    from app.utils.cookie_helper import check_bilibili_cookie
    print(f"Cookie 配置状态:\n")
    cookie_keys = {"BILIBILI_COOKIE": "B站", "DOUYIN_COOKIE": "抖音", "KUAISHOU_COOKIE": "快手"}
    for key, label in cookie_keys.items():
        cookie_value = get_secret(key)
        if cookie_value:
            if key == "BILIBILI_COOKIE":
                has_sessdata = "SESSDATA" in cookie_value
                if not has_sessdata:
                    print(f"  ⚠ 已配置  {key:25s}  {label}（缺少 SESSDATA，可能无法获取字幕）")
                else:
                    # 请求 nav 接口验证 cookie 有效性
                    valid, detail = check_bilibili_cookie(cookie_value)
                    icon = "✓" if valid else "✗"
                    print(f"  {icon} 已配置  {key:25s}  {label}（{detail}）")
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
        config = get_model_config(model_id, report_missing=False)
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

    print_separator(width=50, before=True)
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
