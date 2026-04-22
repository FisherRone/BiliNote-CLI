
from enum import Enum
from typing import List, Set

from app.transcriber.base import Transcriber
from app.transcriber.groq import GroqTranscriber
from app.transcriber.bcut import BcutTranscriber
from app.transcriber.kuaishou import KuaishouTranscriber
from app.transcriber.whisper_cpp import WhisperCppTranscriber
from app.config_manager import get_config_manager
from app.utils.logger import get_logger
from app.models.transcriber_model import TranscriptResult

config_manager = get_config_manager()
logger = get_logger(__name__)

class TranscriberType(str, Enum):
    BCUT = "bcut"
    KUAISHOU = "kuaishou"
    GROQ = "groq"
    WHISPER_CPP = "whisper-cpp"

TRANSCRIBER_CLASSES = {
    TranscriberType.BCUT: BcutTranscriber,
    TranscriberType.KUAISHOU: KuaishouTranscriber,
    TranscriberType.GROQ: GroqTranscriber,
    TranscriberType.WHISPER_CPP: WhisperCppTranscriber,
}

UNAVAILABLE_TRANSCRIBERS: Set[TranscriberType] = set()


logger.info('初始化转录服务提供器')

# 转录器单例缓存
_transcribers = {
    TranscriberType.BCUT: None,
    TranscriberType.KUAISHOU: None,
    TranscriberType.GROQ: None,
    TranscriberType.WHISPER_CPP: None,
}

# 公共实例初始化函数
def _init_transcriber(key: TranscriberType, **kwargs):
    cls = TRANSCRIBER_CLASSES[key]
    if _transcribers[key] is None:
        logger.info(f'创建 {cls.__name__} 实例: {key}')
        try:
            _transcribers[key] = cls(**kwargs)
            logger.info(f'{cls.__name__} 创建成功')
        except Exception as e:
            logger.error(f"{cls.__name__} 创建失败: {e}")
            raise
    return _transcribers[key]


# 通用入口
def get_transcriber(transcriber_type: TranscriberType):
    """获取指定类型的转录器实例"""
    if transcriber_type not in TRANSCRIBER_CLASSES:
        raise ValueError(f"未知的转录器类型: {transcriber_type}")
    
    logger.info(f'请求转录器类型: {transcriber_type.value}')

    config = config_manager.get_transcriber_config(transcriber_type.value)
    
    # 构建参数
    kwargs = {}
    
    return _init_transcriber(transcriber_type, **kwargs)


def _get_fallback_order() -> List[TranscriberType]:
    """生成 fallback 顺序列表，优先使用用户指定的转写器"""
    # 从配置文件读取 fallback 优先级
    priority_list = config_manager.get_fallback_priority()
    
    # 将字符串列表转为 TranscriberType 枚举
    fallback_priority = []
    for t in priority_list:
        try:
            fallback_priority.append(TranscriberType(t))
        except ValueError:
            logger.warning(f'未知的转写器类型 "{t}"，跳过')
            continue
    
    try:
        preferred_str = config_manager.get("transcriber.default_type")
        preferred_type = TranscriberType(preferred_str)
    except ValueError:
        preferred_type = None
    
    if preferred_type is not None:
        try:
            fallback_priority.remove(preferred_type)
        except:
            pass
        fallback_priority.insert(0, preferred_type)
    
    return fallback_priority


class FallbackTranscriber(Transcriber):
    """带自动 fallback 功能的转写器包装类"""
    
    def __init__(self):
        pass
    
    def transcript(self, file_path: str) -> TranscriptResult:
        """执行转写，失败时自动尝试其他转写器"""
        fallback_order = _get_fallback_order()
        attempted = []
        last_error = None
        
        for t in fallback_order:
            attempted.append(t.value)
            try:
                transcriber = get_transcriber(t)
                result = transcriber.transcript(file_path)
                
                if result and result.segments:
                    logger.info(f"转写成功: {t.value}")
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"{t.value} 失败: {e}")
                continue
        
        raise RuntimeError(f"所有转写器失败 (已尝试: {', '.join(attempted)})") from last_error


def get_transcriber_with_fallback() -> FallbackTranscriber:
    """获取带自动 fallback 功能的转写器"""
    return FallbackTranscriber()
