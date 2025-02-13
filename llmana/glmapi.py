# 请先安装 ZhipuAI SDK: `pip install zhipuai`

from zhipuai import ZhipuAI

class GLMClient:
    def __init__(self, api_key):
        """初始化 GLMClient 类
        
        :param api_key: ZhipuAI API 密钥
        """
        self.client = ZhipuAI(api_key=api_key)

    def get_response(self, user_message):
        """发送用户消息并获取响应
        
        :param user_message: 用户输入的消息
        :return: API 返回的响应内容或错误消息
        """
        try:
            response = self.client.chat.completions.create(
                model="glm-4-plus",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个熟练紫微斗数的大师，请根据用户需求进行紫微斗数命盘分析。"
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                top_p=0.7,
                temperature=0.95,
                stream=False
            )
            
            print(response.choices[0].message.content)

            return response.choices[0].message.content
        except Exception as e:
            # 捕获异常并返回错误消息
            return f"发生错误: {str(e)}"

# if __name__ == "__main__":
#     # 示例用法
#     api_key = "your api key"
#     glm_client = GLMClient(api_key)
#     response_content = glm_client.get_response("你好")
#     print(response_content) 