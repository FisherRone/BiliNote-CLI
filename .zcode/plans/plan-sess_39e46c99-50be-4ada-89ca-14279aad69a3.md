# Obsidian 格式笔记生成（后处理"挂件"方案）

## 核心设计

Obsidian 格式做成**落盘前的格式化挂件**，与现有提示词体系完全解耦：

- **提示词零改动**：BASE_PROMPT、9 种 --style、--format(screenshot/link)、--extras 照常工作，LLM 只负责生成正文。
- **frontmatter 由代码确定性构建**（不让 LLM 生成）：从视频元数据按平台归一化取值，用 `yaml.safe_dump(allow_unicode=True, sort_keys=False)` 保证合法转义。
- **`# 标题` 规范化在代码里做**：去掉 LLM 可能输出的首个一级标题，统一在其后插入 `# {title}`。

输出结构（与你示例一致 + 建议的附加字段）：

```markdown
---
title: 没人告诉你的二十几岁那些事
author: 莫莉的TED演讲精选
description: ...
data: 7520 播放 · 245 点赞
tags:
  - TED
  - 自我成长
source: https://www.bilibili.com/video/BVxxx
platform: bilibili
created: 2026-10-01
---
# 没人告诉你的二十几岁那些事

（LLM 正文，## 级小节，screenshot/link 标记替换照常）
```

## 默认取值（刚才未确认的问题，按推荐执行）

1. **小红书**：本次仅做格式层平台兼容（元数据"有什么填什么"），小红书下载器是独立任务不在本次范围。
2. **tags 来源**：用平台自带标签（bilibili/douyin/kuaishou/youtube 的 raw_info.tags），纯后处理。
3. **文件命名**：顺便统一全平台为 `标题[:50] - 作者[:20] - 视频ID.md`（作者缺失则回退 `标题 - ID`），复用 `bilibili_meta.sanitize_filename`；解决抖音/快手当前 `{数字ID}.md` 在 Obsidian 里不可读的问题。
4. **frontmatter 字段**：示例字段 + platform + created（利于多平台库 dataview 检索）；`data` 键名保持与示例一致（统计串 "7520 播放 · 245 点赞"）。

## 改动清单

### 新增 `src/app/formatters/` 包
- `video_meta.py`：`CanonicalVideoMeta` dataclass + `build_video_meta(prepared)`。平台归一化：bilibili（yt-dlp 全量：uploader/description/播放点赞投币收藏分享）→ douyin（item_title 当 description、tags，无作者）→ kuaishou（caption、tags）→ youtube（title、tags）→ local（仅 title）。tags 兼容 str 和 {tag|title} dict 两种形态（复用 note_helper 现有逻辑）。
- `obsidian.py`：`ObsidianFormatter.decorate(markdown, prepared)` → frontmatter + `# {title}` + 正文；description 截断 200 字、拍平换行；无一级标题则补、有则替换。
- `markdown.py`：`MarkdownFormatter.decorate` = 现有 `prepend_source_link` + `prepend_video_meta` 逻辑原样迁入（默认输出行为不变）。
- `__init__.py`：`NoteFormatter` 协议 + `get_formatter(note_format)` 注册表。

### 修改
- `src/app/models/process_config.py`：加 `note_format: str = "markdown"`。
- `src/app/models/pipeline_model.py`：`PreparedTask` 加 `note_format: str = "markdown"`。
- `src/app/services/pipeline/preparer.py`：构建 PreparedTask 时传入 `note_format=cfg.note_format`。
- `src/app/services/pipeline/ai_processor.py`：
  - `process()` 中把硬编码的 `prepend_source_link`/`prepend_video_meta` 两行替换为 `markdown = get_formatter(prepared.note_format).decorate(markdown, prepared)`；截图/链接标记替换、B 站热评追加逻辑不变。
  - `_resolve_output_path()`：命名规则从 B 站专属改为全平台统一（用 CanonicalVideoMeta），B 站产物文件名与现状完全一致。
- `src/app/cli/__init__.py`：process 子命令加 `--note-format`（choices: markdown/obsidian）。
- `src/app/cli/process_cmd.py`：优先级 CLI 参数 > config.yaml `output.note_format`（仿照 --output-dir 的现有覆盖模式）。
- `src/app/config/config.yaml.example`：加 `output.note_format: markdown`；**顺手修复已发现的 bug**——模板里 `output:` 键出现两次（default_dir 与 default_notes_dir 分属两个 output 块，YAML 后者覆盖前者导致 default_dir 实际读不到），合并为一个块。

### 测试
- 新增 `tests/unit/test_formatters_obsidian.py`：frontmatter 转义（标题含冒号/引号/换行）、各平台元数据降级（douyin 无作者、local 仅标题）、标题规范化、`data` 统计串格式。
- 新增/确认默认格式回归测试：markdown formatter 输出与改造前一致。

## 兼容性保证
- 默认（不加参数）输出 byte 级不变。
- `--style`/`--format`/`--extras`/`--screenshot`/`--link` 在 obsidian 模式下照常叠加。
- 批量 URL、`--json` 搜索结果、本地视频路径自动生效（同一落盘通道）。

## 明确不做
- 小红书平台下载器（后续独立任务，届时只需新增 downloader + SUPPORT_PLATFORM_MAP 注册 + url_parser 分支，格式层天然兼容）。
- LLM 生成语义标签（如后续需要，可通过 GPTSource.extras 通道以挂件方式追加，不影响本次架构）。

## 验证
1. `pytest tests/unit` 全绿。
2. 手动冒烟：`bilinote process <B站URL> --note-format obsidian -o /tmp/obsidian-test` 检查 frontmatter 与 `# 标题`；再跑一次不带参数对比默认输出无变化。