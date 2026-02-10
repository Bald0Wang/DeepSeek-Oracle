import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { InkButton } from "../components/InkButton";
import { useAnalysis } from "../hooks/useAnalysis";
import type { BirthInfo } from "../types";


const INPUT_FORMAT_HINT = "农历(或者阳历)2000年1月1日00:01男";


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

const parseBirthInput = (rawInput: string): BirthInfo => {
  const input = rawInput.replace(/\s+/g, "").replace(/（/g, "(").replace(/）/g, ")").trim();

  if (!input) {
    throw new Error("请输入出生信息");
  }

  let calendar: BirthInfo["calendar"] | null = null;
  if (/农历|阴历|lunar/i.test(input)) {
    calendar = "lunar";
  } else if (/阳历|公历|solar/i.test(input)) {
    calendar = "solar";
  }

  if (!calendar) {
    throw new Error("请标注农历或阳历");
  }

  const genderMatches = input.match(/男|女/g);
  const gender =
    genderMatches && genderMatches.length > 0
      ? (genderMatches[genderMatches.length - 1] as BirthInfo["gender"])
      : undefined;
  if (!gender) {
    throw new Error("请在末尾补充性别（男/女）");
  }

  const dateMatch = input.match(/(\d{4})年(\d{1,2})月(\d{1,2})日?/);
  if (!dateMatch) {
    throw new Error(`格式错误，请使用：${INPUT_FORMAT_HINT}`);
  }

  const year = Number(dateMatch[1]);
  const month = Number(dateMatch[2]);
  const day = Number(dateMatch[3]);

  if (month < 1 || month > 12) {
    throw new Error("月份范围应为 1-12");
  }

  if (calendar === "lunar") {
    if (day < 1 || day > 30) {
      throw new Error("农历日期范围应为 1-30");
    }
  } else {
    const temp = new Date(year, month - 1, day);
    const isValidSolarDate =
      temp.getFullYear() === year && temp.getMonth() === month - 1 && temp.getDate() === day;
    if (!isValidSolarDate) {
      throw new Error("阳历日期无效，请检查年月日");
    }
  }

  const timeMatch = input.match(/(\d{1,2})[:：](\d{1,2})/);
  if (!timeMatch) {
    throw new Error("请补充时间，例如 00:01");
  }

  const hour = Number(timeMatch[1]);
  const minute = Number(timeMatch[2]);
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
    throw new Error("时间无效，请使用 24 小时制，例如 00:01");
  }

  return {
    date: `${year}-${pad2(month)}-${pad2(day)}`,
    timezone: hourToTimezone(hour),
    gender,
    calendar,
  };
};


export default function HomePage() {
  const navigate = useNavigate();
  const { submit, isSubmitting, error } = useAnalysis();

  const [query, setQuery] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    let birthInfo: BirthInfo;
    try {
      birthInfo = parseBirthInput(query);
    } catch (parseError) {
      setLocalError(parseError instanceof Error ? parseError.message : "输入格式错误");
      return;
    }

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
          <p className="home-search__desc">用于生成紫微命盘与三类专项解读；若你想直接提问近期问题，请使用咨询对话。</p>
        </div>

        <div className="home-search__row">
          <input
            className="home-search__input"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={INPUT_FORMAT_HINT}
            aria-label="输入出生信息"
          />
          <InkButton className="home-search__submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "分析中..." : "开始分析"}
          </InkButton>
        </div>

        <div className="home-search__meta">
          <p className="home-search__hint">格式：{INPUT_FORMAT_HINT}</p>
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
