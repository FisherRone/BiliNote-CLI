# config.yaml 升级与变更注意事项

> 更新于 2026-10-02。回答两个问题：**从 PyPI 重装会不会动用户的本地配置？在 config.yaml 里加新变量后，老用户升级会发生什么？**

## 1. 机制：升级/重装不会碰用户配置

用户配置在 `~/.bilinote/config.yaml`（`app/config_manager.py` 的 `_get_config_path`），在包外；PyPI 安装只替换 site-packages 里的包文件（`config.yaml.example`、`transcriber.json`、`models.json`、代码），两者隔离。程序只有两条写盘路径，都安全：

- `ensure_default_config()`：每次 CLI 启动调用（`cli/__init__.py`），但有 `if not exists` 守卫，**只在文件缺失时创建**，永不覆盖；
- `ConfigManager.set()`：只在用户主动执行 `bilinote config set` 时写盘。

## 2. 分层合并：新变量自动有默认值

加载时深度合并（`ConfigManager._load`），优先级从低到高：

```
config.yaml.example（新版包里的模板）
  ← transcriber.json
  ← dev_config.json
  ← 用户 ~/.bilinote/config.yaml（最优先）
```

- **新增变量**：老用户的 config.yaml 没有该键 → 自动取新模板/代码里的默认值，无感升级；想改行为时自己往文件里补一行即可。
- **废弃变量**：老文件里遗留的键被静默忽略，无害。

## 3. 加新变量的纪律（改代码前必读）

1. **新键必须同时满足三件事**：写进 `config.yaml.example` 带默认值、代码用 `config.get(key, default)` 读取、`_load_default_config()` 能跑通。裸取 `config["key"]` 只允许出现在**程序自己完整构造的派生字典**上（如 `get_model_config` 返回的 dict，已有 None 守卫）。
2. **⚠️ 模板花括号陷阱**：`config.yaml.example` 每次加载都要过 `template.format(default_whisper_model_path=..., example_whisper_model_path=...)`（`config_manager.py` 的 `_get_default_config`）。模板里出现任何**其他** `{xxx}` 占位符或游离的 `{` `}`（如想举例 JSON/dict 字面量），启动即 `KeyError`/`ValueError`，**所有命令全挂**。要写花括号示例只能写进代码注释或转义（`{{` `}}`）。改完模板跑一遍验证：
   ```bash
   PYTHONPATH=src .venv/bin/python -c "from app.config_manager import _load_default_config; _load_default_config()"
   ```
3. **禁止"改名"式变更**（旧键 → 新键）：合并机制不迁移，老用户的旧值会被静默忽略、行为悄悄改变。确需改名，在 `_load` 里加迁移逻辑（读到旧键映射到新键）并在 CHANGELOG 标注。
4. **`config set` 会重写整个 config.yaml**（`yaml.dump`），手写的注释和排版会在那一刻丢失——这是既有行为，向用户答疑时注意区分"重装"（不动文件）和"`config set`"（重写文件）。

## 4. 审计结果（2026-10-02）

代码侧执行情况良好：

- ✅ 所有用户配置读取点均走 `ConfigManager.get(key, default)` / `config.get(...)`，无裸取键；
- ✅ `get_model_config` 返回 None 的路径在 `ai_processor._get_gpt`（raise + 明确报错）和 `check_cmd`（skip）都有守卫；
- ✅ 模板 `format()` 实测通过，合并加载实测通过；
- ✅ 近期新增的 `output.default_dir`、`output.note_format` 均已进模板，且读取点带默认值（note_format 的 None 回退已由 46ac90a 修复）。

模板与代码的同步缺口（✅ 已于 2026-10-02 修复：四个键补进模板、死键移除，模板 format() 与全量单测验证通过）：

| 键 | 代码读取点 | 代码默认值 | 处理 |
| --- | --- | --- | --- |
| `gpt_client.token_threshold` | `gpt/universal_gpt.py:29` | 0.8 | ✅ 已补进模板 |
| `gpt_client.chunk_history_n` | `gpt/universal_gpt.py:30` | 3 | ✅ 已补进模板 |
| `fallback_priority` | `config_manager.py:273` | `["bcut","kuaishou","whisper-cpp","groq"]` | ✅ 已补进模板 |
| `image_base_url` | `services/note.py:22` | `/static/screenshots` | ✅ 已补进模板（CLI 下截图链接前缀） |
| `transcriber.whisper_model_size` | **无任何读取点**（faster-whisper 移除后的遗留） | — | ✅ 已从模板删除 |

注意：用户自己的 `~/.bilinote/config.yaml` 若手写过 `whisper_model_size`，会随用户层透传进合并结果——无害（代码不读），属设计行为，不必清理。
