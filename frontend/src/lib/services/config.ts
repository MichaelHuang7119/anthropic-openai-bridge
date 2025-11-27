import { apiClient } from "./api";
import type { RequestOptions } from "./api";
import type { GlobalConfig } from "$types/config";

export const configService = {
  async get(options?: RequestOptions): Promise<GlobalConfig> {
    return apiClient.get<GlobalConfig>("/api/config", options);
  },

  async update(
    config: GlobalConfig,
  ): Promise<{ success: boolean; message: string }> {
    return apiClient.put("/api/config", config);
  },
};
