/**
 * 认证状态存储
 * 提供响应式的认证状态管理，支持状态监听和订阅
 */
import { browser } from '$app/environment';

export interface User {
  id: number;
  email: string;
  name?: string;
  is_admin: boolean;
  avatar_url?: string;
  permissions?: Record<string, boolean>;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
}

// 创建响应式状态
let isAuthenticated = $state(false);
let user = $state<User | null>(null);
let initialized = $state(false);

// 订阅者列表
const subscribers: Set<(state: AuthState) => void> = new Set();

// 存储验证轮询定时器
let storagePollInterval: ReturnType<typeof setInterval> | null = null;

/**
 * 通知所有订阅者状态变化
 */
function notifySubscribers() {
  const state: AuthState = {
    isAuthenticated,
    user
  };
  subscribers.forEach(callback => callback(state));
}

/**
 * 轮询检测存储变化（用于检测当前页面的缓存清除）
 * 当 storage 事件不触发时（如手动清除缓存），通过轮询来检测
 */
function startStoragePoll() {
  if (!browser || storagePollInterval) return;

  // 初始验证
  validateToken();

  // 每秒检查一次存储状态
  storagePollInterval = setInterval(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');

    // 如果有 token 但状态是未认证，验证 token
    if (storedToken && !isAuthenticated) {
      console.log('[Auth] Poll: token exists but not authenticated, validating...');
      validateToken();
      return;
    }

    // 如果没有 token 但状态是已认证，清除状态
    if (!storedToken && isAuthenticated) {
      console.log('[Auth] Poll: token missing but authenticated, clearing state');
      clearAuthState();
      return;
    }

    // 如果有 token 验证失败（token 为空说明已清除）
    if (!storedToken) {
      // 状态已同步，无需额外操作
      return;
    }

    // 如果 user 数据缺失，验证并恢复
    if (storedToken && !storedUser && isAuthenticated) {
      console.log('[Auth] Poll: user data missing, validating...');
      validateToken();
    }
  }, 1000);
}

/**
 * 停止存储轮询
 */
function stopStoragePoll() {
  if (storagePollInterval) {
    clearInterval(storagePollInterval);
    storagePollInterval = null;
  }
}

/**
 * 验证 token 是否有效（通过 API）
 * 如果 token 无效，会清除状态并重定向到登录页
 */
export async function validateToken(): Promise<boolean> {
  if (!browser) return false;

  const token = localStorage.getItem('auth_token');
  if (!token) return false;

  try {
    const response = await fetch('/api/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.ok) {
      const userData = await response.json();
      // 更新用户信息
      user = userData;
      localStorage.setItem('auth_user', JSON.stringify(userData));
      notifySubscribers();
      return true;
    }

    // 响应不成功，清除无效的 token
    if (response.status === 401) {
      console.warn('[Auth] Token expired or invalid, clearing auth state');
      // 清除状态（不重定向，因为 validateToken 会触发重定向）
      clearAuthState(false);
      return false;
    }
    return false;
  } catch (error) {
    console.error('[Auth] Token validation failed:', error);
    return false;
  }
}

/**
 * 初始化认证状态
 */
export function initAuthState(): void {
  if (!browser || initialized) return;
  initialized = true;

  // 从 localStorage 恢复状态
  const token = localStorage.getItem('auth_token');
  const userStr = localStorage.getItem('auth_user');

  // 如果 token 不存在，直接设置未认证
  if (!token) {
    isAuthenticated = false;
    user = null;
    return;
  }

  isAuthenticated = true;

  if (userStr) {
    try {
      user = JSON.parse(userStr);
    } catch {
      user = null;
      // 如果 token 存在但 user 数据损坏，需要验证 token
      tokenValidationRequired();
    }
  } else {
    // token 存在但没有用户数据，需要验证
    tokenValidationRequired();
  }

  // 启动存储轮询（检测当前页面的缓存清除）
  startStoragePoll();

  // 监听 storage 变化（多标签页同步）
  window.addEventListener('storage', (event) => {
    if (event.key === 'auth_token') {
      const hasToken = !!event.newValue;
      isAuthenticated = hasToken;
      if (!hasToken) {
        user = null;
        // 停止轮询
        stopStoragePoll();
      }
      notifySubscribers();
    }
    if (event.key === 'auth_user' && !event.newValue) {
      user = null;
      notifySubscribers();
    }
  });
}

/**
 * 标记需要验证 token（用于存储不完整时）
 */
function tokenValidationRequired(): void {
  // 异步验证 token，不阻塞初始化
  validateToken().catch(() => {
    // 验证失败时已由 clearAuthState 处理
  });
}

/**
 * 获取当前认证状态
 */
export function getAuthState(): AuthState {
  return {
    isAuthenticated,
    user
  };
}

/**
 * 设置认证状态（登录时调用）
 */
export function setAuthState(newUser: User, token: string): void {
  if (!browser) return;

  // 存储到 localStorage
  localStorage.setItem('auth_token', token);
  localStorage.setItem('auth_user', JSON.stringify(newUser));

  // 更新状态
  isAuthenticated = true;
  user = newUser;

  notifySubscribers();
}

/**
 * 清除认证状态（登出时调用）
 * @param redirectToLogin 是否重定向到登录页，默认 true
 */
export function clearAuthState(redirectToLogin: boolean = true): void {
  if (!browser) return;

  // 停止轮询
  stopStoragePoll();

  // 清除 localStorage
  localStorage.removeItem('auth_token');
  localStorage.removeItem('auth_user');

  // 更新状态
  isAuthenticated = false;
  user = null;

  notifySubscribers();

  // 如果需要，重定向到登录页
  if (redirectToLogin) {
    const { href } = window.location;
    // 只有不在登录页时才重定向
    if (!href.includes('/login') && !href.includes('/oauth/')) {
      window.location.href = '/login';
    }
  }
}

/**
 * 更新用户信息
 */
export function updateUserState(newUser: Partial<User>): void {
  if (!browser || !user) return;

  user = { ...user, ...newUser };
  localStorage.setItem('auth_user', JSON.stringify(user));
  notifySubscribers();
}

/**
 * 订阅认证状态变化
 */
export function subscribeAuth(callback: (state: AuthState) => void): () => void {
  subscribers.add(callback);
  // 立即回调一次，返回当前状态
  callback({
    isAuthenticated,
    user
  });

  // 返回取消订阅函数
  return () => {
    subscribers.delete(callback);
  };
}

/**
 * 检查是否已认证
 */
export function checkAuthenticated(): boolean {
  return isAuthenticated;
}

/**
 * 获取当前用户
 */
export function getCurrentUser(): User | null {
  return user;
}

/**
 * 检查用户是否有特定权限
 */
export function checkPermission(permission: string): boolean {
  if (!user) return false;

  // 管理员拥有所有权限
  if (user.is_admin) return true;

  // 检查权限字段
  if (user.permissions && permission in user.permissions) {
    const result = user.permissions[permission] ?? false;
    console.log('[Auth] checkPermission:', permission, 'from user.permissions:', result);
    return result;
  }

  // 默认权限
  const defaultPermissions: Record<string, boolean> = {
    chat: true,
    conversations: true,
    preferences: true,
    providers: false,
    api_keys: false,
    stats: false,
    health: false,
    config: false,
    users: false,
  };

  console.log('[Auth] checkPermission:', permission, 'using defaults, user.permissions:', user.permissions);
  return defaultPermissions[permission] ?? false;
}