import apiClient from "./client";
import { endpoints } from "./endpoints";

export interface ApiUsageTotals {
  usage_records: number;
  sessions: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_input: number;
  cost_output: number;
  cost_total: number;
  currency: string;
}

export interface ApiSessionUsageMetrics {
  session_id: string;
  status: string;
  updated_at: string;
  messages: number;
  usage_records: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_input: number;
  cost_output: number;
  cost_total: number;
  feedback_rating?: number | null;
}

export interface ApiFeedbackMetrics {
  average_rating?: number | null;
  rated_sessions: number;
}

export interface ApiUsageMetricsResponse {
  totals: ApiUsageTotals;
  sessions: ApiSessionUsageMetrics[];
  feedback: ApiFeedbackMetrics;
  pricing_configured: boolean;
}

export const fetchUsageMetrics = async (
  signal?: AbortSignal
): Promise<ApiUsageMetricsResponse> => {
  const { data } = await apiClient.get<ApiUsageMetricsResponse>(endpoints.metrics.usage(), {
    signal
  });
  return data;
};
