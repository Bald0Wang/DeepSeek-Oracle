import hashlib
import math
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from flask import current_app

from app.models import InsightRepo
from app.services.ziwei_service import ZiweiService
from app.utils.errors import business_error


GANZHI_CYCLE = [
    "甲子",
    "乙丑",
    "丙寅",
    "丁卯",
    "戊辰",
    "己巳",
    "庚午",
    "辛未",
    "壬申",
    "癸酉",
    "甲戌",
    "乙亥",
    "丙子",
    "丁丑",
    "戊寅",
    "己卯",
    "庚辰",
    "辛巳",
    "壬午",
    "癸未",
    "甲申",
    "乙酉",
    "丙戌",
    "丁亥",
    "戊子",
    "己丑",
    "庚寅",
    "辛卯",
    "壬辰",
    "癸巳",
    "甲午",
    "乙未",
    "丙申",
    "丁酉",
    "戊戌",
    "己亥",
    "庚子",
    "辛丑",
    "壬寅",
    "癸卯",
    "甲辰",
    "乙巳",
    "丙午",
    "丁未",
    "戊申",
    "己酉",
    "庚戌",
    "辛亥",
    "壬子",
    "癸丑",
    "甲寅",
    "乙卯",
    "丙辰",
    "丁巳",
    "戊午",
    "己未",
    "庚申",
    "辛酉",
    "壬戌",
    "癸亥",
]

BRANCH_ELEMENT = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}

FIVE_ELEMENT_BIAS = {
    "木": 2.0,
    "火": 1.4,
    "土": 1.0,
    "金": 0.7,
    "水": 1.8,
}

STAR_BIAS = {
    "紫微": 2.8,
    "天府": 2.4,
    "太阳": 2.2,
    "太阴": 2.2,
    "天相": 1.8,
    "天梁": 1.6,
    "七杀": -1.1,
    "破军": -1.3,
    "廉贞": -0.6,
    "贪狼": 0.4,
}

YI_POOL = ["推进关键事项", "沟通协作", "复盘规划", "学习提升", "主动表达", "整理财务", "情绪调节"]
JI_POOL = ["冲动决策", "情绪化争执", "高风险投机", "拖延失约", "过度透支", "极端承诺", "临时变更"]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _month_key(target: date) -> str:
    return target.strftime("%Y-%m")


def _next_month(target: date) -> date:
    first = target.replace(day=1)
    if first.month == 12:
        return date(first.year + 1, 1, 1)
    return date(first.year, first.month + 1, 1)


def _calc_year_ganzhi(year_value: int) -> str:
    idx = (year_value - 1984) % 60
    return GANZHI_CYCLE[idx]


def _score_summary(score: float) -> str:
    if score >= 82:
        return "大吉"
    if score >= 72:
        return "顺势"
    if score >= 60:
        return "平稳"
    if score >= 48:
        return "需稳住"
    return "需留意"


def _stable_jitter(seed: str, amplitude: float) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF
    return (value * 2 - 1) * amplitude


@dataclass
class _PalaceProfile:
    name: str
    bias: float
    dayun: str
    focus: str


def _parse_birth_year(birth_info: dict[str, Any]) -> int:
    raw_date = str(birth_info.get("date", "")).strip()
    if len(raw_date) >= 4 and raw_date[:4].isdigit():
        return int(raw_date[:4])
    return datetime.utcnow().year


