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
}
