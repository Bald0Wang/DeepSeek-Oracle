import { FormEvent, useMemo, useState } from "react";

import { oracleChat } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import type { BirthInfo, DisclaimerLevel, EnabledSchool, OracleChatRequest, OracleChatResponse, SelectedSchool } from "../types";


const SCHOOL_OPTIONS: Array<{ value: SelectedSchool; label: string }> = [
  { value: "east", label: "东方占卜（MVP）" },
  { value: "mixed", label: "中西混合" },
  { value: "west", label: "西方占卜" },
];

const ENABLED_SCHOOL_OPTIONS: Array<{ value: EnabledSchool; label: string }> = [
  { value: "ziwei", label: "紫微长线" },
  { value: "meihua", label: "梅花短线" },
  { value: "daily_card", label: "每日卡片" },
  { value: "philosophy", label: "心法解读" },
  { value: "actionizer", label: "行动化" },
];

const DISCLAIMER_LABELS: Record<DisclaimerLevel, string> = {
  none: "普通提示",
  light: "轻度提醒",
  strong: "强提醒",
};

const DEFAULT_ENABLED: EnabledSchool[] = ["ziwei", "meihua", "daily_card", "philosophy", "actionizer"];
const CORE_SKILLS: EnabledSchool[] = ["ziwei", "meihua", "daily_card", "philosophy", "tarot"];
const QUICK_PROMPTS = [
  "我最近在考虑换工作，想看长期走势与本周应对策略。",
  "这周有一次重要沟通，我该怎么准备更稳妥？",
  "最近情绪波动有点大，怎么调整节奏并落到行动？",
];


