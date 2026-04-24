#!/usr/bin/env python3
"""
测试脚本：对比 B站字幕 和 音频转写 给 AI 的 prompt 差异

运行方式:
    cd /Users/rongziyu/Documents/📝projects/BiliNote-cli
    uv run python test_subtitle_vs_transcript.py
"""

import sys
import os
import json

# 添加项目 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from datetime import timedelta
from app.downloaders.bilibili_downloader import BilibiliDownloader
from app.transcriber.transcriber_provider import get_transcriber_with_fallback
from app.gpt.prompt_builder import generate_base_prompt
from app.gpt.prompt import CHUNK_INSTRUCTION
from app.utils.url_parser import extract_video_id
from app.utils.path_helper import get_path_manager

VIDEO_URL = "https://www.bilibili.com/video/BV1Sh97BYEUK"
VIDEO_ID = "BV1Sh97BYEUK"


def format_time(seconds: float) -> str:
    """直接使用已有模块中的时间格式化逻辑 (universal_gpt._format_time)"""
    return str(timedelta(seconds=int(seconds)))[2:]


def build_segment_text(segments):
    """直接使用已有模块中的逻辑 (universal_gpt._build_segment_text)"""
    return "\n".join(
        f"{format_time(seg.start)} - {seg.text.strip()}"
        for seg in segments
    )


def build_full_prompt(title, tags, segments, _format=None, style=None):
    """
    复现 universal_gpt.create_messages 中的 prompt 构建逻辑，
    使用已有模块的 generate_base_prompt 和 CHUNK_INSTRUCTION。
    返回最终交给 AI 的完整文本内容。
    """
    # 1. 系统指令与全局信息（调用已有模块）
    system_text = generate_base_prompt(
        title=title,
        tags=tags,
        _format=_format,
        style=style,
        extras=None,
    )

    # 2. 当前块指令（直接引用已有常量）
    system_text += "\n\n" + CHUNK_INSTRUCTION

    # 3. 当前块转录文本
    segment_text = build_segment_text(segments)
    content_text = system_text + f"\n\n视频分段（格式：开始时间 - 内容）：\n\n{segment_text}"

    return content_text


def analyze_segments(name, segments, max_show=20):
    """分析 segment 结构"""
    print(f"\n{'='*60}")
    print(f"📊 {name} - Segment 分析")
    print(f"{'='*60}")
    print(f"总段数: {len(segments)}")

    if not segments:
        print("无 segment 数据")
        return

    # 统计时长
    durations = [seg.end - seg.start for seg in segments]
    avg_duration = sum(durations) / len(durations)
    max_duration = max(durations)
    min_duration = min(durations)

    print(f"平均段时长: {avg_duration:.2f}s")
    print(f"最长段: {max_duration:.2f}s")
    print(f"最短段: {min_duration:.2f}s")

    # 统计文本长度
    text_lengths = [len(seg.text) for seg in segments]
    avg_text_len = sum(text_lengths) / len(text_lengths)
    print(f"平均文本长度: {avg_text_len:.1f} 字符")

    # 展示前 max_show 段
    print(f"\n前 {min(max_show, len(segments))} 段示例:")
    for i, seg in enumerate(segments[:max_show]):
        duration = seg.end - seg.start
        text_preview = seg.text[:60].replace('\n', ' ')
        if len(seg.text) > 60:
            text_preview += "..."
        print(f"  [{i+1:3d}] {format_time(seg.start)}-{format_time(seg.end)} "
              f"({duration:5.2f}s) | {text_preview}")


