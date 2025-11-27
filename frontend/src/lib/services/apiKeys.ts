import { apiClient } from "./api";
import type { RequestOptions } from "./api";
import type {
  APIKey,
  CreateAPIKeyRequest,
  CreateAPIKeyResponse,
  UpdateAPIKeyRequest,
} from "$types/apiKey";

export interface APIKeyListResponse {
  data: APIKey[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const apiKeysService = {
  async getAll(
    params?: {
      limit?: number;
      offset?: number;
      name_filter?: string;
      is_active?: boolean;
    },
    options?: RequestOptions,
  ): Promise<APIKeyListResponse> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    if (params?.offset) queryParams.append("offset", params.offset.toString());
    if (params?.name_filter)
      queryParams.append("name_filter", params.name_filter);
    if (params?.is_active !== undefined)
      queryParams.append("is_active", params.is_active.toString());

    const response = await apiClient.get<APIKeyListResponse>(
      `/api/api-keys?${queryParams.toString()}`,
      options,
    );
    // response 本身就是 APIKeyListResponse，直接返回
    return response;
  },

  async getById(id: number): Promise<APIKey> {
    return apiClient.get<APIKey>(`/api/api-keys/${id}`);
  },

  async create(data: CreateAPIKeyRequest): Promise<CreateAPIKeyResponse> {
    return apiClient.post<CreateAPIKeyResponse>("/api/api-keys", data);
  },

  async update(id: number, data: UpdateAPIKeyRequest): Promise<APIKey> {
    return apiClient.put<APIKey>(`/api/api-keys/${id}`, data);
  },

  async delete(id: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/api-keys/${id}`);
  },
};
