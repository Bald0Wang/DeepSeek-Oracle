export type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface BirthInfo {
  date: string;
  timezone: number;
  gender: "男" | "女";
  calendar: "solar" | "lunar";
}

export interface AnalyzeAcceptedData {
  task_id: string;
  status: TaskStatus;
  poll_after_ms: number;
  hit_cache: false;
  reused_task?: boolean;
}

export interface AnalyzeCacheHitData {
  result_id: number;
  hit_cache: true;
}

export type SubmitAnalysisData = AnalyzeAcceptedData | AnalyzeCacheHitData;

export interface TaskError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface TaskData {
  task_id: string;
  status: TaskStatus;
  progress: number;
  step: string;
  result_id: number | null;
  retry_count: number;
  error: TaskError | null;
  updated_at?: string;
}

export interface AnalysisItem {
  content: string;
  execution_time: number;
  token_count: number;
  input_tokens: number;
  output_tokens: number;
}

export interface AnalysisResult {
  id: number;
  birth_info: BirthInfo;
  provider: string;
  model: string;
  prompt_version: string;
  text_description: string;
  analysis: {
    marriage_path: AnalysisItem;
    challenges: AnalysisItem;
    partner_character: AnalysisItem;
  };
  total_execution_time: number;
  total_token_count: number;
  created_at: string;
}

export interface AnalysisDetailItem {
  result_id: number;
  analysis_type: "marriage_path" | "challenges" | "partner_character";
  content: string;
  execution_time: number;
  token_count: number;
  input_tokens: number;
  output_tokens: number;
  provider: string;
  model: string;
  prompt_version: string;
  created_at: string;
}

export interface HistoryItem {
  id: number;
  date: string;
  timezone: number;
  gender: string;
  calendar: string;
  provider: string;
  model: string;
  prompt_version: string;
  created_at: string;
}

export interface HistoryResponseData {
  items: HistoryItem[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    has_next: boolean;
  };
}

export interface ApiResponse<T> {
  code: number | string;
  message: string;
  data?: T;
  request_id: string;
}

export type SelectedSchool = "east" | "west" | "mixed";
export type EnabledSchool = "ziwei" | "meihua" | "tarot" | "daily_card" | "actionizer" | "philosophy";
export type DisclaimerLevel = "none" | "light" | "strong";

export interface OracleActionItem {
  task: string;
  when: string;
  reason: string;
}

export interface OracleTraceItem {
  stage: string;
  skill: string;
  reason?: string;
  intent?: string;
  skills?: string[];
  reasons?: string[];
  result?: Record<string, unknown>;
}

export interface OracleToolEvent {
  tool_name: string;
  display_name: string;
  status: "running" | "success" | "error";
  elapsed_ms?: number | null;
  source?: "tool_calling" | "fallback_router";
}

export type OracleStreamEvent =
  | { event: "session_start"; data: { provider: string; model: string } }
  | { event: "tool_start"; data: { tool_name: string; display_name: string } }
  | { event: "tool_end"; data: { tool_name: string; display_name: string; status: "success"; elapsed_ms?: number } }
  | { event: "tool_error"; data: { tool_name: string; display_name: string; elapsed_ms?: number } }
  | {
      event: "final";
      data: {
        answer_text: string;
        follow_up_questions: string[];
        action_items: OracleActionItem[];
        safety_disclaimer_level: DisclaimerLevel;
      };
    }
  | { event: "done"; data: Record<string, never> }
  | { event: "error"; data: { message: string } };

export interface OracleChatRequest {
  user_query: string;
  conversation_history_summary?: string;
  user_profile_summary?: string;
  /** @deprecated 路由策略改为后端控制 */
  selected_school?: SelectedSchool;
  /** @deprecated 路由策略改为后端控制 */
  enabled_schools?: EnabledSchool[];
  birth_info?: BirthInfo;
  provider?: string;
  model?: string;
}

