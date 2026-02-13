from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

from flask import current_app

from app.llm_providers import create_provider
from app.llm_providers.base import UnsupportedToolCallingError
from app.services.ziwei_service import ZiweiService
from app.utils.errors import AppError


ALL_MVP_SCHOOLS = ["ziwei", "meihua", "daily_card", "actionizer", "philosophy"]
DISCLAIMER_ORDER = {"none": 0, "light": 1, "strong": 2}
MAX_TOOL_ROUNDS = 8
TOOL_DISPLAY_NAMES = {
    "safety_guard_precheck": "安全预检",
    "safety_guard_postcheck": "安全后检",
    "ziwei_long_reading": "紫微长线工具",
    "meihua_short_reading": "梅花短线工具",
    "daily_card": "每日卡片工具",
    "philosophy_guidance": "心法解读工具",
    "actionizer": "行动化工具",
}

# ---------------------------------------------------------------------------
# 路由关键词集合（扩充版，减少用户常见表达漏匹配）
# ---------------------------------------------------------------------------
LONG_TERM_KEYWORDS = {
    "人生", "长期", "未来", "几年", "走势", "格局", "大运", "规划", "命盘",
    "事业方向", "婚姻长期", "十年", "五年", "三年", "老了", "晚年", "一辈子",
    "下半年", "明年", "后年", "长远", "趋势", "方向", "终身", "整体运势",
    "大局", "人生规划", "一生", "前途", "前景", "命运", "总体",
}
SHORT_TERM_KEYWORDS = {
    "今天", "明天", "本周", "这周", "近期", "这次", "要不要", "面试", "告白",
    "考试", "短期", "下周", "最近", "马上", "这件事", "应该去吗", "合适吗",
    "该不该", "能不能", "行不行", "适不适合", "这个月", "接下来", "眼前",
    "当下", "目前", "来得及吗", "赶得上吗", "约会", "相亲", "出差", "签合同",
    "谈判", "投简历", "答辩", "开会", "求职", "入职",
}
EMOTION_KEYWORDS = {
    "焦虑", "压力", "内耗", "迷茫", "难过", "情绪", "害怕", "自我成长", "修心",
    "心烦", "失眠", "不开心", "委屈", "无力感", "抑郁", "烦躁", "崩溃",
    "痛苦", "纠结", "恐惧", "自卑", "孤独", "空虚", "疲惫", "心累",
    "想哭", "受不了", "撑不住", "不想动", "没动力", "心态", "情绪低落",
}
DAILY_KEYWORDS = {
    "每日", "日卡", "今日宜忌", "今日运势", "今天适合", "日运", "晨间",
    "今天做什么", "明日运势", "今天运气", "今天注意什么", "今日提醒",
}
TAROT_KEYWORDS = {"塔罗", "牌阵", "抽牌", "西方占卜"}

S4_KEYWORDS = {
    "杀人", "报复", "炸药", "诈骗", "黑客攻击", "贩毒",
    "如何犯罪", "袭击", "伤害他人",
}
S3_MENTAL_CRISIS_KEYWORDS = {"自杀", "自残", "不想活", "结束生命", "轻生", "割腕"}
S3_MEDICAL_KEYWORDS = {"处方", "诊断", "确诊", "药量", "吃什么药", "医学治疗", "治疗方案"}
S2_FINANCE_KEYWORDS = {
    "股票", "基金", "币圈", "杠杆", "做空", "抄底",
    "买入", "卖出", "仓位", "止盈", "止损",
}
S1_LIFE_DECISION_KEYWORDS = {"离婚", "结婚", "辞职", "跳槽", "搬家", "创业", "分手"}

ABSOLUTE_PHRASES = ("一定", "必须", "不做就会出事", "保证赚钱", "必然发生")


@dataclass
class SafetyDecision:
    """安全审查决策结果。"""

    risk_level: str
    decision: str
    reasons: list[str]
    constraints: list[str]
    disclaimer_level: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "decision": self.decision,
            "reasons": self.reasons,
            "constraints": self.constraints,
            "disclaimer_level": self.disclaimer_level,
        }


@dataclass
class RoutingResult:
    """意图路由结果。"""

    intent: str
    skills: list[str]
    reasons: list[str]


@dataclass
class ToolSpec:
    """工具规格定义。"""

    name: str
    description: str
    json_schema: dict[str, Any]
    handler: Callable[[dict[str, Any], dict[str, Any], str, str], str]
    fallback_skill: str | None = None


