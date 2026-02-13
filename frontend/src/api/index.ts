import axios from "axios";

import type {
  AdminDashboardData,
  AdminCodeLoginRequest,
  AdminUserListResponse,
  AnalysisDetailItem,
  AnalysisResult,
  AuthMeData,
  AuthPayload,
  EmailCodeRequest,
  AuthRequest,
  ApiResponse,
  BirthInfo,
  DivinationHistoryData,
  DivinationHistoryDetail,
  HistoryResponseData,
  InsightOverviewData,
  MeihuaDivinationRequest,
  MeihuaDivinationResponse,
  OracleChatRequest,
  OracleChatResponse,
  OracleConversationSummary,
  OracleConversationTurnRecord,
  OracleStreamEvent,
  ResetPasswordRequest,
  SubmitAnalysisData,
  SystemLogResponse,
  TaskData,
  ZiweiDivinationRequest,
  ZiweiDivinationResponse,
} from "../types";
import { clearAuthData, getAccessToken } from "../utils/auth";

const api = axios.create({
  baseURL: "/api",
  timeout: 30_000
});
// Divination may take longer when charting + LLM reasoning runs in sequence.
// Use no client-side timeout for these two endpoints; rely on backend/proxy limits.
const DIVINATION_TIMEOUT_MS = 0;

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

export const getInsightOverview = async (resultId?: number) => {
  const query = typeof resultId === "number" ? `?result_id=${resultId}` : "";
  return unwrap(await api.get<ApiResponse<InsightOverviewData>>(`/insights/overview${query}`));
};

export const generateInsightOverviewByBirthInfo = async (birthInfo: BirthInfo) =>
  unwrap(await api.post<ApiResponse<InsightOverviewData>>("/insights/overview", { birth_info: birthInfo }));

export const getResultItem = async (
  id: number,
  analysisType: "marriage_path" | "challenges" | "partner_character"
) => unwrap(await api.get<ApiResponse<AnalysisDetailItem>>(`/result/${id}/${analysisType}`));

export const getHistory = async (page = 1, pageSize = 20) =>
  unwrap(await api.get<ApiResponse<HistoryResponseData>>(`/history?page=${page}&page_size=${pageSize}`));

export const getDivinationHistory = async (
  page = 1,
  pageSize = 20,
  type: "all" | "ziwei" | "meihua" = "all"
) =>
  unwrap(
    await api.get<ApiResponse<DivinationHistoryData>>(
      `/history/divinations?page=${page}&page_size=${pageSize}&type=${type}`
    )
  );

export const getDivinationHistoryDetail = async (recordId: number) =>
  unwrap(await api.get<ApiResponse<DivinationHistoryDetail>>(`/history/divinations/${recordId}`));

export const exportReport = async (id: number, scope = "full") =>
  api.get(`/export/${id}?scope=${scope}`, { responseType: "blob" });

export const oracleChat = async (payload: OracleChatRequest) =>
  unwrap(await api.post<ApiResponse<OracleChatResponse>>("/oracle/chat", payload));

export const createOracleConversation = async (title?: string) =>
  unwrap(await api.post<ApiResponse<{ id: number; title?: string; created_at: string; updated_at: string }>>("/oracle/conversations", { title }));

export const getOracleConversations = async (limit = 50) =>
  unwrap(await api.get<ApiResponse<{ items: OracleConversationSummary[] }>>(`/oracle/conversations?limit=${limit}`));

export const getOracleConversationTurns = async (conversationId: number) =>
  unwrap(
    await api.get<ApiResponse<{ conversation: OracleConversationSummary; turns: OracleConversationTurnRecord[] }>>(
      `/oracle/conversations/${conversationId}/turns`
    )
  );

export const divinateZiwei = async (payload: ZiweiDivinationRequest) =>
  unwrap(
    await api.post<ApiResponse<ZiweiDivinationResponse>>("/divination/ziwei", payload, {
      timeout: DIVINATION_TIMEOUT_MS,
    })
  );

export const divinateMeihua = async (payload: MeihuaDivinationRequest) =>
  unwrap(
    await api.post<ApiResponse<MeihuaDivinationResponse>>("/divination/meihua", payload, {
      timeout: DIVINATION_TIMEOUT_MS,
    })
  );

