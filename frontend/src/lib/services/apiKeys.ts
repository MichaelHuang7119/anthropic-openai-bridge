import { apiClient } from './api';
import type { APIKey, CreateAPIKeyRequest, CreateAPIKeyResponse, UpdateAPIKeyRequest } from '$types/apiKey';

export const apiKeysService = {
  async getAll(): Promise<APIKey[]> {
    return apiClient.get<APIKey[]>('/api/api-keys');
  },

  async getById(id: number): Promise<APIKey> {
    return apiClient.get<APIKey>(`/api/api-keys/${id}`);
  },

  async create(data: CreateAPIKeyRequest): Promise<CreateAPIKeyResponse> {
    return apiClient.post<CreateAPIKeyResponse>('/api/api-keys', data);
  },

  async update(id: number, data: UpdateAPIKeyRequest): Promise<APIKey> {
    return apiClient.put<APIKey>(`/api/api-keys/${id}`, data);
  },

  async delete(id: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/api-keys/${id}`);
  }
};
