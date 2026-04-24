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
- 本地音频转写：基于 whisper-cpp
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
  default_type: "bcut" # 默认音频转写器
  whisper_model_size: "base"
```

### 【教程】提取 Safari Cookie

1. 打开 Safari 的开发者模式。
2. 在浏览器中打开目标网站，按 F12（或 Cmd + Opt + I）打开开发者工具。
3. 切换到 **Network (网络)** 标签页。
4. 刷新页面，随便找一个请求，**右键**点击该请求。
5. 选择 **Copy** -> **Copy as cURL**。
6. 在你的剪贴板里，你会看到一串完整的命令，其中 `-H 'cookie: ...'` 后面就是该网站的所有 Cookie。

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

```bash
~/.bilinote/ #windows： C:\Users\<user_name>\.bilinote\
├── data/
│   ├── downloads/     # 下载的音频
│   ├── cache/         # 转写缓存
│   ├── output/notes/  # 生成的笔记★
│   └── state/         # 任务状态
├── config.yaml        # 用户配置★
└── logs/
```

## 【指南】配置 whisper-cpp 作为本地音频转写器

### macOS 安装 whisper.cpp 指南

#### 1. 安装 whisper-cpp
```bash
brew install whisper-cpp
```
#### 2. 下载模型
```bash
# 创建目录并进入
mkdir -p ~/whisper-models && cd ~/whisper-models
# 下载模型（以 base 模型为例）
curl -L -o ggml-base.bin 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin?download=true'
```
- 或：到 [huggingface 网站](https://huggingface.co/ggerganov/whisper.cpp/tree/main) 下载 whisper 模型。手动移动到模型存储目录。
- ⚠️ **注意**：如果你选择把模型放入其他目录，那么需在 `config.yaml` 内修改模型地址。

### Windows 安装 whisper.cpp 指南

#### 1. 下载程序

- 访问 [whisper.cpp Github Releases 页面](https://github.com/ggerganov/whisper.cpp/releases)
- 下载软件压缩包：
	- CPU 版：`whisper-bin-x64.zip`
	- NVIDIA 显卡加速版：`whisper-cublas-12.4.0-bin-x64.zip`
- 解压到固定目录，如 `D:\ProgramFiles\whispercpp`

#### 2. 下载模型

- 访问 [Huggingface 模型页面](https://huggingface.co/ggerganov/whisper.cpp/tree/main)
- 下载 `ggml-base.bin`（或其他模型）
- 建议放入 `D:\ProgramFiles\whispercpp\models\`

#### 3. 添加到 PATH

以**管理员**身份打开命令提示符，执行：
```cmd
setx /M PATH "D:\ProgramFiles\whispercpp;%PATH%"
```

- ⚠️ **注意**：上面的 `D:\ProgramFiles\whispercpp` 需替换为 `whisper-cli.exe` 所在的目录。
- **重启命令提示符**后生效。  
- 验证是否安装成功：`whisper-cli --help`
- 如果安装遇到问题，建议手动在系统环境变量中添加。

### 配置 whisper-cpp（macOS / Windows 通用）

在 `config.yaml` 中填写模型文件（如`ggml-base.bin`）的路径：

```yaml

transcriber:
  default_type: "whisper-cpp"
  whisper-cpp:
    model_path: "D:/ProgramFiles/whispercpp/models/ggml-base.bin"  # Win
    # model_path: "~/whisper-models/ggml-base.bin"                 # macOS
```

- ⚠️ **注意**：地址应该使用 `/` 而不是 `\`
- ⚠️ **注意**：如果模型放在其他位置，`model_path` 需相应修改。

## License

MIT
