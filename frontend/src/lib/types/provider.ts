export interface Provider {
  name: string;
  enabled: boolean;
  priority: number;
  api_key: string;
  base_url: string;
  api_version?: string | null;
  timeout: number;
  max_retries: number;
  custom_headers: Record<string, string>;
  models: {
    big: string[];
    middle: string[];
    small: string[];
  };
  api_format?: "openai" | "anthropic"; // API format: 'openai' (default) or 'anthropic'
}

export interface ProviderFormData {
  name: string;
  enabled: boolean;
  priority: number;
  api_key: string;
  base_url: string;
  api_version?: string | null;
  timeout: number;
  max_retries: number;
  custom_headers: Record<string, string>;
  models: {
    big: string[];
    middle: string[];
    small: string[];
  };
  api_format?: "openai" | "anthropic"; // API format: 'openai' (default) or 'anthropic'
}

export interface CategoryHealthStatus {
  healthy: boolean;
  responseTime: number | null;
  testedModels: string[];
  workingModel: string | null;
  error: string | null;
}

export interface ProviderTestResponse {
  success: boolean;
  healthy: boolean;
  categories: {
    big?: CategoryHealthStatus;
    middle?: CategoryHealthStatus;
    small?: CategoryHealthStatus;
  };
  responseTime: number | null;
  message: string;
  error?: string;
}
