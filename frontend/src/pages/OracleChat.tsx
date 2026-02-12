import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import {
  clearOracleChatSession,
  getOracleChatSessionState,
  startOracleChatSession,
  subscribeOracleChatSession,
  type OracleConversationTurn,
  type OracleThinkingItem,
} from "../stores/oracleChatSession";
import type { BirthInfo, OracleChatRequest } from "../types";

const DISCLAIMER_LABELS: Record<"none" | "light" | "strong", string> = {
  none: "普通提示",
  light: "轻度提醒",
  strong: "强提醒",
};

const QUICK_PROMPTS = [
  "我最近在考虑换工作，想看长期走势与本周应对策略。",
  "这周有一次重要沟通，我该怎么准备更稳妥？",
  "最近情绪波动有点大，怎么调整节奏并落到行动？",
];

const ORACLE_CHAT_DRAFT_KEY = "oracle:chat:draft";
const AUTO_HISTORY_MAX_TURNS = 4;

interface OracleChatDraft {
  userQuery: string;
  historySummary: string;
  profileSummary: string;
  birthDate: string;
  timezone: string;
  gender: BirthInfo["gender"];
  calendar: BirthInfo["calendar"];
}

const DEFAULT_DRAFT: OracleChatDraft = {
  userQuery: "",
  historySummary: "",
  profileSummary: "",
  birthDate: "",
  timezone: "4",
  gender: "男",
  calendar: "solar",
};

const getDraft = (): OracleChatDraft => {
  if (typeof window === "undefined") {
    return DEFAULT_DRAFT;
  }
  const raw = window.sessionStorage.getItem(ORACLE_CHAT_DRAFT_KEY);
  if (!raw) {
    return DEFAULT_DRAFT;
  }
  try {
    return { ...DEFAULT_DRAFT, ...(JSON.parse(raw) as Partial<OracleChatDraft>) };
  } catch {
    return DEFAULT_DRAFT;
  }
};

const statusLabel = (status: OracleThinkingItem["status"]) => {
  if (status === "running") {
    return "执行中";
  }
  if (status === "success") {
    return "完成";
  }
  return "失败";
};

const buildAutoHistorySummary = (turns: OracleConversationTurn[]) => {
  const recent = turns.filter((turn) => turn.status === "succeeded").slice(-AUTO_HISTORY_MAX_TURNS);
  if (!recent.length) {
    return "";
  }
  return recent
    .map((turn, index) => {
      const answer = turn.answerText.replace(/\s+/g, " ").trim();
      const answerPreview = answer.length > 200 ? `${answer.slice(0, 200)}...` : answer;
      return `${index + 1}. 用户：${turn.query}\n助手：${answerPreview}`;
    })
    .join("\n\n");
};

const formatTurnTime = (timestamp: number) =>
  new Date(timestamp).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });


