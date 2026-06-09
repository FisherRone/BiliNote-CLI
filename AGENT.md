# AGENT.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

# Project-associated Notes

1. 本项目由 UV 管理。
2. 本项目的根目录为 /Users/rongziyu/Documents/📝projects/BiliNote/BiliNote-CLI，所有操作需在此目录内运行。

## uv 操作

安装包：uv add


### 运行临时 Python 代码
```bash
uv run python -c "print('import yt_dlp;Hello from uv')"
```

## 查看文档
| 方法 | 能否执行 | 经验 |
|------|---------|------|
| `help()` / `dir()` | ✅ 可执行 | 对 yt-dlp 这类大库，`help()` 输出太长不实用；`dir()` 列方法名还行，但看不出参数含义 |
| `inspect.getsource()` | ✅ **最实用** | 直接看源码，能精确找到参数定义和行为逻辑，比任何文档都准 |
| `__doc__` | ✅ 可执行 | yt-dlp 的模块级 `__doc__` 为空，类级文档也不完整，价值有限 |
| `__file__` | ✅ 可执行 | 能定位安装路径，方便进一步看源码文件 |
| `pydoc` 本地服务 | ✅ 可执行 | 但不如 `inspect.getsource()` 直接，且需要开浏览器 |
| `pip show` / `uv pip show` | ✅ 可执行 | 能拿到 Home-page，但 yt-dlp 的文档主要在 GitHub README |
| WebSearch | ✅ 可执行 | 找官方 README 和第三方翻译文档很快，但信息可能过时或不完整 |

**结论**：对于 Python 库的参数确认，**`inspect.getsource()` + 正则搜索** 是最高效的方式，比查文档更准确。WebSearch 适合找概述和用法示例。
