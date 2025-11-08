import { apiClient } from './api';
import type { RequestOptions } from './api';
import type { Provider, ProviderFormData, ProviderTestResponse } from '$types/provider';

export const providerService = {
  async getAll(options?: RequestOptions): Promise<Provider[]> {
    return apiClient.get<Provider[]>('/api/providers', options);
  },

  async getAllForEdit(options?: RequestOptions): Promise<Provider[]> {
    return apiClient.get<Provider[]>('/api/providers?include_secrets=true', options);
  },

  async create(data: ProviderFormData): Promise<{ success: boolean; message: string }> {
    return apiClient.post('/api/providers', data);
  },

  async update(name: string, data: ProviderFormData): Promise<{ success: boolean; message: string }> {
    return apiClient.put(`/api/providers/${encodeURIComponent(name)}`, data);
  },

  async delete(name: string): Promise<{ success: boolean; message: string }> {
    return apiClient.delete(`/api/providers/${encodeURIComponent(name)}`);
  },

  async test(name: string): Promise<ProviderTestResponse> {
    return apiClient.post(`/api/providers/${encodeURIComponent(name)}/test`);
  },

  async toggleEnabled(name: string, enabled: boolean): Promise<{ success: boolean; message: string }> {
    return apiClient.patch(`/api/providers/${encodeURIComponent(name)}/enable?enabled=${enabled}`);
  }
};