export default function OracleChatPage() {
  const [chatSession, setChatSession] = useState(getOracleChatSessionState());
  const [userQuery, setUserQuery] = useState(() => getDraft().userQuery);
  const [historySummary, setHistorySummary] = useState(() => getDraft().historySummary);
  const [profileSummary, setProfileSummary] = useState(() => getDraft().profileSummary);
  const [birthDate, setBirthDate] = useState(() => getDraft().birthDate);
  const [timezone, setTimezone] = useState(() => getDraft().timezone);
  const [gender, setGender] = useState<BirthInfo["gender"]>(() => getDraft().gender);
  const [calendar, setCalendar] = useState<BirthInfo["calendar"]>(() => getDraft().calendar);
  const [localError, setLocalError] = useState<string | null>(null);
  const [formTip] = useState<string | null>("同一会话内会按计划逐步输出结果，可持续追问。");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const unsubscribe = subscribeOracleChatSession((state) => {
      setChatSession(state);
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    const draft = {
      userQuery,
      historySummary,
      profileSummary,
      birthDate,
      timezone,
      gender,
      calendar,
    };
    window.sessionStorage.setItem(ORACLE_CHAT_DRAFT_KEY, JSON.stringify(draft));
  }, [birthDate, calendar, gender, historySummary, profileSummary, timezone, userQuery]);

  const timezoneOptions = useMemo(
    () => Array.from({ length: 13 }, (_, index) => ({ value: String(index), label: `${index}` })),
    []
  );

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    const query = userQuery.trim();
    if (!query) {
      setLocalError("请先输入你想咨询的问题。");
      return;
    }

    const autoHistory = buildAutoHistorySummary(chatSession.turns);
    const manualHistory = historySummary.trim();
    const mergedHistory = [autoHistory, manualHistory].filter(Boolean).join("\n\n");

    const payload: OracleChatRequest = {
      user_query: query,
      conversation_history_summary: mergedHistory || undefined,
      user_profile_summary: profileSummary.trim() || undefined,
    };

    if (birthDate) {
      payload.birth_info = {
        date: birthDate,
        timezone: Number(timezone),
        gender,
        calendar,
      };
    }

    setUserQuery("");
    void startOracleChatSession(payload);
  };

  return (
    <div className="oracle-chat fade-in">
      <InkCard title="多智能体咨询台" icon="卦">
        <div className="oracle-chat__single-frame">
          <div className="oracle-chat__thread" aria-live="polite">
            {!chatSession.turns.length ? (
              <div className="oracle-chat__empty">
                <p className="oracle-chat__empty-title">还没有咨询记录</p>
                <p className="oracle-chat__empty-desc">输入问题后，系统会按计划逐步执行并在同一对话框持续返回。</p>
              </div>
            ) : null}

            {chatSession.turns.map((turn) => (
              <article key={turn.id} className="oracle-turn">
                <div className="oracle-turn__bubble oracle-turn__bubble--user">
                  <p className="oracle-turn__meta">你 · {formatTurnTime(turn.createdAt)}</p>
                  <p className="oracle-turn__query">{turn.query}</p>
                </div>

                <div className="oracle-turn__bubble oracle-turn__bubble--assistant">
                  <p className="oracle-turn__meta">
                    Oracle · {turn.status === "running" ? "执行计划中" : turn.status === "succeeded" ? "已完成" : "执行失败"}
                  </p>
                  {turn.answerText ? (
                    <p className="oracle-turn__meta oracle-turn__meta--hint">
                      安全级别：{DISCLAIMER_LABELS[turn.safetyDisclaimerLevel]}
                    </p>
                  ) : null}

                  <div className="oracle-turn__plan">
                    <p className="oracle-turn__section-title">计划步骤</p>
                    {turn.planSteps.length ? (
                      <div className="oracle-turn__plan-list">
                        {turn.planSteps.map((step, index) => (
                          <div key={`${turn.id}-${step.tool_name}-${index}`} className="oracle-turn__plan-item">
                            <span>{step.display_name}</span>
                            <span className={`oracle-turn__status oracle-turn__status--${step.status}`}>
                              {statusLabel(step.status)}
                              {typeof step.elapsed_ms === "number" ? ` · ${step.elapsed_ms}ms` : ""}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="oracle-turn__plan-empty">
                        {turn.status === "running" ? "正在准备执行工具..." : "本轮无工具步骤。"}
                      </p>
                    )}
                  </div>

                  {turn.answerText ? (
                    <div className="oracle-turn__answer markdown-body">
                      <MarkdownRenderer content={turn.answerText} />
                    </div>
                  ) : null}

                  {turn.actionItems.length ? (
                    <div className="oracle-turn__actions">
                      {turn.actionItems.map((item, index) => (
                        <div key={`${turn.id}-${item.task}-${index}`} className="oracle-chat__action-item">
                          <p className="oracle-chat__action-title">{index + 1}. {item.task}</p>
                          <p className="oracle-chat__action-meta">建议时间：{item.when}</p>
                          <p className="oracle-chat__action-meta">原因：{item.reason}</p>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  {turn.followUpQuestions.length ? (
                    <div className="oracle-turn__follow-grid">
                      {turn.followUpQuestions.map((question, index) => (
                        <button
                          key={`${turn.id}-${question}-${index}`}
                          type="button"
                          className="oracle-turn__follow-chip"
                          onClick={() => {
                            setUserQuery(question);
                            textareaRef.current?.focus();
                          }}
                        >
                          {question}
                        </button>
                      ))}
                    </div>
                  ) : null}

                  {turn.error ? <p className="error-text">{turn.error}</p> : null}
                </div>
              </article>
            ))}
          </div>

          <form className="oracle-chat__composer stack" onSubmit={onSubmit}>
            <div className="field">
              <label className="field__label" htmlFor="oracle-query">继续提问</label>
              <textarea
                ref={textareaRef}
                id="oracle-query"
                className="oracle-chat__textarea"
                placeholder="继续追问：例如“把这周计划拆成每天行动清单”"
                value={userQuery}
                onChange={(event) => setUserQuery(event.target.value)}
                rows={3}
              />
              <div className="oracle-chat__prompt-grid" aria-label="快捷问题模板">
                {QUICK_PROMPTS.map((prompt, index) => (
                  <button
                    key={`${prompt}-${index}`}
                    type="button"
                    className="oracle-chat__prompt-chip"
                    onClick={() => setUserQuery(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            <details className="oracle-chat__details">
              <summary className="details-toggle">补充上下文（可选）</summary>
              <div className="stack">
                <div className="field">
                  <label className="field__label" htmlFor="oracle-profile">用户画像摘要</label>
                  <textarea
                    id="oracle-profile"
                    className="oracle-chat__textarea"
                    placeholder="例如：95后，互联网产品经理，近期工作压力偏高。"
                    value={profileSummary}
                    onChange={(event) => setProfileSummary(event.target.value)}
                    rows={3}
                  />
                </div>

                <div className="field">
                  <label className="field__label" htmlFor="oracle-history">手动历史摘要（可覆盖）</label>
                  <textarea
                    id="oracle-history"
                    className="oracle-chat__textarea"
                    placeholder="你也可以手工补充对话背景。系统会自动拼接最近几轮咨询记录。"
                    value={historySummary}
                    onChange={(event) => setHistorySummary(event.target.value)}
                    rows={3}
                  />
                </div>

                <div className="form-grid">
                  <div className="field">
                    <label className="field__label" htmlFor="oracle-birth-date">出生日期（可选）</label>
                    <input
                      id="oracle-birth-date"
                      type="date"
                      value={birthDate}
                      onChange={(event) => setBirthDate(event.target.value)}
                    />
                  </div>

                  <div className="field">
                    <label className="field__label" htmlFor="oracle-timezone">时辰（0-12）</label>
                    <select
                      id="oracle-timezone"
                      value={timezone}
                      onChange={(event) => setTimezone(event.target.value)}
                    >
                      {timezoneOptions.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>

                  <div className="field">
                    <label className="field__label" htmlFor="oracle-gender">性别</label>
                    <select
                      id="oracle-gender"
                      value={gender}
                      onChange={(event) => setGender(event.target.value as BirthInfo["gender"])}
                    >
                      <option value="男">男</option>
                      <option value="女">女</option>
                    </select>
                  </div>

                  <div className="field">
                    <label className="field__label" htmlFor="oracle-calendar">历法</label>
                    <select
                      id="oracle-calendar"
                      value={calendar}
                      onChange={(event) => setCalendar(event.target.value as BirthInfo["calendar"])}
                    >
                      <option value="solar">阳历</option>
                      <option value="lunar">农历</option>
                    </select>
                  </div>
                </div>
              </div>
            </details>

            {localError ? <p className="error-text">{localError}</p> : null}
            {!localError && chatSession.error ? <p className="error-text">{chatSession.error}</p> : null}
            {formTip ? <p className="oracle-chat__tip">{formTip}</p> : null}
            {chatSession.loading && chatSession.startedAt ? (
              <p className="oracle-chat__tip">当前轮次正在按计划执行中，可切换页面后返回继续查看。</p>
            ) : null}

            <div className="actions-row">
              <InkButton type="submit" disabled={chatSession.loading}>
                {chatSession.loading ? "执行中..." : "发送问题"}
              </InkButton>
              <InkButton
                type="button"
                kind="ghost"
                onClick={() => {
                  setLocalError(null);
                  clearOracleChatSession();
                }}
                disabled={chatSession.loading}
              >
                清空会话
              </InkButton>
            </div>
          </form>
        </div>
      </InkCard>
    </div>
  );
}
