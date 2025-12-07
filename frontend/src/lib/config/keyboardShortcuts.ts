/**
 * 全局键盘快捷键配置
 */

import { browser } from "$app/environment";
import { theme } from "$stores/theme";

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  action: () => void;
  description: string;
  scope?: "global" | "chat" | "modal";
  category?: "system" | "navigation" | "actions";
}

export const keyboardShortcuts: Record<string, KeyboardShortcut> = {
  // 系统主题切换快捷键 - 支持常见快捷键
  TOGGLE_THEME: {
    key: "L",
    ctrlKey: true,
    shiftKey: true,
    action: () => {
      if (!browser) return;
      theme.toggle();
    },
    description: "切换主题",
    scope: "global",
    category: "system",
  },
  TOGGLE_THEME_MAC: {
    key: "D",
    metaKey: true,
    shiftKey: true,
    action: () => {
      if (!browser) return;
      theme.toggle();
    },
    description: "切换主题",
    scope: "global",
    category: "system",
  },
  TOGGLE_THEME_MAC_ALT: {
    key: "T",
    metaKey: true,
    altKey: true,
    action: () => {
      if (!browser) return;
      theme.toggle();
    },
    description: "切换主题",
    scope: "global",
    category: "system",
  },
};

// 快捷键事件处理
export function handleKeyboardEvent(event: KeyboardEvent): boolean {
  // 跳过在输入框、文本域和可编辑元素中的按键
  const target = event.target as HTMLElement;
  if (
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.tagName === "SELECT" ||
    target.isContentEditable
  ) {
    return false;
  }

  // 检查所有注册的快捷键
  for (const shortcut of Object.values(keyboardShortcuts)) {
    // 检查按键匹配
    if (
      event.key.toLowerCase() === shortcut.key.toLowerCase() &&
      !!event.ctrlKey === !!shortcut.ctrlKey &&
      !!event.metaKey === !!shortcut.metaKey &&
      !!event.shiftKey === !!shortcut.shiftKey &&
      !!event.altKey === !!shortcut.altKey
    ) {
      // 检查作用域（如果指定了）
      const currentPath = window.location.pathname;
      if (shortcut.scope === "chat" && !currentPath.startsWith("/chat")) {
        continue;
      }
      if (shortcut.scope === "modal") {
        // 检查是否有模态框打开
        const modal = document.querySelector('[role="dialog"]');
        if (!modal) continue;
      }

      event.preventDefault();
      shortcut.action();
      return true;
    }
  }

  return false;
}

// 获取快捷键描述文本
export function getShortcutDescription(action: string): string {
  const shortcut = keyboardShortcuts[action];
  if (!shortcut) return "";

  const parts: string[] = [];
  if (shortcut.ctrlKey) parts.push("Ctrl");
  if (shortcut.metaKey) parts.push("Cmd");
  if (shortcut.shiftKey) parts.push("Shift");
  if (shortcut.altKey) parts.push("Alt");
  parts.push(shortcut.key.toUpperCase());

  return parts.join(" + ");
}

// 获取系统主题切换的所有快捷键
export function getAllThemeShortcuts(): KeyboardShortcut[] {
  return Object.values(keyboardShortcuts).filter(
    (shortcut) => shortcut.category === "system",
  );
}

// 获取系统主题切换快捷键的显示文本
export function getThemeShortcutsText(): string[] {
  const shortcuts = getAllThemeShortcuts();
  return shortcuts.map((shortcut) => {
    const parts: string[] = [];
    if (shortcut.ctrlKey) parts.push("Ctrl");
    if (shortcut.metaKey) parts.push("Cmd");
    if (shortcut.shiftKey) parts.push("Shift");
    if (shortcut.altKey) parts.push("Alt");
    parts.push(shortcut.key.toUpperCase());
    return parts.join(" + ");
  });
}
