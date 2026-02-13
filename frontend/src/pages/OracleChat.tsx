import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  createOracleConversation,
  getOracleConversations,
  getOracleConversationTurns,
} from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import {
  clearOracleChatSession,
  getOracleChatSessionState,
  hydrateOracleChatSession,
  setOracleChatConversation,
  startOracleChatSession,
  subscribeOracleChatSession,
  type OracleConversationTurn,
  type OracleThinkingItem,
} from "../stores/oracleChatSession";
import type {
  EnabledSchool,
  OracleChatRequest,
  OracleConversationSummary,
  OracleConversationTurnRecord,
} from "../types";
import { getAccessToken, getStoredUser } from "../utils/auth";

const DISCLAIMER_LABELS: Record<"none" | "light" | "strong", string> = {
  none: "普通提示",
  light: "轻度提醒",
  strong: "强提醒",
};

const QUICK_PROMPTS = [
  "我最近在考虑换工作，想看长期走势与本周应对策略。",
  "这周有一次重要沟通，我该怎么准备更稳妥？",
  "最近情绪波动有点大，怎么调整节奏并养回行动力？",
];

const ORACLE_QUERY_DRAFT_KEY = "oracle:chat:query_draft";
const ORACLE_AGENT_PREF_KEY = "oracle:chat:enabled_agents";
const ORACLE_GUEST_DRAFT_KEY = "oracle:guest_chat_draft";
const AUTO_HISTORY_MAX_TURNS = 4;
const AGENT_OPTIONS: Array<{ id: EnabledSchool; label: string; desc: string }> = [
  { id: "ziwei", label: "紫微斗数", desc: "长期趋势" },
  { id: "meihua", label: "梅花易数", desc: "短期应对" },
  { id: "philosophy", label: "心学心法", desc: "情绪与行动修正" },
];

