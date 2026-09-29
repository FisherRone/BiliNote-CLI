"""
模型配置管理器
双层配置：
- 内置模型（只读）：app/config/models.json，随源码分发
- 用户模型（可写）：~/.bilinote/config/models.json，用户手动编辑
运行时合并两层配置，用户配置覆盖内置同名模型。
配置延迟加载：import 本模块不读文件，首次访问配置的函数触发加载并缓存。
"""
import os
import json
from typing import Optional, Dict
from app.utils.logger import get_logger
from app.utils.path_helper import get_path_manager
from app.secret_manager import get_secret
from app.config_manager import get_config_manager

logger = get_logger(__name__)

# 内置配置文件路径（只读），数据文件随 app/config 包分发
_BUILTIN_CONFIG_DIR = os.path.dirname(__file__)
_BUILTIN_MODELS_FILE = os.path.join(_BUILTIN_CONFIG_DIR, "models.json")

# 双层配置缓存，经 _ensure_loaded() 初始化后供各函数读写
_models: Dict = {}
_default_model: str = ""
_loaded = False


def _ensure_loaded() -> None:
    """首次访问时加载并合并双层配置，之后走缓存"""
    global _loaded, _models, _default_model
    if _loaded:
        return
    _models, _default_model = load_model_config()
    _loaded = True


def _user_models_file() -> str:
    """用户模型配置文件路径"""
    return os.path.join(get_path_manager().user_config_dir, "models.json")


def _load_json(filepath: str) -> Dict:
    """从 JSON 文件加载模型配置"""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('models', {})
    except Exception as e:
        logger.error(f"加载模型配置文件失败 {filepath}: {e}")
        return {}


def _save_user_config(models: Dict):
    """保存用户模型配置到 ~/.bilinote/config/models.json"""
    filepath = _user_models_file()
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"models": models}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存用户模型配置失败 {filepath}: {e}")


def load_model_config() -> tuple[Dict, str]:
    """加载并合并双层模型配置
    内置配置为基础，用户配置覆盖同名模型。
    用户可通过 _removed 列表标记删除内置模型。
    默认模型从 config.yaml 读取。
    """
    builtin_models = _load_json(_BUILTIN_MODELS_FILE)
    user_models = _load_json(_user_models_file())

    # 合并：用户配置覆盖内置同名模型
    merged = {**builtin_models, **user_models}

    # 移除被用户标记删除的模型
    removed = merged.pop("_removed", [])
    for mid in removed:
        merged.pop(mid, None)

    # 默认模型从 config.yaml 读取，回退到内置配置
    config_mgr = get_config_manager()
    default_model = config_mgr.get("models.default_model", "deepseek-chat")

    return merged, default_model


def get_model_config(model_id: str, report_missing: bool = True) -> Optional[Dict]:
    """
    根据 model_id 获取模型配置

    从模型配置字典中查找配置，然后从环境变量读取 API Key

    :param model_id: 模型标识符（如 gpt-4o, deepseek-chat）
    :param report_missing: API Key 未配置时是否记录 warning（调用方自行报告状态时传 False）
    :return: 模型配置字典或 None
    """
    _ensure_loaded()
    model_id_lower = model_id.lower()

    # 查找模型配置
    if model_id_lower not in _models:
        logger.error(f"未知的模型: {model_id}，请在用户模型配置 {_user_models_file()} 或内置 models.json 中添加")
        return None

    template = _models[model_id_lower]
    api_key_env = template["api_key_env"]

    # 从 keyring 读取 API key
    api_key = get_secret(api_key_env)
    if not api_key:
        if report_missing:
            logger.warning(f"密钥 {api_key_env} 未设置，请使用 bilinote config set {api_key_env} <value> 设置")
        return None

    # 读取配置，优先使用 config.yaml 中的 base_url
    config_mgr = get_config_manager()
    # 从 api_key_env 推导 provider 名称（如 OPENAI_API_KEY → openai）
    provider = api_key_env.replace("_API_KEY", "").lower()
    config_base_url = config_mgr.get(f"models.{provider}.base_url")
    base_url = config_base_url or template["base_url"]
    model_name = template["model_name"]

    logger.info(f"使用模型配置: {model_id}")
    return {
        "model_id": model_id,
        "api_key": api_key,
        "base_url": base_url,
        "model_name": model_name
    }

def get_default_model() -> str:
    """获取默认模型"""
    _ensure_loaded()
    return _default_model


def set_default_model(model_id: str) -> bool:
    """
    设置默认模型（写入 config.yaml）

    :param model_id: 模型标识符
    :return: 是否设置成功
    """
    global _default_model

    _ensure_loaded()
    model_id_lower = model_id.lower()
    if model_id_lower not in _models:
        logger.error(f"无法设置默认模型：未知的模型 {model_id}")
        return False

    _default_model = model_id_lower
    # 写入 config.yaml
    config_mgr = get_config_manager()
    config_mgr.set("models.default_model", _default_model)
    logger.info(f"已设置默认模型: {model_id}")
    return True


def list_available_models() -> list:
    """列出所有已配置的模型（不检查 API Key）"""
    _ensure_loaded()
    return list(_models.keys())


def add_model(model_id: str, api_key_env: str, base_url: str, model_name: str):
    """
    添加模型配置（写入用户配置）

    :param model_id: 模型标识符（如 my-custom-model）
    :param api_key_env: API Key 环境变量名（如 MY_API_KEY）
    :param base_url: API 基础 URL
    :param model_name: 实际模型名称
    """
    _ensure_loaded()

    model_id_lower = model_id.lower()

    # 添加到模型配置
    _models[model_id_lower] = {
        "api_key_env": api_key_env,
        "base_url": base_url,
        "model_name": model_name
    }

    # 写入用户配置
    user_models = _load_json(_user_models_file())
    user_models[model_id_lower] = {
        "api_key_env": api_key_env,
        "base_url": base_url,
        "model_name": model_name
    }
    _save_user_config(user_models)

    logger.info(f"已添加模型配置: {model_id}")


def remove_model(model_id: str) -> bool:
    """
    删除模型配置

    :param model_id: 模型标识符
    :return: 是否删除成功
    """
    global _default_model

    _ensure_loaded()
    model_id_lower = model_id.lower()

    if model_id_lower not in _models:
        logger.error(f"无法删除模型：未知的模型 {model_id}")
        return False

    # 从内存中删除
    del _models[model_id_lower]

    # 如果删除的是默认模型，清空默认模型设置
    if _default_model == model_id_lower:
        _default_model = ""
        logger.info(f"默认模型 {model_id} 已被移除")

    # 从用户配置中删除并标记（避免内置模型合并后重新出现）
    user_models = _load_json(_user_models_file())
    user_models.pop(model_id_lower, None)
    if "_removed" not in user_models:
        user_models["_removed"] = []
    if model_id_lower not in user_models["_removed"]:
        user_models["_removed"].append(model_id_lower)
    _save_user_config(user_models)

    logger.info(f"已删除模型配置: {model_id}")
    return True
