/**
 * 基础API客户端
 * 使用相对路径，通过 nginx 代理访问后端 API
 */
export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    // 使用相对路径，通过 nginx 代理转发到后端
    this.baseUrl = baseUrl || '';
  }

  private async request<T>(
    url: string,
    options: RequestInit = {}
  ): Promise<T> {
    const fullUrl = this.baseUrl + url;
    
    try {
      const response = await fetch(fullUrl, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const error = await response.json();
          errorMessage = error.detail || error.message || errorMessage;
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
      // 处理网络错误
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`网络错误: 无法连接到服务器。请检查后端服务是否正常运行。`);
      }
      // 重新抛出其他错误
      throw error;
    }
  }

  async get<T>(url: string): Promise<T> {
    return this.request<T>(url, { method: 'GET' });
  }

  async post<T>(url: string, data?: unknown): Promise<T> {
    return this.request<T>(url, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    });
  }

  async put<T>(url: string, data?: unknown): Promise<T> {
    return this.request<T>(url, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
    });
  }

  async delete<T>(url: string): Promise<T> {
    return this.request<T>(url, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
