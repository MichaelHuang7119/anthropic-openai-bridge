import { apiClient as api } from "./api";
import type { RequestOptions } from "./api";

export interface RequestLog {
  id: number;
  request_id: string;
  provider_name: string;
  model: string;
  request_params: any;
  response_data?: any;
  status_code: number;
  error_message?: string;
  input_tokens?: number;
  output_tokens?: number;
  response_time_ms?: number;
  created_at: string;
}

export interface TokenUsage {
  date: string;
  provider_name: string;
  model: string;
  request_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_estimate: number;
}

export interface PerformanceSummary {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  avg_response_time_ms: number;
  provider_stats: Record<
    string,
    {
      total: number;
      success: number;
      failed: number;
      total_tokens: number;
      total_cost: number;
    }
  >;
  token_usage: {
    summary: TokenUsage[];
    total_requests: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_cost_estimate: number;
  };
}

class StatsService {
  async getRequests(
    params?: {
      limit?: number;
      offset?: number;
      provider_name?: string;
      model?: string;
      status_code?: number;
      status_min?: number;
      date_from?: string;
      date_to?: string;
    },
    options?: RequestOptions,
  ): Promise<{
    data: RequestLog[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    if (params?.offset) queryParams.append("offset", params.offset.toString());
    if (params?.provider_name)
      queryParams.append("provider_name", params.provider_name);
    if (params?.model) queryParams.append("model", params.model);
    if (params?.status_code !== undefined)
      queryParams.append("status_code", params.status_code.toString());
    if (params?.status_min !== undefined)
      queryParams.append("status_min", params.status_min.toString());
    if (params?.date_from) queryParams.append("date_from", params.date_from);
    if (params?.date_to) queryParams.append("date_to", params.date_to);

    const response = await api.get(
      `/api/stats/requests?${queryParams.toString()}`,
      options,
    );
    const data = response.data?.data || response.data || [];
    return {
      data: Array.isArray(data) ? data : [],
      total: response.data?.total || data.length || 0,
      page: response.data?.page || 1,
      page_size: response.data?.page_size || params?.limit || 10,
      total_pages: response.data?.total_pages || 1,
    };
  }

  async getTokenUsage(
    params?: {
      date_from?: string;
      date_to?: string;
    },
    options?: RequestOptions,
  ): Promise<{
    summary: TokenUsage[];
    total_requests: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_cost_estimate: number;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.date_from) queryParams.append("date_from", params.date_from);
    if (params?.date_to) queryParams.append("date_to", params.date_to);

    const response = await api.get(
      `/api/stats/token-usage?${queryParams.toString()}`,
      options,
    );
    const data = response.data?.data || response.data;
    return (
      data || {
        summary: [],
        total_requests: 0,
        total_input_tokens: 0,
        total_output_tokens: 0,
        total_cost_estimate: 0,
      }
    );
  }

  async getSummary(options?: RequestOptions): Promise<PerformanceSummary> {
    const response = await api.get("/api/stats/summary", options);
    const data = response.data?.data || response.data;
    return (
      data || {
        total_requests: 0,
        successful_requests: 0,
        failed_requests: 0,
        success_rate: 0,
        avg_response_time_ms: 0,
        provider_stats: {},
        token_usage: {
          summary: [],
          total_requests: 0,
          total_input_tokens: 0,
          total_output_tokens: 0,
          total_cost_estimate: 0,
        },
      }
    );
  }
}

export const statsService = new StatsService();
