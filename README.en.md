# BiliNote-CLI
[简体中文](README.md) | English

AI Video Note Generator - Let AI Take Notes for Your Videos

> **Project Note**: This project is forked from [BiliNote](https://github.com/JefferyHcool/BiliNote) and heavily refactored.
> Thanks to the original author Jeffery Huang for the outstanding work.

## Features

Let AI automatically convert videos into markdown notes.
- Multi-platform support: Bilibili, YouTube, Douyin, Kuaishou, local videos
- AI note generation: supports DeepSeek, OpenAI, Qwen, etc.
- Screenshot insertion, video jump links, multimodal understanding
- Batch processing, keyword search

## Installation

```bash
# Install CLI
uv tool install bilinote-cli

# Install FFmpeg (required)
brew install ffmpeg  # macOS
winget install ffmpeg # Windows
# For Windows also: download from ffmpeg.org, extract, then add the bin folder path to system environment variable PATH
```

## Configuration

```bash
# Set API Key (required)
bilinote config set DEEPSEEK_API_KEY sk-your-api-key

# Set Cookie (recommended, to fetch platform subtitles and avoid anti-scraping)
bilinote config set BILIBILI_COOKIE "SESSDATA=xxx; ..."

# Check configuration status
bilinote config list
```

Other options live in `~/.bilinote/config.yaml` (Windows: `C:\Users\<user_name>\.bilinote\config.yaml`):
```yaml
output:
  default_dir: ""      # Default note output directory (empty = ~/.bilinote/data/output/notes/)
                       # Example: default_dir: "~/Documents/Notes"

transcriber:
  default_type: "bcut" # default audio transcriber
  whisper_model_size: "base"
```

## Usage

```bash
# Basic usage
bilinote process "https://www.bilibili.com/video/BV1mQ9jBcEf4"

# Batch processing
bilinote process "<url1>" "<url2>"

# With screenshots and links
bilinote process "<url>" --screenshot --link --style academic

# Multimodal understanding (AI analyzes visuals)
bilinote process "<url>" --video-understanding --model gpt-4o

# Custom output directory
bilinote process "<url>" --output-dir <dir>

# Search videos (results saved as JSON)
bilinote search "Python tutorial" --platform bilibili --output-dir <dir>
bilinote process --json "<search_result.json>" --index 2 3 8

# Other commands
bilinote model-list            # List available models
bilinote model-set-default deepseek  # Set default model
bilinote check                 # Check environment (ffmpeg, LLM availability)
bilinote install-shortcut      # Install macOS Shortcut (recommended)
```

## Directory Structure

```bash
~/.bilinote/ # Windows: C:\Users\<user_name>\.bilinote\
├── data/
│   ├── downloads/     # Downloaded audio
│   ├── cache/         # Transcription cache
│   ├── output/notes/  # Generated notes ★
│   └── state/         # Task states
├── config.yaml        # User configuration ★
└── logs/
```

## Command Reference

| Command | Description |
|---------|-------------|
| `process <url>` | Process video and generate notes |
| `search <keyword>` | Search videos and save results as JSON |
| `model-list` | List available models |
| `model-set-default <model>` | Set default model |
| `config set <key> <value>` | Set a configuration key |
| `config list` | Show configuration status |
| `install-shortcut` | Install macOS Shortcut (macOS only) |
| `check` | Environment check |

### process Parameters

| Parameter | Description |
|-----------|-------------|
| `--model` | AI model, e.g., `deepseek-chat`, `gpt-4o` |
| `--screenshot` | Insert video screenshots |
| `--link` | Insert video timestamps as jump links |
| `--style` | Note style |
| `--output-dir` | Output directory path |
| `--json` | Path to a search-result JSON file |
| `--index` | Select items from the JSON file by index |

### Available note styles

| Value | Description |
|-------|-------------|
| `minimal` | Minimal |
| `detailed` | Detailed |
| `tutorial` | Tutorial |
| `xiaohongshu` | Xiaohongshu style |
| `academic` | Academic |
| `life_journal` | Life journal |
| `task_oriented` | Task oriented |
| `business` | Business |
| `meeting_minutes` | Meeting minutes |

## [Guide] Extracting Safari Cookies

1. Open Safari's developer mode.
2. Open the target website in the browser and press F12 (or Cmd+Opt+I) to open Developer Tools.
3. Switch to the **Network** tab.
4. Refresh the page, find any request, and **right-click** on it.
5. Select **Copy** -> **Copy as cURL**.
6. In your clipboard, you'll see a complete command string; the `-H 'cookie: ...'` part contains all cookies for that site.

## [Guide] One-click Run via macOS Shortcut (macOS only)

**Install the Shortcut**: run `bilinote install-shortcut` in a terminal.

**Usage**:
1. In your browser, select the video URL in the address bar.
2. Click the browser app name in the menu bar (top-left of the screen, e.g. "Safari").
3. Click **Services** -> **BiliNote**.

## [Guide] Configuring whisper-cpp as Local Audio Transcriber

### macOS whisper.cpp Installation Guide

#### 1. Install whisper-cpp
```bash
brew install whisper-cpp
```
#### 2. Download a Model
```bash
# Create directory and navigate
mkdir -p ~/whisper-models && cd ~/whisper-models
# Download the base model as an example
curl -L -o ggml-base.bin 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin?download=true'
```
- Or manually download models from the [Hugging Face website](https://huggingface.co/ggerganov/whisper.cpp/tree/main) and move them to the model directory.
- ⚠️ **Note**: If you choose to put models in a different directory, update the `model_path` in `config.yaml` accordingly.

### Windows whisper.cpp Installation Guide

#### 1. Download the Program

- Visit the [whisper.cpp GitHub Releases page](https://github.com/ggerganov/whisper.cpp/releases)
- Download the appropriate package:
  - CPU version: `whisper-bin-x64.zip`
  - NVIDIA GPU accelerated version: `whisper-cublas-12.4.0-bin-x64.zip`
- Extract to a fixed directory, e.g., `D:\ProgramFiles\whispercpp`

#### 2. Download a Model

- Visit the [Hugging Face models page](https://huggingface.co/ggerganov/whisper.cpp/tree/main)
- Download `ggml-base.bin` (or any other model)
- Recommended to place it in `D:\ProgramFiles\whispercpp\models\`

#### 3. Add to PATH

Open Command Prompt as **Administrator** and run:
```cmd
setx /M PATH "D:\ProgramFiles\whispercpp;%PATH%"
```

- ⚠️ **Note**: Replace `D:\ProgramFiles\whispercpp` above with the directory containing `whisper-cli.exe`.
- **Restart Command Prompt** for changes to take effect.
- Verify installation: `whisper-cli --help`
- If you encounter issues, manually add the directory to system environment variables.

### Configure whisper-cpp (macOS / Windows)

Fill in the path to the model file (e.g., `ggml-base.bin`) in `config.yaml`:

```yaml
transcriber:
  default_type: "whisper-cpp"
  whisper-cpp:
    model_path: "D:/ProgramFiles/whispercpp/models/ggml-base.bin"  # Windows
    # model_path: "~/whisper-models/ggml-base.bin"                 # macOS
```

- ⚠️ **Note**: Use forward slashes `/` instead of backslashes `\`.
- ⚠️ **Note**: If your model is stored elsewhere, adjust `model_path` accordingly.

## License

MIT
