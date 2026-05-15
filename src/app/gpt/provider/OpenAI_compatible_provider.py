from typing import Optional, Union

from openai import OpenAI

from app.utils.logger import get_logger

logging= get_logger(__name__)
class OpenAICompatibleProvider:
    def __init__(self, api_key: str, base_url: str, model: Union[str, None]=None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    @property
    def get_client(self):
        return self.client

    @staticmethod
    def test_connection(api_key: str, base_url: str, model_name: str) -> tuple[bool, str]:
        """
        轻量级连通性测试：发送一条最小 chat 请求验证 Key/服务/模型名是否有效。
        返回 (是否成功, 错误描述)。
        """
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "ok"}],
                max_tokens=1,
            )
            logging.info("连通性测试成功")
            return True, ""
        except Exception as e:
            error_str = str(e)
            logging.info(f"连通性测试失败：{error_str}")
            return False, error_str