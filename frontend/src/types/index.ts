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