def main():
    print(f"🎬 测试视频: {VIDEO_URL}")
    print(f"🆔 Video ID: {VIDEO_ID}")

    downloader = BilibiliDownloader()
    path_manager = get_path_manager()
    downloads_dir = path_manager.downloads_dir
    os.makedirs(downloads_dir, exist_ok=True)

    # ========== 1. 获取字幕 ==========
    print("\n" + "="*60)
    print("📥 步骤 1: 尝试获取平台字幕...")
    print("="*60)

    subtitle_result = None
    try:
        subtitle_result = downloader.download_subtitles(VIDEO_URL, output_dir=downloads_dir)
        if subtitle_result:
            print(f"✅ 成功获取字幕! 语言: {subtitle_result.language}")
            print(f"   总段数: {len(subtitle_result.segments)}")
            # 保存字幕结果
            subtitle_cache = os.path.join(downloads_dir, f"{VIDEO_ID}_subtitle_raw.json")
            with open(subtitle_cache, "w", encoding="utf-8") as f:
                json.dump({
                    "language": subtitle_result.language,
                    "full_text": subtitle_result.full_text,
                    "segments": [
                        {"start": s.start, "end": s.end, "text": s.text}
                        for s in subtitle_result.segments
                    ],
                    "raw": subtitle_result.raw,
                }, f, ensure_ascii=False, indent=2)
            print(f"   字幕原始数据已保存: {subtitle_cache}")
        else:
            print("❌ 该平台视频无可用字幕")
    except Exception as e:
        print(f"❌ 获取字幕失败: {e}")
        import traceback
        traceback.print_exc()

    # ========== 2. 下载音频并转写 ==========
    print("\n" + "="*60)
    print("📥 步骤 2: 下载音频并转写...")
    print("="*60)

    transcript_result = None
    audio_path = None
    try:
        print("   正在下载音频...")
        audio_meta = downloader.download(VIDEO_URL, output_dir=downloads_dir)
        audio_path = audio_meta.file_path
        print(f"✅ 音频下载完成: {audio_path}")
        print(f"   标题: {audio_meta.title}")
        print(f"   时长: {audio_meta.duration}s")

        # 转写
        print("   正在转写音频...")
        transcriber = get_transcriber_with_fallback()
        transcript_result = transcriber.transcript(audio_path)
        print(f"✅ 转写完成! 语言: {transcript_result.language}")
        print(f"   总段数: {len(transcript_result.segments)}")

        # 保存转写结果
        transcript_cache = os.path.join(downloads_dir, f"{VIDEO_ID}_transcript_raw.json")
        with open(transcript_cache, "w", encoding="utf-8") as f:
            json.dump({
                "language": transcript_result.language,
                "full_text": transcript_result.full_text,
                "segments": [
                    {"start": s.start, "end": s.end, "text": s.text}
                    for s in transcript_result.segments
                ],
                "raw": str(transcript_result.raw)[:500] if transcript_result.raw else None,
            }, f, ensure_ascii=False, indent=2)
        print(f"   转写原始数据已保存: {transcript_cache}")

    except Exception as e:
        print(f"❌ 下载/转写失败: {e}")
        import traceback
        traceback.print_exc()

    # ========== 3. 对比分析 ==========
    print("\n" + "="*60)
    print("🔍 步骤 3: 对比分析")
    print("="*60)

    # ========== 3.5 构建完整 Prompt ==========
    audio_title = "迷茫的26岁"  # 测试视频标题
    audio_tags = "生活,感悟"

    if subtitle_result:
        analyze_segments("📝 B站字幕", subtitle_result.segments)
        # 使用已有模块构建完整 prompt
        subtitle_full_prompt = build_full_prompt(
            title=audio_title,
            tags=audio_tags,
            segments=subtitle_result.segments,
        )
        subtitle_prompt_file = os.path.join(downloads_dir, f"{VIDEO_ID}_subtitle_full_prompt.txt")
        with open(subtitle_prompt_file, "w", encoding="utf-8") as f:
            f.write(subtitle_full_prompt)
        print(f"\n   字幕完整 prompt 已保存: {subtitle_prompt_file}")
        print(f"   prompt 总长度: {len(subtitle_full_prompt)} 字符")
        print(f"   prompt 行数: {subtitle_full_prompt.count(chr(10))}")

    if transcript_result:
        analyze_segments("🎙️ 音频转写", transcript_result.segments)
        transcript_full_prompt = build_full_prompt(
            title=audio_title,
            tags=audio_tags,
            segments=transcript_result.segments,
        )
        transcript_prompt_file = os.path.join(downloads_dir, f"{VIDEO_ID}_transcript_full_prompt.txt")
        with open(transcript_prompt_file, "w", encoding="utf-8") as f:
            f.write(transcript_full_prompt)
        print(f"\n   转写完整 prompt 已保存: {transcript_prompt_file}")
        print(f"   prompt 总长度: {len(transcript_full_prompt)} 字符")
        print(f"   prompt 行数: {transcript_full_prompt.count(chr(10))}")

    # ========== 4. 直接对比完整 Prompt 的前半部分 ==========
    print("\n" + "="*60)
    print("📋 步骤 4: 完整 Prompt 对比 (系统指令 + 前10行转录)")
    print("="*60)

    if subtitle_result:
        print("\n--- 📝 字幕完整 Prompt (前半) ---")
        lines = subtitle_full_prompt.split("\n")
        for line in lines[:35]:
            print(line)
        if len(lines) > 35:
            print(f"... (共 {len(lines)} 行)")

    if transcript_result:
        print("\n--- 🎙️ 转写完整 Prompt (前半) ---")
        lines = transcript_full_prompt.split("\n")
        for line in lines[:35]:
            print(line)
        if len(lines) > 35:
            print(f"... (共 {len(lines)} 行)")

    print("\n" + "="*60)
    print("✅ 测试完成！所有输出文件保存在:")
    print(f"   {downloads_dir}")
    print("="*60)


if __name__ == "__main__":
    main()
