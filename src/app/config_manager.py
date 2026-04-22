"""
配置管理器
使用 YAML 文件管理非敏感配置，存储在 ~/.bilinote/config.yaml
同时加载 transcriber.json 作为转写器默认配置
"""
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any, Optional, Dict, List

import yaml

logger = logging.getLogger(__name__)

# 转写器类型列表（用于注释说明）
_TRANSCRIBER_TYPES = ["groq", "bcut", "kuaishou", "fast-whisper", "mlx-whisper", "whisper-cpp"]


def _get_config_example_path() -> Path:
    """获取 config.yaml.example 模板文件路径"""
    # 从当前文件位置推导: app/config_manager.py -> src/config/config.yaml.example
    base_dir = Path(__file__).parent.parent
    return base_dir / "config" / "config.yaml.example"


def _get_default_config() -> str:
    """根据操作系统读取配置模板并填充占位符"""
    example_path = _get_config_example_path()
    if not example_path.exists():
        raise FileNotFoundError(f"配置文件模板不存在: {example_path}")

    template = example_path.read_text(encoding="utf-8")

    # 根据操作系统确定占位符值
    system = platform.system()
    if system == "Darwin":  # macOS
        default_transcriber = "mlx-whisper"
    else:
        default_transcriber = "fast-whisper"

    # macOS 默认 whisper 模型路径
    if system == "Darwin":
        default_whisper_model_path = str(Path.home() / "whisper-models" / "ggml-base.bin")
    else:
        default_whisper_model_path = ""

    # 填充占位符
    return template.format(
        default_transcriber=default_transcriber,
        default_whisper_model_path=default_whisper_model_path,
        example_whisper_model_path="~/whisper-models/ggml-base.bin",
    )


def _get_config_path() -> Path:
    """获取配置文件路径"""
    bilinote_home = Path.home() / ".bilinote"
    return bilinote_home / "config.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并字典，override 覆盖 base"""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _get_by_path(data: dict, path: str, default: Any = None) -> Any:
    """通过点号路径获取嵌套字典值，如 'models.openai.base_url'"""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _set_by_path(data: dict, path: str, value: Any) -> dict:
    """通过点号路径设置嵌套字典值"""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return data


def _load_default_config() -> dict:
    """加载默认配置"""
    return yaml.safe_load(_get_default_config())


def _get_transcriber_json_path() -> Path:
    """获取 transcriber.json 路径"""
    # 从当前文件位置推导: app/config_manager.py -> src/config/transcriber.json
    base_dir = Path(__file__).parent.parent
    return base_dir / "config" / "transcriber.json"


def _load_transcriber_defaults() -> dict:
    """加载 transcriber.json 作为默认配置"""
    path = _get_transcriber_json_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载 transcriber.json 失败: {e}")
        return {}


def _get_dev_config_json_path() -> Path:
    """获取 dev_config.json 路径"""
    base_dir = Path(__file__).parent.parent
    return base_dir / "config" / "dev_config.json"


def _load_dev_config_defaults() -> dict:
    """加载 dev_config.json 作为开发者默认配置"""
    path = _get_dev_config_json_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载 dev_config.json 失败: {e}")
        return {}


