import { FormEvent, useEffect, useMemo, useState } from "react";

import { oracleChat } from "../api";
import type { EnabledSchool, OracleActionItem } from "../types";
import { InkButton } from "./InkButton";
import { InkCard } from "./InkCard";
import { MarkdownRenderer } from "./MarkdownRenderer";

type DivinationMode = "ziwei" | "meihua";

interface AssistTurn {
  id: string;
  query: string;
  answer: string;
  actionItems: OracleActionItem[];
  followUpQuestions: string[];
  createdAt: string;
}

interface DivinationAssistChatProps {
  mode: DivinationMode;
  sourceTitle: string;
  sourceText: string;
}

const STORAGE_PREFIX = "oracle:divination:assist:v1";

/**
 * 生成稳定的简易哈希，用于基于求签内容区分本地会话存储键。
 */
function simpleHash(text: string): string {
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(index)) | 0;
  }
  return Math.abs(hash).toString(36);
}

/**
 * 构建解签机器人系统所需的画像摘要，将求签结果压缩注入上下文。
 */
function buildProfileSummary(mode: DivinationMode, sourceTitle: string, sourceText: string): string {
  const trimmed = sourceText.replace(/\s+/g, " ").trim();
  const clipped = trimmed.length > 2200 ? `${trimmed.slice(0, 2200)}...` : trimmed;
  const modeLabel = mode === "ziwei" ? "紫微斗数" : "梅花易数";
  return [
    `当前是${modeLabel}解签场景，请围绕用户求签结果做持续解读。`,
    "回答重点：先解释签文含义，再给可执行建议，保持温和、非绝对化。",
    `求签标题：${sourceTitle}`,
    `求签内容：${clipped || "暂无"}`,
  ].join("\n");
}

/**
 * 从历史轮次中构建轻量对话摘要，帮助后端编排器保持连续性。
 */
function buildHistorySummary(turns: AssistTurn[]): string {
  const recent = turns.slice(-4);
  return recent
    .map((turn, index) => {
      const answer = turn.answer.replace(/\s+/g, " ").trim();
      const preview = answer.length > 180 ? `${answer.slice(0, 180)}...` : answer;
      return `${index + 1}. 用户：${turn.query}\n解签助手：${preview}`;
    })
    .join("\n\n");
}

/**
 * 解签辅助聊天组件：读取当前求签结果，并支持多轮追问。
 */
export function DivinationAssistChat({ mode, sourceTitle, sourceText }: DivinationAssistChatProps) {
  const storageKey = useMemo(() => {
    return `${STORAGE_PREFIX}:${mode}:${simpleHash(`${sourceTitle}\n${sourceText}`)}`;
  }, [mode, sourceText, sourceTitle]);

  const enabledSchools = useMemo<EnabledSchool[]>(() => {
    if (mode === "ziwei") {
      return ["ziwei", "philosophy", "actionizer"];
    }
    return ["meihua", "philosophy", "actionizer"];
  }, [mode]);

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [turns, setTurns] = useState<AssistTurn[]>([]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) {
        setTurns([]);
        return;
      }
      const parsed = JSON.parse(raw) as AssistTurn[];
      if (!Array.isArray(parsed)) {
        setTurns([]);
        return;
      }
      setTurns(parsed);
    } catch {
      setTurns([]);
    }
  }, [storageKey]);

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(turns));
    } catch {
      // 忽略本地存储异常，保持页面功能可用。
    }
  }, [storageKey, turns]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const ask = query.trim();
    if (!ask || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await oracleChat({
        user_query: ask,
        selected_school: "east",
        enabled_schools: enabledSchools,
        user_profile_summary: buildProfileSummary(mode, sourceTitle, sourceText),
        conversation_history_summary: buildHistorySummary(turns) || undefined,
      });
      const data = response.data;
      if (!data) {
        throw new Error("解签助手返回为空，请稍后重试。");
      }
      const nextTurn: AssistTurn = {
        id: `assist_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
        query: ask,
        answer: data.answer_text || "",
        actionItems: Array.isArray(data.action_items) ? data.action_items : [],
        followUpQuestions: Array.isArray(data.follow_up_questions) ? data.follow_up_questions : [],
        createdAt: new Date().toISOString(),
      };
      setTurns((prev) => [...prev, nextTurn]);
      setQuery("");
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "解签请求失败，请稍后重试。";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <InkCard title="解签助手" icon="聊">
      <div className="divination-assist">
        <p className="divination-assist__hint">
          已自动读取当前{mode === "ziwei" ? "紫微" : "梅花"}求签内容，你可以继续追问细节、行动节奏和注意事项。
        </p>

        {!turns.length ? (
          <div className="divination-assist__empty">
            <p className="divination-assist__empty-title">还没有提问</p>
            <p className="divination-assist__empty-text">示例：我下周先做哪一步最稳妥？这条建议对应的风险点是什么？</p>
          </div>
        ) : (
          <div className="divination-assist__turns">
            {turns.map((turn) => (
              <article key={turn.id} className="divination-assist__turn">
                <p className="divination-assist__q">你：{turn.query}</p>
                <div className="divination-assist__a markdown-body">
                  <MarkdownRenderer content={turn.answer} />
                </div>
                {turn.actionItems.length ? (
                  <div className="divination-assist__actions">
                    {turn.actionItems.map((item, index) => (
                      <p key={`${turn.id}-${item.task}-${index}`} className="divination-assist__action-item">
                        {index + 1}. {item.task}（{item.when}）
                      </p>
                    ))}
                  </div>
                ) : null}
                {turn.followUpQuestions.length ? (
                  <div className="divination-assist__chips">
                    {turn.followUpQuestions.map((question, index) => (
                      <button
                        key={`${turn.id}-${question}-${index}`}
                        type="button"
                        className="oracle-turn__follow-chip"
                        onClick={() => setQuery(question)}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}

        <form className="stack" onSubmit={onSubmit}>
          <div className="field">
            <label className="field__label" htmlFor={`assist-${mode}-query`}>继续解签提问</label>
            <textarea
              id={`assist-${mode}-query`}
              className="oracle-chat__textarea"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如：结合我的情况，接下来一周具体怎么执行更稳妥？"
              rows={3}
            />
          </div>
          {error ? <p className="error-text">{error}</p> : null}
          <div className="actions-row">
            <InkButton type="submit" disabled={loading}>
              {loading ? "解签中..." : "发送给解签助手"}
            </InkButton>
          </div>
        </form>
      </div>
    </InkCard>
  );
}

