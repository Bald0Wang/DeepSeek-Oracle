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

LONG_TERM_KEYWORDS = {
    "人生",
    "长期",
    "未来",
    "几年",
    "走势",
    "格局",
    "大运",
    "规划",
    "命盘",
    "事业方向",
    "婚姻长期",
}
SHORT_TERM_KEYWORDS = {
    "今天",
    "明天",
    "本周",
    "这周",
    "近期",
    "这次",
    "要不要",
    "面试",
    "告白",
    "考试",
    "短期",
}
EMOTION_KEYWORDS = {"焦虑", "压力", "内耗", "迷茫", "难过", "情绪", "害怕", "自我成长", "修心"}
DAILY_KEYWORDS = {"每日", "日卡", "今日宜忌", "今日运势", "今天适合"}
TAROT_KEYWORDS = {"塔罗", "牌阵", "抽牌", "西方占卜"}

S4_KEYWORDS = {
    "杀人",
    "报复",
    "炸药",
    "诈骗",
    "黑客攻击",
    "贩毒",
    "如何犯罪",
    "袭击",
    "伤害他人",
}
S3_MENTAL_CRISIS_KEYWORDS = {"自杀", "自残", "不想活", "结束生命", "轻生", "割腕"}
S3_MEDICAL_KEYWORDS = {"处方", "诊断", "确诊", "药量", "吃什么药", "医学治疗", "治疗方案"}
S2_FINANCE_KEYWORDS = {"股票", "基金", "币圈", "杠杆", "做空", "抄底", "买入", "卖出", "仓位", "止盈", "止损"}
S1_LIFE_DECISION_KEYWORDS = {"离婚", "结婚", "辞职", "跳槽", "搬家", "创业", "分手"}

ABSOLUTE_PHRASES = ("一定", "必须", "不做就会出事", "保证赚钱", "必然发生")


@dataclass
class SafetyDecision:
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
    intent: str
    skills: list[str]
    reasons: list[str]


@dataclass
class ToolSpec:
    name: str
    description: str
    json_schema: dict[str, Any]
    handler: Callable[[dict[str, Any], dict[str, Any], str, str], str]
    fallback_skill: str | None = None


