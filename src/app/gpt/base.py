from abc import ABC

from app.models.gpt_model import GPTSource


class GPT(ABC):
    def summarize(self, source:GPTSource )->str:
        '''

        :param source:
        :return:
        '''
        pass
    def create_messages(self, segments:list,**kwargs)->list:
        pass
    def list_models(self):
        pass
    def ask(self, user_prompt: str, system_prompt: str = "") -> str:
        '''单次问答，不走转写分块流程

        :param user_prompt: 用户消息正文
        :param system_prompt: 可选的系统消息
        :return: 模型返回文本
        '''
        pass
