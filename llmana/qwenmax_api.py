# Please install OpenAI SDK first: `pip3 install openai`

from openai import OpenAI

class QwenMax2_5Client:
    def __init__(self, api_key, base_url):
        """初始化 DeepSeekClient 类
        
        :param api_key: DeepSeek API 密钥
        :param base_url: API 的基础 URL
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def get_response(self, user_message):
        """发送用户消息并获取响应
        
        :param user_message: 用户输入的消息
        :return: API 返回的响应内容或错误消息
        """
        try:
            response = self.client.chat.completions.create(
                model="qwen-max-latest",
                messages=[
                    {"role": "system", "content": "你是一个熟练紫微斗数的大师，请根据用户需求进行紫微斗数命盘分析。"},
                    {"role": "user", "content": user_message},
                ],
                stream=False
            )
            print(response.choices[0].message.content)
            return response.choices[0].message.content
        except Exception as e:
            # 捕获异常并返回错误消息
            return f"发生错误: {str(e)}"