export default function OracleChatPage() {
  const [userQuery, setUserQuery] = useState("");
  const [historySummary, setHistorySummary] = useState("");
  const [profileSummary, setProfileSummary] = useState("");
  const [selectedSchool, setSelectedSchool] = useState<SelectedSchool>("east");
  const [enabledSchools, setEnabledSchools] = useState<EnabledSchool[]>(DEFAULT_ENABLED);
  const [birthDate, setBirthDate] = useState("");
  const [timezone, setTimezone] = useState("4");
  const [gender, setGender] = useState<BirthInfo["gender"]>("男");
  const [calendar, setCalendar] = useState<BirthInfo["calendar"]>("solar");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formTip, setFormTip] = useState<string | null>("MVP 默认东方模式，回答会自动附带安全提示。");
  const [result, setResult] = useState<OracleChatResponse | null>(null);

  const timezoneOptions = useMemo(
    () => Array.from({ length: 13 }, (_, index) => ({ value: String(index), label: `${index}` })),
    []
  );

  const toggleEnabledSchool = (value: EnabledSchool) => {
    setEnabledSchools((prev) => {
      if (prev.includes(value) && CORE_SKILLS.includes(value)) {
        const next = prev.filter((item) => item !== value);
        const hasCore = next.some((item) => CORE_SKILLS.includes(item));
        if (!hasCore) {
          setFormTip("至少保留一个核心技能（紫微/梅花/每日卡片/心法）。");
          return prev;
        }
      }
      if (prev.includes(value)) {
        setFormTip(null);
        return prev.filter((item) => item !== value);
      }
      setFormTip(null);
      return [...prev, value];
    });
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setResult(null);

    const query = userQuery.trim();
    if (!query) {
      setError("请先输入你想咨询的问题。");
      return;
    }

    const payload: OracleChatRequest = {
      user_query: query,
      conversation_history_summary: historySummary.trim() || undefined,
      user_profile_summary: profileSummary.trim() || undefined,
      selected_school: selectedSchool,
      enabled_schools: enabledSchools,
    };

    if (birthDate) {
      payload.birth_info = {
        date: birthDate,
        timezone: Number(timezone),
        gender,
        calendar,
      };
    }

    setLoading(true);
    try {
      const response = await oracleChat(payload);
      setResult(response.data || null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "咨询失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="oracle-chat fade-in">
      <InkCard title="多智能体咨询台" icon="卦">
        <form className="stack" onSubmit={onSubmit}>
          <div className="field">
            <label className="field__label" htmlFor="oracle-query">咨询问题</label>
            <textarea
              id="oracle-query"
              className="oracle-chat__textarea"
              placeholder="例如：我最近在考虑换工作，想看长期走势与近期最稳妥的行动。"
              value={userQuery}
              onChange={(event) => setUserQuery(event.target.value)}
              rows={4}
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

          <div className="form-grid">
            <div className="field">
              <label className="field__label" htmlFor="oracle-school">占法模式</label>
              <select
                id="oracle-school"
                value={selectedSchool}
                onChange={(event) => setSelectedSchool(event.target.value as SelectedSchool)}
              >
                {SCHOOL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <p className="field__hint">MVP 默认仅启用东方技能，西方路由会自动降级。</p>
            </div>

            <div className="field">
              <label className="field__label">启用技能</label>
              <div className="oracle-chat__skill-grid">
                {ENABLED_SCHOOL_OPTIONS.map((option) => (
                  <label key={option.value} className="oracle-chat__skill-item">
                    <input
                      type="checkbox"
                      checked={enabledSchools.includes(option.value)}
                      onChange={() => toggleEnabledSchool(option.value)}
                    />
                    <span>{option.label}</span>
                  </label>
                ))}
              </div>
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
                <label className="field__label" htmlFor="oracle-history">对话历史摘要</label>
                <textarea
                  id="oracle-history"
                  className="oracle-chat__textarea"
                  placeholder="例如：此前连续两次咨询职业路径，担心决策风险。"
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

          {error ? <p className="error-text">{error}</p> : null}
          {formTip ? <p className="oracle-chat__tip">{formTip}</p> : null}

          <div className="actions-row">
            <InkButton type="submit" disabled={loading}>
              {loading ? "咨询中..." : "开始咨询"}
            </InkButton>
            <InkButton
              type="button"
              kind="ghost"
              onClick={() => {
                setResult(null);
                setError(null);
              }}
              disabled={loading}
            >
              清空结果
            </InkButton>
          </div>
        </form>
      </InkCard>

      {result ? (
        <div className="stack fade-in-up">
          <InkCard title="编排结果" icon="解">
            <div className="stack">
              <div className="meta-grid meta-grid--compact">
                <div className="meta-item">
                  <p className="meta-item__label">安全级别</p>
                  <p className="meta-item__value">{DISCLAIMER_LABELS[result.safety_disclaimer_level]}</p>
                </div>
                <div className="meta-item">
                  <p className="meta-item__label">追问数量</p>
                  <p className="meta-item__value">{result.follow_up_questions.length}</p>
                </div>
                <div className="meta-item">
                  <p className="meta-item__label">行动项</p>
                  <p className="meta-item__value">{result.action_items.length}</p>
                </div>
              </div>

              <div className="markdown-body">
                <MarkdownRenderer content={result.answer_text} />
              </div>
            </div>
          </InkCard>

          <InkCard title="行动清单" icon="策">
            <div className="stack">
              {result.action_items.map((item, index) => (
                <div key={`${item.task}-${index}`} className="oracle-chat__action-item">
                  <p className="oracle-chat__action-title">{index + 1}. {item.task}</p>
                  <p className="oracle-chat__action-meta">建议时间：{item.when}</p>
                  <p className="oracle-chat__action-meta">原因：{item.reason}</p>
                </div>
              ))}
            </div>
          </InkCard>

          <InkCard title="可追问方向" icon="问">
            <ul className="oracle-chat__question-list">
              {result.follow_up_questions.map((question, index) => (
                <li key={`${question}-${index}`}>{question}</li>
              ))}
            </ul>
          </InkCard>

          <InkCard title="调用轨迹" icon="迹">
            <pre className="pre-wrap">{JSON.stringify(result.trace, null, 2)}</pre>
          </InkCard>
        </div>
      ) : null}
    </div>
  );
}
