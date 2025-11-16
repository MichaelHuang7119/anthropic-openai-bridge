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

  async update(name: string, data: ProviderFormData, api_format?: string): Promise<{ success: boolean; message: string }> {
    // Use query parameter for precise provider identification when api_format is specified
    const url = api_format
      ? `/api/providers/${encodeURIComponent(name)}?api_format=${encodeURIComponent(api_format)}`
      : `/api/providers/${encodeURIComponent(name)}`;
    return apiClient.put(url, data);
  },

  async delete(name: string, api_format?: string): Promise<{ success: boolean; message: string }> {
    // Use query parameter for precise provider identification when api_format is specified
    const url = api_format
      ? `/api/providers/${encodeURIComponent(name)}?api_format=${encodeURIComponent(api_format)}`
      : `/api/providers/${encodeURIComponent(name)}`;
    return apiClient.delete(url);
  },

  async test(name: string): Promise<ProviderTestResponse> {
    return apiClient.post(`/api/providers/${encodeURIComponent(name)}/test`);
  },

  async toggleEnabled(name: string, enabled: boolean, api_format?: string): Promise<{ success: boolean; message: string }> {
    // Use query parameter for precise provider identification when api_format is specified
    const url = api_format
      ? `/api/providers/${encodeURIComponent(name)}/enable?enabled=${enabled}&api_format=${encodeURIComponent(api_format)}`
      : `/api/providers/${encodeURIComponent(name)}/enable?enabled=${enabled}`;
    return apiClient.patch(url);
  }
};
