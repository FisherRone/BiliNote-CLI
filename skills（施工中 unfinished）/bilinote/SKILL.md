---
name: bilinote-agent-helper
description: |
  指导 AI agent 使用 BiliNote-cli 工具为用户的 B 站视频生成 AI 笔记、总结视频内容，或在 B 站上搜索主题并生成调研报告。
  当用户发送 B 站/YouTube/抖音/快手视频链接要求"记笔记"、"做总结"、"整理要点"，或仅有链接，什么都不说时触发；
  当用户要求在 B 站上"搜索"、"调查"、"调研"某个主题时触发；
  当用户提到"视频笔记"、"视频总结"、"BiliNote"时触发。
  即使链接不是 B 站（YouTube、抖音、快手、本地视频），只要用户需要 AI 生成视频笔记，也应该使用此 skill。
---

# BiliNote Agent Helper

本 skill 指导 AI agent 通过终端调用 [BiliNote-CLI](https://github.com/FisherRone/BiliNote-CLI) 工具，满足用户的视频笔记和搜索调研需求。

## BiliNote-cli 的功能

BiliNote-CLI 是一个专门用于 AI 视频笔记生成的  CLI 工具，支持：
- 多平台视频：Bilibili、YouTube、抖音、快手、本地视频
- AI 笔记生成：基于视频音频/字幕自动生成结构化 Markdown 笔记
- 搜索功能：在 B 站搜索视频并批量生成笔记
- 智能缓存：转写结果自动缓存，重复处理速度快

作为 AI agent，你不需要自己看视频或写笔记摘要——让这个工具来做，你只需调用它并整理结果给用户。

## 工作流程
```text
检查是否已安装和配置？
├── 否 -> 自行安装/配置，或告知用户如何安装/配置
└── 是 -> 用户的输入是什么？
    ├── 包含视频链接或本地视频文件地址 -> 使用 process 指令 ──┐
    ├── 要求在 B 站调查或搜索 ->  使用 search 指令 ─────────└── 完成后续任务。
    └── 非上述情况 -> 缺少执行任务的必要信息，需询问/提示用户。
```

- 除非用户明确要求，一律使用默认调用方式。
- 使用 `--output` 参数指定笔记生成到**你能访问**的文件夹内。
  - 笔记默认保存到：
    - macOS：~/.bilinote/output/notes/
    - windows： C:\Users\<user_name>\.bilinote\output\notes\
- 除了完成用户要求的任务，还应报告生成的笔记的地址，或将笔记发送给用户。

### 检查是否已安装和配置

```bash
where bilinote && bilinote check
where ffmpeg
```
### 安装和配置

```bash
where uv
uv tool install bilinote-cli
```

```bash
where brew
brew install ffmpeg # macOS
```

- Windows 下提醒用户手动下载 ffmpeg，并写入系统 PATH

```bash
bilinote config set DEEPSEEK_API_KEY "sk-xxx"
bilinote config set BILIBILI_COOKIE "xxx"
bilinote check
```

## process & search 指令
```bash
bilinote process "<url1>" "<url2>" --output-dir "<dir>" # 可传入一个或多个
bilinote search "<tag1>+<tag2>" --platform bilibili --output-dir "<dir>" # 可搜索一个或多个关键词
```

| 参数 | 说明 |
|------|------|
| `--model` | AI 模型，如 `deepseek-chat`, `gpt-4o` |
| `--quality` | 音频质量：`fast`, `medium`, `slow` |
| `--screenshot` | 插入视频截图 |
| `--link` | 插入视频跳转链接 |
| `--style` | 笔记风格：学术风、口语风等 |
| `--video-understanding` | 启用多模态理解 |
| `--output-dir` | 输出文件目录 |



