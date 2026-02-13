import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  generateInsightOverviewByBirthInfo,
  getHistory,
  getInsightOverview,
} from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LifeKlineChart } from "../components/LifeKlineChart";
import { LoadingAnimation } from "../components/LoadingAnimation";
import type { HistoryItem, InsightOverviewData, MonthlyCalendarDay, MonthlyCalendarPayload } from "../types";
import type { ZiweiFortuneFormState } from "../stores/ziweiFortuneSession";
import { formatBirthPreview, toBirthInfo, validateBirthForm } from "../utils/birthForm";

type CalendarView = "near30" | "current" | "next";

const SOLAR_FESTIVALS: Record<string, string[]> = {
  "01-01": ["元旦"],
  "02-14": ["情人节"],
  "03-08": ["妇女节"],
  "04-01": ["愚人节"],
  "05-01": ["劳动节"],
  "05-04": ["青年节"],
  "06-01": ["儿童节"],
  "07-01": ["建党节"],
  "08-01": ["建军节"],
  "09-10": ["教师节"],
  "10-01": ["国庆节"],
  "12-24": ["平安夜"],
  "12-25": ["圣诞节"],
};

const LUNAR_FESTIVALS: Record<string, string> = {
  "正月-1": "春节",
  "正月-15": "元宵节",
  "五月-5": "端午节",
  "七月-7": "七夕",
  "八月-15": "中秋节",
  "九月-9": "重阳节",
  "腊月-8": "腊八节",
  "腊月-23": "小年",
  "腊月-24": "小年",
};

const SOLAR_TERMS_21ST = [
  { name: "小寒", month: 1, c: 5.4055 },
  { name: "大寒", month: 1, c: 20.12 },
  { name: "立春", month: 2, c: 3.87 },
  { name: "雨水", month: 2, c: 18.73 },
  { name: "惊蛰", month: 3, c: 5.63 },
  { name: "春分", month: 3, c: 20.646 },
  { name: "清明", month: 4, c: 4.81 },
  { name: "谷雨", month: 4, c: 20.1 },
  { name: "立夏", month: 5, c: 5.52 },
  { name: "小满", month: 5, c: 21.04 },
  { name: "芒种", month: 6, c: 5.678 },
  { name: "夏至", month: 6, c: 21.37 },
  { name: "小暑", month: 7, c: 7.108 },
  { name: "大暑", month: 7, c: 22.83 },
  { name: "立秋", month: 8, c: 7.5 },
  { name: "处暑", month: 8, c: 23.13 },
  { name: "白露", month: 9, c: 7.646 },
  { name: "秋分", month: 9, c: 23.042 },
  { name: "寒露", month: 10, c: 8.318 },
  { name: "霜降", month: 10, c: 23.438 },
  { name: "立冬", month: 11, c: 7.438 },
  { name: "小雪", month: 11, c: 22.36 },
  { name: "大雪", month: 12, c: 7.18 },
  { name: "冬至", month: 12, c: 21.94 },
];

const TWO_DIGIT = (value: number) => String(value).padStart(2, "0");

/**
 * 生成本地日期键（YYYY-MM-DD），用于“今日高亮”匹配。
 */
const getTodayDateKey = () => {
  const today = new Date();
  return `${today.getFullYear()}-${TWO_DIGIT(today.getMonth() + 1)}-${TWO_DIGIT(today.getDate())}`;
};

/**
 * 计算24节气（21世纪常用近似公式），返回当年的“MM-DD => 节气名称”映射。
 */
const buildSolarTermMap = (year: number) => {
  const yearTail = year % 100;
  const termMap: Record<string, string> = {};
  SOLAR_TERMS_21ST.forEach((item) => {
    const day = Math.floor(yearTail * 0.2422 + item.c) - Math.floor((yearTail - 1) / 4);
    const key = `${TWO_DIGIT(item.month)}-${TWO_DIGIT(day)}`;
    termMap[key] = item.name;
  });
  return termMap;
};

/**
 * 解析某天对应的农历月日，用于匹配传统节日。
 */
const parseLunarMonthDay = (dateStr: string): { month: string; day: number } | null => {
  try {
    const date = new Date(`${dateStr}T00:00:00`);
    const formatter = new Intl.DateTimeFormat("zh-CN-u-ca-chinese", {
      month: "long",
      day: "numeric",
    });
    const parts = formatter.formatToParts(date);
    const monthPart = parts.find((part) => part.type === "month")?.value || "";
    const dayPart = parts.find((part) => part.type === "day")?.value || "";
    const day = Number(dayPart.replace(/[^\d]/g, ""));
    if (!monthPart || Number.isNaN(day) || day <= 0) {
      return null;
    }
    const month = monthPart.replace("月", "").replace("十二", "腊");
    return { month: `${month}月`.replace("腊月月", "腊月"), day };
  } catch {
    return null;
  }
};

