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


def format_count(n) -> str | None:
    """格式化数量，使用中文单位（无、k、w），最多3位有效数字"""
    if n is None:
        return None
    if n >= 10000:
        w = n / 10000
        # 万位数值 >=1000 时 %.3g 会退化为科学计数法（如 2.04e+03w），改用整数
        if w >= 100:
            return f"{w:.0f}w"
        return f"{w:.3g}w"
    if n >= 1000:
        return f"{n / 1000:.3g}k"
    return str(n)


def format_duration(seconds) -> str | None:
    """格式化视频时长，如 "1h30min", "7min", "45s"""
    if seconds is None:
        return None
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return None

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        if minutes > 0:
            return f"{hours}h{minutes}min"
        return f"{hours}h"
    elif minutes > 0:
        return f"{minutes}min"
    else:
        return f"{secs}s"


def print_note_preview(markdown: str, limit: int = 500) -> None:
    """打印笔记前 limit 字符预览"""
    print(markdown[:limit])
    if len(markdown) > limit:
        print("\n... (更多内容请查看文件)")
