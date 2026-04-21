
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