/**
 * 汇总单日的“节日 + 节气”标签。
 */
const buildCalendarMarkers = (dateStr: string, solarTermMap: Record<string, string>) => {
  const markerSet = new Set<string>();
  const [, month = "", day = ""] = dateStr.split("-");
  const mdKey = `${month}-${day}`;

  (SOLAR_FESTIVALS[mdKey] || []).forEach((item) => markerSet.add(item));
  if (solarTermMap[mdKey]) {
    markerSet.add(solarTermMap[mdKey]);
  }

  const lunar = parseLunarMonthDay(dateStr);
  if (lunar) {
    const lunarKey = `${lunar.month}-${lunar.day}`;
    const lunarFestival = LUNAR_FESTIVALS[lunarKey];
    if (lunarFestival) {
      markerSet.add(lunarFestival);
    }
  }

  return Array.from(markerSet);
};

export default function InsightsPage() {
  const [loading, setLoading] = useState(true);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<InsightOverviewData | null>(null);
  const [calendarView, setCalendarView] = useState<CalendarView>("near30");
  const [historyOptions, setHistoryOptions] = useState<HistoryItem[]>([]);
  const [selectedResultId, setSelectedResultId] = useState<string>("");
  const [birthForm, setBirthForm] = useState<ZiweiFortuneFormState>({
    question: "",
    calendar: "lunar",
    year: "2000",
    month: "1",
    day: "1",
    hour: "0",
    minute: "0",
    gender: "男",
  });

  const loadData = async (resultId?: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await getInsightOverview(resultId);
      setData(response.data || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载人生线与日历失败。");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 加载可选分析历史，供用户按生成时间选择数据源。
   */
  const loadHistoryOptions = async () => {
    setOptionsLoading(true);
    try {
      const response = await getHistory(1, 80);
      const items = response.data?.items || [];
      setHistoryOptions(items);
      setSelectedResultId((prev) => {
        if (prev && items.some((item) => String(item.id) === prev)) {
          return prev;
        }
        return items.length ? String(items[0].id) : "";
      });
    } catch {
      setHistoryOptions([]);
      setSelectedResultId("");
    } finally {
      setOptionsLoading(false);
    }
  };

  /**
   * 一键触发人生K线与日历生成并展示，优先使用用户选择的生成时间。
   */
  const onGenerateAndShow = async () => {
    if (selectedResultId) {
      await loadData(Number(selectedResultId));
      return;
    }
    await loadData();
  };

  /**
   * 按用户输入的八字信息直接生成人生K线与日历并展示。
   */
  const onGenerateByBirthInfo = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const validationError = validateBirthForm(birthForm);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await generateInsightOverviewByBirthInfo(toBirthInfo(birthForm));
      setData(response.data || null);
      setSelectedResultId("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "按八字生成失败，请稍后重试。");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    void loadHistoryOptions();
  }, []);

  /**
   * 提交生成请求：按“生成时间”对应的分析结果生成人生K线与日历。
   */
  const onSubmitByTime = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedResultId) {
      await loadData();
      return;
    }
    const parsed = Number(selectedResultId);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setError("选择的生成时间无效，请重新选择。");
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

  const todayDateKey = useMemo(() => getTodayDateKey(), []);
  const solarTermMap = useMemo(() => {
    if (!calendarDays.length) {
      return {};
    }
    const year = Number((calendarDays[0]?.date || "").slice(0, 4));
    if (!Number.isFinite(year) || year <= 0) {
      return {};
    }
    return buildSolarTermMap(year);
  }, [calendarDays]);

  return (
    <div className="insights-page fade-in">
      <InkCard title="人生线与日历总览" icon="盘">
        <form className="insights-toolbar" onSubmit={onSubmitByTime}>
          <div className="field">
            <label className="field__label" htmlFor="insights-result-time">选择生成时间（可选）</label>
            <select
              id="insights-result-time"
              value={selectedResultId}
              onChange={(event) => setSelectedResultId(event.target.value)}
              disabled={optionsLoading}
            >
              <option value="">使用最新一次分析</option>
              {historyOptions.map((item) => (
                <option key={item.id} value={String(item.id)}>
                  {item.created_at} · {item.date} · {item.gender} · 时辰{item.timezone}
                </option>
              ))}
            </select>
          </div>
          <div className="actions-row">
            <InkButton type="submit" disabled={loading}>{loading ? "加载中..." : "查询"}</InkButton>
            <InkButton type="button" kind="ghost" disabled={loading} onClick={() => void loadData()}>
              刷新最新
            </InkButton>
            <InkButton type="button" disabled={loading || optionsLoading} onClick={() => void onGenerateAndShow()}>
              一键生成并展示
            </InkButton>
          </div>
        </form>

        <form className="stack" onSubmit={onGenerateByBirthInfo}>
          <div className="form-grid">
            <div className="field">
              <label className="field__label" htmlFor="insights-calendar">历法</label>
              <select
                id="insights-calendar"
                value={birthForm.calendar}
                onChange={(event) => setBirthForm((prev) => ({ ...prev, calendar: event.target.value as ZiweiFortuneFormState["calendar"] }))}
              >
                <option value="lunar">阴历（农历）</option>
                <option value="solar">阳历（公历）</option>
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="insights-gender">性别</label>
              <select
                id="insights-gender"
                value={birthForm.gender}
                onChange={(event) => setBirthForm((prev) => ({ ...prev, gender: event.target.value as ZiweiFortuneFormState["gender"] }))}
              >
                <option value="男">男</option>
                <option value="女">女</option>
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="insights-year">出生年</label>
              <input
                id="insights-year"
                type="number"
                value={birthForm.year}
                onChange={(event) => setBirthForm((prev) => ({ ...prev, year: event.target.value }))}
                min={1900}
                max={2100}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="insights-month">出生月</label>
              <input
                id="insights-month"
                type="number"
                value={birthForm.month}
                onChange={(event) => setBirthForm((prev) => ({ ...prev, month: event.target.value }))}
                min={1}
                max={12}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="insights-day">出生日</label>
              <input
                id="insights-day"
                type="number"
                value={birthForm.day}
                onChange={(event) => setBirthForm((prev) => ({ ...prev, day: event.target.value }))}
                min={1}
                max={birthForm.calendar === "lunar" ? 30 : 31}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="insights-hour">出生时（24小时）</label>
              <input
                id="insights-hour"
                type="number"
                value={birthForm.hour}
                onChange={(event) => setBirthForm((prev) => ({ ...prev, hour: event.target.value }))}
                min={0}
                max={23}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="insights-minute">出生分</label>
              <input
                id="insights-minute"
                type="number"
                value={birthForm.minute}
                onChange={(event) => setBirthForm((prev) => ({ ...prev, minute: event.target.value }))}
                min={0}
                max={59}
              />
            </div>
          </div>
          <p className="oracle-chat__tip">当前八字输入：{formatBirthPreview(birthForm)}</p>
          <div className="actions-row">
            <InkButton type="submit" disabled={loading}>{loading ? "生成中..." : "按八字生成人生K线/日历"}</InkButton>
          </div>
        </form>

        {error ? <p className="error-text">{error}</p> : null}
        {!loading && !error && !data ? (
          <div className="stack">
            <p className="loading-state-text">暂无数据，请先完成一次咨询分析。</p>
            <div className="actions-row">
              <InkButton type="button" disabled={loading || optionsLoading} onClick={() => void onGenerateAndShow()}>
                启动生成
              </InkButton>
              <Link to="/oracle">
                <InkButton type="button" kind="ghost">去咨询并生成基础分析</InkButton>
              </Link>
            </div>
          </div>
        ) : null}
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
              {calendarDays.map((day) => {
                const markers = buildCalendarMarkers(day.date, solarTermMap);
                return (
                  <article
                    key={day.date}
                    className={`calendar-day-card ${day.date === todayDateKey ? "calendar-day-card--today" : ""}`}
                  >
                    <p className="calendar-day-card__date">{day.date}</p>
                    {markers.length ? (
                      <div className="calendar-day-card__markers">
                        {markers.map((marker) => (
                          <span
                            key={`${day.date}-${marker}`}
                            className={`calendar-day-card__marker ${SOLAR_TERMS_21ST.some((item) => item.name === marker) ? "calendar-day-card__marker--term" : ""}`}
                          >
                            {marker}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <p className="calendar-day-card__score">{day.level} · {day.score}</p>
                    <p className="calendar-day-card__text">宜：{day.yi.join("、")}</p>
                    <p className="calendar-day-card__text">忌：{day.ji.join("、")}</p>
                    <p className="calendar-day-card__text">{day.note}</p>
                  </article>
                );
              })}
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
          <Link to="/oracle">
            <InkButton type="button" kind="ghost">返回咨询对话</InkButton>
          </Link>
          <Link to="/history">
            <InkButton type="button" kind="ghost">查看历史记录</InkButton>
          </Link>
        </div>
      </InkCard>
    </div>
  );
}