class OracleOrchestratorService:
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

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._run_chat(payload, event_callback=None)

    def chat_stream(
        self,
        payload: dict[str, Any],
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        return self._run_chat(payload, event_callback=event_callback)

    def chat_with_tools(
        self,
        payload: dict[str, Any],
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        return self._run_chat(payload, event_callback=event_callback)

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

    def _build_tools_for_provider(self, specs: list[ToolSpec] | None = None) -> list[dict[str, Any]]:
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
        if not isinstance(arguments, dict):
            return {}
        allowed = set(spec.json_schema.get("properties", {}).keys())
        if not allowed:
            return {}
        return {key: value for key, value in arguments.items() if key in allowed}

    def _build_orchestrator_messages(
        self,
        payload: dict[str, Any],
        enabled_schools: list[str],
        enabled_tool_names: list[str],
    ) -> list[dict[str, Any]]:
        system_prompt = (
            "你是 DeepSeek Oracle 的中控编排智能体。"
            "你必须优先通过工具调用完成分析，最后输出安抚 + 解释 + 可执行建议 + 风险提示。"
            "严禁绝对化断言、恐惧营销、投资买卖指令、医疗诊断与违法建议。"
            "你只能调用“已启用工具列表”里的工具，不允许调用未启用工具。"
        )
        user_content = (
            f"用户问题：{payload['user_query']}\n"
            f"历史摘要：{payload.get('conversation_history_summary') or '暂无'}\n"
            f"用户画像：{payload.get('user_profile_summary') or '暂无'}\n"
            f"出生信息：{payload.get('birth_info') or '暂无'}\n"
            f"已启用智能体：{', '.join(enabled_schools) if enabled_schools else '无'}\n"
            f"已启用工具：{', '.join(enabled_tool_names) if enabled_tool_names else '无'}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _build_tool_registry(self) -> dict[str, ToolSpec]:
        return {
            "safety_guard_precheck": ToolSpec(
                name="safety_guard_precheck",
                description="执行输入安全审查，返回风险等级与策略。",
                json_schema={"type": "object", "properties": {"content": {"type": "string"}}},
                handler=self._tool_safety_precheck,
            ),
            "safety_guard_postcheck": ToolSpec(
                name="safety_guard_postcheck",
                description="执行输出安全审查，返回风险等级与策略。",
                json_schema={"type": "object", "properties": {"content": {"type": "string"}}},
                handler=self._tool_safety_postcheck,
            ),
            "ziwei_long_reading": ToolSpec(
                name="ziwei_long_reading",
                description="紫微斗数长线趋势解读。",
                json_schema={
                    "type": "object",
                    "properties": {"focus_domain": {"type": "string"}, "intent": {"type": "string"}},
                },
                handler=self._tool_ziwei_long_reading,
                fallback_skill="ziwei",
            ),
            "meihua_short_reading": ToolSpec(
                name="meihua_short_reading",
                description="梅花易数短期倾向与应对建议。",
                json_schema={
                    "type": "object",
                    "properties": {"time_window": {"type": "string"}, "intent": {"type": "string"}},
                },
                handler=self._tool_meihua_short_reading,
                fallback_skill="meihua",
            ),
            "daily_card": ToolSpec(
                name="daily_card",
                description="根据问题与用户信息生成每日卡片。",
                json_schema={"type": "object", "properties": {"theme": {"type": "string"}}},
                handler=self._tool_daily_card,
                fallback_skill="daily_card",
            ),
            "philosophy_guidance": ToolSpec(
                name="philosophy_guidance",
                description="生成国学心法解释与实践建议。",
                json_schema={"type": "object", "properties": {"theme": {"type": "string"}}},
                handler=self._tool_philosophy_guidance,
                fallback_skill="philosophy",
            ),
            "actionizer": ToolSpec(
                name="actionizer",
                description="把建议转为可执行行动清单。",
                json_schema={"type": "object", "properties": {"intent": {"type": "string"}}},
                handler=self._tool_actionizer,
                fallback_skill="actionizer",
            ),
        }

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

    def _route_intent(self, query: str, selected_school: str, enabled_schools: list[str]) -> RoutingResult:
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
                ["命中长期关键词，但紫微技能未开启，降级到梅花策略"],
            )

        if has_short and "meihua" in enabled_schools:
            return RoutingResult("short_term", self._with_actionizer(["meihua"], enabled_schools), ["命中短期事件关键词"])
        if has_short and "meihua" not in enabled_schools and "ziwei" in enabled_schools:
            return RoutingResult(
                "long_term",
                self._with_actionizer(["ziwei"], enabled_schools),
                ["命中短期关键词，但梅花技能未开启，降级到紫微趋势"],
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

    def _run_ziwei_agent(
        self,
        payload: dict[str, Any],
        intent: str,
        provider_name: str,
        model_name: str,
    ) -> str:
        query = payload["user_query"]
        profile = payload.get("user_profile_summary", "")
        chart_summary = self._build_chart_summary(payload.get("birth_info"))
        fallback = (
            "总论：当前阶段更适合用“稳中求进”的策略布局人生关键面向。\n"
            "分领域解读：事业宜先打基础再放大机会；感情宜重沟通与边界；财富宜做风险分层；健康宜规律作息。\n"
            "未来3个关键窗口：\n"
            "1) 近期1-3个月更适合梳理方向和资源。\n"
            "2) 中期3-6个月更适合推进关键决策。\n"
            "3) 若遇到外部不确定，更需谨慎控制节奏。\n"
            "可执行建议：明确年度主线、每周复盘一次、保留20%机动空间。"
        )
        prompt = (
            "你是紫微斗数长线解读智能体。"
            "只做趋势与结构，不做确定性断言，不渲染灾祸。\n"
            f"用户问题：{query}\n"
            f"用户画像：{profile or '暂无'}\n"
            f"命盘摘要：{chart_summary or '暂无'}\n"
            f"意图：{intent}\n"
            "请按以下顺序输出：总论、分领域解读、未来3个关键窗口、可执行建议（3条）、可追问方向（3条）。"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_meihua_agent(self, payload: dict[str, Any], provider_name: str, model_name: str) -> str:
        query = payload["user_query"]
        history = payload.get("conversation_history_summary", "")
        fallback = (
            "占题重述：围绕你当前最关心的近期事件，判断短期趋势与应对策略。\n"
            "时间窗口：未来7天内。\n"
            "短期倾向：整体可推进，但节奏宜先稳后快。\n"
            "关键变数：沟通质量、信息确认完整度、你本人的执行连贯性。\n"
            "宜与忌：宜先确认关键事实再行动；忌在情绪波动时做最终拍板。\n"
            "应对策略：先做低成本试探，再根据反馈做二次决策。"
        )
        prompt = (
            "你是梅花易数短期占断智能体。"
            "你先重述占题，再给短期倾向、关键变数、宜忌和应对策略，避免绝对化。\n"
            f"问题：{query}\n"
            f"历史摘要：{history or '暂无'}\n"
            "输出顺序：占题重述、时间窗口、短期倾向、关键变数、宜与忌、应对策略。"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_tarot_agent(self, payload: dict[str, Any], provider_name: str, model_name: str) -> str:
        query = payload["user_query"]
        fallback = (
            "象征解读：你当前更像处在“收束旧模式、建立新节奏”的阶段。\n"
            "情绪镜像：焦虑来自不确定，而不是能力不足。\n"
            "行动建议：先处理最关键的一件事，再安排一次对话澄清。\n"
            "提醒：保持现实验证，不把单次解读当成确定结论。"
        )
        prompt = (
            "你是塔罗解读智能体，用象征语言帮助用户理解内在状态与行动选择。"
            "避免保证结果。\n"
            f"问题：{query}\n"
            "请输出：象征解读、情绪镜像、行动建议、提醒。"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_daily_card_agent(self, payload: dict[str, Any], provider_name: str, model_name: str) -> str:
        query = payload["user_query"]
        profile = payload.get("user_profile_summary", "")
        fallback = (
            "关键词：收心、聚焦、留白。\n"
            "今日倾向：适合处理一件高价值事务，不宜同时开太多战线。\n"
            "今日宜：上午完成最难事项；下午做沟通收尾；晚间做15分钟复盘。\n"
            "今日忌：在情绪高波动时临时推翻既定安排。\n"
            "可追问：我今天更适合推进哪一类事情？"
        )
        prompt = (
            "你是每日卡片编排智能体，固定输出关键词、今日倾向、今日宜、今日忌、可追问。\n"
            f"用户问题：{query}\n"
            f"用户画像：{profile or '暂无'}"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _run_philosophy_agent(self, payload: dict[str, Any], provider_name: str, model_name: str) -> str:
        query = payload["user_query"]
        fallback = (
            "核心心法：知行合一、致良知。\n"
            "白话解释：先回到内心真实的判断，再把判断落实到一个具体行动；不空想，也不蛮干。\n"
            "可实践方法：\n"
            "1) 先写下你此刻最真实的顾虑与期待各1条；\n"
            "2) 用“此事是否更接近良知”筛选当下选择；\n"
            "3) 立刻执行一个10分钟可完成的小动作，做到知行同步。\n"
            "补充脉络：心学重“反求诸己”，可结合陆九渊一系的内在觉察来校准节奏。\n"
            "今日一问：我现在的这个决定，是否既对得起内心，也能落到现实行动？"
        )
        prompt = (
            "你是心法解读智能体，重点参考王阳明“知行合一、致良知”，"
            "并可吸收陆九渊心学脉络，使用现代语言提炼可实践方法。\n"
            f"问题：{query}\n"
            "输出：核心心法、白话解释、可实践方法、今日一问。"
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
        query = payload["user_query"]
        fallback = (
            "行动建议：\n"
            "1) 今天先完成一个可交付的小目标。\n"
            "2) 预留一个30分钟窗口做信息核对。\n"
            "3) 晚上记录一次进展与偏差。"
        )
        prompt = (
            "你是日历行动化智能体。"
            "把建议转成可执行任务，不用命令口吻。\n"
            f"问题：{query}\n"
            f"意图：{intent}"
        )
        return self._complete_with_fallback(
            prompt=prompt,
            fallback=fallback,
            temperature_safe=True,
            provider_name=provider_name,
            model_name=model_name,
        )

    def _complete_with_fallback(
        self,
        prompt: str,
        fallback: str,
        temperature_safe: bool,
        provider_name: str,
        model_name: str,
    ) -> str:
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

    def _build_chart_summary(self, birth_info: dict[str, Any] | None) -> str:
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

    def _build_action_items(
        self,
        intent: str,
        query: str,
        specialist_outputs: dict[str, str],
    ) -> list[dict[str, str]]:
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

        if any(keyword in query for keyword in ("面试", "考试", "汇报")):
            base_items.append(
                {
                    "task": "准备一版 3 分钟高密度表达稿",
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
        if intent == "long_term":
            return [
                "你想先聚焦事业、情感、财富还是健康？",
                "我可以把未来 3 个月的关键窗口再细化吗？",
                "要不要把建议拆成每周行动清单？",
            ]
        if intent == "short_term":
            return [
                "你希望我把这件事拆成今天到本周的节奏表吗？",
                "要不要给你一版“最稳妥方案 vs 更积极方案”？",
                "我可以帮你识别这件事里最关键的变数吗？",
            ]
        if intent == "daily_card":
            return [
                "我可以按情感/事业/健康分别给你一条今日建议吗？",
                "要不要把今日宜忌转成日历提醒？",
                "我可以给你一个今晚的复盘问题吗？",
            ]
        if intent == "mindset":
            return [
                "你现在最想先缓解的是哪种情绪？",
                "要不要我给你一个 10 分钟可执行的减压步骤？",
                "我可以把这次建议整理成 3 天练习版吗？",
            ]
        return [
            "你更想看长期方向还是近期应对？",
            "我可以把建议收敛成最小行动清单吗？",
            "要不要我继续给你一个更细的下一步？",
        ]

    def _compose_answer_text(
        self,
        intent: str,
        specialist_outputs: dict[str, str],
        action_items: list[dict[str, str]],
        follow_up_questions: list[str],
        risk_reminder: str,
    ) -> str:
        calming = {
            "long_term": "先别急着下结论，你当前处在可调整、可优化的阶段。",
            "short_term": "你现在面对的是可应对的问题，先稳住节奏就会更清晰。",
            "dual_track": "这件事既有短期决策面，也牵动长期方向，我们可以分层处理。",
            "daily_card": "今天不需要把所有事都做完，先做好最关键的一件就足够。",
            "mindset": "情绪波动并不代表你做错了，先把心稳住再推进会更有效。",
            "symbolic": "你已经开始看见问题的核心，这本身就是积极变化。",
        }.get(intent, "你现在的困惑是可以被拆解和处理的。")

        focus_lines = []
        for skill, content in specialist_outputs.items():
            line = self._first_meaningful_line(content)
            if line:
                focus_lines.append(f"- {self._skill_label(skill)}：{line}")
            if len(focus_lines) >= 3:
                break
        if not focus_lines:
            focus_lines = ["- 当前更适合采用“先确认信息、再推进决策”的节奏。"]

        suggestion_lines = []
        for item in action_items[:4]:
            suggestion_lines.append(f"- {item['task']}（{item['when']}）")

        follow_lines = [f"- {question}" for question in follow_up_questions[:3]]

        return (
            f"安抚：{calming}\n\n"
            "核心解读：\n"
            f"{chr(10).join(focus_lines)}\n\n"
            "可执行建议：\n"
            f"{chr(10).join(suggestion_lines)}\n\n"
            f"风险提示：{risk_reminder}\n\n"
            "可追问方向：\n"
            f"{chr(10).join(follow_lines)}"
        )

    def _safety_check(self, content: str) -> SafetyDecision:
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
        rewritten = self._rewrite_absolute_to_probabilistic(text)
        rewritten = re.sub(r"(买入|卖出|梭哈|满仓|抄底|加杠杆)", "谨慎评估", rewritten)
        rewritten = rewritten.replace("诊断", "评估")
        reminder = self._risk_reminder(policy.disclaimer_level)
        return self._ensure_risk_line(rewritten, reminder)

    @staticmethod
    def _rewrite_absolute_to_probabilistic(text: str) -> str:
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
        answer_text = (
            "安抚：你愿意把问题说出来已经很重要。\n\n"
            "核心解读：这个问题超出了可安全回答的范围，我不能继续提供占断或可执行指令。\n\n"
            "可执行建议：\n"
            "- 先确保你和他人的现实安全。\n"
            "- 尽快联系专业机构、医生或当地紧急服务。\n"
            "- 找一位可信任的人陪同沟通。\n\n"
            "风险提示：涉及高风险场景，本系统只能提供安全导向信息，不能提供危险、违法或医疗诊断指令。\n\n"
            "可追问方向：\n"
            "- 我现在可以先做哪些安全动作？\n"
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

    @staticmethod
    def _first_meaningful_line(text: str) -> str:
        for line in text.splitlines():
            normalized = line.strip().lstrip("-").strip()
            if normalized:
                return normalized
        return ""

    @staticmethod
    def _skill_reason(skill: str, intent: str) -> str:
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
        reminders = {
            "none": "以上内容用于启发和自我反思，请结合现实情况自主判断。",
            "light": "以上内容为 AI 解读，仅供参考，不替代你对重大人生决策的独立判断。",
            "strong": "以上内容为 AI 生成，仅供参考，不构成投资、医疗、法律等专业建议。",
        }
        return reminders.get(level, reminders["none"])

    @staticmethod
    def _ensure_risk_line(answer_text: str, risk_reminder: str) -> str:
        if "风险提示：" in answer_text:
            return re.sub(r"风险提示：.*", f"风险提示：{risk_reminder}", answer_text, count=1)
        return f"{answer_text}\n\n风险提示：{risk_reminder}"

    @staticmethod
    def _max_disclaimer(level_a: str, level_b: str) -> str:
        return level_a if DISCLAIMER_ORDER.get(level_a, 0) >= DISCLAIMER_ORDER.get(level_b, 0) else level_b


def get_oracle_orchestrator_service() -> OracleOrchestratorService:
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
