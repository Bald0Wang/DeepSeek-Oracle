from .deepseek import DeepSeekProvider


class AliyunProvider(DeepSeekProvider):
    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-r1"):
        super().__init__(api_key=api_key, base_url=base_url, model=model)

    def generate(self, user_message: str, timeout_s: int = 1800):
        result = super().generate(user_message, timeout_s)
        result.provider = "aliyun"
        return result

    def chat_with_tools(self, messages: list[dict], tools: list[dict], timeout_s: int = 1800):
        result = super().chat_with_tools(messages=messages, tools=tools, timeout_s=timeout_s)
        result.provider = "aliyun"
        return result
