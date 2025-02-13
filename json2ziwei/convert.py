import json
from .api import SolarAPI

def convert_palace_json_to_text(json_data):
    """
    将单个宫位的紫微斗数 JSON 数据转换为文本描述。

    参数:
    json_data (dict): 包含单个宫位紫微斗数信息的 JSON 数据。

    返回:
    str: 描述单个宫位紫微斗数信息的文本字符串。
    """

    output_lines = []

    # 宫位信息
    output_lines.append(f"宫位{json_data['index']}号位，宫位名称是{json_data['name']}。")
    output_lines.append(f"{'是' if json_data['isBodyPalace'] else '不是'}身宫，{'是' if json_data['isOriginalPalace'] else '不是'}来因宫。")
    output_lines.append(f"宫位天干为{json_data['heavenlyStem']}，宫位地支为{json_data['earthlyBranch']}。")

    # 主星
    major_stars_desc = "主星:"
    major_stars_list = []
    for star in json_data['majorStars']:
        brightness_desc = f"亮度为{star['brightness']}" if star['brightness'] else "无亮度标志"
        #  修改部分：使用 get 方法安全获取 mutagen，并判断 None 或 "" 都表示无四化星
        mutagen_value = star.get('mutagen')
        mutagen_desc = "，无四化星" if star['type'] == 'major' and (mutagen_value is None or mutagen_value == "") else f"，{mutagen_value}四化星" if mutagen_value else ""

        star_desc = f"{star['name']}（本命星耀，{brightness_desc}{mutagen_desc}）" if star['scope'] == 'origin' else f"{star['name']}（{star['scope']}星耀，{brightness_desc}{mutagen_desc}）" # 兼容其他scope，虽然例子里只有 origin

        if star['type'] == 'tianma':
            star_desc = f"{star['name']}（本命星耀，无亮度标志）" # 天马 特殊处理
        major_stars_list.append(star_desc)
    major_stars_desc += "，".join(major_stars_list)
    output_lines.append(major_stars_desc)

    # 辅星
    if not json_data['minorStars']:
        output_lines.append("辅星：无")
    else: # 如果有辅星，可以继续扩展代码来处理，目前例子没有辅星
        minor_stars_desc = "辅星："
        minor_stars_list = []
        for star in json_data['minorStars']:
            star_desc = f"{star['name']}（本命星耀）" # 示例中辅星没有更多信息，可以根据实际情况扩展
            minor_stars_list.append(star_desc)
        minor_stars_desc += "，".join(minor_stars_list)
        output_lines.append(minor_stars_desc)

    # 杂耀
    adjective_stars_desc = "杂耀:"
    adjective_stars_list = []
    for star in json_data['adjectiveStars']:
        star_desc = f"{star['name']}（本命星耀）" # 示例中杂耀也没有更多信息
        adjective_stars_list.append(star_desc)
    adjective_stars_desc += "，".join(adjective_stars_list)
    output_lines.append(adjective_stars_desc)

    # 长生 12 神，博士 12 神，流年将前 12 神，流年岁前 12 神
    output_lines.append(f"长生 12 神:{json_data['changsheng12']}。")
    output_lines.append(f"博士 12 神:{json_data['boshi12']}。")
    output_lines.append(f"流年将前 12 神:{json_data['jiangqian12']}。")
    output_lines.append(f"流年岁前 12 神:{json_data['suiqian12']}。")

    # 大限
    decadal_info = json_data.get('decadal') # 使用get方法防止KeyError
    if decadal_info:
        output_lines.append(f"大限:{decadal_info['range'][0]},{decadal_info['range'][1]}(运限天干为{decadal_info['heavenlyStem']}，运限地支为{decadal_info['earthlyBranch']})。")

    # 小限
    if json_data.get('ages'): # 使用get方法防止KeyError
        output_lines.append(f"小限:{','.join(map(str, json_data['ages']))}") # 将数字列表转换为逗号分隔的字符串

    return "\n".join(output_lines)

def convert_main_json_to_text(main_json_data):
    """
    将包含个人信息和宫位数组的紫微斗数 JSON 数据转换为文本描述。

    参数:
    main_json_data (dict): 包含完整紫微斗数信息的 JSON 数据。

    返回:
    str: 描述完整紫微斗数信息的文本字符串。
    """
    output_lines = []

    #  基本信息
    output_lines.append("----------基本信息----------")
    output_lines.append(f"命主性别：{main_json_data.get('gender', '未知')}")
    output_lines.append(f"阳历生日：{main_json_data.get('solarDate', '未知')}")
    output_lines.append(f"阴历生日：{main_json_data.get('lunarDate', '未知')}")
    output_lines.append(f"八字：{main_json_data.get('chineseDate', '未知')}")
    output_lines.append(f"生辰时辰：{main_json_data.get('time', '未知')} ({main_json_data.get('timeRange', '未知')})")
    output_lines.append(f"星座：{main_json_data.get('sign', '未知')}")
    output_lines.append(f"生肖：{main_json_data.get('zodiac', '未知')}")
    output_lines.append(f"身宫地支：{main_json_data.get('earthlyBranchOfBodyPalace', '未知')}")
    output_lines.append(f"命宫地支：{main_json_data.get('earthlyBranchOfSoulPalace', '未知')}")
    output_lines.append(f"命主星：{main_json_data.get('soul', '未知')}")
    output_lines.append(f"身主星：{main_json_data.get('body', '未知')}")
    output_lines.append(f"五行局：{main_json_data.get('fiveElementsClass', '未知')}")
    output_lines.append("----------宫位信息----------")

    # 宫位信息 (如果 palaces 数组存在且不为空)
    palaces_data = main_json_data.get('palaces')
    if palaces_data and isinstance(palaces_data, list):
        if not palaces_data:
            output_lines.append("宫位信息：暂未提供") # 或者其他提示信息
        else:
            for palace_json in palaces_data:
                palace_text = convert_palace_json_to_text(palace_json)
                output_lines.append(palace_text)
                output_lines.append("----------") # 分隔每个宫位的信息
    else:
        output_lines.append("宫位信息：数据格式不正确或缺失")

    return "\n".join(output_lines)




# 示例 JSON 数据
solar_api = SolarAPI("http://localhost:3000")
json_string = solar_api.get_astrolabe_data("2000-8-16", 2, "女", is_solar=True)

# 将 JSON 字符串解析为 Python 字典
main_data = json_string

# 转换并打印结果
text_description = convert_main_json_to_text(main_data)
# print(text_description)