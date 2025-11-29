import { apiClient } from "./api";
import type { RequestOptions } from "./api";

export interface LanguagePreference {
  language: string;
}

export const preferencesService = {
  async getLanguage(options?: RequestOptions): Promise<LanguagePreference> {
    return apiClient.get<LanguagePreference>(
      "/api/preferences/language",
      options,
    );
  },

  async updateLanguage(
    language: string,
    options?: RequestOptions,
  ): Promise<{ success: boolean; message: string; language: string }> {
    return apiClient.put<{
      success: boolean;
      message: string;
      language: string;
    }>("/api/preferences/language", { language }, options);
  },
};
