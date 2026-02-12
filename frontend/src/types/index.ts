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

export interface OracleChatRequest {
  user_query: string;
  conversation_history_summary?: string;
  user_profile_summary?: string;
  selected_school?: SelectedSchool;
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
  trace: OracleTraceItem[];
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
