from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import time
from typing import Any

from flask import current_app

from app.llm_providers import create_provider
from app.services.ziwei_service import ZiweiService
from app.utils.errors import AppError


@dataclass(frozen=True)
class Trigram:
    idx: int
    name: str
    symbol: str
    image: str
    element: str
    lines: tuple[int, int, int]  # bottom -> top


TRIGRAMS: dict[int, Trigram] = {
    1: Trigram(1, "乾", "☰", "天", "金", (1, 1, 1)),
    2: Trigram(2, "兑", "☱", "泽", "金", (1, 1, 0)),
    3: Trigram(3, "离", "☲", "火", "火", (1, 0, 1)),
    4: Trigram(4, "震", "☳", "雷", "木", (1, 0, 0)),
    5: Trigram(5, "巽", "☴", "风", "木", (0, 1, 1)),
    6: Trigram(6, "坎", "☵", "水", "水", (0, 1, 0)),
    7: Trigram(7, "艮", "☶", "山", "土", (0, 0, 1)),
    8: Trigram(8, "坤", "☷", "地", "土", (0, 0, 0)),
}
TRIGRAM_BY_LINES = {value.lines: value for value in TRIGRAMS.values()}
MOVING_LINE_NAMES = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}


class DivinationService:
    def __init__(
        self,
        izthon_src_path: str,
        default_provider: str,
        default_model: str,
        request_timeout_s: int,
        llm_max_retries: int,
        provider_config: dict[str, Any],
    ):
        self.ziwei_service = ZiweiService(izthon_src_path)
        self.default_provider = default_provider
        self.default_model = default_model
        self.request_timeout_s = request_timeout_s
        self.llm_max_retries = llm_max_retries
        self.provider_config = provider_config

    def run_ziwei(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider_name = payload.get("provider", self.default_provider)
        model_name = payload.get("model", self.default_model)
        question = payload["question"]
        birth_info = payload["birth_info"]

        astrolabe_data = self.ziwei_service.get_astrolabe_data(**birth_info)
        chart_text = self.ziwei_service.build_text_description(astrolabe_data)
        chart_summary = self._trim_chart_text(chart_text)

        fallback = (
            "总论：你当前的运势更适合“稳中求进”，优先确保节奏稳定与决策一致。\n"
            "分项建议：事业宜做长期布局，关系宜强化沟通，财务宜风险分层，健康宜规律作息。\n"
            "关键窗口：近期先打基础，中期再放大投入，遇到不确定性时放慢节奏。\n"
            "行动建议：\n1. 每周一次复盘；\n2. 保留20%机动时间；\n3. 先做低风险验证再做大决策。"
        )
        prompt = (
            "你是紫微斗数长线解读智能体。请基于命盘信息进行结构化解读。"
            "禁止宿命化和灾祸渲染，强调可执行建议。\n"
            f"用户问题：{question}\n"
            f"命盘摘要：\n{chart_summary}\n"
            "输出格式：总论、事业、情感、财富、健康、关键窗口（3条）、行动建议（3条）。"
        )
        reading = self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            provider_name=provider_name,
            model_name=model_name,
        )
        return {
            "question": question,
            "birth_info": birth_info,
            "chart_summary": chart_summary,
            "reading": reading,
            "provider": provider_name,
            "model": model_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def run_meihua(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider_name = payload.get("provider", self.default_provider)
        model_name = payload.get("model", self.default_model)
        topic = payload["topic"]
        occurred_at = datetime.fromisoformat(payload["occurred_at"])

        gua = self._calculate_meihua(topic, occurred_at)
        fallback = self._build_meihua_fallback(topic=topic, gua=gua)
        prompt = (
            "你是梅花易数短占智能体，请基于以下起卦结果解读短期倾向。"
            "避免绝对化断言，用“更适合/更需谨慎”表述。\n"
            f"占题：{topic}\n"
            f"起卦时间：{payload['occurred_at']}\n"
            f"本卦：{gua['base_gua']}（上卦{gua['upper_trigram']}，下卦{gua['lower_trigram']}）\n"
            f"互卦：{gua['mutual_gua']}\n"
            f"变卦：{gua['changed_gua']}\n"
            f"动爻：{gua['moving_line_name']}\n"
            f"体用：体卦{gua['ti_gua']} / 用卦{gua['yong_gua']} / 关系{gua['relation']}\n"
            "输出：占题重述、短期倾向、关键变数、宜、忌、行动建议。"
        )
        reading = self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            provider_name=provider_name,
            model_name=model_name,
        )
        return {
            "topic": topic,
            "occurred_at": payload["occurred_at"],
            "method": "qizhounian-time-meihua",
            "gua": gua,
            "reading": reading,
            "provider": provider_name,
            "model": model_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _complete_with_fallback(self, prompt: str, fallback: str, provider_name: str, model_name: str) -> str:
        if provider_name == "mock":
            return fallback

        text = ""
        for attempt in range(self.llm_max_retries + 1):
            try:
                provider = create_provider(
                    provider_name,
                    model_name,
                    app_config=self.provider_config,
                )
                response = provider.generate(prompt, timeout_s=self.request_timeout_s)
                text = (response.content or "").strip()
                if text:
                    return text
            except AppError:
                if attempt < self.llm_max_retries:
                    time.sleep(2**attempt)
                    continue
                return fallback
            except Exception:
                if attempt < self.llm_max_retries:
                    time.sleep(2**attempt)
                    continue
                return fallback
        return text or fallback

    @staticmethod
    def _trim_chart_text(text: str, max_lines: int = 40) -> str:
        lines = [line for line in text.splitlines() if line.strip()]
        return "\n".join(lines[:max_lines])

    def _calculate_meihua(self, topic: str, occurred_at: datetime) -> dict[str, Any]:
        year = occurred_at.year
        month = occurred_at.month
        day = occurred_at.day
        hour = occurred_at.hour

        # Follow the 7th-anniversary meihua core formula:
        # upper=(年+月+日)%8, lower=(年+月+日+时)%8, moving=(年+月+日+时)%6.
        upper_idx = (year + month + day) % 8 or 8
        lower_idx = (year + month + day + hour) % 8 or 8
        moving_line = (year + month + day + hour) % 6 or 6

        upper = TRIGRAMS[upper_idx]
        lower = TRIGRAMS[lower_idx]
        base_lines = list(lower.lines + upper.lines)  # bottom -> top
        hu_lower = TRIGRAM_BY_LINES[tuple(base_lines[1:4])]
        hu_upper = TRIGRAM_BY_LINES[tuple(base_lines[2:5])]

        changed_lines = base_lines.copy()
        changed_lines[moving_line - 1] = 1 - changed_lines[moving_line - 1]
        changed_lower = TRIGRAM_BY_LINES[tuple(changed_lines[:3])]
        changed_upper = TRIGRAM_BY_LINES[tuple(changed_lines[3:])]
        is_upper_moving = moving_line > 3
        ti = lower if is_upper_moving else upper
        yong = upper if is_upper_moving else lower

        def line_text(lines: list[int]) -> str:
            return "".join("阳" if value == 1 else "阴" for value in lines)

        return {
            "seed": int(occurred_at.strftime("%Y%m%d%H")),
            "upper_trigram": upper.name,
            "lower_trigram": lower.name,
            "base_gua": f"上{upper.name}下{lower.name}",
            "mutual_gua": f"上{hu_upper.name}下{hu_lower.name}",
            "changed_gua": f"上{changed_upper.name}下{changed_lower.name}",
            "moving_line": moving_line,
            "moving_line_name": MOVING_LINE_NAMES[moving_line],
            "base_line_pattern": line_text(base_lines),
            "changed_line_pattern": line_text(changed_lines),
            "symbol": f"{upper.symbol}{lower.symbol}",
            "element_hint": f"{upper.element}/{lower.element}",
            "ti_gua": ti.name,
            "yong_gua": yong.name,
            "relation": self._wuxing_relation(ti.element, yong.element),
            "formula_inputs": {
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "topic_length": len(topic),
            },
        }

    @staticmethod
    def _build_meihua_fallback(topic: str, gua: dict[str, Any]) -> str:
        return (
            f"占题重述：围绕“{topic}”进行短期起卦解读。\n"
            f"短期倾向：本卦{gua['base_gua']}，互卦{gua['mutual_gua']}，近期更适合先稳住节奏再推进关键动作。\n"
            f"关键变数：动爻在{gua['moving_line_name']}，说明执行顺序和沟通方式是主要变量。\n"
            f"体用关系：体卦{gua['ti_gua']}、用卦{gua['yong_gua']}，当前关系为{gua['relation']}。\n"
            "宜：先确认事实、先小步验证、保留调整余地。\n"
            "忌：情绪化拍板、一次性押注、忽略外部反馈。\n"
            "行动建议：先列出3个可控动作，48小时内完成第一步并复盘。"
        )

    @staticmethod
    def _wuxing_relation(ti_element: str, yong_element: str) -> str:
        relations = {
            "金": {"金": "比和", "木": "体克用", "水": "体生用", "火": "用克体", "土": "用生体"},
            "木": {"木": "比和", "土": "体克用", "火": "体生用", "金": "用克体", "水": "用生体"},
            "水": {"水": "比和", "火": "体克用", "木": "体生用", "土": "用克体", "金": "用生体"},
            "火": {"火": "比和", "金": "体克用", "土": "体生用", "水": "用克体", "木": "用生体"},
            "土": {"土": "比和", "水": "体克用", "金": "体生用", "木": "用克体", "火": "用生体"},
        }
        return relations.get(ti_element, {}).get(yong_element, "比和")


def get_divination_service() -> DivinationService:
    service = current_app.extensions.get("divination_service")
    if service:
        return service

    service = DivinationService(
        izthon_src_path=current_app.config["IZTHON_SRC_PATH"],
        default_provider=current_app.config["LLM_PROVIDER"],
        default_model=current_app.config["LLM_MODEL"],
        request_timeout_s=current_app.config["REQUEST_TIMEOUT_S"],
        llm_max_retries=current_app.config["LLM_MAX_RETRIES"],
        provider_config={
            "LLM_MODEL": current_app.config.get("LLM_MODEL", ""),
            "VOLCANO_API_KEY": current_app.config.get("VOLCANO_API_KEY", ""),
            "VOLCANO_MODEL": current_app.config.get("VOLCANO_MODEL", ""),
            "ALIYUN_API_KEY": current_app.config.get("ALIYUN_API_KEY", ""),
            "ALIYUN_BASE_URL": current_app.config.get("ALIYUN_BASE_URL", ""),
            "DEEPSEEK_API_KEY": current_app.config.get("DEEPSEEK_API_KEY", ""),
            "DEEPSEEK_BASE_URL": current_app.config.get("DEEPSEEK_BASE_URL", ""),
            "ZHIPU_API_KEY": current_app.config.get("ZHIPU_API_KEY", ""),
            "QWEN_API_KEY": current_app.config.get("QWEN_API_KEY", ""),
            "QWEN_BASE_URL": current_app.config.get("QWEN_BASE_URL", ""),
        },
    )
    current_app.extensions["divination_service"] = service
    return service