def _build_palace_profiles(astrolabe_data: dict[str, Any]) -> list[_PalaceProfile]:
    palaces = astrolabe_data.get("palaces") if isinstance(astrolabe_data.get("palaces"), list) else []
    output: list[_PalaceProfile] = []

    for palace in palaces:
        if not isinstance(palace, dict):
            continue
        palace_name = str(palace.get("name", "未知"))
        major_stars = palace.get("majorStars") if isinstance(palace.get("majorStars"), list) else []
        bias = 0.0
        for star in major_stars:
            if not isinstance(star, dict):
                continue
            star_name = str(star.get("name", ""))
            for key, star_bias in STAR_BIAS.items():
                if key in star_name:
                    bias += star_bias
        decadal = palace.get("decadal") if isinstance(palace.get("decadal"), dict) else {}
        dayun = ""
        stem = str(decadal.get("heavenlyStem", "")) if decadal else ""
        branch = str(decadal.get("earthlyBranch", "")) if decadal else ""
        if stem or branch:
            dayun = f"{stem}{branch}".strip()
        if not dayun:
            dayun = "童限"

        focus = f"{palace_name}相关事务"
        output.append(
            _PalaceProfile(
                name=palace_name,
                bias=bias,
                dayun=dayun,
                focus=focus,
            )
        )

    if output:
        return output

    return [_PalaceProfile(name="命宫", bias=0.0, dayun="童限", focus="日常节奏")]


