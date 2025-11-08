import { apiClient } from './api';
import type { HealthStatus, ProviderHealth } from '$types/health';

export const healthService = {
  async getAll(): Promise<HealthStatus> {
    return apiClient.get<HealthStatus>('/api/health');
  },

  async getProvider(name: string): Promise<ProviderHealth> {
    return apiClient.get<ProviderHealth>(`/api/health/${encodeURIComponent(name)}`);
  }
};
