import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { InkButton } from "../components/InkButton";
import { useAnalysis } from "../hooks/useAnalysis";
import {
  getZiweiFortuneSessionState,
  subscribeZiweiFortuneSession,
  updateZiweiFortuneForm,
} from "../stores/ziweiFortuneSession";
import { formatBirthPreview, toBirthInfo, validateBirthForm } from "../utils/birthForm";
import { clearLastTaskId, getLastTaskId, setLastTaskId } from "../utils/taskResume";
import type { BirthInfo } from "../types";

export default function StartAnalysisPage() {
  const navigate = useNavigate();
  const { submit, pollTask, isSubmitting, error } = useAnalysis();

  const [session, setSession] = useState(getZiweiFortuneSessionState());
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = subscribeZiweiFortuneSession((state) => {
      setSession(state);
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    let cancelled = false;

    const resumeTaskIfNeeded = async () => {
      const lastTaskId = getLastTaskId();
      if (!lastTaskId) {
        return;
      }

      try {
        const task = await pollTask(lastTaskId);
        if (cancelled) {
          return;
        }
        if (task.status === "queued" || task.status === "running") {
          navigate(`/loading/${lastTaskId}`, {
            replace: true,
            state: { reusedTask: true, resumed: true },
          });
          return;
        }
        if (task.status === "succeeded" && task.result_id) {
          clearLastTaskId();
          navigate(`/result/${task.result_id}`, { replace: true });
          return;
        }
        clearLastTaskId();
      } catch {
        clearLastTaskId();
      }
    };

    void resumeTaskIfNeeded();
    return () => {
      cancelled = true;
    };
  }, [navigate, pollTask]);

  const inputPreview = useMemo(() => formatBirthPreview(session.form), [session.form]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    const validationError = validateBirthForm(session.form);
    if (validationError) {
      setLocalError(validationError);
      return;
    }

    const birthInfo: BirthInfo = toBirthInfo(session.form);

    try {
      const data = await submit(birthInfo);
      if ("result_id" in data) {
        clearLastTaskId();
        navigate(`/result/${data.result_id}`);
        return;
      }
      setLastTaskId(data.task_id);
      navigate(`/loading/${data.task_id}`, {
        state: { reusedTask: Boolean(data.reused_task) },
      });
    } catch {
      setLocalError("提交失败，请稍后重试");
    }
  };

  return (
    <div className="home-search fade-in">
      <form className="home-search__form home-search__form--ornate fade-in-up" onSubmit={onSubmit}>
        <div className="home-search__intro">
          <p className="home-search__title">东方命盘分析入口</p>
          <p className="home-search__desc">出生信息与紫微求签页实时同步，切换页面不会丢失输入。</p>
        </div>

        <div className="form-grid">
          <div className="field">
            <label className="field__label" htmlFor="calendar">历法</label>
            <select
              id="calendar"
              value={session.form.calendar}
              onChange={(event) => updateZiweiFortuneForm({ calendar: event.target.value as BirthInfo["calendar"] })}
            >
              <option value="lunar">阴历（农历）</option>
              <option value="solar">阳历（公历）</option>
            </select>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="gender">性别</label>
            <select
              id="gender"
              value={session.form.gender}
              onChange={(event) => updateZiweiFortuneForm({ gender: event.target.value as BirthInfo["gender"] })}
            >
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
              value={session.form.year}
              onChange={(event) => updateZiweiFortuneForm({ year: event.target.value })}
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
              value={session.form.month}
              onChange={(event) => updateZiweiFortuneForm({ month: event.target.value })}
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
              max={session.form.calendar === "lunar" ? 30 : 31}
              value={session.form.day}
              onChange={(event) => updateZiweiFortuneForm({ day: event.target.value })}
              placeholder={session.form.calendar === "lunar" ? "1-30" : "1-31"}
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
              value={session.form.hour}
              onChange={(event) => updateZiweiFortuneForm({ hour: event.target.value })}
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
              value={session.form.minute}
              onChange={(event) => updateZiweiFortuneForm({ minute: event.target.value })}
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
          <div className="home-search__meta-links">
            <Link to="/home-variants" className="home-search__quick-link">筛选首页风格</Link>
            <Link to="/ziwei" className="home-search__quick-link">转到紫微求签</Link>
            <Link to="/oracle" className="home-search__quick-link">转到咨询对话</Link>
          </div>
        </div>

        <div className="home-search__tips" aria-label="输入建议">
          <span className="home-search__tip-chip">若存在进行中任务，会自动恢复到分析进度页</span>
          <span className="home-search__tip-chip">与紫微求签页共享同一份出生信息</span>
        </div>

        {(localError || error) && <p className="error-text home-search__error">{localError || error}</p>}
      </form>
    </div>
  );
}

