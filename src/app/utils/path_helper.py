import os
import sys
from pathlib import Path

# 源代码项目根目录（始终指向源码位置，只读）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

# 用户数据根目录
_BILINOTE_HOME = os.path.join(os.path.expanduser("~"), ".bilinote")


def _get_hf_cache_dir() -> str:
    """获取 HuggingFace 模型缓存目录
    
    优先级：HF_HOME > HF_CACHE_HOME > 默认路径
    参考 HuggingFace 官方文档：https://huggingface.co/docs/huggingface_hub/guides/manage-cache
    """
    # 优先级 1: HF_HOME 环境变量
    hf_home = os.getenv("HF_HOME")
    if hf_home:
        return os.path.join(hf_home, "hub")
    
    # 优先级 2: HF_CACHE_HOME 环境变量
    hf_cache_home = os.getenv("HF_CACHE_HOME")
    if hf_cache_home:
        return os.path.join(hf_cache_home, "hub")
    
    # 优先级 3: 默认路径
    return os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")


class PathManager:
    """
    统一管理项目目录结构

    用户数据目录 ~/.bilinote/:
    ├── data/
    │   ├── downloads/          # 原始音视频（转录后可删除）
    │   ├── cache/              # 中间产物（保留）
    │   │   ├── transcript/
    │   │   └── audio_meta/
    │   ├── output/             # 最终成果（永久保留）
    │   │   └── notes/
    │   ├── temp/               # 临时文件（处理中，崩溃后残留）
    │   ├── state/              # 任务状态
    │   └── resources/          # 资源文件（字体等）
    ├── config/                 # 用户可写配置（模型等）
    └── logs/

    只读目录（随源码分发）:
    ├── src/config/             # 内置配置
    ~/.cache/huggingface/hub/   # ML 模型缓存（HuggingFace 标准）
    """

    def __init__(self):
        # 数据根目录
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = _BILINOTE_HOME

        # 数据目录
        self.data_dir = self._ensure_dir(os.path.join(self.base_dir, "data"))

        # 定义所有目录（都在 data/ 下）
        self.downloads_dir = self._ensure_dir(os.path.join(self.data_dir, "downloads"))
        self.cache_dir = self._ensure_dir(os.path.join(self.data_dir, "cache"))
        self.cache_transcript_dir = self._ensure_dir(os.path.join(self.cache_dir, "transcript"))
        self.cache_audio_meta_dir = self._ensure_dir(os.path.join(self.cache_dir, "audio_meta"))
        self.output_dir = self._ensure_dir(os.path.join(self.data_dir, "output"))
        self.output_notes_dir = self._ensure_dir(os.path.join(self.output_dir, "notes"))
        self.temp_dir = self._ensure_dir(os.path.join(self.data_dir, "temp"))
        self.state_dir = self._ensure_dir(os.path.join(self.data_dir, "state"))
        self.resources_dir = self._ensure_dir(os.path.join(self.data_dir, "resources"))

        # 日志目录
        self.logs_dir = self._ensure_dir(os.path.join(self.base_dir, "logs"))

        # 用户可写配置目录
        self.user_config_dir = self._ensure_dir(os.path.join(self.base_dir, "config"))

        # 用户配置文件
        self.config_yaml_path = os.path.join(self.base_dir, "config.yaml")

        # 内置配置目录（只读，随源码分发）
        self.config_dir = os.path.join(_PROJECT_ROOT, "src", "config")

        # 模型目录（HuggingFace 标准缓存）
        self.models_dir = _get_hf_cache_dir()
    
    @staticmethod
    def _ensure_dir(path: str) -> str:
        """确保目录存在并返回路径"""
        os.makedirs(path, exist_ok=True)
        return path
    
    def get_download_path(self, task_id: str, ext: str = ".mp3") -> str:
        """获取下载文件路径"""
        return os.path.join(self.downloads_dir, f"{task_id}{ext}")
    
    def get_transcript_cache_path(self, task_id: str) -> str:
        """获取转写缓存路径"""
        return os.path.join(self.cache_transcript_dir, f"{task_id}_transcript.json")
    
    def get_audio_meta_cache_path(self, task_id: str) -> str:
        """获取音频元信息缓存路径"""
        return os.path.join(self.cache_audio_meta_dir, f"{task_id}_audio.json")
    
    def get_note_output_path(self, task_id: str, ext: str = ".md") -> str:
        """获取笔记输出路径"""
        return os.path.join(self.output_notes_dir, f"{task_id}{ext}")
    
    def get_temp_dir(self, task_id: str, subdir: str = "") -> str:
        """获取临时目录"""
        if subdir:
            path = os.path.join(self.temp_dir, f"{task_id}_{subdir}")
        else:
            path = os.path.join(self.temp_dir, task_id)
        return self._ensure_dir(path)
    
    def get_state_file_path(self, task_id: str) -> str:
        """获取状态文件路径"""
        return os.path.join(self.state_dir, f"{task_id}.status.json")
    
    def get_metadata_file_path(self, task_id: str) -> str:
        """获取元数据文件路径"""
        return os.path.join(self.cache_dir, f"{task_id}_metadata.json")
    
    def get_gpt_checkpoint_path(self, task_id: str) -> str:
        """获取 GPT 检查点路径"""
        return os.path.join(self.cache_dir, f"{task_id}.gpt.checkpoint.json")
    
    def get_model_dir(self, subdir: str = "whisper") -> str:
        """获取模型目录"""
        path = os.path.join(self.models_dir, subdir)
        return self._ensure_dir(path)



# 全局单例
_path_manager = None

def get_path_manager() -> PathManager:
    """获取全局 PathManager 单例"""
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
    return _path_manager


