import axios from "axios";

import type {
  AdminDashboardData,
  AdminUserListResponse,
  AnalysisDetailItem,
  AnalysisResult,
  AuthMeData,
  AuthPayload,
  EmailCodeRequest,
  AuthRequest,
  ApiResponse,
  BirthInfo,
  HistoryResponseData,
  OracleChatRequest,
  OracleChatResponse,
  ResetPasswordRequest,
  SubmitAnalysisData,
  SystemLogResponse,
  TaskData
} from "../types";
import { clearAuthData, getAccessToken } from "../utils/auth";

const api = axios.create({
  baseURL: "/api",
  timeout: 30_000
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const code = error?.response?.data?.code;
    if (code === "A4010" || code === "A4011") {
      clearAuthData();
    }
    return Promise.reject(error);
  }
);

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

export const registerByEmail = async (payload: AuthRequest) =>
  unwrap(await api.post<ApiResponse<AuthPayload>>("/auth/register", payload));

export const loginByEmail = async (payload: AuthRequest) =>
  unwrap(await api.post<ApiResponse<AuthPayload>>("/auth/login", payload));

export const sendRegisterCode = async (payload: EmailCodeRequest) =>
  unwrap(await api.post<ApiResponse<{ sent: boolean; expire_minutes: number }>>("/auth/register/send-code", payload));

export const sendForgotPasswordCode = async (payload: EmailCodeRequest) =>
  unwrap(await api.post<ApiResponse<{ sent: boolean; expire_minutes: number }>>("/auth/password/forgot", payload));

export const resetPasswordByEmail = async (payload: ResetPasswordRequest) =>
  unwrap(await api.post<ApiResponse<{ ok: boolean }>>("/auth/password/reset", payload));

export const getMe = async () =>
  unwrap(await api.get<ApiResponse<AuthMeData>>("/auth/me"));

export const logout = async () =>
  unwrap(await api.post<ApiResponse<{ ok: boolean }>>("/auth/logout"));

export const getAdminDashboard = async () =>
  unwrap(await api.get<ApiResponse<AdminDashboardData>>("/admin/dashboard"));

export const getAdminLogs = async (page = 1, pageSize = 50) =>
  unwrap(await api.get<ApiResponse<SystemLogResponse>>(`/admin/logs?page=${page}&page_size=${pageSize}`));

export const getAdminUsers = async (page = 1, pageSize = 20) =>
  unwrap(await api.get<ApiResponse<AdminUserListResponse>>(`/admin/users?page=${page}&page_size=${pageSize}`));
