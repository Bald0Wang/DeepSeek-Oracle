import os
# 升级方舟 SDK 到最新版本 pip install -U 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark


class deepseek_huoshan:
    def __init__(self, api_key):
        """初始化 DeepSeekClient 类
        
        :param api_key: DeepSeek API 密钥
        :param base_url: API 的基础 URL
        """
        self.client = Ark(
        # 从环境变量中读取您的方舟API Key
        api_key=api_key, 
        # 深度推理模型耗费时间会较长，请您设置较大的超时时间，避免超时，推荐30分钟以上
        timeout=1800,
        # max_tokens = 8000
        
        )

    def get_response(self, user_message):
        """发送用户消息并获取响应
        
        :param user_message: 用户输入的消息
        :return: API 返回的响应内容或错误消息
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一个熟练紫微斗数的大师，请根据用户需求进行紫微斗数命盘分析。"
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
            
            # 打印将要发送的请求内容
            print("发送的消息:", messages)
            ark_model = os.getenv('ARK_API_model')
            response = self.client.chat.completions.create(
                model=ark_model, # 这里请改为你自己的推理接入点 
                messages=messages
            )
            print(response.choices[0].message.content)
            return response.choices[0].message.content
        except Exception as e:
            # 捕获异常并返回错误消息
            return f"发生错误: {str(e)}"

if __name__ == "__main__":
    # 示例 API 密钥
    api_key = ""
    
    # 实例化 deepseek_huoshan 类
    deepseek = deepseek_huoshan(api_key)
    
    # 用户输入消息
    user_message = input("请输入您的消息: ")
    
    # 获取响应并打印
    response = deepseek.get_response(user_message)
    print("API 响应:", response)

