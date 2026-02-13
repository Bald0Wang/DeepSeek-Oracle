import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LoadingAnimation } from "../components/LoadingAnimation";
import { useAnalysis } from "../hooks/useAnalysis";
import { clearLastTaskId, getLastTaskId, setLastTaskId } from "../utils/taskResume";
import type { TaskData } from "../types";


const TERMINAL_STATUS = new Set(["succeeded", "failed", "cancelled"]);

const STEP_LABELS: Record<string, string> = {
  queued: "等待排队",
  generate_chart: "生成命盘",
  llm_marriage_path: "推演婚姻道路",
  llm_challenges: "推演困难挑战",
  llm_partner_character: "推演伴侣性格",
  persist_result: "保存结果",
  done: "推演完成",
};


export default function LoadingPage() {
  const { taskId = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { pollTask, retry, cancel } = useAnalysis();

  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canRetry = useMemo(() => taskData?.status === "failed", [taskData?.status]);
  const canCancel = useMemo(
    () => taskData?.status === "queued" || taskData?.status === "running",
    [taskData?.status]
  );

  const reusedTask = Boolean((location.state as { reusedTask?: boolean } | null)?.reusedTask);
  const resumedTask = Boolean((location.state as { resumed?: boolean } | null)?.resumed);

  useEffect(() => {
    if (!taskId) {
      const lastTaskId = getLastTaskId();
      if (lastTaskId) {
        navigate(`/loading/${lastTaskId}`, { replace: true });
        return;
      }
    }

    if (!taskId) {
      setError("无效的任务 ID");
      return;
    }

    setLastTaskId(taskId);

    let active = true;
    let timer: number | null = null;

    const run = async () => {
      try {
        const data = await pollTask(taskId);
        if (!active) {
          return;
        }

        setTaskData(data);
        setError(null);

        if (data.status === "succeeded" && data.result_id) {
          clearLastTaskId();
          navigate(`/result/${data.result_id}`, { replace: true });
          return;
        }

        if (TERMINAL_STATUS.has(data.status)) {
          return;
        }
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "轮询失败");
      }

      timer = window.setTimeout(run, 2000);
    };

    run();

    return () => {
      active = false;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [navigate, pollTask, taskId]);

  const onRetry = async () => {
    if (!taskId) {
      return;
    }
    await retry(taskId);
    setTaskData((prev) =>
      prev ? { ...prev, status: "queued", progress: 0, error: null } : prev
    );
  };

  const onCancel = async () => {
    if (!taskId) {
      return;
    }
    await cancel(taskId);
    setTaskData((prev) => (prev ? { ...prev, status: "cancelled" } : prev));
  };

  const progress = taskData?.progress ?? 0;
  const stepLabel = STEP_LABELS[taskData?.step || "queued"] || taskData?.step || "准备中";

  return (
    <div className="fade-in">
      <InkCard title="天演推演中">
        <div className="loading-container">
          <LoadingAnimation size="large" />
          <p className="loading-title">正在解析星曜轨迹</p>

          <div className="progress-bar" aria-label="分析进度">
            <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
          </div>
          <p className="loading-percent">{progress}%</p>

          <div className="step-info">
            <span className="step-info__label">当前步骤:</span>
            {stepLabel}
          </div>

          <p className="task-chip">任务 ID: {taskId}</p>

          {reusedTask && <p className="step-info">检测到相同命盘输入，已复用进行中的分析任务。</p>}
          {resumedTask && <p className="step-info">已自动恢复上次进行中的分析任务。</p>}

          {taskData?.error && <p className="error-text">{taskData.error.message}</p>}
          {error && <p className="error-text">{error}</p>}

          {taskData?.status === "cancelled" && <p className="loading-state-text">任务已取消</p>}

          <div className="actions-row actions-row--center">
            {canRetry && (
              <InkButton type="button" onClick={onRetry}>
                重试分析
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
