---
name: bilinote-agent-helper
description: |
  指导 AI agent 使用 BiliNote-cli 工具为用户的 B 站视频生成 AI 笔记、总结视频内容，或在 B 站上搜索主题并生成调研报告。
  当用户发送 B 站/YouTube/抖音/快手视频链接要求"记笔记"、"做总结"、"整理要点"时触发；
  当用户要求在 B 站上"搜索"、"调查"、"调研"某个主题时触发；
  当用户提到"视频笔记"、"视频总结"、"BiliNote"时触发。
  即使链接不是 B 站（YouTube、抖音、快手、本地视频），只要用户需要 AI 生成视频笔记，也应该使用此 skill。
---

# BiliNote Agent Helper

本 skill 指导 AI agent 通过终端调用 [BiliNote-cli](https://github.com/JefferyHcool/BiliNote) 工具，满足用户的视频笔记和搜索调研需求。

## 为什么用 BiliNote-cli

BiliNote-cli 是一个专门用于 AI 视频笔记生成的 Python CLI 工具，支持：
- 多平台视频：Bilibili、YouTube、抖音、快手、本地视频
- AI 笔记生成：基于视频音频/字幕自动生成结构化 Markdown 笔记
- 搜索功能：在 B 站搜索视频并批量生成笔记
- 智能缓存：转写结果自动缓存，重复处理速度快

作为 AI agent，你不需要自己看视频或写笔记摘要——让这个工具来做，你只需调用它并整理结果给用户。

## 工具安装

### 1. 检查是否已安装

```bash
which bilinote || bilinote --help
```

如果命令找不到，执行安装：

```bash
# 方式1：从 PyPI 安装（如果已发布）
# uv tool install bilinote-cli

# 方式2：从源码安装（推荐，确保最新版）
# 先 clone 项目，然后：
uv tool install --editable "/Users/rongziyu/Documents/📝projects/BiliNote-cli"
```

> **注意**：BiliNote-cli 依赖 FFmpeg，如果后续运行报错提示找不到 ffmpeg，需要指导用户先安装：`brew install ffmpeg`（macOS）或从 ffmpeg.org 下载（Windows）。

### 2. 检查配置

```bash
bilinote config list
```

至少需要配置 **AI 模型的 API Key**。常见的：
- `DEEPSEEK_API_KEY` — DeepSeek（推荐，性价比高）
- `OPENAI_API_KEY` — OpenAI
- `QWEN_API_KEY` — 通义千问

如果未配置，询问用户是否有 API Key，然后设置：

```bash
bilinote config set DEEPSEEK_API_KEY "sk-xxx"
```

**BILIBILI_COOKIE（可选但推荐）**：如果用户主要处理 B 站视频，建议配置 Cookie 以获取字幕和避免反爬：

```bash
bilinote config set BILIBILI_COOKIE "SESSDATA=xxx; bili_jct=xxx;"
```

获取方式：登录 B 站 → F12 → Application/Storage → Cookies → bilibili.com → 复制 `SESSDATA` 和 `bili_jct`。

## 核心工作流

### Step1: 阅读用户偏好和记忆
- 阅读`memory.md`

### Step2: 使用工具

#### 场景 A：用户发送视频链接，要求做笔记/总结

**步骤：**

1. **提取链接**：从用户消息中识别所有视频 URL（B 站、YouTube、抖音、快手、本地文件路径均可）

2. **确定参数**（根据上下文推断。**若用户未说明，一般不填写以下参数**）：
   - `--model`：AI 模型（如 `deepseek-chat`、`gpt-4o`）。不指定则使用默认模型
   - `--screenshot`：是否在笔记中插入视频截图（用户说"详细笔记"、"带图"时加上）
   - `--link`：是否插入视频时间戳跳转链接
   - `--style`：笔记风格，如 `学术风`、`口语风`、`极简风`

3. **执行生成**：

```bash
# 单视频
bilinote process "https://www.bilibili.com/video/BV1xx" --link --screenshot --style 学术风

# 多视频批量处理
bilinote process "https://www.bilibili.com/video/BV1xx" "https://www.bilibili.com/video/BV2yy" --link --output-dir ./notes/
```

4. **获取结果**：
   - 成功后会输出文件保存路径（如 `~/.bilinote/data/output/notes/BV1xx.md`）
   - 读取该 Markdown 文件内容
   - 将结果整理后发给用户（可以直接转发全文，也可以提取要点做摘要）

### 场景 B：用户在 B 站上搜索/调查某个主题

**步骤：**

1. **执行搜索**：

```bash
bilinote search "Python 异步编程" --platform bilibili
```

2. **分析搜索结果**：终端会输出视频列表，包含标题、播放量、时长等信息。你需要根据用户的需求自行判断哪些视频最相关。

3. **选择视频生成笔记**：由于 `bilinote search` 是交互式命令（需要用户输入序号），在自动化环境中建议跳过交互，直接基于搜索结果的 URL 用 `bilinote process` 处理。

   例如，搜索后你看到了这些结果：
   ```
   1. Python 异步编程入门  播放量：1.2w  时长：15min
   2. asyncio 实战教程     播放量：8k   时长：30min
   3. 深入理解 Python 协程  播放量：5k   时长：45min
   ```

   根据用户需求挑选最相关的 1-3 个视频，然后用 `process` 处理（可能需要先获取视频 URL）。

   > **提示**：如果 search 命令没有直接输出 URL，你可以根据标题 + 作者信息辅助判断，或建议用户指定具体链接。

4. **批量生成笔记**：

```bash
bilinote process "<url1>" "<url2>" --link --output-dir ./调研报告/
```

5. **整合输出**：读取所有生成的 markdown 文件，整合成一份完整的调研总结发给用户。


### Step4: 整理记忆（仅当有必要时）
- `memory.md`供你记录使用该工具中，用户提出的额外要求，或其他关于该工具使用的需要记忆的注意事项。**禁止编辑SKILL.md**。
- 你需确保`memory.md`的总字数小于 400 字。

## 输出文件位置

生成的笔记默认保存在：
- macOS/Linux：`~/.bilinote/data/output/notes/<task_id>.md`
- Windows：`C:\Users\<用户名>\.bilinote\data\output\notes\<task_id>.md`

批量处理时如果使用 `--output-dir`，则保存在指定目录。

## 常用命令速查

```bash
# 处理单个视频
bilinote process <url> [--model <模型>] [--screenshot] [--link] [--style <风格>]

# 批量处理
bilinote process <url1> <url2> ... --output-dir <目录>

# 搜索视频
bilinote search <关键词> --platform bilibili

# 查看/设置配置
bilinote config list
bilinote config set <KEY> <VALUE>

# 查看可用模型
bilinote model-list
bilinote model-set-default <model-id>
```

## 故障排查

| 问题 | 解决方式 |
|------|---------|
| `bilinote: command not found` | 执行安装步骤，或检查 uv tool 的全局 bin 目录是否在 PATH 中 |
| `未配置默认模型` | `bilinote model-list` 查看可用模型，然后 `bilinote model-set-default <模型ID>` |
| `FFmpeg 相关错误` | `brew install ffmpeg`（macOS）或从 ffmpeg.org 下载 |
| API Key 错误 | `bilinote config set DEEPSEEK_API_KEY sk-xxx` |
| B 站视频获取失败 | 配置 BILIBILI_COOKIE，或检查视频是否需要登录 |

## 最佳实践

1. **优先使用批量处理**：用户发多个链接时，一次性 `process` 比逐个调用更高效
2. **合理设置 style**：用户要"快速了解"用 `极简风`，要"深入学习"用 `学术风`
3. **保存位置告知用户**：处理完后告诉用户笔记文件保存在哪里，方便他们后续查看
4. **不要重复处理**：同一个视频链接，如果没有特别说明"重新生成"，可以复用缓存的结果



