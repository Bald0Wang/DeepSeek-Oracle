import axios from "axios";

import type {
  AnalysisDetailItem,
  AnalysisResult,
  ApiResponse,
  BirthInfo,
  HistoryResponseData,
  OracleChatRequest,
  OracleChatResponse,
  SubmitAnalysisData,
  TaskData
} from "../types";

const api = axios.create({
  baseURL: "/api",
  timeout: 30_000
});

const isSuccessCode = (code: number | string) => code === 0;

const unwrap = <T>(response: { data: ApiResponse<T> }) => {
  const payload = response.data;
  if (!isSuccessCode(payload.code)) {
    throw new Error(payload.message || "request failed");
  }
  return payload;
};

export const submitAnalysis = async (birthInfo: BirthInfo) =>
  unwrap(await api.post<ApiResponse<SubmitAnalysisData>>("/analyze", birthInfo));

export const getTask = async (taskId: string) =>
  unwrap(await api.get<ApiResponse<TaskData>>(`/task/${taskId}`));

export const retryTask = async (taskId: string) =>
  unwrap(await api.post<ApiResponse<{ task_id: string }>>(`/task/${taskId}/retry`));

export const cancelTask = async (taskId: string) =>
  unwrap(await api.post<ApiResponse<{ task_id: string }>>(`/task/${taskId}/cancel`));

export const getResult = async (id: number) =>
  unwrap(await api.get<ApiResponse<AnalysisResult>>(`/result/${id}`));

export const getResultItem = async (
  id: number,
  analysisType: "marriage_path" | "challenges" | "partner_character"
) => unwrap(await api.get<ApiResponse<AnalysisDetailItem>>(`/result/${id}/${analysisType}`));

export const getHistory = async (page = 1, pageSize = 20) =>
  unwrap(await api.get<ApiResponse<HistoryResponseData>>(`/history?page=${page}&page_size=${pageSize}`));

export const exportReport = async (id: number, scope = "full") =>
  api.get(`/export/${id}?scope=${scope}`, { responseType: "blob" });

export const oracleChat = async (payload: OracleChatRequest) =>
  unwrap(await api.post<ApiResponse<OracleChatResponse>>("/oracle/chat", payload));
