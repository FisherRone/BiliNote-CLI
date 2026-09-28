"""模型管理子命令：列表 / 设置默认 / 删除"""

from config.model_config_manager import (
    get_default_model,
    get_model_config,
    list_available_models,
    remove_model,
    set_default_model,
)

from .console import print_separator


def list_models():
    """列出所有已配置的模型"""
    models = list_available_models()
    default_model = get_default_model()
    print(f"\n已配置的模型 ({len(models)} 个):")
    print_separator("-")
    for model_id in models:
        config = get_model_config(model_id, report_missing=False)
        is_default = model_id == default_model
        marker = "★" if is_default else "✓"
        default_tag = " (默认)" if is_default else ""
        if config:
            print(f"  {marker} {model_id:20s} -> {config['model_name']}{default_tag}")
        else:
            print(f"  {marker} {model_id:20s} (未配置 API Key){default_tag}")
    print()


def set_default_model_cli(model_id: str):
    """通过 CLI 设置默认模型"""
    if set_default_model(model_id):
        print(f"\n✓ 已设置默认模型: {model_id}")
    else:
        print(f"\n✗ 设置默认模型失败: {model_id}")
    print()


def remove_model_cli(model_id: str):
    """通过 CLI 删除模型"""
    if remove_model(model_id):
        print(f"\n✓ 已删除模型: {model_id}")
    else:
        print(f"\n✗ 删除模型失败: {model_id}")
    print()
