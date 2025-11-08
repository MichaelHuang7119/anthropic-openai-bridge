import { apiClient } from './api';
import type { Provider, ProviderFormData } from '$types/provider';

export const providerService = {
  async getAll(): Promise<Provider[]> {
    return apiClient.get<Provider[]>('/api/providers');
  },

  async getAllForEdit(): Promise<Provider[]> {
    return apiClient.get<Provider[]>('/api/providers?include_secrets=true');
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

  async test(name: string): Promise<{
    success: boolean;
    healthy: boolean;
    responseTime: number | null;
    message: string;
    error?: string;
  }> {
    return apiClient.post(`/api/providers/${encodeURIComponent(name)}/test`);
  }
};