const loadEnabledAgents = (): EnabledSchool[] => {
  const fallback: EnabledSchool[] = ["ziwei", "meihua", "philosophy"];
  const raw = window.sessionStorage.getItem(ORACLE_AGENT_PREF_KEY);
  if (!raw) {
    return fallback;
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return fallback;
    }
    const allowed = AGENT_OPTIONS.map((option) => option.id);
    const normalized = parsed
      .map((item) => String(item))
      .filter((item): item is EnabledSchool => allowed.includes(item as EnabledSchool));
    return normalized.length ? normalized : fallback;
  } catch {
    return fallback;
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

const turnStatusLabel = (status: OracleConversationTurn["status"]) => {
  if (status === "running") {
    return "执行中";
  }
  if (status === "succeeded") {
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

const turnTitle = (query: string) => (query.length > 26 ? `${query.slice(0, 26)}...` : query);
const previewContext = (text: string) => (text.length > 180 ? `${text.slice(0, 180)}...` : text);
const toTimestamp = (value: string) => {
  const ts = Date.parse(value);
  return Number.isFinite(ts) ? ts : Date.now();
};
const conversationTitle = (item: OracleConversationSummary) => {
  const title = String(item.title || "").trim();
  if (title) {
    return title;
  }
  const fallback = String(item.last_query || "").trim();
  return fallback ? turnTitle(fallback) : "新对话";
};
const mapServerTurn = (turn: OracleConversationTurnRecord): OracleConversationTurn => ({
  id: `turn_${turn.id}`,
  query: turn.user_query,
  contextSummary: turn.context_summary || "",
  createdAt: toTimestamp(turn.created_at),
  status: turn.status === "failed" ? "failed" : "succeeded",
  planSteps: Array.isArray(turn.plan_steps) ? turn.plan_steps : [],
  answerText: turn.answer_text || "",
  actionItems: Array.isArray(turn.action_items) ? turn.action_items : [],
  followUpQuestions: Array.isArray(turn.follow_up_questions) ? turn.follow_up_questions : [],
  safetyDisclaimerLevel: turn.safety_disclaimer_level || "none",
  error: turn.error_message || null,
});


export default function OracleChatPage() {
  const navigate = useNavigate();
  const isAuthenticated = Boolean(getAccessToken()) && Boolean(getStoredUser());

  const [chatSession, setChatSession] = useState(getOracleChatSessionState());
  const [conversations, setConversations] = useState<OracleConversationSummary[]>([]);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(
    getOracleChatSessionState().conversationId
  );
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
  const [userQuery, setUserQuery] = useState(() => window.sessionStorage.getItem(ORACLE_QUERY_DRAFT_KEY) || "");
  const [guestQuery, setGuestQuery] = useState(() => window.sessionStorage.getItem(ORACLE_GUEST_DRAFT_KEY) || "");
  const [enabledAgents, setEnabledAgents] = useState<EnabledSchool[]>(() => loadEnabledAgents());
  const [localError, setLocalError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      return () => {};
    }
    const unsubscribe = subscribeOracleChatSession((state) => {
      setChatSession(state);
    });
    return unsubscribe;
  }, [isAuthenticated]);

  useEffect(() => {
    setActiveConversationId(chatSession.conversationId);
  }, [chatSession.conversationId]);

  useEffect(() => {
    const thread = threadRef.current;
    if (!thread) {
      return;
    }
    thread.scrollTop = thread.scrollHeight;
  }, [chatSession.turns, chatSession.activeTurnId]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    window.sessionStorage.setItem(ORACLE_QUERY_DRAFT_KEY, userQuery);
  }, [isAuthenticated, userQuery]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    window.sessionStorage.setItem(ORACLE_AGENT_PREF_KEY, JSON.stringify(enabledAgents));
  }, [enabledAgents, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    const draft = window.sessionStorage.getItem(ORACLE_GUEST_DRAFT_KEY);
    if (!draft) {
      return;
    }
    setUserQuery((prev) => (prev.trim() ? prev : draft));
    window.sessionStorage.removeItem(ORACLE_GUEST_DRAFT_KEY);
  }, [isAuthenticated]);

  useEffect(() => {
    if (chatSession.activeTurnId) {
      setSelectedTurnId(chatSession.activeTurnId);
      return;
    }
    if (!chatSession.turns.length) {
      setSelectedTurnId(null);
      return;
    }
    if (!selectedTurnId || !chatSession.turns.some((turn) => turn.id === selectedTurnId)) {
      setSelectedTurnId(chatSession.turns[chatSession.turns.length - 1].id);
    }
  }, [chatSession.activeTurnId, chatSession.turns, selectedTurnId]);

  const selectedTurn = useMemo(
    () => chatSession.turns.find((turn) => turn.id === selectedTurnId) || chatSession.turns[chatSession.turns.length - 1] || null,
    [chatSession.turns, selectedTurnId]
  );

  const loadConversationTurns = async (conversationId: number) => {
    setConversationLoading(true);
    try {
      const response = await getOracleConversationTurns(conversationId);
      const turns = (response.data?.turns || []).map(mapServerTurn);
      hydrateOracleChatSession(conversationId, turns);
      setActiveConversationId(conversationId);
      setLocalError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "加载会话失败，请稍后重试。";
      setLocalError(message);
    } finally {
      setConversationLoading(false);
    }
  };

  const reloadConversations = async (preferredConversationId?: number) => {
    try {
      const response = await getOracleConversations(60);
      const list = response.data?.items || [];
      setConversations(list);
      if (!list.length) {
        setActiveConversationId(null);
        clearOracleChatSession();
        return;
      }

      const fallbackId = preferredConversationId || activeConversationId || chatSession.conversationId || list[0].id;
      const matched = list.find((item) => item.id === fallbackId);
      const nextId = matched ? matched.id : list[0].id;
      if (nextId !== activeConversationId || !chatSession.turns.length) {
        await loadConversationTurns(nextId);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "加载会话列表失败，请稍后重试。";
      setLocalError(message);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    void reloadConversations();
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated || !chatSession.conversationId) {
      return;
    }
    if (!conversations.some((item) => item.id === chatSession.conversationId)) {
      void reloadConversations(chatSession.conversationId);
      return;
    }
    setActiveConversationId(chatSession.conversationId);
  }, [chatSession.conversationId, conversations, isAuthenticated]);

  const onGuestSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    const query = guestQuery.trim();
    if (!query) {
      setLocalError("请先输入问题，再进入登录。");
      return;
    }

    window.sessionStorage.setItem(ORACLE_GUEST_DRAFT_KEY, query);
    navigate("/login");
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    const query = userQuery.trim();
    if (!query) {
      setLocalError("请先输入你想咨询的问题。");
      return;
    }

    if (!enabledAgents.length) {
      setLocalError("至少启用一个智能体后再发送问题。");
      return;
    }

    const payload: OracleChatRequest = {
      user_query: query,
      conversation_id: activeConversationId || chatSession.conversationId || undefined,
      conversation_history_summary: buildAutoHistorySummary(chatSession.turns) || undefined,
      selected_school: "east",
      enabled_schools: enabledAgents,
    };

    setUserQuery("");
    await startOracleChatSession(payload);
    if (getOracleChatSessionState().conversationId) {
      void reloadConversations(getOracleChatSessionState().conversationId || undefined);
    }
  };

  const onCreateNewConversation = async () => {
    if (chatSession.loading) {
      return;
    }
    setConversationLoading(true);
    try {
      const created = await createOracleConversation("新对话");
      const nextId = created.data?.id;
      if (!nextId) {
        throw new Error("新建会话失败");
      }
      setOracleChatConversation(nextId);
      setActiveConversationId(nextId);
      setSelectedTurnId(null);
      setConversations((prev) => {
        const nextItem: OracleConversationSummary = {
          id: nextId,
          title: "新对话",
          created_at: created.data?.created_at || new Date().toISOString(),
          updated_at: created.data?.updated_at || new Date().toISOString(),
          turn_count: 0,
          last_query: "",
        };
        return [nextItem, ...prev.filter((item) => item.id !== nextId)];
      });
      setLocalError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "新建会话失败，请稍后重试。";
      setLocalError(message);
    } finally {
      setConversationLoading(false);
    }
  };

  const toggleAgent = (agentId: EnabledSchool) => {
    setLocalError(null);
    setEnabledAgents((prev) => {
      if (prev.includes(agentId)) {
        if (prev.length === 1) {
          setLocalError("至少保留一个智能体。");
          return prev;
        }
        return prev.filter((item) => item !== agentId);
      }
      return [...prev, agentId];
    });
  };

  if (!isAuthenticated) {
    return (
      <div className="oracle-chat oracle-chat--guest fade-in">
        <InkCard title="多智能体咨询台" icon="询">
          <section className="oracle-guest">
            <div className="oracle-guest__intro">
              <p className="oracle-guest__title">先输入你的问题，登录后继续完整分析</p>
              <p className="oracle-guest__desc">
                系统会根据问题自动调用紫微斗数、梅花易数与心学辅助，输出可执行建议与风险提醒。
              </p>
            </div>

            <form className="oracle-chat__composer stack" onSubmit={onGuestSubmit}>
              <div className="field">
                <label className="field__label" htmlFor="oracle-guest-query">你想咨询什么？</label>
                <textarea
                  id="oracle-guest-query"
                  className="oracle-chat__textarea"
                  placeholder="例如：我最近是否适合换工作，该怎么安排接下来一个月？"
                  value={guestQuery}
                  onChange={(event) => setGuestQuery(event.target.value)}
                  rows={5}
                />
                <div className="oracle-chat__prompt-row" aria-label="备选问题">
                  {QUICK_PROMPTS.map((prompt, index) => (
                    <button
                      key={`${prompt}-${index}`}
                      type="button"
                      className="oracle-turn__follow-chip"
                      onClick={() => setGuestQuery(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>

              {localError ? <p className="error-text">{localError}</p> : null}
              <div className="actions-row">
                <InkButton type="submit">发送并登录继续</InkButton>
              </div>
            </form>
          </section>
        </InkCard>
      </div>
    );
  }

  return (
    <div className="oracle-chat oracle-chat--flat fade-in">
      <InkCard title="多智能体咨询台" icon="卦">
        <div className="oracle-chat__workspace">
          <aside className="oracle-chat__sidebar" aria-label="对话历史">
            <div className="oracle-panel__header">
              <h3>历史会话</h3>
              <span>{conversations.length} 个</span>
            </div>

            <div className="oracle-history__list">
              {conversations.length === 0 ? <p className="oracle-history__empty">暂无历史会话</p> : null}
              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  className={`oracle-history__item ${activeConversationId === conversation.id ? "oracle-history__item--active" : ""}`}
                  onClick={() => {
                    void loadConversationTurns(conversation.id);
                  }}
                  disabled={conversationLoading || chatSession.loading}
                >
                  <p className="oracle-history__title">{conversationTitle(conversation)}</p>
                  <p className="oracle-history__meta">{conversation.turn_count || 0} 轮</p>
                </button>
              ))}
            </div>

            <InkButton
              type="button"
              onClick={() => {
                void onCreateNewConversation();
              }}
              disabled={chatSession.loading || conversationLoading}
            >
              开启新对话
            </InkButton>
          </aside>

          <section className="oracle-chat__main">
            <div ref={threadRef} className="oracle-chat__thread" aria-live="polite">
              {!chatSession.turns.length ? (
                <div className="oracle-chat__empty">
                  <p className="oracle-chat__empty-title">还没有咨询记录</p>
                  <p className="oracle-chat__empty-desc">输入问题后，系统会在这里按 chat 对话流持续返回。</p>
                </div>
              ) : null}

              {chatSession.turns.map((turn) => (
                <article
                  key={turn.id}
                  className={`oracle-turn ${selectedTurn?.id === turn.id ? "oracle-turn--selected" : ""}`}
                  onClick={() => setSelectedTurnId(turn.id)}
                >
                  <div className="oracle-turn__bubble oracle-turn__bubble--user">
                    <p className="oracle-turn__meta">你 · {formatTurnTime(turn.createdAt)}</p>
                    <p className="oracle-turn__query">{turn.query}</p>
                  </div>

                  <div className="oracle-turn__bubble oracle-turn__bubble--assistant">
                    <p className="oracle-turn__meta">
                      Oracle · {turn.status === "running" ? "执行计划中" : turn.status === "succeeded" ? "已完成" : "执行失败"}
                    </p>
                    {turn.contextSummary ? (
                      <p className="oracle-turn__context">上下文参考：{previewContext(turn.contextSummary)}</p>
                    ) : null}

                    {turn.answerText ? (
                      <div className="oracle-turn__answer markdown-body">
                        <MarkdownRenderer content={turn.answerText} />
                      </div>
                    ) : (
                      <p className="oracle-turn__plan-empty">正在分析，结果会按步骤返回...</p>
                    )}

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
                  rows={4}
                />
                <div className="oracle-chat__prompt-row" aria-label="备选问题">
                  {QUICK_PROMPTS.map((prompt, index) => (
                    <button
                      key={`${prompt}-${index}`}
                      type="button"
                      className="oracle-turn__follow-chip"
                      onClick={() => setUserQuery(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
                <p className="oracle-chat__agent-toggle-title">智能体配置（可多选）</p>
                <div className="oracle-chat__agent-toggle-row" aria-label="智能体配置">
                  {AGENT_OPTIONS.map((agent) => {
                    const active = enabledAgents.includes(agent.id);
                    return (
                      <button
                        key={agent.id}
                        type="button"
                        className={`oracle-agent-toggle ${active ? "oracle-agent-toggle--active" : ""}`}
                        onClick={() => toggleAgent(agent.id)}
                        aria-pressed={active}
                      >
                        <span className="oracle-agent-toggle__title">{agent.label}</span>
                        <span className="oracle-agent-toggle__desc">{agent.desc}</span>
                      </button>
                    );
                  })}
                </div>
                <p className="oracle-chat__tip">
                  已启用智能体：{enabledAgents.map((item) => AGENT_OPTIONS.find((opt) => opt.id === item)?.label || item).join("、")}
                </p>
              </div>

              {localError ? <p className="error-text">{localError}</p> : null}
              {!localError && chatSession.error ? <p className="error-text">{chatSession.error}</p> : null}
              {chatSession.loading ? <p className="oracle-chat__tip">当前轮次正在执行，可继续等待返回。</p> : null}

              <div className="actions-row">
                <InkButton type="submit" disabled={chatSession.loading}>
                  {chatSession.loading ? "执行中..." : "发送问题"}
                </InkButton>
              </div>
            </form>
          </section>

          <aside className="oracle-chat__inspector" aria-label="思路过程">
            <div className="oracle-panel__header">
              <h3>思路过程</h3>
              <span>{selectedTurn ? turnStatusLabel(selectedTurn.status) : "未开始"}</span>
            </div>

            {!selectedTurn ? (
              <p className="oracle-history__empty">请选择一轮对话查看计划步骤</p>
            ) : (
              <div className="oracle-inspector__content">
                <p className="oracle-inspector__meta">时间：{formatTurnTime(selectedTurn.createdAt)}</p>
                <p className="oracle-inspector__meta">安全：{DISCLAIMER_LABELS[selectedTurn.safetyDisclaimerLevel]}</p>

                <div className="oracle-turn__plan">
                  <p className="oracle-turn__section-title">工具执行计划</p>
                  {selectedTurn.planSteps.length ? (
                    <div className="oracle-turn__plan-list">
                      {selectedTurn.planSteps.map((step, index) => (
                        <div key={`${selectedTurn.id}-${step.tool_name}-${index}`} className="oracle-turn__plan-item">
                          <span>{step.display_name}</span>
                          <span className={`oracle-turn__status oracle-turn__status--${step.status}`}>
                            {statusLabel(step.status)}
                            {typeof step.elapsed_ms === "number" ? ` · ${step.elapsed_ms}ms` : ""}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="oracle-turn__plan-empty">本轮暂无工具步骤。</p>
                  )}
                </div>

                {selectedTurn.followUpQuestions.length ? (
                  <div className="oracle-turn__follow-grid">
                    {selectedTurn.followUpQuestions.map((question, index) => (
                      <button
                        key={`${selectedTurn.id}-${question}-${index}`}
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
              </div>
            )}
          </aside>
        </div>
      </InkCard>
    </div>
  );
}
