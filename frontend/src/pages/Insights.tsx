import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getInsightOverview } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LifeKlineChart } from "../components/LifeKlineChart";
import { LoadingAnimation } from "../components/LoadingAnimation";
import type { InsightOverviewData, MonthlyCalendarDay, MonthlyCalendarPayload } from "../types";

type CalendarView = "near30" | "current" | "next";

export default function InsightsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<InsightOverviewData | null>(null);
  const [calendarView, setCalendarView] = useState<CalendarView>("near30");
  const [resultIdInput, setResultIdInput] = useState("");

  const loadData = async (resultId?: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await getInsightOverview(resultId);
      setData(response.data || null);
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) {
        // No analysis profile yet: treat as empty state instead of hard error.
        setData(null);
        setError(null);
      } else {
        setError(err instanceof Error ? err.message : "加载人生线与日历失败。");
        setData(null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const onSubmitResultId = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = resultIdInput.trim();
    if (!value) {
      await loadData();
      return;
    }
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setError("结果ID格式无效，请输入正整数。");
      return;
    }
    await loadData(parsed);
  };

  const calendarDays: MonthlyCalendarDay[] = useMemo(() => {
    if (!data) {
      return [];
    }
    if (calendarView === "near30") {
      return data.calendar.near_30_days;
    }
    const payload: MonthlyCalendarPayload =
      calendarView === "current" ? data.calendar.current_month : data.calendar.next_month;
    return payload.days || [];
  }, [calendarView, data]);

  const calendarCaption = useMemo(() => {
    if (!data) {
      return "";
    }
    if (calendarView === "near30") {
      return "未来30天（跨月）";
    }
    return calendarView === "current"
      ? `本月 ${data.calendar.current_month.month_key}`
      : `下月 ${data.calendar.next_month.month_key}`;
  }, [calendarView, data]);

  return (
    <div className="insights-page fade-in">
      <InkCard title="人生线与日历总览" icon="盘">
        <form className="insights-toolbar" onSubmit={onSubmitResultId}>
          <div className="field">
            <label className="field__label" htmlFor="insights-result-id">结果ID（可选）</label>
            <input
              id="insights-result-id"
              type="text"
              value={resultIdInput}
              onChange={(event) => setResultIdInput(event.target.value)}
              placeholder="留空=按你最新一次分析"
            />
          </div>
          <div className="actions-row">
            <InkButton type="submit" disabled={loading}>{loading ? "加载中..." : "查询"}</InkButton>
            <InkButton type="button" kind="ghost" disabled={loading} onClick={() => void loadData()}>
              刷新最新
            </InkButton>
          </div>
        </form>

        {error ? <p className="error-text">{error}</p> : null}
        {!loading && !error && !data ? <p className="loading-state-text">暂无数据，请先完成一次开始分析。</p> : null}
        {loading ? (
          <div className="loading-container">
            <LoadingAnimation size="large" />
            <p className="loading-state-text">正在读取人生线与日历...</p>
          </div>
        ) : null}
      </InkCard>

      {data ? (
        <>
          <InkCard title="紫微日历" icon="历">
            <div className="insights-segmented">
              <button
                type="button"
                className={calendarView === "near30" ? "active" : ""}
                onClick={() => setCalendarView("near30")}
              >
                近30天
              </button>
              <button
                type="button"
                className={calendarView === "current" ? "active" : ""}
                onClick={() => setCalendarView("current")}
              >
                本月
              </button>
              <button
                type="button"
                className={calendarView === "next" ? "active" : ""}
                onClick={() => setCalendarView("next")}
              >
                下月
              </button>
            </div>
            <p className="home-search__hint">
              {calendarCaption} · 主轴：{data.calendar.current_month.dominant_focus}
            </p>
            <div className="calendar-grid">
              {calendarDays.map((day) => (
                <article key={day.date} className="calendar-day-card">
                  <p className="calendar-day-card__date">{day.date}</p>
                  <p className="calendar-day-card__score">{day.level} · {day.score}</p>
                  <p className="calendar-day-card__text">宜：{day.yi.join("、")}</p>
                  <p className="calendar-day-card__text">忌：{day.ji.join("、")}</p>
                  <p className="calendar-day-card__text">{day.note}</p>
                </article>
              ))}
            </div>
          </InkCard>

          <InkCard title="人生K线关键点（每5年）" icon="线">
            <div className="meta-grid meta-grid--compact">
              <div className="meta-item">
                <div className="meta-item__label">平均分</div>
                <div className="meta-item__value">{data.life_kline.summary.averageScore}</div>
              </div>
              <div className="meta-item">
                <div className="meta-item__label">高点年龄</div>
                <div className="meta-item__value">{data.life_kline.summary.bestYears.join(" / ")}</div>
              </div>
              <div className="meta-item">
                <div className="meta-item__label">低点年龄</div>
                <div className="meta-item__value">{data.life_kline.summary.worstYears.join(" / ")}</div>
              </div>
            </div>
            <p className="home-search__hint">{data.life_kline.summary.overallTrend}</p>
            <LifeKlineChart
              points={data.life_kline.sparse.years}
              bestYears={data.life_kline.summary.bestYears}
              worstYears={data.life_kline.summary.worstYears}
            />
            <div className="kline-list">
              {data.life_kline.sparse.years.map((item) => (
                <article key={`${item.age}-${item.year}`} className="kline-item">
                  <p className="kline-item__title">{item.age}岁 · {item.year} · {item.yearGanZhi}</p>
                  <p className="kline-item__meta">评分 {item.score} · {item.summary} · 大运 {item.daYun}</p>
                </article>
              ))}
            </div>
          </InkCard>
        </>
      ) : null}

      <InkCard title="快捷入口" icon="捷">
        <div className="actions-row">
          <Link to="/start-analysis">
            <InkButton type="button" kind="ghost">返回开始分析</InkButton>
          </Link>
          <Link to="/history">
            <InkButton type="button" kind="ghost">查看历史记录</InkButton>
          </Link>
        </div>
      </InkCard>
    </div>
  );
}
