import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LoadingAnimation } from "../components/LoadingAnimation";
import { useAnalysis } from "../hooks/useAnalysis";
import type { TaskData } from "../types";


const TERMINAL_STATUS = new Set(["succeeded", "failed", "cancelled"]);
const LAST_TASK_KEY = "oracle:last_task_id";

const STEP_LABELS: Record<string, string> = {
  queued: "等待排队",
  generate_chart: "生成命盘",
  llm_marriage_path: "推演婚姻道路",
  llm_challenges: "推演困难挑战",
  llm_partner_character: "推演伴侣性格",
  persist_result: "保存结果",
  done: "推演完成",
};

const FORTUNES = [
  "天机星正在为你排列星辰…",
  "紫微帝座光芒渐显…",
  "命盘十二宫位逐一点亮…",
  "大语言模型正在深度推演…",
  "星曜交会，命运脉络渐清…",
  "天相星化吉，前途渐明…",
];


export default function LoadingPage() {
  const { taskId = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { pollTask, retry, cancel } = useAnalysis();

  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fortuneIdx, setFortuneIdx] = useState(0);

  const canRetry = useMemo(() => taskData?.status === "failed", [taskData?.status]);
  const canCancel = useMemo(
    () => taskData?.status === "queued" || taskData?.status === "running",
    [taskData?.status]
  );

  // Rotate fortune text
  useEffect(() => {
    const timer = setInterval(() => {
      setFortuneIdx((prev) => (prev + 1) % FORTUNES.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!taskId) {
      const lastTaskId = window.localStorage.getItem(LAST_TASK_KEY);
      if (lastTaskId) {
        navigate(`/loading/${lastTaskId}`, { replace: true });
        return;
      }
    }

    if (!taskId) {
      setError("无效的任务 ID");
      return;
    }

    window.localStorage.setItem(LAST_TASK_KEY, taskId);

    let active = true;
    let timer: number | null = null;

    const run = async () => {
      try {
        const data = await pollTask(taskId);
        if (!active) return;

        setTaskData(data);
        setError(null);

        if (data.status === "succeeded" && data.result_id) {
          window.localStorage.removeItem(LAST_TASK_KEY);
          navigate(`/result/${data.result_id}`, { replace: true });
          return;
        }

        if (TERMINAL_STATUS.has(data.status)) return;
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "轮询失败");
      }

      timer = window.setTimeout(run, 2000);
    };

    run();

    return () => {
      active = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [navigate, pollTask, taskId]);

  const onRetry = async () => {
    if (!taskId) return;
    await retry(taskId);
    setTaskData((prev) =>
      prev ? { ...prev, status: "queued", progress: 0, error: null } : prev
    );
  };

  const onCancel = async () => {
    if (!taskId) return;
    await cancel(taskId);
    setTaskData((prev) => (prev ? { ...prev, status: "cancelled" } : prev));
  };

  const progress = taskData?.progress ?? 0;
  const stepLabel = STEP_LABELS[taskData?.step || "queued"] || taskData?.step || "准备中";

  return (
    <div className="fade-in">
      <InkCard title="天机推演中" icon="☯">
        <div className="loading-container">
          <LoadingAnimation size="large" />

          {/* Fortune text */}
          <p style={{ fontSize: 15, color: "var(--text-soft)", marginBottom: 20, minHeight: 24 }}>
            {FORTUNES[fortuneIdx]}
          </p>

          {/* Progress bar */}
          <div className="progress-bar">
            <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
          </div>

          <p style={{ fontSize: 24, fontWeight: 700, marginTop: 12 }}>{progress}%</p>

          <div className="step-info">
            <span className="step-info__label">当前步骤：</span>
            {stepLabel}
          </div>

            <p className="step-info" style={{ marginTop: 4 }}>
              任务 ID：{taskId}
            </p>

            {location.state && (location.state as { reusedTask?: boolean }).reusedTask && (
              <p className="step-info" style={{ marginTop: 4 }}>
                检测到相同命盘任务，已复用正在执行的推演进程。
              </p>
            )}

          {/* Placeholder image */}
          <div
            className="placeholder-image placeholder-image--md"
            style={{ maxWidth: 320, marginTop: 24 }}
          >
            <div className="placeholder-image__icon">🌌</div>
            <div className="placeholder-image__text">星盘推演动画</div>
          </div>

          {taskData?.error && (
            <p className="error-text" style={{ marginTop: 16 }}>
              {taskData.error.message}
            </p>
          )}
          {error && (
            <p className="error-text" style={{ marginTop: 16 }}>
              {error}
            </p>
          )}

          {taskData?.status === "cancelled" && (
            <p style={{ color: "var(--text-muted)", marginTop: 16 }}>任务已取消</p>
          )}

          <div className="actions-row" style={{ justifyContent: "center", marginTop: 20 }}>
            {canRetry && (
              <InkButton type="button" onClick={onRetry}>
                重试推演
              </InkButton>
            )}
            {canCancel && (
              <InkButton type="button" kind="secondary" onClick={onCancel}>
                取消任务
              </InkButton>
            )}
          </div>
        </div>
      </InkCard>
    </div>
  );
}
