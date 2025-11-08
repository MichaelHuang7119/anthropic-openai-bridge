import { apiClient } from './api';
import type { GlobalConfig } from '$types/config';

export const configService = {
  async get(): Promise<GlobalConfig> {
    return apiClient.get<GlobalConfig>('/api/config');
  },

  async update(config: GlobalConfig): Promise<{ success: boolean; message: string }> {
    return apiClient.put('/api/config', config);
  }
};
