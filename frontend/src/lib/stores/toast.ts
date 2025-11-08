import { writable } from 'svelte/store';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number; // 自动关闭时间（毫秒），默认 2000
}

function createToastStore() {
  const { subscribe, update } = writable<Toast[]>([]);

  const show = (message: string, type: ToastType = 'info', duration: number = 2000) => {
    const id = Math.random().toString(36).substring(2, 9);
    const toast: Toast = { id, message, type, duration };
    
    update((toasts) => [...toasts, toast]);
    
    // 自动移除
    setTimeout(() => {
      update((toasts) => toasts.filter((t) => t.id !== id));
    }, duration);
    
    return id;
  };

  return {
    subscribe,
    show,
    success: (message: string, duration?: number) => {
      return show(message, 'success', duration);
    },
    error: (message: string, duration?: number) => {
      return show(message, 'error', duration);
    },
    info: (message: string, duration?: number) => {
      return show(message, 'info', duration);
    },
    warning: (message: string, duration?: number) => {
      return show(message, 'warning', duration);
    },
    remove: (id: string) => {
      update((toasts) => toasts.filter((t) => t.id !== id));
    },
    clear: () => {
      update(() => []);
    }
  };
}

export const toast = createToastStore();

