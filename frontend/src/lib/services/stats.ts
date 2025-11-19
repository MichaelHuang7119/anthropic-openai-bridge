import { apiClient as api } from './api';
import type { RequestOptions } from './api';

interface ApiResponse<T = any> {
  data?: T;
  [key: string]: any;
}

interface PaginatedApiResponse<T = any> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

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
    options?: RequestOptions
  ): Promise<{
    data: RequestLog[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.provider_name) queryParams.append('provider_name', params.provider_name);
    if (params?.model) queryParams.append('model', params.model);
    if (params?.status_code !== undefined)
      queryParams.append('status_code', params.status_code.toString());
    if (params?.status_min !== undefined)
      queryParams.append('status_min', params.status_min.toString());
    if (params?.date_from) queryParams.append('date_from', params.date_from);
    if (params?.date_to) queryParams.append('date_to', params.date_to);

    const response = await api.get(`/api/stats/requests?${queryParams.toString()}`, options);
    const responseData = response as ApiResponse<PaginatedApiResponse<RequestLog>>;
    
    // Handle different response shapes
    let dataArray: RequestLog[] = [];
    let total = 0;
    let page = 1;
    let page_size = params?.limit || 10;
    let total_pages = 1;
    
    if (responseData?.data) {
      // Check if data is already the paginated response with nested data array
      if (Array.isArray(responseData.data.data)) {
        dataArray = responseData.data.data;
        total = responseData.data.total || dataArray.length;
        page = responseData.data.page || 1;
        page_size = responseData.data.page_size || page_size;
        total_pages = responseData.data.total_pages || 1;
      }
      // Check if data is directly the array
      else if (Array.isArray(responseData.data)) {
        dataArray = responseData.data;
        total = dataArray.length;
      }
      // Fallback for other shapes
      else {
        dataArray = [];
        total = 0;
      }
    }
    
    return {
      data: dataArray,
      total,
      page,
      page_size,
      total_pages,
    };
  }

  async getTokenUsage(
    params?: {
      date_from?: string;
      date_to?: string;
    },
    options?: RequestOptions
  ): Promise<{
    summary: TokenUsage[];
    total_requests: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_cost_estimate: number;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.date_from) queryParams.append('date_from', params.date_from);
    if (params?.date_to) queryParams.append('date_to', params.date_to);

    const response = await api.get(`/api/stats/token-usage?${queryParams.toString()}`, options);
    const responseData = response as ApiResponse<any>;
    const data = responseData?.data?.data || responseData?.data;
    
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
    const response = await api.get('/api/stats/summary', options);
    const responseData = response as ApiResponse<any>;
    const data = responseData?.data?.data || responseData?.data;
    
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
