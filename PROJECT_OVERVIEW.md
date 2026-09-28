## BiliNote-CLI 项目目录概览

BiliNote-CLI 是一个 AI 视频笔记生成命令行工具，输入视频链接，输出 Markdown 笔记。支持 B站、YouTube、抖音、快手和本地视频，使用 OpenAI 兼容的大模型做内容总结。项目基于 Python 3.12+，由 UV 管理依赖，使用 hatchling 构建。

**项目根目录**：`BiliNote-CLI/`

### 入口与构建

`src/cli.py` 是唯一的 CLI 入口（`bilinote` 命令），基于 argparse 实现子命令分发：`process`（生成笔记）、`search`（搜索视频）、`check`（环境诊断）、`config`（密钥管理）、`model-list` / `model-set-default`（模型管理）等。所有命令行参数在此文件中定义，业务逻辑通过调用 `NoteGenerator` 和 `AsyncBatchProcessor` 完成。

`pyproject.toml` 定义了项目元信息、依赖和入口点（`bilinote = "src.cli:main"`）。

### 核心业务层：services/

`src/app/services/note.py` — `NoteGenerator` 类，是整个笔记生成流程的门面（Facade）。它将工作拆分为两个阶段：`prepare()`（同步准备：下载+转写）和 `summarize_and_save()`（AI 处理+保存）。单任务时同步串行调用两者，批量时主线程串行 prepare、线程池并行 summarize。

`src/app/services/pipeline/preparer.py` — `TaskPreparer` 类，负责 prepare 阶段：选择下载器下载音频/字幕、选择转写器转写、构建 `PreparedTask` 数据对象传递给 AI 阶段。

`src/app/services/pipeline/ai_processor.py` — `AIProcessor` 类，负责 AI 阶段：通过 `GPTFactory` 获取模型实例，调用 `gpt.summarize()` 生成 Markdown，再经 `PostProcessor` 处理截图和链接插入，最终保存笔记文件。

`src/app/services/batch_processor.py` — `AsyncBatchProcessor`，批量任务调度，主线程串行准备 + 线程池并行 AI 处理。

`src/app/services/searcher.py` — 视频搜索逻辑（B站、YouTube），返回结构化搜索结果。

`src/app/services/postprocessing.py` — `PostProcessor`，笔记后处理，负责截图插入和视频跳转链接替换。

`src/app/services/cache/task_cache.py` — `TaskCache`，任务状态缓存与持久化。

`src/app/services/serial_executor.py` — 串行执行器，用于需要顺序处理的场景。

### 下载器层：downloaders/

`src/app/downloaders/base.py` — `Downloader` 抽象基类，定义 `download()`（下载音频）、`download_video()`（下载视频）、`download_subtitles()`（获取平台字幕）三个核心接口。

具体实现按平台拆分：`bilibili_downloader.py`（B站，基于 bilibili-api-python）、`youtube_downloader.py`（YouTube，基于 yt-dlp）、`douyin_downloader.py`（抖音，含 `douyin_helper/abogus.py` 反爬辅助）、`kuaishou_downloader.py`（快手）、`xiaoyuzhoufm_download.py`（小宇宙播客）、`local_downloader.py`（本地文件）。`common.py` 存放下载器共用逻辑。

### 转写器层：transcriber/

`src/app/transcriber/base.py` — `Transcriber` 抽象基类，定义 `transcript(file_path) -> TranscriptResult` 接口。

`src/app/transcriber/transcriber_provider.py` — 转写器工厂与回退策略（`get_transcriber_with_fallback()`），是 prepare 阶段选择转写器的入口。

具体实现：`bcut.py`（必剪云转写）、`groq.py`（Groq Whisper API）、`whisper_cpp.py`（本地 whisper.cpp）、`kuaishou.py`（快手字幕）。

### GPT 层：gpt/

`src/app/gpt/base.py` — `GPT` 抽象基类，定义 `summarize(source: GPTSource) -> str` 接口。

`src/app/gpt/gpt_factory.py` — `GPTFactory`，根据模型名创建对应的 GPT 实例。

