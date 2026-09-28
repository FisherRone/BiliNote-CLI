"""CLI 层打印辅助：分隔线、状态图标、笔记预览。

仅服务 cli 包；服务层的 print 收敛属 P2 范围。
"""

SEPARATOR_WIDTH = 60


def print_separator(char: str = "=", width: int = SEPARATOR_WIDTH,
                    before: bool = False, after: bool = False) -> None:
    """打印分隔线；before/after 控制前后空行"""
    if before:
        print()
    print(char * width)
    if after:
        print()


def print_success(message: str) -> None:
    print(f"✓ {message}")


def print_error(message: str) -> None:
    print(f"✗ {message}")


def print_note_preview(markdown: str, limit: int = 500) -> None:
    """打印笔记前 limit 字符预览"""
    print(markdown[:limit])
    if len(markdown) > limit:
        print("\n... (更多内容请查看文件)")
