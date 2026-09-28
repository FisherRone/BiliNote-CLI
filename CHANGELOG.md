# Changelog

## [Unreleased]
### Changed
- P1 清理与结构优化：清除死代码与 Web 后端遗留（BatchProcessor 同步类、validators 包、localhost:8483 封面上传逻辑等），移除零引用依赖 browser-cookie3。
- CLI 代码由 816 行单文件拆分为 `app.cli` 包（process/search/model/config/check/shortcut 各归其位）。
- 包布局正规化：wheel 仅打包 `app` 与 `config` 两个顶层包，移除 sys.path hack，入口改为 `app.cli:main`；本地视频封面改存本地路径。
- `get_model_config` 新增 `report_missing` 参数，model-list/check 不再依赖日志级别 hack。
- uv.lock 与 .python-version 纳入版本管理；untrack 本地 AI 笔记目录；重建 CI（uv + pytest + deptry，三平台矩阵）。

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