export interface OracleChatResponse {
  answer_text: string;
  follow_up_questions: string[];
  action_items: OracleActionItem[];
  safety_disclaimer_level: DisclaimerLevel;
  trace?: OracleTraceItem[];
  tool_events?: OracleToolEvent[];
}

export type UserRole = "admin" | "user";

export interface UserProfile {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at?: string | null;
  created_at: string;
}

export interface AuthPayload {
  token: string;
  user: UserProfile;
}

export interface AuthRequest {
  email: string;
  password: string;
  email_code?: string;
  invite_code?: string;
}

export interface EmailCodeRequest {
  email: string;
}

export interface AdminCodeLoginRequest {
  email: string;
  login_code: string;
}

export interface ResetPasswordRequest {
  email: string;
  reset_code: string;
  new_password: string;
}

export interface AuthMeData {
  user: UserProfile;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  has_next: boolean;
}

export interface SystemLogItem {
  id: number;
  request_id?: string | null;
  method?: string | null;
  path?: string | null;
  status_code?: number | null;
  duration_ms?: number | null;
  level: string;
  message?: string | null;
  user_id?: number | null;
  user_email?: string | null;
  ip?: string | null;
  user_agent?: string | null;
  created_at: string;
}

export interface SystemLogResponse {
  items: SystemLogItem[];
  pagination: Pagination;
}

export interface AdminUserListResponse {
  items: UserProfile[];
  pagination: Pagination;
}

export interface AdminDashboardData {
  user_metrics: {
    total_users: number;
    admin_users: number;
  };
  analysis_metrics: {
    total_tasks: number;
    queued_tasks: number;
    running_tasks: number;
    succeeded_tasks: number;
    failed_tasks: number;
    total_results: number;
    results_last_24h: number;
  };
  log_metrics: {
    total_logs: number;
    error_logs: number;
    logs_last_24h: number;
    top_paths: Array<{ path: string; total: number }>;
  };
}

export interface LifeKlineYearPoint {
  age: number;
  year: number;
  yearGanZhi: string;
  daYun: string;
  score: number;
  summary: string;
  focus?: string;
}

export interface LifeKlineSummary {
  averageScore: number;
  bestYears: number[];
  worstYears: number[];
  overallTrend: string;
}

export interface MonthlyCalendarDay {
  date: string;
  score: number;
  level: string;
  focus: string;
  yi: string[];
  ji: string[];
  note: string;
}

export interface MonthlyCalendarPayload {
  month_key: string;
  start_date: string;
  end_date: string;
  generated_by: string;
  dominant_focus: string;
  days: MonthlyCalendarDay[];
}

export interface InsightOverviewData {
  life_kline: {
    sparse: {
      years: LifeKlineYearPoint[];
    };
    summary: LifeKlineSummary;
    updated_at?: string;
  };
  calendar: {
    current_month: MonthlyCalendarPayload;
    next_month: MonthlyCalendarPayload;
    near_30_days: MonthlyCalendarDay[];
  };
}

export interface ZiweiDivinationRequest {
  question: string;
  birth_info: BirthInfo;
  provider?: string;
  model?: string;
}

export interface ZiweiDivinationResponse {
  question: string;
  birth_info: BirthInfo;
  chart_summary: string;
  reading: string;
  provider: string;
  model: string;
  generated_at: string;
}

export interface MeihuaDivinationRequest {
  topic: string;
  occurred_at?: string;
  provider?: string;
  model?: string;
}

export interface MeihuaDivinationResponse {
  topic: string;
  occurred_at: string;
  method: string;
  gua: {
    seed: number;
    upper_trigram: string;
    lower_trigram: string;
    base_gua: string;
    mutual_gua?: string;
    changed_gua: string;
    moving_line: number;
    moving_line_name: string;
    base_line_pattern: string;
    changed_line_pattern: string;
    symbol: string;
    element_hint: string;
    ti_gua?: string;
    yong_gua?: string;
    relation?: string;
    formula_inputs?: {
      year: number;
      month: number;
      day: number;
      hour: number;
      topic_length: number;
    };
  };
  reading: string;
  provider: string;
  model: string;
  generated_at: string;
}
