# BiliNote-CLI

AI 视频笔记生成工具 - 让 AI 为你的视频做笔记

> **项目说明**：本项目基于 [BiliNote](https://github.com/JefferyHcool/BiliNote) fork 并进行大量重构。  
> 原项目采用 MIT 许可证，感谢原作者 Jeffery Huang 的杰出工作。

## 🧬 与原项目的关系

- **Fork 自**：[BiliNote v2.0.0](https://github.com/JefferyHcool/BiliNote)
- **主要重构内容**：
  -  改为 cli 应用
  -  目录结构调整
  -  添加 b 站视频搜索等若干功能
- **许可证**：继承 MIT 许可证
- **是否继续同步上游**：否

## 功能

- 多平台支持：Bilibili、YouTube、抖音、快手、本地视频
- 本地音频转写：基于 faster-whisper 或 MLX-whisper
- AI 笔记生成：支持 DeepSeek、OpenAI、Qwen 等
- 智能缓存：转写结果和笔记自动缓存
- 截图插入、视频跳转链接、多模态理解

## 安装

```bash
# 安装 CLI
cd BiliNote-cli
uv tool install .

# 安装 FFmpeg（必需）
brew install ffmpeg  # macOS
winget install ffmpeg # Windows
# Windows还可以：从 ffmpeg.org 下载，解压后，再将 bin 文件夹路径添加到系统环境变量 PATH 中
```

## 配置

```bash
# 设置 API Key（必需）
bilinote config set DEEPSEEK_API_KEY sk-your-api-key

# 设置 Cookie（推荐，用于获取平台字幕、避免被反爬虫）
bilinote config set BILIBILI_COOKIE "SESSDATA=xxx; ..."

# 查看配置状态
bilinote config list
```

非敏感配置在 `~/.bilinote/config.yaml`：
```yaml
transcriber:
  default_type: "fast-whisper" # 默认音频转写器
  whisper_model_size: "base"
```

## 使用

```bash
# 基础用法
bilinote process "https://www.bilibili.com/video/BV1mQ9jBcEf4"

# 带截图和链接
bilinote process "<url>" --screenshot --link --style 学术风

# 多模态理解（AI 看画面）
bilinote process "<url>" --video-understanding --model gpt-4o

# 自定义输出目录
bilinote process "<url>" --output-dir ./notes/

# 搜索视频
bilinote search "Python 教程" --platform bilibili

# 其他命令
bilinote model-list            # 列出可用模型
bilinote model-set-default deepseek  # 设置默认模型
```

## 命令说明

| 命令 | 说明 |
|------|------|
| `process <url>` | 处理视频生成笔记 |
| `search <keyword>` | 搜索视频并批量生成 |
| `model-list` | 列出可用模型 |
| `model-set-default <model>` | 设置默认模型 |
| `config set <key> <value>` | 设置密钥 |
| `config list` | 查看配置状态 |

### process 参数

| 参数 | 说明 |
|------|------|
| `--model` | AI 模型，如 `deepseek-chat`, `gpt-4o` |
| `--quality` | 音频质量：`fast`, `medium`, `slow` |
| `--screenshot` | 插入视频截图 |
| `--link` | 插入视频跳转链接 |
| `--style` | 笔记风格：学术风、口语风等 |
| `--video-understanding` | 启用多模态理解 |
| `--output` | 输出文件路径 |

## 目录结构

```
~/.bilinote/
├── data/
│   ├── downloads/     # 下载的音频
│   ├── cache/         # 转写缓存
│   ├── output/notes/  # 生成的笔记
│   └── state/         # 任务状态
├── config.yaml        # 用户配置
└── logs/
```

## License

MIT
