# python_iztro/json2ziwei/solar_api.py

import requests
import json

class SolarAPI:
    def __init__(self, base_url):
        """初始化 SolarAPI 类
        
        :param base_url: API 的基础 URL
        """
        self.base_url = base_url

    def get_astrolabe_data(self, date, timezone, gender, is_solar=True):
        """发送 POST 请求以获取星盘数据
        
        :param date: 日期字符串，格式为 "YYYY-MM-DD"
        :param timezone: 时区偏移量
        :param gender: 性别字符串
        :param is_solar: 是否为阳历数据
        :return: 响应的 JSON 数据
        """
        endpoint = "solar" if is_solar else "lunar"
        url = f"{self.base_url}/api/astro/{endpoint}"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "date": date,
            "timezone": timezone,
            "gender": gender
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()  # 抛出异常以处理错误

# 示例用法
if __name__ == "__main__":
    solar_api = SolarAPI("http://localhost:3000")
    try:
        solar_result = solar_api.get_astrolabe_data("2000-8-16", 2, "女", is_solar=True)
        # print("阳历响应内容:", solar_result)

        lunar_result = solar_api.get_astrolabe_data("2000-8-16", 2, "女", is_solar=False)
        # print("农历响应内容:", lunar_result)
    except Exception as e:
        print("请求失败:", e)