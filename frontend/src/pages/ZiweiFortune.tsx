import { FormEvent, useEffect, useMemo, useState } from "react";

import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import {
  clearZiweiFortuneError,
  getZiweiFortuneSessionState,
  setZiweiFortuneError,
  startZiweiDivinationTask,
  subscribeZiweiFortuneSession,
  updateZiweiFortuneForm,
} from "../stores/ziweiFortuneSession";
import type { BirthInfo } from "../types";

const pad2 = (value: number) => String(value).padStart(2, "0");

const hourToTimezone = (hour: number) => {
  if (hour === 23) {
    return 12;
  }
  if (hour === 0) {
    return 0;
  }
  return Math.floor((hour + 1) / 2);
};

export default function ZiweiFortunePage() {
  const [session, setSession] = useState(getZiweiFortuneSessionState());

  useEffect(() => {
    const unsubscribe = subscribeZiweiFortuneSession((state) => {
      setSession(state);
    });
    return unsubscribe;
  }, []);

  const inputPreview = useMemo(() => {
    const y = Number(session.form.year) || 0;
    const m = Number(session.form.month) || 0;
    const d = Number(session.form.day) || 0;
    const h = Number(session.form.hour) || 0;
    const min = Number(session.form.minute) || 0;
    return `${session.form.calendar === "lunar" ? "阴历" : "阳历"} ${y}年${m}月${d}日 ${pad2(h)}:${pad2(min)} ${session.form.gender}`;
  }, [
    session.form.calendar,
    session.form.day,
    session.form.gender,
    session.form.hour,
    session.form.minute,
    session.form.month,
    session.form.year,
  ]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearZiweiFortuneError();

    const yearNumber = Number(session.form.year);
    const monthNumber = Number(session.form.month);
    const dayNumber = Number(session.form.day);
    const hourNumber = Number(session.form.hour);
    const minuteNumber = Number(session.form.minute);

    if ([yearNumber, monthNumber, dayNumber, hourNumber, minuteNumber].some((value) => Number.isNaN(value))) {
      setZiweiFortuneError("请完整填写出生年月日和时间。");
      return;
    }
    if (yearNumber < 1900 || yearNumber > 2100) {
      setZiweiFortuneError("年份范围建议在 1900-2100。");
      return;
    }
    if (monthNumber < 1 || monthNumber > 12) {
      setZiweiFortuneError("月份范围应为 1-12。");
      return;
    }
    if (session.form.calendar === "lunar") {
      if (dayNumber < 1 || dayNumber > 30) {
        setZiweiFortuneError("阴历日期范围应为 1-30。");
        return;
      }
    } else {
      const temp = new Date(yearNumber, monthNumber - 1, dayNumber);
      const isValidSolarDate =
        temp.getFullYear() === yearNumber
        && temp.getMonth() === monthNumber - 1
        && temp.getDate() === dayNumber;
      if (!isValidSolarDate) {
        setZiweiFortuneError("阳历日期无效，请检查年月日。");
        return;
      }
    }
    if (hourNumber < 0 || hourNumber > 23 || minuteNumber < 0 || minuteNumber > 59) {
      setZiweiFortuneError("时间无效，请使用 24 小时制。");
      return;
    }

    await startZiweiDivinationTask({
      question: session.form.question.trim() || "请给我一份紫微斗数长线解读与行动建议。",
      birth_info: {
        date: `${yearNumber}-${pad2(monthNumber)}-${pad2(dayNumber)}`,
        timezone: hourToTimezone(hourNumber),
        gender: session.form.gender,
        calendar: session.form.calendar,
      },
    });
  };

  return (
    <div className="stack fade-in">
      <InkCard title="紫微斗数求签" icon="紫">
        <form className="stack" onSubmit={onSubmit}>
          <div className="field">
            <label className="field__label" htmlFor="ziwei-question">求签问题</label>
            <textarea
              id="ziwei-question"
              className="oracle-chat__textarea"
              value={session.form.question}
              onChange={(event) => updateZiweiFortuneForm({ question: event.target.value })}
              rows={3}
            />
          </div>

          <div className="form-grid">
            <div className="field">
              <label className="field__label" htmlFor="ziwei-calendar">历法</label>
              <select
                id="ziwei-calendar"
                value={session.form.calendar}
                onChange={(event) => updateZiweiFortuneForm({ calendar: event.target.value as BirthInfo["calendar"] })}
              >
                <option value="lunar">阴历（农历）</option>
                <option value="solar">阳历（公历）</option>
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ziwei-gender">性别</label>
              <select
                id="ziwei-gender"
                value={session.form.gender}
                onChange={(event) => updateZiweiFortuneForm({ gender: event.target.value as BirthInfo["gender"] })}
              >
                <option value="男">男</option>
                <option value="女">女</option>
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ziwei-year">出生年</label>
              <input
                id="ziwei-year"
                type="number"
                value={session.form.year}
                onChange={(event) => updateZiweiFortuneForm({ year: event.target.value })}
                min={1900}
                max={2100}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ziwei-month">出生月</label>
              <input
                id="ziwei-month"
                type="number"
                value={session.form.month}
                onChange={(event) => updateZiweiFortuneForm({ month: event.target.value })}
                min={1}
                max={12}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ziwei-day">出生日</label>
              <input
                id="ziwei-day"
                type="number"
                value={session.form.day}
                onChange={(event) => updateZiweiFortuneForm({ day: event.target.value })}
                min={1}
                max={session.form.calendar === "lunar" ? 30 : 31}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ziwei-hour">出生时（24小时）</label>
              <input
                id="ziwei-hour"
                type="number"
                value={session.form.hour}
                onChange={(event) => updateZiweiFortuneForm({ hour: event.target.value })}
                min={0}
                max={23}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ziwei-minute">出生分</label>
              <input
                id="ziwei-minute"
                type="number"
                value={session.form.minute}
                onChange={(event) => updateZiweiFortuneForm({ minute: event.target.value })}
                min={0}
                max={59}
              />
            </div>
          </div>

          <p className="oracle-chat__tip">当前输入：{inputPreview}</p>
          {session.error ? <p className="error-text">{session.error}</p> : null}
          {session.loading ? <p className="oracle-chat__tip">任务进行中，切换页面后回来仍会保留状态。</p> : null}

          <div className="actions-row">
            <InkButton type="submit" disabled={session.loading}>
              {session.loading ? "求签中..." : "开始紫微求签"}
            </InkButton>
          </div>
        </form>
      </InkCard>

      {session.result ? (
        <div className="stack fade-in-up">
          <InkCard title="紫微解读结果" icon="解">
            <div className="meta-grid meta-grid--compact">
              <div className="meta-item">
                <p className="meta-item__label">生成时间</p>
                <p className="meta-item__value">{session.result.generated_at}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">模型</p>
                <p className="meta-item__value">{session.result.provider} / {session.result.model}</p>
              </div>
            </div>
            <div className="markdown-body">
              <MarkdownRenderer content={session.result.reading} />
            </div>
          </InkCard>

          <InkCard title="命盘摘要">
            <pre className="pre-wrap">{session.result.chart_summary}</pre>
          </InkCard>
        </div>
      ) : null}
    </div>
  );
}
