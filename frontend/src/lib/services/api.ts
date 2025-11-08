/**
 * 基础API客户端
 * 使用相对路径，通过 nginx 代理访问后端 API
 * 支持请求取消（AbortController）以应对高并发场景
 */
import { authService } from './auth';

export type RequestOptions = RequestInit & {
  signal?: AbortSignal;
};

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    // 使用相对路径，通过 nginx 代理转发到后端
    this.baseUrl = baseUrl || '';
  }

  private getApiKey(): string | null {
    // 优先从环境变量获取（构建时）
    if (typeof window !== 'undefined' && (window as any).__API_KEY__) {
      return (window as any).__API_KEY__;
    }
    
    // 从 localStorage 获取（运行时）
    if (typeof window !== 'undefined') {
      return localStorage.getItem('api_key');
    }
    
    return null;
  }

  private async request<T>(
    url: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const fullUrl = this.baseUrl + url;
    
    // 添加认证头
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {})
    };
    
    // 添加 JWT Token（用于管理面板 API）
    const authHeaders = authService.getAuthHeaders();
    if (authHeaders['Authorization']) {
      Object.assign(headers, authHeaders);
      if (typeof window !== 'undefined') {
        console.debug('[API] Adding Authorization header for:', url);
      }
    } else if (typeof window !== 'undefined' && url.startsWith('/api/')) {
      // 只在浏览器环境和管理 API 请求时警告
      console.warn('[API] No auth token available for request:', url);
      console.warn('[API] localStorage token:', localStorage.getItem('auth_token') ? 'exists' : 'missing');
    }
    
    // 添加 API Key（如果存在，用于服务 API）
    const apiKey = this.getApiKey();
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    try {
      const response = await fetch(fullUrl, {
        headers,
        ...options,
        // 确保 signal 被传递
        signal: options.signal
      });

      // 如果请求被取消，抛出 AbortError
      if (options.signal?.aborted) {
        throw new DOMException('Request aborted', 'AbortError');
      }

      // Handle 401 Unauthorized - redirect to login
      if (response.status === 401 && url.startsWith('/api/auth/') === false) {
        if (typeof window !== 'undefined') {
          console.error('[API] 401 Unauthorized for:', url);
          console.error('[API] Request headers:', JSON.stringify(headers, null, 2));
          console.error('[API] Token in localStorage:', localStorage.getItem('auth_token') ? 'exists' : 'missing');
        }
        authService.logout();
        throw new Error('Unauthorized - Please login again');
      }

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const error = await response.json();
          // 处理 FastAPI 的验证错误格式
          if (error.detail) {
            if (Array.isArray(error.detail)) {
              // FastAPI 验证错误格式: [{loc: [...], msg: "...", type: "..."}]
              const errors = error.detail.map((e: any) => {
                const field = e.loc?.join('.') || 'unknown';
                return `${field}: ${e.msg}`;
              }).join(', ');
              errorMessage = errors || errorMessage;
            } else if (typeof error.detail === 'string') {
              errorMessage = error.detail;
            } else {
              errorMessage = JSON.stringify(error.detail);
            }
          } else if (typeof error === 'string') {
            errorMessage = error;
          } else if (error.message) {
            errorMessage = error.message;
          } else {
            errorMessage = JSON.stringify(error);
          }
        } catch {
          // 如果响应不是 JSON，尝试读取文本
          try {
            const text = await response.text();
            errorMessage = text || errorMessage;
          } catch {
            // 忽略解析错误
          }
        }
        throw new Error(errorMessage);
      }

      return response.json();
    } catch (error) {
      // 处理请求取消错误（不显示错误提示）
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw error;
      }
      // 处理网络错误
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`网络错误: 无法连接到服务器。请检查后端服务是否正常运行。`);
      }
      // 重新抛出其他错误
      throw error;
    }
  }

  async get<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'GET' });
  }

  async post<T>(url: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    });
  }

  async put<T>(url: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
    });
  }

  async delete<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'DELETE' });
  }

  async patch<T>(url: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined
    });
  }
}

export const apiClient = new ApiClient();