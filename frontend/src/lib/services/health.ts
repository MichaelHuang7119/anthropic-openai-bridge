import { apiClient } from "./api";
import type { RequestOptions } from "./api";
import type { HealthStatus, ProviderHealth } from "$types/health";

export const healthService = {
  async getAll(options?: RequestOptions): Promise<HealthStatus> {
    return apiClient.get<HealthStatus>("/api/health", options);
  },

  async getProvider(name: string): Promise<ProviderHealth> {
    return apiClient.get<ProviderHealth>(
      `/api/health/${encodeURIComponent(name)}`,
    );
  },
};
