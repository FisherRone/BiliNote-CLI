# Changelog

## [Unreleased]
### Added
- 支持在 config.yaml 中配置默认笔记保存目录（`output.default_dir`），永久生效。

### Fixed
- 修复 `process` 单任务成功路径因 `print_success` 未导入而误报错误并 exit(1) 的问题；新增 CLI 冒烟测试防止回归。
- 清理抖音下载器调试输出（含 Cookie/msToken 的请求头与完整响应打印）；修复异常消息为元组的问题。
- 补齐抖音/快手/本地下载器的 `skip_download` 参数，"已有字幕不下载"优化对这三个平台恢复生效。
- 日志目录由 macOS 专属的 `~/Library/Logs/bilinote-cli` 统一迁移至 `~/.bilinote/logs`（跨平台一致）。

### Removed
- 删除被合并操作意外恢复的遗留入口 `src/cli.py`（与 `app.cli` 包重复且已损坏）。
- 清理各转写器/下载器中的调试 print 残留。

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
