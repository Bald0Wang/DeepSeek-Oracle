import sys
from pathlib import Path
from typing import Any

from app.utils.errors import business_error


class ZiweiService:
    def __init__(self, izthon_src_path: str = ""):
        self.izthon_src_path = izthon_src_path
        self._by_solar = None
        self._by_lunar = None

    def get_astrolabe_data(
        self,
        date: str,
        timezone: int,
        gender: str,
        calendar: str,
    ) -> dict[str, Any]:
        self._load_izthon()
        normalized_gender = self._normalize_gender(gender)
        try:
            if calendar == "solar":
                astrolabe = self._by_solar(date, timezone, normalized_gender)
            else:
                astrolabe = self._by_lunar(date, timezone, normalized_gender)
            return self._serialize_astrolabe(astrolabe)
        except ValueError as exc:
            raise business_error("A1002", f"invalid ziwei input: {exc}", 422, False) from exc
        except Exception as exc:
            raise business_error("A2001", f"izthon compute failed: {exc}", 502, True) from exc

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

    def _load_izthon(self) -> None:
        if self._by_solar and self._by_lunar:
            return

        candidate_paths: list[Path] = []
        if self.izthon_src_path:
            candidate_paths.append(Path(self.izthon_src_path))

        # Monorepo fallback: <outer-root>/izthon/src
        candidate_paths.append(Path(__file__).resolve().parents[4] / "izthon" / "src")

        for candidate in candidate_paths:
            if candidate.exists():
                candidate_str = str(candidate)
                if candidate_str not in sys.path:
                    sys.path.insert(0, candidate_str)

        try:
            from izthon.astro import by_lunar, by_solar

            self._by_solar = by_solar
            self._by_lunar = by_lunar
        except ModuleNotFoundError as exc:
            raise business_error(
                "A2001",
                "izthon package unavailable; install izthon or set IZTHON_SRC_PATH",
                502,
                True,
            ) from exc

    @staticmethod
    def _normalize_gender(gender: str) -> str:
        mapping = {
            "男": "male",
            "女": "female",
            "male": "male",
            "female": "female",
            "m": "male",
            "f": "female",
        }
        normalized = mapping.get(str(gender).strip().lower(), mapping.get(str(gender).strip()))
        if not normalized:
            raise business_error("A1002", "gender must be one of: 男, 女", 422, False)
        return normalized

    @staticmethod
    def _serialize_star(star: Any) -> dict[str, Any]:
        return {
            "name": getattr(star, "name", ""),
            "type": getattr(star, "type", ""),
            "scope": getattr(star, "scope", "origin"),
            "brightness": getattr(star, "brightness", None),
            "mutagen": getattr(star, "mutagen", None),
        }

    def _serialize_palace(self, palace: Any) -> dict[str, Any]:
        decadal = getattr(palace, "decadal", None)
        decadal_payload = None
        if decadal:
            range_value = list(getattr(decadal, "range", []))
            if len(range_value) != 2:
                range_value = [0, 0]
            decadal_payload = {
                "range": range_value,
                "heavenlyStem": getattr(decadal, "heavenly_stem", "未知"),
                "earthlyBranch": getattr(decadal, "earthly_branch", "未知"),
            }

        return {
            "index": getattr(palace, "index", 0),
            "name": getattr(palace, "name", "未知"),
            "isBodyPalace": bool(getattr(palace, "is_body_palace", False)),
            "isOriginalPalace": bool(getattr(palace, "is_original_palace", False)),
            "heavenlyStem": getattr(palace, "heavenly_stem", "未知"),
            "earthlyBranch": getattr(palace, "earthly_branch", "未知"),
            "majorStars": [self._serialize_star(star) for star in getattr(palace, "major_stars", [])],
            "minorStars": [self._serialize_star(star) for star in getattr(palace, "minor_stars", [])],
            "adjectiveStars": [
                self._serialize_star(star) for star in getattr(palace, "adjective_stars", [])
            ],
            "changsheng12": getattr(palace, "changsheng12", "未知"),
            "boshi12": getattr(palace, "boshi12", "未知"),
            "jiangqian12": getattr(palace, "jiangqian12", "未知"),
            "suiqian12": getattr(palace, "suiqian12", "未知"),
            "decadal": decadal_payload,
            "ages": list(getattr(palace, "ages", [])),
        }

    def _serialize_astrolabe(self, astrolabe: Any) -> dict[str, Any]:
        return {
            "gender": getattr(astrolabe, "gender", "未知"),
            "solarDate": getattr(astrolabe, "solar_date", "未知"),
            "lunarDate": getattr(astrolabe, "lunar_date", "未知"),
            "chineseDate": getattr(astrolabe, "chinese_date", "未知"),
            "time": getattr(astrolabe, "time", "未知"),
            "timeRange": getattr(astrolabe, "time_range", "未知"),
            "sign": getattr(astrolabe, "sign", "未知"),
            "zodiac": getattr(astrolabe, "zodiac", "未知"),
            "earthlyBranchOfBodyPalace": getattr(astrolabe, "earthly_branch_of_body_palace", "未知"),
            "earthlyBranchOfSoulPalace": getattr(astrolabe, "earthly_branch_of_soul_palace", "未知"),
            "soul": getattr(astrolabe, "soul", "未知"),
            "body": getattr(astrolabe, "body", "未知"),
            "fiveElementsClass": getattr(astrolabe, "five_elements_class", "未知"),
            "palaces": [self._serialize_palace(palace) for palace in getattr(astrolabe, "palaces", [])],
        }
