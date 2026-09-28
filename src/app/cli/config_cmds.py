"""config 子命令：密钥（keyring）与非敏感配置（config.yaml）管理"""


def config_cli(args):
    """配置管理命令"""
    from app.secret_manager import (
        set_secret, get_secret, delete_secret,
        list_known_keys, get_configured_keys, mask_value, KNOWN_KEYS,
    )
    from app.config_manager import get_config_manager

    if not args.config_action:
        print('请指定配置操作: set, get, delete, list')
        print('示例: bilinote config set DEEPSEEK_API_KEY sk-xxx')
        return

    if args.config_action == 'set':
        key = args.key
        value = args.value
        if key in KNOWN_KEYS:
            # 密钥类 key → keyring
            set_secret(key, value)
            print(f"✓ 已设置密钥: {key}")
        else:
            # 非密钥 key → config.yaml
            config_mgr = get_config_manager()
            config_mgr.set(key, value)
            print(f"✓ 已设置配置: {key}")

    elif args.config_action == 'get':
        key = args.key
        if key in KNOWN_KEYS:
            value = get_secret(key)
            if value:
                print(f"{key} = {mask_value(value)}")
            else:
                print(f"✗ 密钥 {key} 未配置")
        else:
            config_mgr = get_config_manager()
            value = config_mgr.get(key)
            if value is not None and value != "":
                print(f"{key} = {value}")
            else:
                print(f"✗ 配置 {key} 未设置")

    elif args.config_action == 'delete':
        key = args.key
        if key in KNOWN_KEYS:
            if delete_secret(key):
                print(f"✓ 已删除密钥: {key}")
            else:
                print(f"✗ 密钥 {key} 不存在或删除失败")
        else:
            # 从 config.yaml 中删除（设为空字符串）
            config_mgr = get_config_manager()
            config_mgr.set(key, "")
            print(f"✓ 已清除配置: {key}")

    elif args.config_action == 'list':
        known = list_known_keys()
        configured = get_configured_keys()
        print(f"\n密钥配置状态 ({len(configured)}/{len(known)} 已配置):\n")
        for key, desc in known.items():
            status = "✓ 已配置" if key in configured else "✗ 未配置"
            print(f"  {status}  {key:25s}  {desc}")

        # 展示 YAML 配置项
        config_mgr = get_config_manager()
        notes_dir = config_mgr.get("output.default_notes_dir", "")
        notes_status = f"✓ {notes_dir}" if notes_dir else "✗ 未设置（使用默认路径）"
        print(f"\n输出配置:\n")
        print(f"  {notes_status}  output.default_notes_dir   自定义笔记输出目录")
        print(f"\n使用 bilinote config set <KEY> <VALUE> 设置密钥或配置")
