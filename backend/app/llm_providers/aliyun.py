from .deepseek import DeepSeekProvider


class AliyunProvider(DeepSeekProvider):
    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-r1"):
        super().__init__(api_key=api_key, base_url=base_url, model=model)

    def generate(self, user_message: str, timeout_s: int = 1800):
        result = super().generate(user_message, timeout_s)
        result.provider = "aliyun"
        return result
