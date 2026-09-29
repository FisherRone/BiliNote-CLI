# Changelog

## [Unreleased]
### Added
- 支持在 config.yaml 中配置默认笔记保存目录（`output.default_dir`），永久生效。

### Fixed
- 修复 B 站笔记落盘绕过 `--output-dir`/批次目录的问题：落盘目录现在始终跟随用户指定（未指定才用默认目录），B 站友好命名"{标题} - {UP主} - {BV号}.md"只决定文件名（长标题/UP主名自动截断，BV号保留在末尾）。
- 笔记写盘点收敛到 AIProcessor 单处：`process` 单任务不再写入两份相同文件，CLI"保存到"提示显示真实落盘路径（`NoteResult.output_path`）。
- 修复 `process` 单任务成功路径因 `print_success` 未导入而误报错误并 exit(1) 的问题；新增 CLI 冒烟测试防止回归。
- 修复 `note_helper.replace_content_markers` 中 merge 残留导致的 UnboundLocalError（B站时间戳链接替换必崩）。
- 清理抖音下载器调试输出（含 Cookie/msToken 的请求头与完整响应打印）；修复异常消息为元组的问题。
- 补齐抖音/快手/本地下载器的 `skip_download` 参数，"已有字幕不下载"优化对这三个平台恢复生效。
- 修复 bilibili 下载器异常路径下 cookie 临时文件泄漏（含登录态文件残留磁盘）的问题。
- 日志目录由 macOS 专属的 `~/Library/Logs/bilinote-cli` 统一迁移至 `~/.bilinote/logs`（跨平台一致）。

### Changed
- 引入 ruff（E/F/W）并完成首轮清理；CI 新增 lint 步骤。
- 集成测试改为显式 pytest `integration` marker（CI 用 `-m "not integration"` 排除）。
- `enmus` 目录更名为 `enums`，`UNKNOW_ERROR` 拼写修正。
- 数量/时长格式化函数收敛至 `cli/console.py`，消除与 search 命令的重复实现。

### Removed
- 删除被合并操作意外恢复的遗留入口 `src/cli.py`（与 `app.cli` 包重复且已损坏）。
- 删除死代码：`services/serial_executor.py`、`utils/status_code.py`、`gpt/utils.py`、空的 `models/video_record.py`。
- 清理各转写器/下载器中的调试 print 残留。
- 移除过时文档 `dev-docs/发布到 githubTODO.md`。

## [0.1.4] - 2026-06-15
### Add
- bilinote check 命令加入 cookie 有效性检查的功能。
### Fixed
- 解决在某些沙箱环境下 log 目录不可访问导致的报错。

## [0.1.3] - 2026-05-19
### Changed
- search 指令改为输出 json 文件，由 process 指令对 json 文件中的视频链接进行批量处理。

## [0.1.2] - 2026-05-17
### Changed
- search 指令后的批量记笔记功能，支持并行处理

## [0.1.1] - 2026-05-15
### Added
- 首次发布至 PyPI
