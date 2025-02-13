import json
from json2ziwei.api import SolarAPI
from json2ziwei.convert import convert_main_json_to_text


# 示例 JSON 数据
solar_api = SolarAPI("http://localhost:3000")
json_string = solar_api.get_astrolabe_data("1996-03-26", 4, "男", is_solar=False)

# 将 JSON 字符串解析为 Python 字典
main_data = json_string

# 转换并打印结果
text_description = convert_main_json_to_text(main_data)
print(text_description)

