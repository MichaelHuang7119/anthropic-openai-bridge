export interface APIKey {
  id: number;
  key_prefix: string;
  name: string;
  email?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  last_used_at?: string;
  user_id?: number;
}

export interface CreateAPIKeyRequest {
  name: string;
  email?: string;
}

export interface CreateAPIKeyResponse {
  id: number;
  api_key: string; // 只在创建时返回完整Key
  key_prefix: string;
  name: string;
  email?: string;
  is_active: boolean;
}

export interface UpdateAPIKeyRequest {
  name?: string;
  email?: string;
  is_active?: boolean;
}
