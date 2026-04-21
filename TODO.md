
## 发布前待办清单

### 🔴 高优先级（阻塞发布）

#### 代码与功能
- [ ] **GitHub Actions 修复**：`.github/workflows/main.yml` 仍引用旧的前端路径（`BillNote_frontend`、`backend`），需要更新或移除

#### 文档
- [ ] **README 更新**：
  - [ ] 删除 "cd backend" 等旧路径引用
  - [ ] 更新输出目录说明（README 写的是 `note_results/`，实际是 `data/output/notes/`）
  - [ ] 添加安装方式：`pip install -e .` 或 `pip install -r src/requirements.txt`
  - [ ] 添加 CLI 入口点说明（`python -m src.cli` 或 `python src/cli.py`）
- [ ] **添加 CONTRIBUTING.md**：贡献指南
- [ ] **添加 CHANGELOG.md**：版本历史

#### 配置与打包
- [ ] **pyproject.toml 完善**：
  - [ ] 更新 `name`（`bilinote-master` → `bilinote`？）
  - [ ] 完善 `description`
  - [ ] 添加 `authors`、`license`、`keywords`、`classifiers`
  - [ ] 添加 CLI 入口点脚本（`[project.scripts]`）

### 🟡 中优先级（建议完成）

- [ ] **测试**：确认现有测试能通过 `pytest src/tests/`
- [ ] **类型检查**：添加 `mypy` 或类似工具配置
- [ ] **代码格式化**：添加 `black`、`ruff` 配置
- [ ] **Docker 支持**：更新 `docker-build.yml`（如需要）
- [ ] **Issue 模板检查**：确认 `.github/ISSUE_TEMPLATE/` 内容合适

### 🟢 低优先级（可选）

- [ ] **Logo 和徽章**：为 README 添加项目 logo
- [ ] **示例输出**：在 README 中添加生成的笔记示例
- [ ] **演示 GIF**：添加使用演示动画

---

## TODO

### LLM 配置
- [x] config：user_model 和 model 合并

### CLI
- [x] 自动识别 platform
- [x] 默认模型
- [x] 搜索功能，搜索后展示时长、播放量等。可批量记笔记。
- [x] 批量执行结果以新文件夹存储。
- [x] process 支持批量执行。
- [ ] 保存文件的文件名加入标题
- [ ] 搜索功能支持参数，如搜索多少条，搜索平台，搜索条件
- [ ] 搜索结果打印视觉效果优化
- [ ] 检查带图笔记的结果文件形式
- [x] 指定保存目录
- [ ] 指定默认转写器
- [ ] 当前进度未打印

### 扩展
- [ ] 小红书识图/视频/文本笔记。

### Agent
- [ ] 创建 skills
- [ ] 提供一键打开匹配识别结果文件的指令

### 性能
- [ ] 自动清理缓存
- [ ] 批处理：AI 生成部分并发。

1. AI生成并发是在任务级别还是阶段级别？
   - 方案A（推荐）：保持任务串行，但AI生成步骤使用异步/线程池并发调用API
   - 方案B：整体任务流水线化，多个任务的不同阶段并行（复杂度高）
2. 错误处理
   - 并发AI生成时，部分失败如何处理？
   - 是否需要重试机制？
3. 进度报告：当前打印的进度是实时的，并发后需要调整输出格式。（我没看到现在有进度条）
4. 并发数的配置。

### 测试
- [ ]  转写器 fallback
- [ ]  批量处理