`src/app/gpt/provider/OpenAI_compatible_provider.py` — OpenAI 兼容协议的统一实现，支持 DeepSeek、Qwen、Claude、Gemini、Ollama 等所有 OpenAI 兼容 API，含 `test_connection()` 静态方法用于连通性检测。

`src/app/gpt/prompt.py` / `prompt_builder.py` — Prompt 模板和动态构建逻辑，根据笔记风格参数（academic、tutorial、xiaohongshu 等）组装 system prompt。

`src/app/gpt/universal_gpt.py` — 通用 GPT 封装，处理长文本分块（配合 `request_chunker.py`）和多段合并。

`src/app/gpt/utils.py` — GPT 相关工具函数。

### 模型层：models/

所有 Pydantic 数据模型集中于此：`process_config.py`（`ProcessConfig`，CLI 参数映射）、`pipeline_model.py`（`PreparedTask`，prepare→AI 阶段的中间数据）、`notes_model.py`（`NoteResult`、`AudioDownloadResult`）、`gpt_model.py`（`GPTSource`，喂给 GPT 的结构化输入）、`transcriber_model.py`（`TranscriptResult`）、`video_record.py`、`audio_model.py`、`model_config.py`（`ModelConfig`）、`provide_model.py`。

### 配置与密钥

`src/config/` — 配置管理目录。`model_config_manager.py` 管理模型配置（API Key、base_url、模型名的映射），读取 `models.json`（内置模型定义）和用户自定义模型。`transcriber.json` 定义转写器配置。`config.yaml.example` 是用户配置模板。

`src/app/config_manager.py` — `ConfigManager`，管理 `~/.bilinote/config.yaml` 中的非敏感配置（输出目录、默认转写器等）。

`src/app/secret_manager.py` — 密钥管理，基于系统 keyring 存储 API Key 和 Cookie，提供 `set_secret` / `get_secret` / `delete_secret` / `list_known_keys` / `get_configured_keys` 等函数。

### 工具层：utils/

`src/app/utils/url_parser.py` — URL 解析，`detect_platform()` 自动识别平台、`extract_video_id()` 提取视频 ID。
`src/app/utils/path_helper.py` — `PathManager`，统一管理所有文件路径（`~/.bilinote/data/` 下的 downloads、cache、output、state 等）。
`src/app/utils/video_helper.py` — 视频处理辅助（帧截取等）。
`src/app/utils/video_reader.py` — 视频多模态读取（抽帧生成缩略图网格）。
`src/app/utils/cookie_helper.py` — Cookie 校验辅助（B站 Cookie 有效性检查）。
`src/app/utils/note_helper.py` — 笔记内容辅助（插入来源链接、视频元信息、热评等）。
`src/app/utils/screenshot_marker.py` — 截图标记处理。
`src/app/utils/bilibili_meta.py` — B站元数据获取与文件名清理。
`src/app/utils/env_checker.py` — 环境检查。
`src/app/utils/file_cleanup.py` — 临时文件清理。
`src/app/utils/logger.py` — 统一日志配置。
`src/app/utils/status_code.py` — 状态码定义。

### 其他辅助模块

`src/app/enmus/` — 枚举定义：`task_status_enums.py`（`TaskStatus`）、`note_enums.py`（`DownloadQuality`）、`exception.py`（错误码）。
`src/app/exceptions/` — 自定义异常：`biz_exception.py`（业务异常基类）、`note.py`、`provider.py`。
`src/app/validators/` — 输入校验：`video_url_validator.py`。
`src/app/decorators/` — 装饰器：`timeit.py`（计时）。
`src/ffmpeg_helper.py` — FFmpeg 检测与调用封装。

### 测试

`tests/` 目录结构与 `src/app/` 对应。`conftest.py` 定义全局 fixture。`unit/` 下按模块分目录存放单元测试（downloaders、gpt、utils、services、transcriber），`integration/` 存放集成测试。

### 运行时数据目录

用户运行时数据存放在 `~/.bilinote/` 下：`config.yaml`（用户配置）、`config/models.json`（用户自定义模型）、`data/downloads/`（音频缓存）、`data/cache/`（转写缓存）、`data/output/notes/`（生成的笔记）、`data/state/`（任务状态）、`logs/`（日志）。
