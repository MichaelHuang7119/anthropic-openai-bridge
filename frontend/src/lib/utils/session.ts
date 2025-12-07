/**
 * 会话管理工具 - 用于支持多会话并发调用
 */

/**
 * 生成唯一的会话ID
 * 格式: session_{timestamp}_{random}
 */
export function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 获取或创建会话ID
 * 使用sessionStorage确保每个窗口/标签页独立
 */
export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") {
    return generateSessionId();
  }

  // 使用sessionStorage，每个窗口/标签页独立存储
  const storageKey = "anthropic_bridge_session_id";
  let sessionId = sessionStorage.getItem(storageKey);

  if (!sessionId) {
    sessionId = generateSessionId();
    sessionStorage.setItem(storageKey, sessionId);
  }

  return sessionId;
}

/**
 * 创建新的会话ID（用于切换会话）
 * 使用sessionStorage确保每个窗口/标签页独立
 */
export function createNewSessionId(): string {
  const sessionId = generateSessionId();

  if (typeof window !== "undefined") {
    sessionStorage.setItem("anthropic_bridge_session_id", sessionId);
  }

  return sessionId;
}

/**
 * 清除会话ID（用于重置会话）
 * 使用sessionStorage确保每个窗口/标签页独立
 */
export function clearSessionId(): void {
  if (typeof window === "undefined") {
    return;
  }

  sessionStorage.removeItem("anthropic_bridge_session_id");
}

/**
 * 获取会话ID（仅获取，不创建）
 * 使用sessionStorage确保每个窗口/标签页独立
 */
export function getSessionId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return sessionStorage.getItem("anthropic_bridge_session_id");
}
