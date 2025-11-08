import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { HealthStatus } from '$types/health';

const STORAGE_KEY = 'health_check_data';
const LAST_CHECK_KEY = 'last_health_check_time';

// 初始健康状态
const initialHealthStatus: HealthStatus = {
  status: 'error',
  timestamp: '',
  providers: []
};

// 从localStorage读取数据
function loadFromStorage(): { healthData: HealthStatus, lastCheck: Date | null } {
  if (!browser) {
    return { healthData: initialHealthStatus, lastCheck: null };
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const lastCheckStr = localStorage.getItem(LAST_CHECK_KEY);

    if (stored) {
      const healthData = JSON.parse(stored) as HealthStatus;
      const lastCheck = lastCheckStr ? new Date(lastCheckStr) : null;
      return { healthData, lastCheck };
    }
  } catch (error) {
    console.error('Failed to load health data from localStorage:', error);
  }

  return { healthData: initialHealthStatus, lastCheck: null };
}

// 保存到localStorage
function saveToStorage(data: HealthStatus) {
  if (!browser) return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (error) {
    console.error('Failed to save health data to localStorage:', error);
  }
}

function saveLastCheckTime(time: Date) {
  if (!browser) return;

  try {
    localStorage.setItem(LAST_CHECK_KEY, time.toISOString());
  } catch (error) {
    console.error('Failed to save last check time to localStorage:', error);
  }
}

// 加载存储的数据
const { healthData, lastCheck } = loadFromStorage();

// 创建可持久化的健康状态store
export const healthStatus = writable<HealthStatus>(healthData);

// 订阅healthStatus变化并保存到localStorage
if (browser) {
  healthStatus.subscribe((data) => {
    // 如果有实际的健康数据才保存
    if (data.providers && data.providers.length > 0) {
      saveToStorage(data);
    }
  });
}

// 创建最后检查时间store
export const lastHealthCheck = writable<Date | null>(lastCheck);

// 订阅lastHealthCheck变化并保存到localStorage
if (browser) {
  lastHealthCheck.subscribe((time) => {
    if (time) {
      saveLastCheckTime(time);
    }
  });
}

// 清除健康检查数据（用于测试或重置）
export function clearHealthData() {
  if (!browser) return;

  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(LAST_CHECK_KEY);
    healthStatus.set(initialHealthStatus);
    lastHealthCheck.set(null);
  } catch (error) {
    console.error('Failed to clear health data:', error);
  }
}