export const oracleChatStream = async (
  payload: OracleChatRequest,
  onEvent: (event: OracleStreamEvent) => void
): Promise<OracleChatResponse> => {
  const token = getAccessToken();
  const response = await fetch("/api/oracle/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`stream request failed (${response.status})`);
  }

  if (!response.body) {
    throw new Error("stream response body is empty");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let finalData: OracleChatResponse | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    while (true) {
      const separatorIndex = buffer.indexOf("\n\n");
      if (separatorIndex === -1) {
        break;
      }
      const chunk = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);

      const lines = chunk.split("\n");
      let eventName = "";
      let dataText = "";
      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataText += line.slice(5).trim();
        }
      }
      if (!eventName) {
        continue;
      }

      let parsedData: Record<string, unknown> = {};
      if (dataText) {
        try {
          parsedData = JSON.parse(dataText) as Record<string, unknown>;
        } catch {
          parsedData = {};
        }
      }

      if (eventName === "session_start") {
        onEvent({
          event: "session_start",
          data: {
            provider: String(parsedData.provider || ""),
            model: String(parsedData.model || ""),
          },
        });
        continue;
      }
      if (eventName === "tool_start") {
        onEvent({
          event: "tool_start",
          data: {
            tool_name: String(parsedData.tool_name || ""),
            display_name: String(parsedData.display_name || ""),
          },
        });
        continue;
      }
      if (eventName === "tool_end") {
        onEvent({
          event: "tool_end",
          data: {
            tool_name: String(parsedData.tool_name || ""),
            display_name: String(parsedData.display_name || ""),
            status: "success",
            elapsed_ms:
              typeof parsedData.elapsed_ms === "number" ? parsedData.elapsed_ms : undefined,
          },
        });
        continue;
      }
      if (eventName === "tool_error") {
        onEvent({
          event: "tool_error",
          data: {
            tool_name: String(parsedData.tool_name || ""),
            display_name: String(parsedData.display_name || ""),
            elapsed_ms:
              typeof parsedData.elapsed_ms === "number" ? parsedData.elapsed_ms : undefined,
          },
        });
        continue;
      }
      if (eventName === "final") {
        const data = parsedData as unknown as OracleChatResponse;
        finalData = data;
        onEvent({
          event: "final",
          data: {
            answer_text: data.answer_text,
            follow_up_questions: data.follow_up_questions,
            action_items: data.action_items,
            safety_disclaimer_level: data.safety_disclaimer_level,
            conversation_id: typeof data.conversation_id === "number" ? data.conversation_id : undefined,
          },
        });
        continue;
      }
      if (eventName === "error") {
        const message = String(parsedData.message || "stream error");
        onEvent({ event: "error", data: { message } });
        throw new Error(message);
      }
      if (eventName === "done") {
        onEvent({ event: "done", data: {} });
        if (finalData) {
          return finalData;
        }
      }
    }
  }

  if (finalData) {
    return finalData;
  }
  throw new Error("stream ended without final result");
};

export const registerByEmail = async (payload: AuthRequest) =>
  unwrap(await api.post<ApiResponse<AuthPayload>>("/auth/register", payload));

export const loginByEmail = async (payload: AuthRequest) =>
  unwrap(await api.post<ApiResponse<AuthPayload>>("/auth/login", payload));

export const sendAdminLoginCode = async (payload: EmailCodeRequest) =>
  unwrap(await api.post<ApiResponse<{ sent: boolean; expire_minutes: number }>>("/auth/admin/send-code", payload));

export const loginAdminByCode = async (payload: AdminCodeLoginRequest) =>
  unwrap(await api.post<ApiResponse<AuthPayload>>("/auth/admin/code-login", payload));

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

export const getAdminDashboard = async (range: "24h" | "7d" | "30d" = "24h") =>
  unwrap(await api.get<ApiResponse<AdminDashboardData>>(`/admin/dashboard?range=${range}`));

export const getAdminLogs = async (page = 1, pageSize = 50) =>
  unwrap(await api.get<ApiResponse<SystemLogResponse>>(`/admin/logs?page=${page}&page_size=${pageSize}`));

export const getAdminUsers = async (page = 1, pageSize = 20) =>
  unwrap(await api.get<ApiResponse<AdminUserListResponse>>(`/admin/users?page=${page}&page_size=${pageSize}`));