class ConfigManager:
    """YAML 配置管理器，单例模式"""

    _instance: Optional["ConfigManager"] = None

    def __init__(self):
        self._config_path = _get_config_path()
        self._config: Optional[dict] = None

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> dict:
        """加载配置文件，与默认配置合并（优先级：config.yaml > dev_config.json > transcriber.json > 代码默认值）"""
        # 1. 代码默认配置
        defaults = _load_default_config()
        # 2. transcriber.json 覆盖
        transcriber_defaults = _load_transcriber_defaults()
        defaults = _deep_merge(defaults, transcriber_defaults)
        # 3. dev_config.json 开发者配置覆盖
        dev_defaults = _load_dev_config_defaults()
        defaults = _deep_merge(defaults, dev_defaults)
        # 4. 用户 config.yaml 覆盖
        if not self._config_path.exists():
            return defaults
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            return _deep_merge(defaults, user_config)
        except Exception as e:
            logger.error(f"加载配置文件失败 {self._config_path}: {e}")
            return defaults

    def get_config(self) -> dict:
        """获取完整配置"""
        if self._config is None:
            self._config = self._load()
        return dict(self._config)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项，优先级：
        1. 系统环境变量（最高优先级，兼容 CI/CD）
        2. config.yaml 用户配置
        3. 默认值
        """
        # 系统环境变量优先
        env_key = key.upper().replace(".", "_")
        env_val = os.getenv(env_key)
        if env_val is not None:
            # 尝试类型转换
            if default is not None:
                try:
                    if isinstance(default, int):
                        return int(env_val)
                    elif isinstance(default, float):
                        return float(env_val)
                    elif isinstance(default, bool):
                        return env_val.lower() in ("true", "1", "yes")
                except (ValueError, TypeError):
                    pass
            return env_val

        # config.yaml 回退
        config = self.get_config()
        return _get_by_path(config, key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置项并保存到文件"""
        # 加载当前文件内容（不含默认值）
        file_config: dict = {}
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}
            except Exception:
                file_config = {}

        # 设置值
        _set_by_path(file_config, key, value)

        # 保存
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(file_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # 清除缓存
        self._config = None
        logger.info(f"已设置配置项: {key}")

    def ensure_default_config(self) -> None:
        """首次运行时创建默认配置文件（根据操作系统选择不同配置）"""
        if not self._config_path.exists():
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                f.write(_get_default_config())
            system = platform.system()
            logger.info(f"已创建默认配置文件 ({system}): {self._config_path}")

    def reload(self) -> None:
        """重新加载配置"""
        self._config = None

    # ========== 转写器配置相关方法（从 TranscriberConfigManager 合并）==========

    def get_transcriber_config(self, transcriber_type: str) -> Dict[str, Any]:
        """获取指定转写器的配置，支持环境变量覆盖"""
        config = self.get_config()
        transcriber_config = config.get("transcribers", {}).get(transcriber_type, {})
        
        # 环境变量覆盖 → config.yaml 覆盖
        if transcriber_type == "fast-whisper":
            transcriber_config["model_size"] = self.get(
                "transcriber.whisper_model_size",
                transcriber_config.get("model_size", "base")
            )
            transcriber_config["device"] = transcriber_config.get("device", "cpu")
        elif transcriber_type == "groq":
            from app.secret_manager import get_secret
            transcriber_config["api_key"] = get_secret("GROQ_API_KEY") or transcriber_config.get("api_key")
            transcriber_config["base_url"] = self.get(
                "models.groq.base_url",
                transcriber_config.get("base_url")
            )
            transcriber_config["model"] = self.get(
                "transcriber.groq_model",
                transcriber_config.get("model")
            )
        elif transcriber_type == "mlx-whisper":
            transcriber_config["model_size"] = self.get(
                "transcriber.whisper_model_size",
                transcriber_config.get("model_size", "base")
            )
        elif transcriber_type == "whisper-cpp":
            cli_path = self.get(
                "transcriber.whisper-cpp.cli_path",
                transcriber_config.get("cli_path", "whisper-cli")
            )
            # cli_path 为空字符串时回退到 whisper-cli
            transcriber_config["cli_path"] = cli_path or "whisper-cli"
            transcriber_config["model_path"] = self.get(
                "transcriber.whisper-cpp.model_path",
                transcriber_config.get("model_path", "")
            )

        return transcriber_config

    def get_fallback_priority(self) -> List[str]:
        """获取 fallback 优先级列表"""
        config = self.get_config()
        return config.get("fallback_priority", ["groq", "bcut", "kuaishou", "fast-whisper", "mlx-whisper"])

    def get_default_transcriber(self) -> str:
        """获取默认转写器类型"""
        return self.get("transcriber.default_type", "fast-whisper")

    def is_transcriber_enabled(self, transcriber_type: str) -> bool:
        """检查转写器是否启用"""
        config = self.get_transcriber_config(transcriber_type)
        return config.get("enabled", True)


def get_config_manager() -> ConfigManager:
    """获取全局 ConfigManager 单例"""
    return ConfigManager.get_instance()