class InsightService:
    def __init__(self, database_path: str, izthon_src_path: str, precompute_day: int):
        self.repo = InsightRepo(database_path)
        self.ziwei_service = ZiweiService(izthon_src_path)
        self.precompute_day = max(1, min(precompute_day, 28))

    def generate_and_store_initial(
        self,
        *,
        user_id: int,
        birth_info: dict[str, Any],
        astrolabe_data: dict[str, Any],
        source_result_id: int | None,
    ) -> None:
        kline_payload = self._build_life_kline_payload(birth_info=birth_info, astrolabe_data=astrolabe_data)
        self.repo.upsert_life_kline_profile(
            user_id=user_id,
            source_result_id=source_result_id,
            birth_info=birth_info,
            sparse=kline_payload["sparse"],
            kline=kline_payload["kline"],
            summary=kline_payload["summary"],
        )

        month_start = date.today().replace(day=1)
        calendar_payload = self._build_month_calendar_payload(
            birth_info=birth_info,
            astrolabe_data=astrolabe_data,
            month_start=month_start,
        )
        self.repo.upsert_monthly_calendar(
            user_id=user_id,
            month_key=_month_key(month_start),
            source_result_id=source_result_id,
            birth_info=birth_info,
            calendar_payload=calendar_payload,
        )

    def get_overview(
        self,
        *,
        user_id: int,
        is_admin: bool = False,
        result_id: int | None = None,
        birth_info_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        birth_info: dict[str, Any] | None = None
        source_result_id: int | None = result_id

        if birth_info_override:
            birth_info = birth_info_override
            source_result_id = None
        elif result_id is not None:
            result_birth = self.repo.get_result_birth_info(
                result_id=result_id,
                user_id=user_id,
                is_admin=is_admin,
            )
            if not result_birth:
                raise business_error("A4004", "result not found", 404, False)
            birth_info = result_birth["birth_info"]
            owner_user_id = result_birth.get("user_id")
            if owner_user_id is not None:
                user_id = int(owner_user_id)
        else:
            latest_items = self.repo.list_latest_birth_info_by_user()
            for item in latest_items:
                if int(item["user_id"]) == int(user_id):
                    birth_info = item["birth_info"]
                    source_result_id = int(item["result_id"])
                    break

        kline_profile = self.repo.get_life_kline_profile(user_id=user_id)
        if not birth_info and kline_profile and isinstance(kline_profile.get("birth_info"), dict):
            cached_birth_info = kline_profile.get("birth_info") or {}
            if cached_birth_info.get("date"):
                birth_info = cached_birth_info

        if not birth_info:
            raise business_error("A4004", "birth profile not found", 404, False)

        should_regenerate = not kline_profile
        if not should_regenerate and isinstance(kline_profile, dict):
            existing_birth = kline_profile.get("birth_info") or {}
            should_regenerate = any(
                str(existing_birth.get(key, "")) != str(birth_info.get(key, ""))
                for key in ("date", "timezone", "gender", "calendar")
            )

        if should_regenerate:
            astrolabe_data = self.ziwei_service.get_astrolabe_data(
                date=birth_info["date"],
                timezone=int(birth_info["timezone"]),
                gender=birth_info["gender"],
                calendar=birth_info["calendar"],
            )
            self.generate_and_store_initial(
                user_id=user_id,
                birth_info=birth_info,
                astrolabe_data=astrolabe_data,
                source_result_id=source_result_id,
            )
            kline_profile = self.repo.get_life_kline_profile(user_id=user_id)

        today = date.today()
        current_month = today.replace(day=1)
        next_month = _next_month(current_month)
        current_calendar = self._get_or_create_month_calendar(
            user_id=user_id,
            birth_info=birth_info,
            source_result_id=source_result_id,
            month_start=current_month,
        )
        next_calendar = self._get_or_create_month_calendar(
            user_id=user_id,
            birth_info=birth_info,
            source_result_id=source_result_id,
            month_start=next_month,
        )

        near_30_days: list[dict[str, Any]] = []
        limit_date = today + timedelta(days=29)
        for payload in (current_calendar, next_calendar):
            for item in payload.get("days", []):
                raw_day = str(item.get("date", ""))
                try:
                    day_obj = datetime.strptime(raw_day, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if today <= day_obj <= limit_date:
                    near_30_days.append(item)

        near_30_days.sort(key=lambda item: item.get("date", ""))

        return {
            "life_kline": {
                "sparse": (kline_profile or {}).get("sparse", {}),
                "summary": (kline_profile or {}).get("summary", {}),
                "updated_at": (kline_profile or {}).get("updated_at"),
            },
            "calendar": {
                "current_month": current_calendar,
                "next_month": next_calendar,
                "near_30_days": near_30_days,
            },
        }

    def precompute_next_month_for_all_users(self, *, target_day: date | None = None) -> dict[str, Any]:
        run_day = target_day or date.today()
        run_key = run_day.strftime("%Y-%m")
        if not self.repo.claim_scheduler_run(
            job_name="precompute_next_month_calendar",
            run_key=run_key,
        ):
            return {"ok": True, "skipped": True, "reason": "already_ran", "run_key": run_key}

        next_month = _next_month(run_day.replace(day=1))
        count = 0
        failures = 0
        for item in self.repo.list_latest_birth_info_by_user():
            user_id = int(item["user_id"])
            birth_info = item["birth_info"]
            source_result_id = int(item["result_id"])
            try:
                self._get_or_create_month_calendar(
                    user_id=user_id,
                    birth_info=birth_info,
                    source_result_id=source_result_id,
                    month_start=next_month,
                    force_regenerate=True,
                )
                count += 1
            except Exception:
                failures += 1
                current_app.logger.exception("precompute next month calendar failed for user_id=%s", user_id)

        return {
            "ok": True,
            "run_key": run_key,
            "generated_users": count,
            "failed_users": failures,
            "month_key": _month_key(next_month),
        }

    def _get_or_create_month_calendar(
        self,
        *,
        user_id: int,
        birth_info: dict[str, Any],
        source_result_id: int | None,
        month_start: date,
        force_regenerate: bool = False,
    ) -> dict[str, Any]:
        month_key = _month_key(month_start)
        existing = self.repo.get_monthly_calendar(user_id=user_id, month_key=month_key)
        if existing and not force_regenerate:
            return existing["calendar"]

        astrolabe_data = self.ziwei_service.get_astrolabe_data(
            date=birth_info["date"],
            timezone=int(birth_info["timezone"]),
            gender=birth_info["gender"],
            calendar=birth_info["calendar"],
        )
        payload = self._build_month_calendar_payload(
            birth_info=birth_info,
            astrolabe_data=astrolabe_data,
            month_start=month_start,
        )
        self.repo.upsert_monthly_calendar(
            user_id=user_id,
            month_key=month_key,
            source_result_id=source_result_id,
            birth_info=birth_info,
            calendar_payload=payload,
        )
        return payload

    def _build_life_kline_payload(
        self,
        *,
        birth_info: dict[str, Any],
        astrolabe_data: dict[str, Any],
    ) -> dict[str, Any]:
        birth_year = _parse_birth_year(birth_info)
        palace_profiles = _build_palace_profiles(astrolabe_data)
        five_elements_text = str(astrolabe_data.get("fiveElementsClass", ""))
        dominant_element = next(
            (key for key in FIVE_ELEMENT_BIAS if key in five_elements_text),
            "土",
        )

        base_score = 58 + FIVE_ELEMENT_BIAS.get(dominant_element, 1.0) * 2
        if str(astrolabe_data.get("soul", "")) == str(astrolabe_data.get("body", "")):
            base_score += 2

        sparse_years: list[dict[str, Any]] = []
        ages = [1 + i * 5 for i in range(20)]
        for age in ages:
            target_year = birth_year + age - 1
            year_ganzhi = _calc_year_ganzhi(target_year)
            profile = palace_profiles[(age // 5) % len(palace_profiles)]
            branch = year_ganzhi[1] if len(year_ganzhi) > 1 else "辰"
            branch_element = BRANCH_ELEMENT.get(branch, "土")
            element_bonus = FIVE_ELEMENT_BIAS.get(branch_element, 1.0) * 1.3
            trend = math.sin(age / 8) * 7 + math.cos(age / 11) * 4
            jitter = _stable_jitter(
                f"{birth_info['date']}|{birth_info['timezone']}|{birth_info['gender']}|{age}",
                2.2,
            )
            score = _clamp(base_score + profile.bias + element_bonus + trend + jitter, 12, 94)
            sparse_years.append(
                {
                    "age": age,
                    "year": target_year,
                    "yearGanZhi": year_ganzhi,
                    "daYun": profile.dayun,
                    "score": int(round(score)),
                    "summary": _score_summary(score),
                    "focus": profile.focus,
                }
            )

        full = self._interpolate_kline(sparse_years=sparse_years, birth_year=birth_year, birth_info=birth_info)
        avg_score = int(round(sum(int(item["score"]) for item in full) / len(full)))
        sorted_full = sorted(full, key=lambda item: int(item["score"]), reverse=True)
        summary = {
            "averageScore": avg_score,
            "bestYears": [int(sorted_full[0]["age"]), int(sorted_full[1]["age"]), int(sorted_full[2]["age"])],
            "worstYears": [int(sorted_full[-1]["age"]), int(sorted_full[-2]["age"])],
            "overallTrend": "前中期需稳中求进，中后期更重在长期积累与节奏管理。",
        }

        return {
            "sparse": {"years": sparse_years},
            "kline": full,
            "summary": summary,
        }

    def _interpolate_kline(
        self,
        *,
        sparse_years: list[dict[str, Any]],
        birth_year: int,
        birth_info: dict[str, Any],
    ) -> list[dict[str, Any]]:
        sparse_map = {int(item["age"]): item for item in sparse_years}
        ages = sorted(sparse_map.keys())
        full: list[dict[str, Any]] = []

        for age in range(1, 101):
            target_year = birth_year + age - 1
            year_ganzhi = _calc_year_ganzhi(target_year)
            exact = sparse_map.get(age)
            if exact:
                score = float(exact["score"])
                prev_close = float(full[-1]["close"]) if full else score
                close = int(round(score))
                open_value = int(round(prev_close))
                full.append(
                    {
                        "age": age,
                        "year": target_year,
                        "yearGanZhi": str(exact.get("yearGanZhi", year_ganzhi)),
                        "daYun": str(exact.get("daYun", "童限")),
                        "open": open_value,
                        "close": close,
                        "high": int(min(100, max(open_value, close) + 2)),
                        "low": int(max(0, min(open_value, close) - 2)),
                        "score": close,
                        "summary": str(exact.get("summary", _score_summary(score))),
                    }
                )
                continue

            prev_candidates = [item_age for item_age in ages if item_age < age]
            next_candidates = [item_age for item_age in ages if item_age > age]
            prev_age = prev_candidates[-1] if prev_candidates else None
            next_age = next_candidates[0] if next_candidates else None

            if prev_age is None and next_age is None:
                score = 55.0
            elif prev_age is None:
                score = float(sparse_map[next_age]["score"])
            elif next_age is None:
                score = float(sparse_map[prev_age]["score"])
            else:
                prev_score = float(sparse_map[prev_age]["score"])
                next_score = float(sparse_map[next_age]["score"])
                ratio = (age - prev_age) / (next_age - prev_age)
                score = prev_score + (next_score - prev_score) * ratio

            score = _clamp(
                score
                + _stable_jitter(
                    f"{birth_info['date']}|{birth_info['timezone']}|interp|{age}",
                    1.8,
                ),
                10,
                95,
            )
            prev_close = float(full[-1]["close"]) if full else score
            close = int(round(score))
            open_value = int(round(prev_close))
            full.append(
                {
                    "age": age,
                    "year": target_year,
                    "yearGanZhi": year_ganzhi,
                    "daYun": str(sparse_map.get(prev_age, {}).get("daYun", "童限")),
                    "open": open_value,
                    "close": close,
                    "high": int(min(100, max(open_value, close) + 2)),
                    "low": int(max(0, min(open_value, close) - 2)),
                    "score": close,
                    "summary": _score_summary(score),
                }
            )

        return full

    def _build_month_calendar_payload(
        self,
        *,
        birth_info: dict[str, Any],
        astrolabe_data: dict[str, Any],
        month_start: date,
    ) -> dict[str, Any]:
        year_value = month_start.year
        month_value = month_start.month
        days_total = monthrange(year_value, month_value)[1]

        palace_profiles = _build_palace_profiles(astrolabe_data)
        top_profile = max(palace_profiles, key=lambda item: item.bias)
        five_elements_text = str(astrolabe_data.get("fiveElementsClass", ""))
        dominant_element = next((item for item in FIVE_ELEMENT_BIAS if item in five_elements_text), "土")
        base_score = 58 + FIVE_ELEMENT_BIAS.get(dominant_element, 1.0) * 3

        days: list[dict[str, Any]] = []
        for day_number in range(1, days_total + 1):
            day_date = date(year_value, month_value, day_number)
            weekday = day_date.weekday()
            profile = palace_profiles[(day_number - 1) % len(palace_profiles)]
            wave = math.sin(day_number / 4.3) * 6 + math.cos(day_number / 5.6) * 4
            weekend_bias = 2.0 if weekday >= 5 else 0.0
            jitter = _stable_jitter(
                f"{birth_info['date']}|{birth_info['timezone']}|{day_date.isoformat()}",
                2.0,
            )
            score = int(round(_clamp(base_score + profile.bias + wave + weekend_bias + jitter, 18, 96)))
            yi_idx = int(abs(_stable_jitter(f"yi|{day_date.isoformat()}", len(YI_POOL) - 1)))
            ji_idx = int(abs(_stable_jitter(f"ji|{day_date.isoformat()}", len(JI_POOL) - 1)))
            yi = [YI_POOL[yi_idx], YI_POOL[(yi_idx + 2) % len(YI_POOL)]]
            ji = [JI_POOL[ji_idx], JI_POOL[(ji_idx + 3) % len(JI_POOL)]]

            days.append(
                {
                    "date": day_date.isoformat(),
                    "score": score,
                    "level": _score_summary(score),
                    "focus": profile.focus,
                    "yi": yi,
                    "ji": ji,
                    "note": f"参考{profile.name}宫位节奏，优先做可控事项。",
                }
            )

        return {
            "month_key": _month_key(month_start),
            "start_date": month_start.isoformat(),
            "end_date": date(year_value, month_value, days_total).isoformat(),
            "generated_by": "ziwei",
            "dominant_focus": top_profile.focus,
            "days": days,
        }


def get_insight_service() -> InsightService:
    service = current_app.extensions.get("insight_service")
    if service:
        return service

    service = InsightService(
        database_path=current_app.config["DATABASE_PATH"],
        izthon_src_path=current_app.config["IZTHON_SRC_PATH"],
        precompute_day=int(current_app.config.get("CALENDAR_PRECOMPUTE_DAY", 15)),
    )
    current_app.extensions["insight_service"] = service
    return service
