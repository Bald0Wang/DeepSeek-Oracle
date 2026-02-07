import { useCallback, useState } from "react";

import { cancelTask, getTask, retryTask, submitAnalysis } from "../api";
import type { BirthInfo, SubmitAnalysisData, TaskData } from "../types";


interface UseAnalysisResult {
  isSubmitting: boolean;
  error: string | null;
  submit: (birthInfo: BirthInfo) => Promise<SubmitAnalysisData>;
  pollTask: (taskId: string) => Promise<TaskData>;
  retry: (taskId: string) => Promise<void>;
  cancel: (taskId: string) => Promise<void>;
}


export function useAnalysis(): UseAnalysisResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async (birthInfo: BirthInfo) => {
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await submitAnalysis(birthInfo);
      if (!response.data) {
        throw new Error("empty response");
      }
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "submit failed";
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const pollTask = useCallback(async (taskId: string) => {
    const response = await getTask(taskId);
    if (!response.data) {
      throw new Error("task not found");
    }
    return response.data;
  }, []);

  const retry = useCallback(async (taskId: string) => {
    await retryTask(taskId);
  }, []);

  const cancel = useCallback(async (taskId: string) => {
    await cancelTask(taskId);
  }, []);

  return {
    isSubmitting,
    error,
    submit,
    pollTask,
    retry,
    cancel
  };
}
