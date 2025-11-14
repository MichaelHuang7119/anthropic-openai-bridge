/**
 * API Key 安全存储服务
 * 用于在创建时保存完整 API Key 到 localStorage，以便后续安全地显示和复制
 * 在清除浏览器缓存后，会尝试从后端接口获取完整 API Key
 */
import { browser } from '$app/environment';
import { apiClient } from './api';

const STORAGE_PREFIX = 'api_key_full_';

/**
 * 保存完整 API Key 到 localStorage
 * @param keyId API Key ID
 * @param fullKey 完整的 API Key
 */
export function saveFullApiKey(keyId: number, fullKey: string): void {
  if (!browser) return;

  try {
    const storageKey = `${STORAGE_PREFIX}${keyId}`;
    localStorage.setItem(storageKey, fullKey);
  } catch (error) {
    console.error('Failed to save API key to localStorage:', error);
  }
}

/**
 * 从本地存储或后端获取完整 API Key
 * @param keyId API Key ID
 * @returns 完整的 API Key，如果不存在则返回 null
 */
export async function getFullApiKey(keyId: number): Promise<string | null> {
  if (!browser) return null;

  try {
    const storageKey = `${STORAGE_PREFIX}${keyId}`;
    const cachedKey = localStorage.getItem(storageKey);

    // 如果 localStorage 中有缓存，直接返回
    if (cachedKey) {
      return cachedKey;
    }

    // 如果没有缓存，尝试从后端接口获取
    console.debug(`[API Key] Key ${keyId} not in localStorage, fetching from server...`);
    const response = await apiClient.get<{ api_key: string }>(`/api/api-keys/${keyId}/full`);
    const fullKey = response.api_key;

    // 保存到 localStorage
    localStorage.setItem(storageKey, fullKey);

    return fullKey;
  } catch (error) {
    console.error('Failed to get API key:', error);
    return null;
  }
}

/**
 * 从 localStorage 获取完整 API Key（仅本地缓存，不调用后端）
 * @param keyId API Key ID
 * @returns 完整的 API Key，如果不存在则返回 null
 */
export function getFullApiKeyLocal(keyId: number): string | null {
  if (!browser) return null;

  try {
    const storageKey = `${STORAGE_PREFIX}${keyId}`;
    return localStorage.getItem(storageKey);
  } catch (error) {
    console.error('Failed to get API key from localStorage:', error);
    return null;
  }
}

/**
 * 检查是否存在完整 API Key
 * @param keyId API Key ID
 * @returns 是否存在
 */
export function hasFullApiKey(keyId: number): boolean {
  if (!browser) return false;
  return getFullApiKey(keyId) !== null;
}

/**
 * 删除完整 API Key（当 key 被删除时调用）
 * @param keyId API Key ID
 */
export function removeFullApiKey(keyId: number): void {
  if (!browser) return;
  
  try {
    const storageKey = `${STORAGE_PREFIX}${keyId}`;
    localStorage.removeItem(storageKey);
  } catch (error) {
    console.error('Failed to remove API key from localStorage:', error);
  }
}

/**
 * 清除所有保存的完整 API Key（用于登出等场景）
 */
export function clearAllFullApiKeys(): void {
  if (!browser) return;
  
  try {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith(STORAGE_PREFIX)) {
        localStorage.removeItem(key);
      }
    });
  } catch (error) {
    console.error('Failed to clear API keys from localStorage:', error);
  }
}

