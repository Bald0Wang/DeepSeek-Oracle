import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { InkButton } from "../components/InkButton";
import { useAnalysis } from "../hooks/useAnalysis";
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


export default function HomePage() {
  const navigate = useNavigate();
  const { submit, isSubmitting, error } = useAnalysis();

  const [calendar, setCalendar] = useState<BirthInfo["calendar"]>("lunar");
  const [year, setYear] = useState("2000");
  const [month, setMonth] = useState("1");
  const [day, setDay] = useState("1");
  const [hour, setHour] = useState("0");
  const [minute, setMinute] = useState("1");
  const [gender, setGender] = useState<BirthInfo["gender"]>("男");
  const [localError, setLocalError] = useState<string | null>(null);

  const inputPreview = useMemo(() => {
    const y = Number(year) || 0;
    const m = Number(month) || 0;
    const d = Number(day) || 0;
    const h = Number(hour) || 0;
    const min = Number(minute) || 0;
    return `${calendar === "lunar" ? "阴历" : "阳历"} ${y}年${m}月${d}日 ${pad2(h)}:${pad2(min)} ${gender}`;
  }, [calendar, day, gender, hour, minute, month, year]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    const yearNumber = Number(year);
    const monthNumber = Number(month);
    const dayNumber = Number(day);
    const hourNumber = Number(hour);
    const minuteNumber = Number(minute);

    if ([yearNumber, monthNumber, dayNumber, hourNumber, minuteNumber].some((value) => Number.isNaN(value))) {
      setLocalError("请完整填写出生年月日和时间。");
      return;
    }

    if (yearNumber < 1900 || yearNumber > 2100) {
      setLocalError("年份范围建议在 1900-2100。");
      return;
    }

    if (monthNumber < 1 || monthNumber > 12) {
      setLocalError("月份范围应为 1-12。");
      return;
    }

    if (calendar === "lunar") {
      if (dayNumber < 1 || dayNumber > 30) {
        setLocalError("阴历日期范围应为 1-30。");
        return;
      }
    } else {
      const temp = new Date(yearNumber, monthNumber - 1, dayNumber);
      const isValidSolarDate =
        temp.getFullYear() === yearNumber
        && temp.getMonth() === monthNumber - 1
        && temp.getDate() === dayNumber;
      if (!isValidSolarDate) {
        setLocalError("阳历日期无效，请检查年月日。");
        return;
      }
    }

    if (hourNumber < 0 || hourNumber > 23 || minuteNumber < 0 || minuteNumber > 59) {
      setLocalError("时间无效，请使用 24 小时制。");
      return;
    }

    const birthInfo: BirthInfo = {
      date: `${yearNumber}-${pad2(monthNumber)}-${pad2(dayNumber)}`,
      timezone: hourToTimezone(hourNumber),
      gender,
      calendar,
    };

    try {
      const data = await submit(birthInfo);
      if ("result_id" in data) {
        window.localStorage.removeItem("oracle:last_task_id");
        navigate(`/result/${data.result_id}`);
        return;
      }
      window.localStorage.setItem("oracle:last_task_id", data.task_id);
      navigate(`/loading/${data.task_id}`, {
        state: { reusedTask: Boolean(data.reused_task) },
      });
    } catch {
      setLocalError("提交失败，请稍后重试");
    }
  };

  return (
    <div className="home-search fade-in">
      <form className="home-search__form fade-in-up" onSubmit={onSubmit}>
        <div className="home-search__intro">
          <p className="home-search__title">东方命盘分析入口</p>
          <p className="home-search__desc">按表单选择出生信息，必须先选择阴历/阳历，再开始分析。</p>
        </div>

        <div className="form-grid">
          <div className="field">
            <label className="field__label" htmlFor="calendar">历法</label>
            <select id="calendar" value={calendar} onChange={(event) => setCalendar(event.target.value as BirthInfo["calendar"])}>
              <option value="lunar">阴历（农历）</option>
              <option value="solar">阳历（公历）</option>
            </select>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="gender">性别</label>
            <select id="gender" value={gender} onChange={(event) => setGender(event.target.value as BirthInfo["gender"])}>
              <option value="男">男</option>
              <option value="女">女</option>
            </select>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="birth-year">出生年</label>
            <input
              id="birth-year"
              type="number"
              inputMode="numeric"
              min={1900}
              max={2100}
              value={year}
              onChange={(event) => setYear(event.target.value)}
              placeholder="2000"
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="birth-month">出生月</label>
            <input
              id="birth-month"
              type="number"
              inputMode="numeric"
              min={1}
              max={12}
              value={month}
              onChange={(event) => setMonth(event.target.value)}
              placeholder="1-12"
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="birth-day">出生日</label>
            <input
              id="birth-day"
              type="number"
              inputMode="numeric"
              min={1}
              max={calendar === "lunar" ? 30 : 31}
              value={day}
              onChange={(event) => setDay(event.target.value)}
              placeholder={calendar === "lunar" ? "1-30" : "1-31"}
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="birth-hour">出生时（24小时）</label>
            <input
              id="birth-hour"
              type="number"
              inputMode="numeric"
              min={0}
              max={23}
              value={hour}
              onChange={(event) => setHour(event.target.value)}
              placeholder="0-23"
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="birth-minute">出生分</label>
            <input
              id="birth-minute"
              type="number"
              inputMode="numeric"
              min={0}
              max={59}
              value={minute}
              onChange={(event) => setMinute(event.target.value)}
              placeholder="0-59"
            />
          </div>
        </div>

        <div className="actions-row actions-row--center">
          <InkButton className="home-search__submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "分析中..." : "开始分析"}
          </InkButton>
        </div>

        <div className="home-search__meta">
          <p className="home-search__hint">当前输入：{inputPreview}</p>
          <Link to="/oracle" className="home-search__quick-link">转到咨询对话</Link>
        </div>

        <div className="home-search__tips" aria-label="输入建议">
          <span className="home-search__tip-chip">先做长期命盘，再做短期追问</span>
          <span className="home-search__tip-chip">不确定时辰可先去咨询对话模块</span>
        </div>

        {(localError || error) && <p className="error-text home-search__error">{localError || error}</p>}
      </form>
    </div>
  );
}