class OracleOrchestratorService:
    """多智能体咨询台编排服务。"""

    def __init__(
        self,
        default_provider: str,
        default_model: str,
        request_timeout_s: int,
        llm_max_retries: int,
        izthon_src_path: str,
        east_only_mvp: bool = True,
    ):
        self.default_provider = default_provider
        self.default_model = default_model
        self.request_timeout_s = request_timeout_s
        self.llm_max_retries = llm_max_retries
        self.east_only_mvp = east_only_mvp
        self.ziwei_service = ZiweiService(izthon_src_path)
        self.tool_registry = self._build_tool_registry()

    # ------------------------------------------------------------------
    # 公开入口
    # ------------------------------------------------------------------

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """同步聊天入口。"""
        return self._run_chat(payload, event_callback=None)

    def chat_stream(
        self,
        payload: dict[str, Any],
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """流式聊天入口。"""
        return self._run_chat(payload, event_callback=event_callback)

    def chat_with_tools(
        self,
        payload: dict[str, Any],
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """工具调用聊天入口。"""
        return self._run_chat(payload, event_callback=event_callback)

    # ------------------------------------------------------------------
    # 核心流程
    # ------------------------------------------------------------------

    def _run_chat(
        self,
        payload: dict[str, Any],
        event_callback: Callable[[str, dict[str, Any]], None] | None,
    ) -> dict[str, Any]:
        provider_name = payload.get("provider", self.default_provider)
        model_name = payload.get("model", self.default_model)
        self._emit_event(event_callback, "session_start", {"provider": provider_name, "model": model_name})

        try:
            result = self._chat_with_tool_calling(
                payload=payload,
                provider_name=provider_name,
                model_name=model_name,
                event_callback=event_callback,
            )
        except (UnsupportedToolCallingError, AppError, RuntimeError) as exc:
            fallback_reason = str(exc)
            result = self._chat_with_fallback_router(
                payload=payload,
                provider_name=provider_name,
                model_name=model_name,
                event_callback=event_callback,
                fallback_reason=fallback_reason,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            result = self._chat_with_fallback_router(
                payload=payload,
                provider_name=provider_name,
                model_name=model_name,
                event_callback=event_callback,
                fallback_reason=str(exc),
            )

        final_payload = {
            "answer_text": result["answer_text"],
            "follow_up_questions": result["follow_up_questions"][:3],
            "action_items": result["action_items"][:5],
            "safety_disclaimer_level": result["safety_disclaimer_level"],
            "tool_events": result.get("tool_events", []),
            "trace": result.get("trace", []),
        }
        self._emit_event(
            event_callback,
            "final",
            {
                "answer_text": final_payload["answer_text"],
                "follow_up_questions": final_payload["follow_up_questions"],
                "action_items": final_payload["action_items"],
                "safety_disclaimer_level": final_payload["safety_disclaimer_level"],
            },
        )
        self._emit_event(event_callback, "done", {})
        return final_payload

    def _chat_with_tool_calling(
        self,
        payload: dict[str, Any],
        provider_name: str,
        model_name: str,
        event_callback: Callable[[str, dict[str, Any]], None] | None,
    ) -> dict[str, Any]:
        user_query = payload["user_query"]
        enabled_schools = self._normalize_enabled_schools(payload.get("enabled_schools"))
        tool_events: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []

        pre_start = time.perf_counter()
        pre_check = self._safety_check(user_query)
        pre_elapsed = int((time.perf_counter() - pre_start) * 1000)
        self._append_tool_event(
            tool_events=tool_events,
            event_callback=event_callback,
            tool_name="safety_guard_precheck",
            status="success",
            elapsed_ms=pre_elapsed,
            source="tool_calling",
        )
        trace.append({"stage": "pre_safety", "result": pre_check.as_dict()})

        if pre_check.decision == "refuse":
            refusal = self._build_refusal_payload(pre_check, trace)
            refusal["tool_events"] = tool_events
            return refusal

        provider = create_provider(provider_name, model_name)
        allowed_specs = self._build_enabled_tool_specs(enabled_schools)
        allowed_tool_names = {spec.name for spec in allowed_specs}
        messages = self._build_orchestrator_messages(
            payload=payload,
            enabled_schools=enabled_schools,
            enabled_tool_names=[spec.name for spec in allowed_specs],
        )
        tools = self._build_tools_for_provider(allowed_specs)
        specialist_outputs: dict[str, str] = {}
        trace.append(
            {
                "stage": "tool_config",
                "enabled_schools": enabled_schools,
                "enabled_tools": sorted(allowed_tool_names),
            }
        )

        answer_text = ""
        reached_final = False
        for _ in range(MAX_TOOL_ROUNDS):
            tool_result = provider.chat_with_tools(
                messages=messages,
                tools=tools,
                timeout_s=self.request_timeout_s,
            )

            if tool_result.tool_calls:
                assistant_tool_calls: list[dict[str, Any]] = []
                for tool_call in tool_result.tool_calls:
                    assistant_tool_calls.append(
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
                            },
                        }
                    )
                messages.append({"role": "assistant", "content": tool_result.content or "", "tool_calls": assistant_tool_calls})

                for tool_call in tool_result.tool_calls:
                    spec = self.tool_registry.get(tool_call.name)
                    if not spec or spec.name not in allowed_tool_names:
                        started_at = time.perf_counter()
                        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                        self._append_tool_event(
                            tool_events=tool_events,
                            event_callback=event_callback,
                            tool_name=tool_call.name,
                            status="error",
                            elapsed_ms=elapsed_ms,
                            source="tool_calling",
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_call.name,
                                "content": f"tool disabled: {tool_call.name}",
                            }
                        )
                        continue
                    started_at = time.perf_counter()
                    self._append_tool_event(
                        tool_events=tool_events,
                        event_callback=event_callback,
                        tool_name=spec.name,
                        status="running",
                        source="tool_calling",
                    )
                    try:
                        parsed_args = self._validate_tool_arguments(spec, tool_call.arguments)
                        tool_output = spec.handler(payload, parsed_args, provider_name, model_name)
                        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                        specialist_outputs[spec.name] = tool_output
                        self._append_tool_event(
                            tool_events=tool_events,
                            event_callback=event_callback,
                            tool_name=spec.name,
                            status="success",
                            elapsed_ms=elapsed_ms,
                            source="tool_calling",
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": spec.name,
                                "content": tool_output,
                            }
                        )
                    except Exception as exc:
                        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                        self._append_tool_event(
                            tool_events=tool_events,
                            event_callback=event_callback,
                            tool_name=spec.name,
                            status="error",
                            elapsed_ms=elapsed_ms,
                            source="tool_calling",
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": spec.name,
                                "content": f"tool error: {exc}",
                            }
                        )
                continue

            answer_text = (tool_result.content or "").strip()
            if answer_text:
                reached_final = True
                break

        if not reached_final:
            raise RuntimeError("tool-calling round limit reached")

        intent = self._intent_from_tool_events(tool_events, payload["user_query"])
        mapped_outputs = self._map_specialist_outputs(specialist_outputs)
        action_items = self._build_action_items(intent=intent, query=user_query, specialist_outputs=mapped_outputs)
        follow_up_questions = self._build_follow_up_questions(intent=intent)
        disclaimer_level = pre_check.disclaimer_level
        risk_reminder = self._risk_reminder(disclaimer_level)

        if not answer_text:
            answer_text = self._compose_answer_text(
                intent=intent,
                specialist_outputs=mapped_outputs,
                action_items=action_items,
                follow_up_questions=follow_up_questions,
                risk_reminder=risk_reminder,
            )

        post_start = time.perf_counter()
        post_check = self._safety_check(answer_text)
        post_elapsed = int((time.perf_counter() - post_start) * 1000)
        self._append_tool_event(
            tool_events=tool_events,
            event_callback=event_callback,
            tool_name="safety_guard_postcheck",
            status="success",
            elapsed_ms=post_elapsed,
            source="tool_calling",
        )
        trace.append({"stage": "post_safety", "result": post_check.as_dict()})

        if post_check.decision == "refuse":
            refusal = self._build_refusal_payload(post_check, trace)
            refusal["tool_events"] = tool_events
            return refusal
        if post_check.decision == "rewrite":
            answer_text = self._rewrite_to_safe(answer_text, post_check)

        disclaimer_level = self._max_disclaimer(pre_check.disclaimer_level, post_check.disclaimer_level)
        answer_text = self._ensure_risk_line(answer_text, self._risk_reminder(disclaimer_level))

        return {
            "answer_text": answer_text,
            "follow_up_questions": follow_up_questions[:3],
            "action_items": action_items[:5],
            "safety_disclaimer_level": disclaimer_level,
            "tool_events": tool_events,
            "trace": trace,
        }

    def _chat_with_fallback_router(
        self,
        payload: dict[str, Any],
        provider_name: str,
        model_name: str,
        event_callback: Callable[[str, dict[str, Any]], None] | None,
        fallback_reason: str,
    ) -> dict[str, Any]:
        user_query = payload["user_query"]
        selected_school = payload.get("selected_school", "east")
        enabled_schools = self._normalize_enabled_schools(payload.get("enabled_schools"))

        tool_events: list[dict[str, Any]] = []
        pre_start = time.perf_counter()
        pre_check = self._safety_check(user_query)
        pre_elapsed = int((time.perf_counter() - pre_start) * 1000)
        self._append_tool_event(
            tool_events=tool_events,
            event_callback=event_callback,
            tool_name="safety_guard_precheck",
            status="success",
            elapsed_ms=pre_elapsed,
            source="fallback_router",
        )

        trace: list[dict[str, Any]] = [
            {
                "stage": "pre_safety",
                "skill": "oracle-safety-guardian",
                "result": pre_check.as_dict(),
                "fallback_reason": fallback_reason,
            }
        ]
        if pre_check.decision == "refuse":
            refusal = self._build_refusal_payload(pre_check, trace)
            refusal["tool_events"] = tool_events
            return refusal

        routing = self._route_intent(
            query=user_query,
            selected_school=selected_school,
            enabled_schools=enabled_schools,
        )

        specialist_outputs: dict[str, str] = {}
        for skill in routing.skills:
            spec_name = self._legacy_skill_to_tool_name(skill)
            started_at = time.perf_counter()
            self._append_tool_event(
                tool_events=tool_events,
                event_callback=event_callback,
                tool_name=spec_name,
                status="running",
                source="fallback_router",
            )
            output = self._invoke_skill(
                skill=skill,
                payload=payload,
                intent=routing.intent,
                provider_name=provider_name,
                model_name=model_name,
            )
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            self._append_tool_event(
                tool_events=tool_events,
                event_callback=event_callback,
                tool_name=spec_name,
                status="success",
                elapsed_ms=elapsed_ms,
                source="fallback_router",
            )
            specialist_outputs[skill] = output

        action_items = self._build_action_items(
            intent=routing.intent,
            query=user_query,
            specialist_outputs=specialist_outputs,
        )
        follow_up_questions = self._build_follow_up_questions(intent=routing.intent)

        disclaimer_level = pre_check.disclaimer_level
        risk_reminder = self._risk_reminder(disclaimer_level)
        answer_text = self._compose_answer_text(
            intent=routing.intent,
            specialist_outputs=specialist_outputs,
            action_items=action_items,
            follow_up_questions=follow_up_questions,
            risk_reminder=risk_reminder,
        )

        post_start = time.perf_counter()
        post_check = self._safety_check(answer_text)
        post_elapsed = int((time.perf_counter() - post_start) * 1000)
        self._append_tool_event(
            tool_events=tool_events,
            event_callback=event_callback,
            tool_name="safety_guard_postcheck",
            status="success",
            elapsed_ms=post_elapsed,
            source="fallback_router",
        )
        trace.append({"stage": "post_safety", "skill": "oracle-safety-guardian", "result": post_check.as_dict()})

        if post_check.decision == "refuse":
            refusal = self._build_refusal_payload(post_check, trace)
            refusal["tool_events"] = tool_events
            return refusal
        if post_check.decision == "rewrite":
            answer_text = self._rewrite_to_safe(answer_text, post_check)

        disclaimer_level = self._max_disclaimer(pre_check.disclaimer_level, post_check.disclaimer_level)
        answer_text = self._ensure_risk_line(answer_text, self._risk_reminder(disclaimer_level))

        return {
            "answer_text": answer_text,
            "follow_up_questions": follow_up_questions[:3],
            "action_items": action_items[:5],
            "safety_disclaimer_level": disclaimer_level,
            "tool_events": tool_events,
            "trace": trace,
        }

    # ------------------------------------------------------------------
    # 事件发射
    # ------------------------------------------------------------------

    @staticmethod
    def _emit_event(
        event_callback: Callable[[str, dict[str, Any]], None] | None,
        event_name: str,
        payload: dict[str, Any],
    ) -> None:
        if event_callback:
            event_callback(event_name, payload)

    def _append_tool_event(
        self,
        tool_events: list[dict[str, Any]],
        event_callback: Callable[[str, dict[str, Any]], None] | None,
        tool_name: str,
        status: str,
        source: str,
        elapsed_ms: int | None = None,
    ) -> None:
        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
        event_item = {
            "tool_name": tool_name,
            "display_name": display_name,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "source": source,
        }
        tool_events.append(event_item)

        event_payload = {"tool_name": tool_name, "display_name": display_name}
        if elapsed_ms is not None:
            event_payload["elapsed_ms"] = elapsed_ms
        if status == "running":
            self._emit_event(event_callback, "tool_start", event_payload)
        elif status == "success":
            event_payload["status"] = "success"
            self._emit_event(event_callback, "tool_end", event_payload)
        elif status == "error":
            self._emit_event(event_callback, "tool_error", event_payload)

    # ------------------------------------------------------------------
    # 工具注册与构建
    # ------------------------------------------------------------------

    def _build_tools_for_provider(self, specs: list[ToolSpec] | None = None) -> list[dict[str, Any]]:
        """将 ToolSpec 列表转换为 LLM provider 可用的 tools 描述。"""
        tools: list[dict[str, Any]] = []
        selected_specs = specs if specs is not None else list(self.tool_registry.values())
        for spec in selected_specs:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": spec.json_schema,
                    },
                }
            )
        return tools

    def _validate_tool_arguments(self, spec: ToolSpec, arguments: dict[str, Any]) -> dict[str, Any]:
        """过滤工具参数，只保留 schema 中定义的属性。"""
        if not isinstance(arguments, dict):
            return {}
        allowed = set(spec.json_schema.get("properties", {}).keys())
        if not allowed:
            return {}
        return {key: value for key, value in arguments.items() if key in allowed}

    # ------------------------------------------------------------------
    # 编排器消息构建（优化版 system prompt + 结构化 user content）
    # ------------------------------------------------------------------

    def _build_orchestrator_messages(
        self,
        payload: dict[str, Any],
        enabled_schools: list[str],
        enabled_tool_names: list[str],
    ) -> list[dict[str, Any]]:
        """构建发送给编排器 LLM 的 messages 列表。"""
        system_prompt = self._build_system_prompt()

        history_summary = payload.get("conversation_history_summary") or ""
        profile_summary = payload.get("user_profile_summary") or ""
        birth_info = payload.get("birth_info")
        birth_str = json.dumps(birth_info, ensure_ascii=False) if birth_info else ""

        user_content_parts = [
            f"## 用户提问\n{payload['user_query']}",
        ]

        if history_summary:
            user_content_parts.append(
                "\n## 对话历史摘要\n"
                f"（请结合历史上下文理解用户的连续性诉求）\n{history_summary}"
            )

        if profile_summary:
            user_content_parts.append(
                "\n## 用户画像\n"
                f"（请根据画像提供个性化建议）\n{profile_summary}"
            )

        if birth_str:
            user_content_parts.append(
                "\n## 出生信息\n"
                f"（可用于紫微排盘等命理分析）\n{birth_str}"
            )

        user_content_parts.append(
            "\n## 可用工具\n"
            f"已启用智能体：{', '.join(enabled_schools) if enabled_schools else '无'}\n"
            f"已启用工具：{', '.join(enabled_tool_names) if enabled_tool_names else '无'}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(user_content_parts)},
        ]

    @staticmethod
    def _build_system_prompt() -> str:
        """构建编排器核心 system prompt，包含角色定义、工作流程和输出规范。"""
        return (
            "# 角色\n"
            "你是 DeepSeek Oracle 多智能体咨询台的中控编排师。\n"
            "你的核心使命是：帮助用户在人生的不确定性中找到可行动的方向，"
            "让每一次对话都既温暖又务实。\n\n"

            "# 性格与语气\n"
            "- 温和而专业：像一位既懂传统智慧又善于倾听的顾问\n"
            "- 共情优先：先理解用户的情绪和处境，再给出分析\n"
            "- 务实不玄学：用现代语言表达传统智慧，避免故弄玄虚\n"
            "- 谦逊坦诚：承认局限性，不做确定性承诺\n\n"

            "# 思考链（在调用工具前先在心中完成）\n"
            "1. 这个人现在最核心的困惑或需求是什么？\n"
            "2. 他/她的情绪状态如何？需要先安抚还是直接给方案？\n"
            "3. 这个问题更偏长期方向还是近期决策？还是情绪疏导？\n"
            "4. 哪些工具组合能给出最有价值的回答？\n"
            "5. 有没有用户提供的出生信息或历史对话需要利用？\n\n"

            "# 工作流程（严格按顺序执行）\n"
            "1. **理解意图**：判断用户核心诉求——\n"
            "   长期规划 / 近期决策 / 每日指引 / 情绪疏导 / 综合咨询\n"
            "2. **选择工具**：根据意图从已启用工具中选择 1-3 个最相关的。\n"
            "   - 涉及人生方向、长期趋势、命盘 => 优先 ziwei_long_reading\n"
            "   - 涉及近期具体事件、该不该做某事 => 优先 meihua_short_reading\n"
            "   - 涉及今日运势、每日提醒 => daily_card\n"
            "   - 涉及情绪困扰、心态调整、自我成长 => philosophy_guidance\n"
            "   - 复杂问题可组合多工具（如紫微+梅花双轨分析），但不超过 3 个\n"
            "   - 获取专家分析后，考虑追加 actionizer 把建议转化为行动清单\n"
            "3. **调用工具**：依次调用，获取各专家领域分析\n"
            "4. **融合输出**：将所有工具结果整合为一份完整、连贯、有温度的回答\n\n"

            "# 最终输出格式（每个部分都必须写）\n\n"
            "**安抚与共情**\n"
            "1-2句，先回应用户的情绪和处境，让对方感到被理解。\n"
            "不要用套话，要针对用户具体情况共情。\n\n"
            "**核心解读**\n"
            "整合各工具分析结果，形成有逻辑的叙述（不是简单罗列工具输出）。\n"
            "要点：\n"
            "- 针对用户的具体问题做有针对性的分析\n"
            "- 如果有多个工具结果，交叉印证，指出趋势的一致性或需要注意的差异\n"
            "- 用用户能理解的现代语言，必要时解释术语含义\n"
            "- 给出具体的时间窗口或阶段划分\n\n"
            "**可执行建议**\n"
            "3-5条具体可落地的行动，每条标明时间节点（今天/本周/本月）。\n"
            "建议要与核心解读逻辑一致，不要泛泛而谈。\n\n"
            "**风险提示**\n"
            "1句温和的提醒，说明这是参考建议。\n\n"
            "**可追问方向**\n"
            "2-3个引导用户深入思考的问题，要与当前话题紧密相关。\n\n"

            "# 铁律（违反任何一条即回答失败）\n"
            "- 严禁绝对化断言：不说 一定/必然/注定，改用 倾向/更适合/可能\n"
            "- 严禁恐惧营销：不渲染灾祸、不制造焦虑、不暗示不做就出事\n"
            "- 严禁越界指导：不给具体投资买卖指令、不做医疗诊断、不提供违法建议\n"
            "- 严禁脱离工具：你必须通过工具获取专业分析，不可凭空编造命理内容\n"
            "- 只调用已启用工具列表中的工具\n"
        )

    # ------------------------------------------------------------------
    # 工具注册表（优化版描述，帮助 LLM 更准确地选择工具）
    # ------------------------------------------------------------------

    def _build_tool_registry(self) -> dict[str, ToolSpec]:
        """构建工具注册表，每个工具包含详细的使用场景描述。"""
        return {
            "safety_guard_precheck": ToolSpec(
                name="safety_guard_precheck",
                description="对用户输入执行安全审查，识别高风险内容（违法、自伤、医疗、金融），返回风险等级与处理策略。",
                json_schema={"type": "object", "properties": {"content": {"type": "string", "description": "需要审查的文本内容"}}},
                handler=self._tool_safety_precheck,
            ),
            "safety_guard_postcheck": ToolSpec(
                name="safety_guard_postcheck",
                description="对生成的回答执行安全审查，确保输出不含绝对化断言、恐惧营销或越界指导。",
                json_schema={"type": "object", "properties": {"content": {"type": "string", "description": "需要审查的回答文本"}}},
                handler=self._tool_safety_postcheck,
            ),
            "ziwei_long_reading": ToolSpec(
                name="ziwei_long_reading",
                description=(
                    "紫微斗数长线趋势解读工具。适用场景：用户询问人生方向、长期规划、整体运势、"
                    "事业发展趋势、感情长期走向、命盘解析等需要结构化长周期分析的问题。"
                    "需要用户提供出生信息才能排盘分析；若无出生信息则给出通用趋势建议。"
                    "输出包含：总论、分领域解读（事业/感情/财富/健康）、关键时间窗口、可执行建议。"
                ),
                json_schema={
                    "type": "object",
                    "properties": {
                        "focus_domain": {
                            "type": "string",
                            "description": "用户关注的领域，如 career/relationship/wealth/health/overall",
                        },
                        "intent": {
                            "type": "string",
                            "description": "分析意图，如 long_term/dual_track",
                        },
                    },
                },
                handler=self._tool_ziwei_long_reading,
                fallback_skill="ziwei",
            ),
            "meihua_short_reading": ToolSpec(
                name="meihua_short_reading",
                description=(
                    "梅花易数短期占断工具。适用场景：用户面临近期具体事件或决策，"
                    "如该不该去面试、这次告白合适吗、本周要不要签合同、近期求职前景等。"
                    "基于问题和时间起卦，分析短期倾向（7天-1个月）。"
                    "输出包含：占题重述、时间窗口、短期倾向、关键变数、宜忌、应对策略。"
                ),
                json_schema={
                    "type": "object",
                    "properties": {
                        "time_window": {
                            "type": "string",
                            "description": "关注的时间范围，如 today/this_week/this_month",
                        },
                        "intent": {
                            "type": "string",
                            "description": "分析意图，如 short_term/decision",
                        },
                    },
                },
                handler=self._tool_meihua_short_reading,
                fallback_skill="meihua",
            ),
            "daily_card": ToolSpec(
                name="daily_card",
                description=(
                    "每日运势卡片工具。适用场景：用户想了解今天的运势、今日宜忌、"
                    "今天适合做什么、每日提醒等轻量级日常指引需求。"
                    "输出固定格式：关键词、今日倾向、今日宜、今日忌、可追问。"
                ),
                json_schema={
                    "type": "object",
                    "properties": {
                        "theme": {
                            "type": "string",
                            "description": "今日主题方向，如 career/relationship/general",
                        },
                    },
                },
                handler=self._tool_daily_card,
                fallback_skill="daily_card",
            ),
            "philosophy_guidance": ToolSpec(
                name="philosophy_guidance",
                description=(
                    "国学心法解读工具。适用场景：用户有情绪困扰（焦虑、迷茫、内耗、压力大）、"
                    "寻求心态调整、自我成长方向、需要精神层面的安慰和引导。"
                    "融合王阳明心学「知行合一」「致良知」等传统智慧，用现代语言给出可实践方法。"
                    "输出包含：核心心法、白话解释、可实践方法（3步）、今日一问。"
                ),
                json_schema={
                    "type": "object",
                    "properties": {
                        "theme": {
                            "type": "string",
                            "description": "情绪或成长主题，如 anxiety/confusion/burnout/growth",
                        },
                    },
                },
                handler=self._tool_philosophy_guidance,
                fallback_skill="philosophy",
            ),
            "actionizer": ToolSpec(
                name="actionizer",
                description=(
                    "行动清单生成工具。适用场景：在获得其他工具的分析结果后，"
                    "将抽象建议转化为具体的、有时间节点的可执行任务清单。"
                    "通常作为最后一个工具调用，与前面的分析结果配合使用。"
                    "输出 3-5 条带时间标记的具体行动步骤。"
                ),
                json_schema={
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "行动化的意图类型，如 long_term/short_term/daily",
                        },
                    },
                },
                handler=self._tool_actionizer,
                fallback_skill="actionizer",
            ),
        }

    # ------------------------------------------------------------------
    # 工具处理器
    # ------------------------------------------------------------------

    def _tool_safety_precheck(
        self,
        payload: dict[str, Any],
        args: dict[str, Any],
        provider_name: str,
        model_name: str,
    ) -> str:
        _ = (provider_name, model_name)
        content = str(args.get("content") or payload.get("user_query") or "")
        return json.dumps(self._safety_check(content).as_dict(), ensure_ascii=False)

    def _tool_safety_postcheck(
        self,
        payload: dict[str, Any],
        args: dict[str, Any],
        provider_name: str,
        model_name: str,
    ) -> str:
        _ = (provider_name, model_name)
        content = str(args.get("content") or payload.get("user_query") or "")
        return json.dumps(self._safety_check(content).as_dict(), ensure_ascii=False)

    def _tool_ziwei_long_reading(
        self,
        payload: dict[str, Any],
        args: dict[str, Any],
        provider_name: str,
        model_name: str,
    ) -> str:
        intent = str(args.get("intent") or "long_term")
        return self._run_ziwei_agent(payload, intent=intent, provider_name=provider_name, model_name=model_name)

    def _tool_meihua_short_reading(
        self,
        payload: dict[str, Any],
        args: dict[str, Any],
        provider_name: str,
        model_name: str,
    ) -> str:
        _ = args
        return self._run_meihua_agent(payload, provider_name=provider_name, model_name=model_name)

    def _tool_daily_card(
        self,
        payload: dict[str, Any],
        args: dict[str, Any],
        provider_name: str,
        model_name: str,
    ) -> str:
        _ = args
        return self._run_daily_card_agent(payload, provider_name=provider_name, model_name=model_name)

    def _tool_philosophy_guidance(
        self,
        payload: dict[str, Any],
        args: dict[str, Any],
        provider_name: str,
        model_name: str,
    ) -> str:
        _ = args
        return self._run_philosophy_agent(payload, provider_name=provider_name, model_name=model_name)

    def _tool_actionizer(
        self,
        payload: dict[str, Any],
        args: dict[str, Any],
        provider_name: str,
        model_name: str,
    ) -> str:
        intent = str(args.get("intent") or "short_term")
        return self._run_actionizer_agent(payload, intent=intent, provider_name=provider_name, model_name=model_name)

    def _map_specialist_outputs(self, specialist_outputs: dict[str, str]) -> dict[str, str]:
        """将工具名映射回学派名以便后续处理。"""
        mapping = {
            "ziwei_long_reading": "ziwei",
            "meihua_short_reading": "meihua",
            "daily_card": "daily_card",
            "philosophy_guidance": "philosophy",
            "actionizer": "actionizer",
        }
        mapped: dict[str, str] = {}
        for tool_name, content in specialist_outputs.items():
            key = mapping.get(tool_name, tool_name)
            mapped[key] = content
        return mapped

    def _intent_from_tool_events(self, tool_events: list[dict[str, Any]], query: str) -> str:
        """从已执行的工具事件中推断意图类型。"""
        tool_names = [item.get("tool_name") for item in tool_events if item.get("status") == "success"]
        if "ziwei_long_reading" in tool_names and "meihua_short_reading" in tool_names:
            return "dual_track"
        if "ziwei_long_reading" in tool_names:
            return "long_term"
        if "daily_card" in tool_names:
            return "daily_card"
        if "philosophy_guidance" in tool_names:
            return "mindset"
        if "meihua_short_reading" in tool_names:
            return "short_term"
        routing = self._route_intent(query=query, selected_school="east", enabled_schools=self._normalize_enabled_schools(None))
        return routing.intent

    @staticmethod
    def _legacy_skill_to_tool_name(skill: str) -> str:
        """学派名到工具名的映射。"""
        mapping = {
            "ziwei": "ziwei_long_reading",
            "meihua": "meihua_short_reading",
            "daily_card": "daily_card",
            "philosophy": "philosophy_guidance",
            "actionizer": "actionizer",
            "tarot": "tarot",
        }
        return mapping.get(skill, skill)

    def _build_enabled_tool_specs(self, enabled_schools: list[str]) -> list[ToolSpec]:
        """根据已启用学派构建可用工具列表。"""
        school_to_tool = {
            "ziwei": "ziwei_long_reading",
            "meihua": "meihua_short_reading",
            "daily_card": "daily_card",
            "philosophy": "philosophy_guidance",
            "actionizer": "actionizer",
        }
        ordered_names: list[str] = ["safety_guard_precheck", "safety_guard_postcheck"]

        for school in enabled_schools:
            tool_name = school_to_tool.get(school)
            if tool_name and tool_name not in ordered_names:
                ordered_names.append(tool_name)

        # Ensure at least one business tool is enabled besides safety checks.
        has_business_tool = any(
            name
            not in {
                "safety_guard_precheck",
                "safety_guard_postcheck",
                "actionizer",
            }
            for name in ordered_names
        )
        if not has_business_tool:
            ordered_names.append("meihua_short_reading")

        specs: list[ToolSpec] = []
        for name in ordered_names:
            spec = self.tool_registry.get(name)
            if spec:
                specs.append(spec)
        return specs

    def _normalize_enabled_schools(self, enabled_schools: list[str] | None) -> list[str]:
        """规范化已启用学派列表。"""
        if enabled_schools:
            normalized = [item for item in enabled_schools if item in ALL_MVP_SCHOOLS or item == "tarot"]
        else:
            normalized = ALL_MVP_SCHOOLS.copy()

        if self.east_only_mvp:
            normalized = [item for item in normalized if item != "tarot"]

        primary_skills = [item for item in normalized if item != "actionizer"]
        if not primary_skills:
            normalized.append("meihua")

        if "actionizer" not in normalized:
            normalized.append("actionizer")
        return normalized

    # ------------------------------------------------------------------
    # 意图路由
    # ------------------------------------------------------------------

    def _route_intent(self, query: str, selected_school: str, enabled_schools: list[str]) -> RoutingResult:
        """基于关键词匹配的意图路由。"""
        lowered = query.lower()

        def has_any(tokens: set[str]) -> bool:
            return any(token in query or token in lowered for token in tokens)

        if has_any(DAILY_KEYWORDS) and "daily_card" in enabled_schools:
            return RoutingResult("daily_card", self._with_actionizer(["daily_card"], enabled_schools), ["命中每日卡片意图"])

        has_long = has_any(LONG_TERM_KEYWORDS)
        has_short = has_any(SHORT_TERM_KEYWORDS)
        has_emotion = has_any(EMOTION_KEYWORDS)
        has_tarot = has_any(TAROT_KEYWORDS)

        if has_tarot and selected_school in {"west", "mixed"} and "tarot" in enabled_schools:
            return RoutingResult("symbolic", self._with_actionizer(["tarot"], enabled_schools), ["命中塔罗/象征关键词"])

        if has_long and has_short and "ziwei" in enabled_schools and "meihua" in enabled_schools:
            return RoutingResult(
                "dual_track",
                self._with_actionizer(["meihua", "ziwei"], enabled_schools),
                ["长短线同时命中，采用双轨回答"],
            )

        if has_long and "ziwei" in enabled_schools:
            skills = ["ziwei"]
            if has_emotion and "philosophy" in enabled_schools:
                skills.insert(1, "philosophy")
            return RoutingResult("long_term", self._with_actionizer(skills[:3], enabled_schools), ["命中长期规划关键词"])
        if has_long and "ziwei" not in enabled_schools and "meihua" in enabled_schools:
            return RoutingResult(
                "short_term",
                self._with_actionizer(["meihua"], enabled_schools),
                ["命中长期关键词但紫微未启用，降级到梅花策略"],
            )

        if has_short and "meihua" in enabled_schools:
            return RoutingResult("short_term", self._with_actionizer(["meihua"], enabled_schools), ["命中短期事件关键词"])
        if has_short and "meihua" not in enabled_schools and "ziwei" in enabled_schools:
            return RoutingResult(
                "long_term",
                self._with_actionizer(["ziwei"], enabled_schools),
                ["命中短期关键词但梅花未启用，降级到紫微趋势"],
            )

        if has_emotion and "philosophy" in enabled_schools:
            return RoutingResult("mindset", self._with_actionizer(["philosophy"], enabled_schools), ["命中情绪/成长关键词"])

        if "meihua" in enabled_schools:
            return RoutingResult("short_term", self._with_actionizer(["meihua"], enabled_schools), ["默认走短期策略"])
        if "ziwei" in enabled_schools:
            return RoutingResult("long_term", self._with_actionizer(["ziwei"], enabled_schools), ["默认走长期趋势策略"])
        if "philosophy" in enabled_schools:
            return RoutingResult("mindset", self._with_actionizer(["philosophy"], enabled_schools), ["默认走心法建议策略"])
        if "daily_card" in enabled_schools:
            return RoutingResult("daily_card", self._with_actionizer(["daily_card"], enabled_schools), ["默认走每日卡片策略"])
        return RoutingResult("short_term", self._with_actionizer(["meihua"], enabled_schools), ["无有效技能配置，回退到梅花短线"])

    @staticmethod
    def _with_actionizer(skills: list[str], enabled_schools: list[str]) -> list[str]:
        """确保 actionizer 排在技能列表末尾。"""
        unique_skills: list[str] = []
        for skill in skills:
            if skill in enabled_schools and skill not in unique_skills:
                unique_skills.append(skill)
        if "actionizer" in enabled_schools and "actionizer" not in unique_skills:
            unique_skills.append("actionizer")
        return unique_skills

    def _invoke_skill(
        self,
        skill: str,
        payload: dict[str, Any],
        intent: str,
        provider_name: str,
        model_name: str,
    ) -> str:
        """根据学派名分派到对应的 agent 方法。"""
        if skill == "ziwei":
            return self._run_ziwei_agent(payload, intent, provider_name, model_name)
        if skill == "meihua":
            return self._run_meihua_agent(payload, provider_name, model_name)
        if skill == "tarot":
            return self._run_tarot_agent(payload, provider_name, model_name)
        if skill == "daily_card":
            return self._run_daily_card_agent(payload, provider_name, model_name)
        if skill == "philosophy":
            return self._run_philosophy_agent(payload, provider_name, model_name)
        if skill == "actionizer":
            return self._run_actionizer_agent(payload, intent, provider_name, model_name)
        return ""

    # ------------------------------------------------------------------
    # 各专家 Agent prompt（优化版：增加深度、推理框架、结构化输出）
    # ------------------------------------------------------------------

    def _run_ziwei_agent(
        self,
        payload: dict[str, Any],
        intent: str,
        provider_name: str,
        model_name: str,
    ) -> str:
        """紫微斗数长线解读 agent。"""
        query = payload["user_query"]
        profile = payload.get("user_profile_summary", "")
        history = payload.get("conversation_history_summary", "")
        chart_summary = self._build_chart_summary(payload.get("birth_info"))

        fallback = (
            "【总论】\n"
            "当前阶段的整体格局倾向于稳中求进。你正处在一个需要打好基础、"
            "理清方向的过渡期，与其急于突破，不如先把手头资源梳理清楚。\n\n"
            "【分领域解读】\n"
            "- 事业：适合先巩固现有成果，再寻找扩展机会。避免同时开太多战线。\n"
            "- 感情：重沟通质量与情感边界。主动表达需求比等待对方猜测更有效。\n"
            "- 财富：宜做风险分层，保守配置为主体，适度尝试为辅。\n"
            "- 健康：规律作息是根基。注意季节交替时的身体信号。\n\n"
            "【关键时间窗口】\n"
            "1. 近期1-3个月：更适合梳理方向和整合资源\n"
            "2. 中期3-6个月：条件成熟后可推进关键决策\n"
            "3. 如遇外部不确定因素，优先控制节奏而非加速\n\n"
            "【可执行建议】\n"
            "1. 明确本年度最核心的一条主线目标\n"
            "2. 每周做一次简短复盘，记录进展与偏差\n"
            "3. 保留20%的时间和精力作为机动空间"
        )

        prompt = (
            "# 角色\n"
            "你是紫微斗数长线解读专家，擅长从命盘结构中提取人生趋势、节奏和关键转折。\n\n"

            "# 解读原则\n"
            "- 只做趋势判断与结构分析，不做确定性预言\n"
            "- 不渲染灾祸、不制造恐惧、不宿命化\n"
            "- 用现代人能理解的语言解释命理术语\n"
            "- 给出的建议必须可落地、可执行\n\n"

            "# 推理步骤\n"
            "1. 先整体判断命盘格局特征和当前大运/流年的核心主题\n"
            "2. 分析事业、感情、财富、健康四个维度的趋势\n"
            "3. 结合用户具体问题，识别最关键的 2-3 个时间窗口\n"
            "4. 将分析结论转化为用户可执行的建议\n\n"

            f"# 输入信息\n"
            f"用户问题：{query}\n"
            f"分析意图：{intent}\n"
            f"用户画像：{profile or '暂无'}\n"
            f"对话历史：{history or '暂无'}\n"
            f"命盘摘要：\n{chart_summary or '暂无（无出生信息，请给出通用趋势建议）'}\n\n"

            "# 输出格式（严格按此结构）\n"
            "【总论】\n（2-3句概括整体格局和当前阶段特点）\n\n"
            "【分领域解读】\n"
            "- 事业：（具体分析）\n"
            "- 感情：（具体分析）\n"
            "- 财富：（具体分析）\n"
            "- 健康：（具体分析）\n\n"
            "【关键时间窗口】\n（列出3个关键时间节点及适合的策略）\n\n"
            "【可执行建议】\n（3条具体行动，标明时间）\n\n"
            "【可追问方向】\n（3个可以深入的话题）"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_meihua_agent(self, payload: dict[str, Any], provider_name: str, model_name: str) -> str:
        """梅花易数短期占断 agent。"""
        query = payload["user_query"]
        history = payload.get("conversation_history_summary", "")
        profile = payload.get("user_profile_summary", "")

        fallback = (
            "【占题重述】\n"
            "围绕你当前最关心的近期事件，判断短期走向与最优应对策略。\n\n"
            "【时间窗口】\n未来7天-1个月内。\n\n"
            "【短期倾向】\n"
            "整体节奏可以推进，但更适合先稳后快。"
            "前半段适合确认信息和准备，后半段适合关键行动。\n\n"
            "【关键变数】\n"
            "1. 沟通质量：表达的清晰度直接影响结果\n"
            "2. 信息完整度：决策前确保掌握关键事实\n"
            "3. 执行节奏：连贯的行动比突击式努力更有效\n\n"
            "【宜】\n"
            "- 先确认关键事实，再做决定\n"
            "- 小步试探，根据反馈调整\n"
            "- 保留调整余地，不把路走死\n\n"
            "【忌】\n"
            "- 在情绪波动时做最终拍板\n"
            "- 一次性押注，不留退路\n"
            "- 忽略外部反馈，只看自己感觉\n\n"
            "【应对策略】\n"
            "先做低成本试探（如先聊一次、先提交初稿），"
            "再根据反馈做二次决策。"
        )

        prompt = (
            "# 角色\n"
            "你是梅花易数短期占断专家，擅长分析近期具体事件的走向和最优应对策略。\n\n"

            "# 占断原则\n"
            "- 聚焦短期（7天到1个月），给出时间窗口明确的判断\n"
            "- 避免绝对化，用「更适合」「倾向于」「需要留意」等表述\n"
            "- 宜忌要具体可操作，不要只说「宜谨慎」这种空话\n"
            "- 关键变数要指出用户自己可控的因素\n\n"

            "# 推理步骤\n"
            "1. 先把用户的问题重述为一个清晰的占题\n"
            "2. 判断事件的短期走向（顺/逆/转折）\n"
            "3. 识别影响结果的 2-3 个关键变数\n"
            "4. 给出具体的宜忌和应对策略\n\n"

            f"# 输入信息\n"
            f"用户问题：{query}\n"
            f"对话历史：{history or '暂无'}\n"
            f"用户画像：{profile or '暂无'}\n\n"

            "# 输出格式（严格按此结构）\n"
            "【占题重述】\n（用一句话清晰描述要占断的核心问题）\n\n"
            "【时间窗口】\n（明确分析覆盖的时间范围）\n\n"
            "【短期倾向】\n（2-3句概括走势，包含阶段划分）\n\n"
            "【关键变数】\n（列出2-3个影响结果的关键因素，标明可控/不可控）\n\n"
            "【宜】\n（3条具体可操作的「应该做」）\n\n"
            "【忌】\n（3条具体可操作的「应该避免」）\n\n"
            "【应对策略】\n（1段话，给出整体应对思路和节奏建议）"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_tarot_agent(self, payload: dict[str, Any], provider_name: str, model_name: str) -> str:
        """塔罗象征解读 agent。"""
        query = payload["user_query"]
        profile = payload.get("user_profile_summary", "")

        fallback = (
            "【象征解读】\n"
            "你当前正处在一个收束旧模式、建立新节奏的过渡阶段。"
            "旧的方式已经不再完全适用，但新的模式尚未完全成型。\n\n"
            "【情绪镜像】\n"
            "你感受到的焦虑更多来自不确定性本身，而不是你的能力不足。"
            "这种不确定感其实是变化的前兆，说明你正在走出舒适区。\n\n"
            "【行动建议】\n"
            "- 先处理当下最紧迫的一件事，完成它会给你信心\n"
            "- 安排一次坦诚的对话来澄清困惑\n"
            "- 给自己设定一个小小的里程碑，完成后奖励自己\n\n"
            "【提醒】\n"
            "保持现实验证的习惯，不要把任何单次解读当作确定结论。"
        )

        prompt = (
            "# 角色\n"
            "你是塔罗象征解读顾问，用温暖的象征语言帮助用户理解内在状态与行动选择。\n\n"

            "# 解读原则\n"
            "- 用象征和隐喻帮助用户看见自己的处境\n"
            "- 重点关注情绪镜像：帮用户理解自己感受的来源\n"
            "- 行动建议要温和但具体\n"
            "- 始终提醒保持现实验证\n\n"

            f"# 输入信息\n"
            f"用户问题：{query}\n"
            f"用户画像：{profile or '暂无'}\n\n"

            "# 输出格式\n"
            "【象征解读】\n（用象征语言描述用户当前的处境和阶段）\n\n"
            "【情绪镜像】\n（帮用户理解当前情绪的来源和含义）\n\n"
            "【行动建议】\n（3条温和但具体的行动）\n\n"
            "【提醒】\n（1句关于保持现实验证的提醒）"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_daily_card_agent(self, payload: dict[str, Any], provider_name: str, model_name: str) -> str:
        """每日卡片生成 agent。"""
        query = payload["user_query"]
        profile = payload.get("user_profile_summary", "")
        history = payload.get("conversation_history_summary", "")

        fallback = (
            "【今日关键词】收心、聚焦、留白\n\n"
            "【今日倾向】\n"
            "今天的整体节奏更适合专注做好一件高价值的事情，"
            "不宜同时铺开太多战线。把精力集中在最关键的那一件上。\n\n"
            "【今日宜】\n"
            "- 上午：处理今天最难或最重要的事项（精力最充沛时做最难的事）\n"
            "- 下午：做一次沟通收尾或信息确认\n"
            "- 晚间：花15分钟做简短复盘，写下今天做对了什么\n\n"
            "【今日忌】\n"
            "- 在情绪波动时临时推翻已有安排\n"
            "- 因为焦虑而同时启动多个任务\n"
            "- 忽略休息信号\n\n"
            "【可追问】\n"
            "「我今天更适合推进事业方面、还是处理人际关系方面的事情？」"
        )

        prompt = (
            "# 角色\n"
            "你是每日运势卡片编排师，为用户提供温暖、实用的每日指引。\n\n"

            "# 编排原则\n"
            "- 关键词要精炼有力（2-3个词）\n"
            "- 宜忌要具体到时间段和行为，不要空泛\n"
            "- 语气温暖但务实，像朋友般的提醒\n"
            "- 如果有用户画像或历史，要做个性化调整\n\n"

            f"# 输入信息\n"
            f"用户问题：{query}\n"
            f"用户画像：{profile or '暂无'}\n"
            f"对话历史：{history or '暂无'}\n\n"

            "# 输出格式（严格按此结构）\n"
            "【今日关键词】（2-3个精炼关键词）\n\n"
            "【今日倾向】\n（2-3句概括今天的整体节奏和重心）\n\n"
            "【今日宜】\n（3条具体到时间段的建议：上午/下午/晚间各1条）\n\n"
            "【今日忌】\n（2-3条具体要避免的行为）\n\n"
            "【可追问】\n（1个引导用户深入的问题）"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_philosophy_agent(self, payload: dict[str, Any], provider_name: str, model_name: str) -> str:
        """心法解读 agent。"""
        query = payload["user_query"]
        profile = payload.get("user_profile_summary", "")
        history = payload.get("conversation_history_summary", "")

        fallback = (
            "【核心心法】知行合一、致良知\n\n"
            "【白话解释】\n"
            "先回到内心最真实的判断，问自己：「这件事，我内心深处的真实感受是什么？」\n"
            "然后把这个判断落实到一个具体行动上，哪怕很小也好。\n"
            "不空想（只想不做），也不蛮干（只做不想）。\n\n"
            "【可实践方法】\n"
            "1. 拿出纸，写下此刻最真实的顾虑和期待各1条（5分钟内完成）\n"
            "2. 用一个简单标准筛选当下的选择：这个决定是否更接近我内心的良知？\n"
            "3. 立刻执行一个10分钟内可完成的小动作，体验知行同步的感觉\n\n"
            "【心学脉络】\n"
            "王阳明心学的核心是「反求诸己」——答案不在外部条件里，而在你内心的觉察中。\n"
            "当外部信息太多太杂时，试着回到内心，问自己最真实的声音。\n\n"
            "【今日一问】\n"
            "我现在面临的这个选择，是否既对得起内心的真实感受，又能落到具体的现实行动？"
        )

        prompt = (
            "# 角色\n"
            "你是国学心法解读顾问，融合王阳明心学、陆九渊心学脉络，"
            "用现代人能理解的语言提供情绪疏导和心态调整。\n\n"

            "# 解读原则\n"
            "- 核心心法要言简意赅，直击要害\n"
            "- 白话解释要让没有哲学背景的人也能立刻理解\n"
            "- 可实践方法必须具体到步骤和时间（如「5分钟内完成」「10分钟可做」）\n"
            "- 今日一问要有思考深度，引导用户自我觉察\n"
            "- 语气温暖共情，不说教\n\n"

            "# 推理步骤\n"
            "1. 先理解用户当前的情绪状态和核心困惑\n"
            "2. 从心学体系中找到最契合的心法\n"
            "3. 翻译成现代人能实践的方法\n"
            "4. 设计一个引导自我觉察的问题\n\n"

            f"# 输入信息\n"
            f"用户问题：{query}\n"
            f"用户画像：{profile or '暂无'}\n"
            f"对话历史：{history or '暂无'}\n\n"

            "# 输出格式（严格按此结构）\n"
            "【核心心法】（一句概括最核心的智慧）\n\n"
            "【白话解释】\n（用日常语言解释这个心法，3-4句）\n\n"
            "【可实践方法】\n（3步，每步标明时间和具体做法）\n\n"
            "【心学脉络】\n（简述这个心法的思想源流，帮助用户加深理解）\n\n"
            "【今日一问】\n（一个引导自我觉察的好问题）"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_actionizer_agent(
        self,
        payload: dict[str, Any],
        intent: str,
        provider_name: str,
        model_name: str,
    ) -> str:
        """行动清单生成 agent。"""
        query = payload["user_query"]
        history = payload.get("conversation_history_summary", "")

        fallback = (
            "【行动清单】\n"
            "1. 今天：完成一个可交付的小目标，哪怕只用30分钟\n"
            "   - 为什么：完成感能打破内耗循环\n"
            "2. 今天：预留30分钟做一次信息核对或沟通\n"
            "   - 为什么：确认关键事实能避免走弯路\n"
            "3. 今晚：花10分钟记录今天的进展与偏差\n"
            "   - 为什么：复盘让明天的决策更精准\n"
        )

        prompt = (
            "# 角色\n"
            "你是行动化顾问，把抽象的建议和分析转化为具体的、可执行的行动清单。\n\n"

            "# 转化原则\n"
            "- 每条行动必须标明时间（今天/明天/本周/本月）\n"
            "- 行动必须具体到可以直接开始做，不要模糊\n"
            "- 为每条行动附上简短理由（为什么要做这个）\n"
            "- 语气温和，像朋友建议而非命令\n"
            "- 行动排序要合理：先确认信息 > 小步试探 > 推进执行 > 复盘调整\n\n"

            f"# 输入信息\n"
            f"用户问题：{query}\n"
            f"分析意图：{intent}\n"
            f"对话历史：{history or '暂无'}\n\n"

            "# 输出格式\n"
            "【行动清单】\n"
            "1. [时间]：[具体行动]\n"
            "   - 为什么：[简短理由]\n"
            "2. [时间]：[具体行动]\n"
            "   - 为什么：[简短理由]\n"
            "3. [时间]：[具体行动]\n"
            "   - 为什么：[简短理由]\n"
            "（最多5条）"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    # ------------------------------------------------------------------
    # LLM 调用与兜底
    # ------------------------------------------------------------------

    def _complete_with_fallback(
        self,
        prompt: str,
        fallback: str,
        temperature_safe: bool,
        provider_name: str,
        model_name: str,
    ) -> str:
        """调用 LLM 生成回答，失败时返回 fallback 文本。"""
        if provider_name == "mock":
            return fallback

        response_text = ""
        for attempt in range(self.llm_max_retries + 1):
            try:
                provider = create_provider(provider_name, model_name)
                response = provider.generate(prompt, timeout_s=self.request_timeout_s)
                response_text = (response.content or "").strip()
                if response_text:
                    break
            except AppError:
                if attempt < self.llm_max_retries:
                    time.sleep(2**attempt)
                    continue
                break
            except Exception:
                if attempt < self.llm_max_retries:
                    time.sleep(2**attempt)
                    continue
                break

        if not response_text:
            return fallback

        if temperature_safe:
            response_text = self._rewrite_absolute_to_probabilistic(response_text)
        return response_text

    # ------------------------------------------------------------------
    # 命盘摘要构建
    # ------------------------------------------------------------------

    def _build_chart_summary(self, birth_info: dict[str, Any] | None) -> str:
        """根据出生信息构建紫微命盘文本摘要。"""
        if not birth_info:
            return ""
        try:
            astrolabe_data = self.ziwei_service.get_astrolabe_data(
                date=birth_info["date"],
                timezone=int(birth_info["timezone"]),
                gender=birth_info["gender"],
                calendar=birth_info["calendar"],
            )
            text = self.ziwei_service.build_text_description(astrolabe_data)
            lines = [line for line in text.splitlines() if line.strip()]
            return "\n".join(lines[:35])
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # 行动项与追问构建
    # ------------------------------------------------------------------

    def _build_action_items(
        self,
        intent: str,
        query: str,
        specialist_outputs: dict[str, str],
    ) -> list[dict[str, str]]:
        """根据意图类型构建行动建议列表。"""
        base_items = [
            {
                "task": "梳理当前问题的关键变量（事实、选择、风险）",
                "when": "今天 20 分钟内完成",
                "reason": "先澄清信息，能减少误判。",
            },
            {
                "task": "确定一个最小可执行动作并立即开始",
                "when": "今天",
                "reason": "用小步行动替代反复内耗。",
            },
            {
                "task": "做一次晚间复盘，记录有效与无效做法",
                "when": "今晚",
                "reason": "复盘能让下一步更稳。",
            },
        ]

        if intent in {"long_term", "dual_track"}:
            base_items[0]["task"] = "列出未来 3 个月的主线目标与优先级"
            base_items[0]["when"] = "本周内"
            base_items[1]["task"] = "把主线目标拆成每周可交付里程碑"
            base_items[1]["when"] = "本周"

        if intent == "short_term":
            base_items[0]["task"] = "在行动前确认这件事的 3 个关键事实"
            base_items[0]["when"] = "今天"
            base_items[1]["task"] = "先做低成本试探，再决定是否加码"
            base_items[1]["when"] = "未来 1-3 天"

        if intent == "daily_card":
            base_items[0]["task"] = "先完成今天最重要的一件事"
            base_items[0]["when"] = "上午"
            base_items[1]["task"] = "下午安排一次沟通或收尾动作"
            base_items[1]["when"] = "下午"

        if any(keyword in query for keyword in ("面试", "考试", "汇报", "答辩", "谈判")):
            base_items.append(
                {
                    "task": "准备一版 3 分钟高密度表达稿并模拟演练",
                    "when": "事件前一天",
                    "reason": "提前演练可显著降低现场波动。",
                }
            )

        if "actionizer" in specialist_outputs:
            snippet = self._first_meaningful_line(specialist_outputs["actionizer"])
            if snippet:
                base_items[0]["reason"] = snippet[:40] if len(snippet) > 40 else snippet

        return base_items[:5]

    def _build_follow_up_questions(self, intent: str) -> list[str]:
        """根据意图类型生成追问建议。"""
        if intent == "long_term":
            return [
                "你想先聚焦事业、情感、财富还是健康方面的深入分析？",
                "我可以帮你把未来 3 个月的关键窗口进一步细化。",
                "要不要把长期建议拆成每周行动清单？",
            ]
        if intent == "short_term":
            return [
                "你希望我帮你把这件事拆成从今天到本周的具体节奏表吗？",
                "要不要我给你对比一下稳妥方案和积极方案各自的利弊？",
                "我可以帮你识别这件事里最关键、你最能把控的变数。",
            ]
        if intent == "daily_card":
            return [
                "要不要我分别针对事业/情感/健康各给一条今日建议？",
                "我可以帮你把今日宜忌转成具体的时间安排。",
                "今晚想不想做一次简短复盘？我可以给你一个好问题。",
            ]
        if intent == "mindset":
            return [
                "你现在最想先缓解的是哪种感受？",
                "要不要我给你一个 10 分钟可完成的减压小练习？",
                "我可以把这次的心法建议整理成 3 天练习计划。",
            ]
        return [
            "你更想深入了解长期方向还是近期应对策略？",
            "我可以把建议收敛成一份最小行动清单。",
            "要不要我继续帮你细化下一步？",
        ]

    # ------------------------------------------------------------------
    # 答案合成（优化版：更完整地利用专家输出）
    # ------------------------------------------------------------------

    def _compose_answer_text(
        self,
        intent: str,
        specialist_outputs: dict[str, str],
        action_items: list[dict[str, str]],
        follow_up_questions: list[str],
        risk_reminder: str,
    ) -> str:
        """将专家输出、行动项、追问整合为最终回答文本。"""
        calming = {
            "long_term": "先别急着下结论，你当前处在一个可调整、可优化的阶段。"
                         "很多事情还有充足的时间窗口去布局。",
            "short_term": "你现在面对的问题是完全可以应对的。"
                          "先稳住节奏，一步一步来，会越来越清晰。",
            "dual_track": "这件事既涉及近期的具体决策，也牵动更长远的方向。"
                          "好消息是我们可以分层来处理，先解决眼前的，再规划长远的。",
            "daily_card": "今天不需要把所有事都搞定。"
                          "专注做好最关键的一件事，就已经是很好的一天了。",
            "mindset": "你能把这些感受说出来，本身就说明你在积极面对。"
                       "情绪波动是正常的，它不代表你做错了什么。",
            "symbolic": "你已经开始觉察到问题的核心，"
                        "这种觉察力本身就是积极变化的开始。",
        }.get(intent, "你现在的困惑是完全可以被拆解和处理的。让我们一起来梳理。")

        # 收集专家分析内容（取完整摘要而非仅第一行）
        focus_sections = []
        for skill, content in specialist_outputs.items():
            if skill == "actionizer":
                continue  # actionizer 的内容会反映在行动建议中
            label = self._skill_label(skill)
            summary = self._extract_meaningful_summary(content, max_lines=8)
            if summary:
                focus_sections.append(f"**{label}分析：**\n{summary}")
        if not focus_sections:
            focus_sections = ["当前的情况更适合采用先确认信息、再分步推进的策略。"]

        suggestion_lines = []
        for item in action_items[:5]:
            suggestion_lines.append(f"- {item['task']}（{item['when']}）")

        follow_lines = [f"- {question}" for question in follow_up_questions[:3]]

        return (
            f"**安抚与共情**\n{calming}\n\n"
            "**核心解读**\n"
            f"{chr(10).join(focus_sections)}\n\n"
            "**可执行建议**\n"
            f"{chr(10).join(suggestion_lines)}\n\n"
            f"**风险提示**\n{risk_reminder}\n\n"
            "**可追问方向**\n"
            f"{chr(10).join(follow_lines)}"
        )

    # ------------------------------------------------------------------
    # 安全守卫
    # ------------------------------------------------------------------

    def _safety_check(self, content: str) -> SafetyDecision:
        """基于关键词的安全风险检查。"""
        text = content.lower()

        if any(keyword in content or keyword in text for keyword in S4_KEYWORDS):
            return SafetyDecision(
                risk_level="S4",
                decision="refuse",
                reasons=["涉及违法或伤害他人风险"],
                constraints=["拒绝提供可执行违法/伤害指令", "仅提供合法与安全替代建议"],
                disclaimer_level="strong",
            )

        if any(keyword in content or keyword in text for keyword in S3_MENTAL_CRISIS_KEYWORDS):
            return SafetyDecision(
                risk_level="S3",
                decision="refuse",
                reasons=["存在自伤/危机信号"],
                constraints=["拒绝占断和鼓动性内容", "引导尽快联系专业支持与紧急服务"],
                disclaimer_level="strong",
            )

        if any(keyword in content or keyword in text for keyword in S3_MEDICAL_KEYWORDS):
            return SafetyDecision(
                risk_level="S3",
                decision="rewrite",
                reasons=["涉及医疗健康高风险内容"],
                constraints=["不得提供诊断和处方", "建议线下就医或咨询专业医生"],
                disclaimer_level="strong",
            )

        if any(keyword in content or keyword in text for keyword in S2_FINANCE_KEYWORDS):
            return SafetyDecision(
                risk_level="S2",
                decision="rewrite",
                reasons=["涉及投资理财风险"],
                constraints=["禁止给出具体买卖指令", "保留风险教育与仓位谨慎提示"],
                disclaimer_level="strong",
            )

        if any(keyword in content or keyword in text for keyword in S1_LIFE_DECISION_KEYWORDS):
            return SafetyDecision(
                risk_level="S1",
                decision="allow",
                reasons=["涉及重大人生决策"],
                constraints=["使用非确定性表述", "明确仅供参考"],
                disclaimer_level="light",
            )

        if any(phrase in content for phrase in ABSOLUTE_PHRASES):
            return SafetyDecision(
                risk_level="S1",
                decision="rewrite",
                reasons=["存在绝对化表达"],
                constraints=["改为可能性表达并补充风险提示"],
                disclaimer_level="light",
            )

        return SafetyDecision(
            risk_level="S0",
            decision="allow",
            reasons=["普通咨询场景"],
            constraints=[],
            disclaimer_level="none",
        )

    def _rewrite_to_safe(self, text: str, policy: SafetyDecision) -> str:
        """将不安全内容重写为安全版本。"""
        rewritten = self._rewrite_absolute_to_probabilistic(text)
        rewritten = re.sub(r"(买入|卖出|梭哈|满仓|抄底|加杠杆)", "谨慎评估", rewritten)
        rewritten = rewritten.replace("诊断", "评估")
        reminder = self._risk_reminder(policy.disclaimer_level)
        return self._ensure_risk_line(rewritten, reminder)

    @staticmethod
    def _rewrite_absolute_to_probabilistic(text: str) -> str:
        """将绝对化表达改为概率化表达。"""
        replace_map = {
            "一定": "可能",
            "必须": "建议优先考虑",
            "不做就会出事": "建议评估风险后再决定",
            "保证赚钱": "不保证收益",
            "必然发生": "存在这种可能",
        }
        output = text
        for old, new in replace_map.items():
            output = output.replace(old, new)
        return output

    def _build_refusal_payload(self, policy: SafetyDecision, trace: list[dict[str, Any]]) -> dict[str, Any]:
        """构建安全拒绝回复。"""
        answer_text = (
            "**安抚与共情**\n"
            "你愿意把问题说出来，这本身就很重要。我理解你现在可能正在经历困难的时刻。\n\n"
            "**核心解读**\n"
            "这个问题涉及到需要专业支持的领域，超出了我作为智慧咨询助手可以安全回答的范围。"
            "我不能继续提供相关的占断或可执行建议，但我想确保你能获得正确的帮助。\n\n"
            "**可执行建议**\n"
            "- 首先确保你和身边人的安全\n"
            "- 尽快联系专业机构、医生或当地紧急服务\n"
            "- 找一位你信任的人，让他们陪着你\n\n"
            "**风险提示**\n"
            "涉及高风险场景，本系统只能提供安全导向信息，无法提供危险、违法或医疗诊断指令。\n\n"
            "**可追问方向**\n"
            "- 我现在可以先做哪些安全的事情？\n"
            "- 如何联系专业帮助资源？\n"
            "- 怎样向家人或朋友表达我需要帮助？"
        )
        return {
            "answer_text": answer_text,
            "follow_up_questions": [
                "我现在可以先做哪些安全动作？",
                "如何联系专业帮助资源？",
                "怎样向家人或朋友表达我需要帮助？",
            ],
            "action_items": [
                {
                    "task": "联系身边可信任的人并说明你当前状态",
                    "when": "现在",
                    "reason": "获得现实支持能显著降低风险。",
                },
                {
                    "task": "尽快联系当地专业机构或紧急服务",
                    "when": "立即",
                    "reason": "高风险问题需要线下专业介入。",
                },
            ],
            "safety_disclaimer_level": "strong",
            "trace": trace,
        }

    # ------------------------------------------------------------------
    # 工具函数
    # ------------------------------------------------------------------

    @staticmethod
    def _first_meaningful_line(text: str) -> str:
        """提取文本中第一行有意义的内容。"""
        for line in text.splitlines():
            normalized = line.strip().lstrip("-").strip()
            if normalized:
                return normalized
        return ""

    @staticmethod
    def _extract_meaningful_summary(text: str, max_lines: int = 8) -> str:
        """从专家输出中提取有意义的摘要（多行），用于答案合成。"""
        meaningful_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # 跳过纯标签行
            if stripped in ("---", "===", "***"):
                continue
            meaningful_lines.append(stripped)
            if len(meaningful_lines) >= max_lines:
                break
        return "\n".join(meaningful_lines)

    @staticmethod
    def _skill_reason(skill: str, intent: str) -> str:
        """获取技能调用原因的描述。"""
        reason_map = {
            "ziwei": "长线趋势与结构解读",
            "meihua": "短期事件判断与策略建议",
            "tarot": "象征解读与内在映射",
            "daily_card": "生成当日可执行卡片",
            "philosophy": "心法解释与情绪稳定",
            "actionizer": "把建议转成可执行任务",
        }
        return reason_map.get(skill, f"匹配意图: {intent}")

    @staticmethod
    def _skill_label(skill: str) -> str:
        """获取技能的显示标签。"""
        labels = {
            "ziwei": "紫微长线",
            "meihua": "梅花短线",
            "tarot": "塔罗象征",
            "daily_card": "每日卡片",
            "philosophy": "心法解读",
            "actionizer": "行动清单",
        }
        return labels.get(skill, skill)

    @staticmethod
    def _risk_reminder(level: str) -> str:
        """获取对应风险等级的提示文本。"""
        reminders = {
            "none": "以上内容用于启发和自我反思，请结合现实情况自主判断。",
            "light": "以上内容为 AI 解读，仅供参考，不替代你对重大人生决策的独立判断。",
            "strong": "以上内容为 AI 生成，仅供参考，不构成投资、医疗、法律等专业建议。",
        }
        return reminders.get(level, reminders["none"])

    @staticmethod
    def _ensure_risk_line(answer_text: str, risk_reminder: str) -> str:
        """确保回答中包含风险提示行。"""
        if "风险提示" in answer_text:
            return re.sub(r"\*?\*?风险提示\*?\*?[：:]\s*.*", f"**风险提示**\n{risk_reminder}", answer_text, count=1)
        return f"{answer_text}\n\n**风险提示**\n{risk_reminder}"

    @staticmethod
    def _max_disclaimer(level_a: str, level_b: str) -> str:
        """取两个风险等级中更高的一个。"""
        return level_a if DISCLAIMER_ORDER.get(level_a, 0) >= DISCLAIMER_ORDER.get(level_b, 0) else level_b


def get_oracle_orchestrator_service() -> OracleOrchestratorService:
    """获取或创建编排服务单例。"""
    service = current_app.extensions.get("oracle_orchestrator_service")
    if service:
        return service

    service = OracleOrchestratorService(
        default_provider=current_app.config["LLM_PROVIDER"],
        default_model=current_app.config["LLM_MODEL"],
        request_timeout_s=current_app.config["REQUEST_TIMEOUT_S"],
        llm_max_retries=current_app.config["LLM_MAX_RETRIES"],
        izthon_src_path=current_app.config["IZTHON_SRC_PATH"],
        east_only_mvp=current_app.config["ORACLE_EAST_ONLY_MVP"],
    )
    current_app.extensions["oracle_orchestrator_service"] = service
    return service
