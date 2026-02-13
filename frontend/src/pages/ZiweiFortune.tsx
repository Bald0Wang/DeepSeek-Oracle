import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import { DivinationAssistChat } from "../components/DivinationAssistChat";
import {
  clearZiweiFortuneError,
  getZiweiFortuneSessionState,
  setZiweiFortuneError,
  startZiweiDivinationTask,
  subscribeZiweiFortuneSession,
  updateZiweiFortuneForm,
} from "../stores/ziweiFortuneSession";
import {
  formatBirthPreview,
  formatTrueSolarCorrectionPreview,
  getTrueSolarCityOptions,
  getTrueSolarProvinceOptions,
  toBirthInfo,
  validateBirthForm,
} from "../utils/birthForm";
import type { BirthInfo } from "../types";

export default function ZiweiFortunePage() {
  const [session, setSession] = useState(getZiweiFortuneSessionState());

  useEffect(() => {
    const unsubscribe = subscribeZiweiFortuneSession((state) => {
      setSession(state);
    });
    return unsubscribe;
  }, []);

  const inputPreview = useMemo(() => {
    return formatBirthPreview(session.form);
  }, [session.form]);
  const provinceOptions = useMemo(() => getTrueSolarProvinceOptions(), []);
  const cityOptions = useMemo(() => getTrueSolarCityOptions(session.form.provinceCode), [session.form.provinceCode]);
  const trueSolarPreview = useMemo(() => formatTrueSolarCorrectionPreview(session.form), [session.form]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearZiweiFortuneError();

    const validationError = validateBirthForm(session.form);
    if (validationError) {
      setZiweiFortuneError(validationError);
      return;
    }

    await startZiweiDivinationTask({
      question: session.form.question.trim() || "请给我一份紫微斗数长线解读与行动建议。",
      birth_info: toBirthInfo(session.form),
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
            <div className="field">
              <label className="field__label" htmlFor="ziwei-province">省级区域</label>
              <select
                id="ziwei-province"
                value={session.form.provinceCode}
                onChange={(event) => {
                  const nextProvinceCode = event.target.value;
                  const nextCities = getTrueSolarCityOptions(nextProvinceCode);
                  updateZiweiFortuneForm({
                    provinceCode: nextProvinceCode,
                    cityCode: nextCities[0]?.code || "",
                  });
                }}
              >
                {provinceOptions.map((item) => (
                  <option key={item.code} value={item.code}>{item.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ziwei-city">城市（真太阳时）</label>
              <select
                id="ziwei-city"
                value={session.form.cityCode}
                onChange={(event) => updateZiweiFortuneForm({ cityCode: event.target.value })}
              >
                {cityOptions.map((item) => (
                  <option key={item.code} value={item.code}>{item.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ziwei-true-solar">真太阳时校正</label>
              <select
                id="ziwei-true-solar"
                value={session.form.enableTrueSolar ? "on" : "off"}
                onChange={(event) => updateZiweiFortuneForm({ enableTrueSolar: event.target.value === "on" })}
              >
                <option value="off">不启用</option>
                <option value="on">启用（经度+均时差）</option>
              </select>
            </div>
          </div>

          <p className="oracle-chat__tip">当前输入：{inputPreview}</p>
          <p className="oracle-chat__tip">{trueSolarPreview}</p>
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
            <div className="actions-row">
              {session.result.record_id ? (
                <Link to={`/history/divination/${session.result.record_id}`}>
                  <InkButton type="button" kind="ghost">查看已存档记录</InkButton>
                </Link>
              ) : (
                <InkButton type="button" kind="ghost" disabled>记录存储中</InkButton>
              )}
              <Link to="/history">
                <InkButton type="button" kind="secondary">打开历史存储桶</InkButton>
              </Link>
            </div>
          </InkCard>

          <InkCard title="命盘摘要">
            <pre className="pre-wrap">{session.result.chart_summary}</pre>
          </InkCard>

          <DivinationAssistChat
            mode="ziwei"
            sourceTitle={session.form.question || "紫微斗数求签"}
            sourceText={`${session.result.reading}\n\n命盘摘要：\n${session.result.chart_summary}`}
          />
        </div>
      ) : null}
    </div>
  );
}
