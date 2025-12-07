/**
 * 会话级别的聊天状态管理
 * 每个会话都有独立的状态，避免多会话并发冲突
 */

import { writable } from "svelte/store";
import type { Writable } from "svelte/store";
import type {
  Conversation,
  ConversationDetail,
  ModelChoice,
} from "$services/chatService";
import { getSessionId } from "$lib/utils/session";

// 会话状态接口
export interface SessionState {
  conversations: Conversation[];
  currentConversation: ConversationDetail | null;
  selectedModel: ModelChoice | null;
  isLoading: boolean;
  streamingMessage: string | null;
  error: string | null;
  sessionId: string;
}

// 会话状态Map，存储所有会话的状态
const sessionStates = new Map<string, Writable<SessionState>>();

/**
 * 获取指定会话的状态store
 * 如果会话不存在，则创建新的
 */
export function getSessionStore(sessionId: string): Writable<SessionState> {
  // 检查会话是否存在
  if (sessionStates.has(sessionId)) {
    return sessionStates.get(sessionId)!;
  }

  // 创建新的会话状态
  const initialState: SessionState = {
    conversations: [],
    currentConversation: null,
    selectedModel: null,
    isLoading: false,
    streamingMessage: null,
    error: null,
    sessionId,
  };

  const store = writable(initialState);
  sessionStates.set(sessionId, store);

  return store;
}

/**
 * 获取当前会话的ID
 * 如果没有会话ID，返回null
 */
export function getCurrentSessionId(): string | null {
  return getSessionId();
}

/**
 * 清除指定会话的状态
 * 用于会话切换或重置
 */
export function clearSessionState(sessionId: string): void {
  sessionStates.delete(sessionId);
}

/**
 * 清除所有会话状态
 * 用于应用重置
 */
export function clearAllSessionStates(): void {
  sessionStates.clear();
}

/**
 * 获取所有会话ID
 * 用于调试或管理
 */
export function getAllSessionIds(): string[] {
  return Array.from(sessionStates.keys());
}
