import json
from typing import Any

import requests

from app.utils.errors import business_error


class ZiweiService:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get_astrolabe_data(
        self,
        date: str,
        timezone: int,
        gender: str,
        calendar: str,
    ) -> dict[str, Any]:
        endpoint = "solar" if calendar == "solar" else "lunar"
        url = f"{self.base_url}/api/astro/{endpoint}"

        payload = {
            "date": date,
            "timezone": timezone,
            "gender": gender,
        }

        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise business_error("A2001", f"iztro service unavailable: {exc}", 502, True) from exc

    def build_text_description(self, main_json_data: dict[str, Any]) -> str:
        return self.convert_main_json_to_text(main_json_data)

    def convert_palace_json_to_text(self, json_data: dict[str, Any]) -> str:
        output_lines: list[str] = []

        output_lines.append(f"宫位{json_data.get('index')}号位，宫位名称是{json_data.get('name', '未知')}。")
        output_lines.append(
            f"{'是' if json_data.get('isBodyPalace') else '不是'}身宫，"
            f"{'是' if json_data.get('isOriginalPalace') else '不是'}来因宫。"
        )
        output_lines.append(
            f"宫位天干为{json_data.get('heavenlyStem', '未知')}，"
            f"宫位地支为{json_data.get('earthlyBranch', '未知')}。"
        )

        major_stars_desc = "主星:"
        major_stars_list: list[str] = []
        for star in json_data.get("majorStars", []):
            brightness_desc = f"亮度为{star['brightness']}" if star.get("brightness") else "无亮度标志"
            mutagen_value = star.get("mutagen")
            if star.get("type") == "major" and (mutagen_value is None or mutagen_value == ""):
                mutagen_desc = "，无四化星"
            elif mutagen_value:
                mutagen_desc = f"，{mutagen_value}四化星"
            else:
                mutagen_desc = ""

            if star.get("scope") == "origin":
                star_desc = f"{star.get('name', '')}（本命星耀，{brightness_desc}{mutagen_desc}）"
            else:
                star_desc = f"{star.get('name', '')}（{star.get('scope', '')}星耀，{brightness_desc}{mutagen_desc}）"

            if star.get("type") == "tianma":
                star_desc = f"{star.get('name', '')}（本命星耀，无亮度标志）"

            major_stars_list.append(star_desc)

        major_stars_desc += "，".join(major_stars_list) if major_stars_list else "无"
        output_lines.append(major_stars_desc)

        minor_stars = json_data.get("minorStars", [])
        if not minor_stars:
            output_lines.append("辅星：无")
        else:
            minor_stars_desc = "辅星："
            minor_stars_list = [f"{star.get('name', '')}（本命星耀）" for star in minor_stars]
            minor_stars_desc += "，".join(minor_stars_list)
            output_lines.append(minor_stars_desc)

        adjective_stars_desc = "杂耀:"
        adjective_stars_list = [
            f"{star.get('name', '')}（本命星耀）" for star in json_data.get("adjectiveStars", [])
        ]
        adjective_stars_desc += "，".join(adjective_stars_list) if adjective_stars_list else "无"
        output_lines.append(adjective_stars_desc)

        output_lines.append(f"长生 12 神:{json_data.get('changsheng12', '未知')}。")
        output_lines.append(f"博士 12 神:{json_data.get('boshi12', '未知')}。")
        output_lines.append(f"流年将前 12 神:{json_data.get('jiangqian12', '未知')}。")
        output_lines.append(f"流年岁前 12 神:{json_data.get('suiqian12', '未知')}。")

        decadal_info = json_data.get("decadal")
        if isinstance(decadal_info, dict) and isinstance(decadal_info.get("range"), list):
            start, end = decadal_info.get("range", ["", ""])
            output_lines.append(
                f"大限:{start},{end}(运限天干为{decadal_info.get('heavenlyStem', '未知')}，"
                f"运限地支为{decadal_info.get('earthlyBranch', '未知')})。"
            )

        ages = json_data.get("ages")
        if isinstance(ages, list) and ages:
            output_lines.append(f"小限:{','.join(map(str, ages))}")

        return "\n".join(output_lines)

    def convert_main_json_to_text(self, main_json_data: dict[str, Any]) -> str:
        output_lines: list[str] = []

        output_lines.append("----------基本信息----------")
        output_lines.append(f"命主性别：{main_json_data.get('gender', '未知')}")
        output_lines.append(f"阳历生日：{main_json_data.get('solarDate', '未知')}")
        output_lines.append(f"阴历生日：{main_json_data.get('lunarDate', '未知')}")
        output_lines.append(f"八字：{main_json_data.get('chineseDate', '未知')}")
        output_lines.append(
            f"生辰时辰：{main_json_data.get('time', '未知')} ({main_json_data.get('timeRange', '未知')})"
        )
        output_lines.append(f"星座：{main_json_data.get('sign', '未知')}")
        output_lines.append(f"生肖：{main_json_data.get('zodiac', '未知')}")
        output_lines.append(f"身宫地支：{main_json_data.get('earthlyBranchOfBodyPalace', '未知')}")
        output_lines.append(f"命宫地支：{main_json_data.get('earthlyBranchOfSoulPalace', '未知')}")
        output_lines.append(f"命主星：{main_json_data.get('soul', '未知')}")
        output_lines.append(f"身主星：{main_json_data.get('body', '未知')}")
        output_lines.append(f"五行局：{main_json_data.get('fiveElementsClass', '未知')}")
        output_lines.append("----------宫位信息----------")

        palaces_data = main_json_data.get("palaces")
        if not isinstance(palaces_data, list):
            output_lines.append("宫位信息：数据格式不正确或缺失")
            return "\n".join(output_lines)

        if not palaces_data:
            output_lines.append("宫位信息：暂未提供")
            return "\n".join(output_lines)

        for palace_json in palaces_data:
            output_lines.append(self.convert_palace_json_to_text(palace_json))
            output_lines.append("----------")

        return "\n".join(output_lines)
