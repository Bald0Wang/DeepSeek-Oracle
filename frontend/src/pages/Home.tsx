import { FormEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { useAnalysis } from "../hooks/useAnalysis";
import type { BirthInfo } from "../types";


const TIMEZONE_LABELS: Record<number, string> = {
  0: "早子时 (0:00–1:00)",
  1: "丑时 (1:00–3:00)",
  2: "寅时 (3:00–5:00)",
  3: "卯时 (5:00–7:00)",
  4: "辰时 (7:00–9:00)",
  5: "巳时 (9:00–11:00)",
  6: "午时 (11:00–13:00)",
  7: "未时 (13:00–15:00)",
  8: "申时 (15:00–17:00)",
  9: "酉时 (17:00–19:00)",
  10: "戌时 (19:00–21:00)",
  11: "亥时 (21:00–23:00)",
  12: "晚子时 (23:00–24:00)",
};

const defaultBirthInfo: BirthInfo = {
  date: "",
  timezone: 2,
  gender: "女",
  calendar: "solar",
};


export default function HomePage() {
  const navigate = useNavigate();
  const { submit, isSubmitting, error } = useAnalysis();
  const [birthInfo, setBirthInfo] = useState<BirthInfo>(defaultBirthInfo);
  const [localError, setLocalError] = useState<string | null>(null);

  const timezoneOptions = useMemo(
    () =>
      Array.from({ length: 13 }, (_, idx) => ({
        value: idx,
        label: TIMEZONE_LABELS[idx],
      })),
    []
  );

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    if (!birthInfo.date) {
      setLocalError("请选择出生日期");
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
    <div className="fade-in">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero__badge">紫微斗数 × AI 深度解析</div>
        <h1 className="hero__title">紫微神算</h1>
        <p className="hero__subtitle">
          以千年紫微斗数为基，结合 DeepSeek 大语言模型深度推演，
          为你解读命盘中的婚姻道路、困难挑战与伴侣性格。
        </p>
        <div className="hero__decoration">
          <span className="hero__decoration-line" />
          <span className="hero__decoration-dot" />
          <span className="hero__decoration-line" />
        </div>

        {/* Placeholder Image */}
        <div className="placeholder-image placeholder-image--hero">
          <div className="placeholder-image__icon">☯</div>
          <div className="placeholder-image__text">紫微星盘示意图</div>
        </div>
      </section>

      {/* Form */}
      <div className="form-container fade-in-up">
        <InkCard title="录入生辰" icon="✦">
          <form className="stack" onSubmit={onSubmit}>
            <label className="field">
              <span className="field__label">出生日期</span>
              <input
                type="date"
                value={birthInfo.date}
                onChange={(e) => setBirthInfo((prev) => ({ ...prev, date: e.target.value }))}
              />
            </label>

            <div className="form-grid">
              <label className="field">
                <span className="field__label">时辰</span>
                <select
                  value={birthInfo.timezone}
                  onChange={(e) =>
                    setBirthInfo((prev) => ({ ...prev, timezone: Number(e.target.value) }))
                  }
                >
                  {timezoneOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span className="field__label">性别</span>
                <select
                  value={birthInfo.gender}
                  onChange={(e) =>
                    setBirthInfo((prev) => ({
                      ...prev,
                      gender: e.target.value as BirthInfo["gender"],
                    }))
                  }
                >
                  <option value="女">女</option>
                  <option value="男">男</option>
                </select>
              </label>
            </div>

            <label className="field">
              <span className="field__label">历法</span>
              <select
                value={birthInfo.calendar}
                onChange={(e) =>
                  setBirthInfo((prev) => ({
                    ...prev,
                    calendar: e.target.value as BirthInfo["calendar"],
                  }))
                }
              >
                <option value="solar">阳历（公历）</option>
                <option value="lunar">阴历（农历）</option>
              </select>
            </label>

            {(localError || error) && <p className="error-text">{localError || error}</p>}

            <InkButton type="submit" disabled={isSubmitting} full>
              {isSubmitting ? "天机推算中…" : "开始推演"}
            </InkButton>
          </form>
        </InkCard>
      </div>

      {/* Feature Cards */}
      <div className="features fade-in-up fade-in-delay-2">
        <div className="feature-card">
          <div className="feature-card__icon">💍</div>
          <div className="feature-card__title">婚姻道路</div>
          <div className="feature-card__desc">解读命盘中的夫妻宫与相关星曜，分析你的感情走向与婚姻运势。</div>
        </div>
        <div className="feature-card">
          <div className="feature-card__icon">⚡</div>
          <div className="feature-card__title">困难挑战</div>
          <div className="feature-card__desc">洞察人生中可能遭遇的困难与挑战，提供紫微斗数视角的建议。</div>
        </div>
        <div className="feature-card">
          <div className="feature-card__icon">🤝</div>
          <div className="feature-card__title">伴侣性格</div>
          <div className="feature-card__desc">从命盘推演另一半的性格特质、相处模式与互补之处。</div>
        </div>
      </div>
    </div>
  );
}
