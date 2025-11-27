/**
 * 认证服务
 * 管理用户登录、登出和认证状态
 */
import { goto } from "$app/navigation";
import { browser } from "$app/environment";

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    name?: string;
    is_admin: boolean;
  };
}

export interface User {
  id: number;
  email: string;
  name?: string;
  is_admin: boolean;
}

class AuthService {
  /**
   * 获取存储的 token
   */
  getToken(): string | null {
    if (!browser) return null;
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * 存储 token
   */
  private setToken(token: string): void {
    if (!browser) return;
    localStorage.setItem(TOKEN_KEY, token);
  }

  /**
   * 清除 token
   */
  private clearToken(): void {
    if (!browser) return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  /**
   * 获取存储的用户信息
   */
  getUser(): User | null {
    if (!browser) return null;
    const userStr = localStorage.getItem(USER_KEY);
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  /**
   * 存储用户信息
   */
  private setUser(user: User): void {
    if (!browser) return;
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  /**
   * 检查是否已认证
   */
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * 获取认证头
   */
  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    if (!token) {
      if (browser) {
        console.warn("[Auth] No token found in localStorage");
      }
      return {};
    }
    if (browser) {
      console.debug("[Auth] Token found, creating Authorization header");
    }
    return {
      Authorization: `Bearer ${token}`,
    };
  }

  /**
   * 登录
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "登录失败" }));
      throw new Error(error.detail || error.message || "登录失败");
    }

    const data: LoginResponse = await response.json();

    // 存储 token 和用户信息
    this.setToken(data.access_token);
    this.setUser(data.user);

    // 验证 token 已存储
    if (browser) {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      if (storedToken === data.access_token) {
        console.debug("[Auth] Token stored successfully");
      } else {
        console.error("[Auth] Token storage verification failed", {
          stored: storedToken?.substring(0, 20) + "...",
          expected: data.access_token.substring(0, 20) + "...",
        });
      }
    }

    return data;
  }

  /**
   * 登出
   */
  logout(): void {
    this.clearToken();
    if (browser) {
      goto("/login");
    }
  }

  /**
   * 获取当前用户信息（从 API）
   */
  async getCurrentUser(): Promise<User | null> {
    const token = this.getToken();
    if (!token) {
      return null;
    }

    try {
      const response = await fetch("/api/auth/me", {
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Token 无效，清除认证信息
          this.logout();
        }
        return null;
      }

      const user: User = await response.json();
      this.setUser(user);
      return user;
    } catch (error) {
      console.error("Failed to get current user:", error);
      return null;
    }
  }
}

export const authService = new AuthService();
