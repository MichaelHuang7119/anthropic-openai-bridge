/**
 * 滑动手势支持工具
 * 提供触摸手势检测功能，支持侧边栏开关和聊天页面滑动
 */

export interface SwipeEvent {
  direction: "left" | "right" | "up" | "down";
  deltaX: number;
  deltaY: number;
  velocity: number;
}

export interface SwipeOptions {
  threshold?: number; // 最小滑动距离，默认50px
  velocity?: number; // 最小滑动速度，默认0.3
  preventDefault?: boolean; // 是否阻止默认事件，默认true
}

export interface TouchPoint {
  x: number;
  y: number;
  time: number;
}

/**
 * 手势检测类
 */
export class GestureDetector {
  private startTouch: TouchPoint | null = null;
  private lastTouch: TouchPoint | null = null;
  private element: HTMLElement;
  private options: Required<SwipeOptions>;

  constructor(element: HTMLElement, options: SwipeOptions = {}) {
    this.element = element;
    this.options = {
      threshold: options.threshold ?? 50,
      velocity: options.velocity ?? 0.3,
      preventDefault: options.preventDefault ?? true,
    };

    this.bindEvents();
  }

  private bindEvents() {
    this.element.addEventListener("touchstart", this.handleTouchStart, {
      passive: false,
    });
    this.element.addEventListener("touchmove", this.handleTouchMove, {
      passive: false,
    });
    this.element.addEventListener("touchend", this.handleTouchEnd, {
      passive: false,
    });
    this.element.addEventListener("touchcancel", this.handleTouchEnd, {
      passive: false,
    });
  }

  private handleTouchStart = (e: TouchEvent) => {
    if (this.options.preventDefault) {
      e.preventDefault();
    }

    const touch = e.touches[0];
    this.startTouch = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
    };
    this.lastTouch = this.startTouch;
  };

  private handleTouchMove = (e: TouchEvent) => {
    if (this.options.preventDefault && this.startTouch) {
      e.preventDefault();
    }

    const touch = e.touches[0];
    this.lastTouch = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
    };
  };

  private handleTouchEnd = (_e: TouchEvent) => {
    if (!this.startTouch || !this.lastTouch) return;

    const deltaX = this.lastTouch.x - this.startTouch.x;
    const deltaY = this.lastTouch.y - this.startTouch.y;
    const deltaTime = this.lastTouch.time - this.startTouch.time;

    // 计算滑动距离
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

    // 检查是否达到最小滑动距离
    if (distance < this.options.threshold) {
      this.reset();
      return;
    }

    // 计算滑动速度 (pixels/ms)
    const velocity = distance / deltaTime;

    // 检查是否达到最小滑动速度
    if (velocity < this.options.velocity) {
      this.reset();
      return;
    }

    // 确定滑动方向
    let direction: SwipeEvent["direction"];
    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);

    if (absX > absY) {
      direction = deltaX > 0 ? "right" : "left";
    } else {
      direction = deltaY > 0 ? "down" : "up";
    }

    // 触发滑动事件
    const swipeEvent: SwipeEvent = {
      direction,
      deltaX,
      deltaY,
      velocity,
    };

    this.element.dispatchEvent(
      new CustomEvent("swipe", {
        detail: swipeEvent,
        bubbles: true,
      }),
    );

    this.reset();
  };

  private reset() {
    this.startTouch = null;
    this.lastTouch = null;
  }

  public destroy() {
    this.element.removeEventListener("touchstart", this.handleTouchStart);
    this.element.removeEventListener("touchmove", this.handleTouchMove);
    this.element.removeEventListener("touchend", this.handleTouchEnd);
    this.element.removeEventListener("touchcancel", this.handleTouchEnd);
  }
}

/**
 * 创建滑动手势监听器
 */
export function createSwipeListener(
  element: HTMLElement,
  callback: (event: SwipeEvent) => void,
  options: SwipeOptions = {},
) {
  const detector = new GestureDetector(element, options);

  const handler = (e: Event) => {
    const customEvent = e as CustomEvent<SwipeEvent>;
    callback(customEvent.detail);
  };

  element.addEventListener("swipe", handler);

  return {
    destroy() {
      element.removeEventListener("swipe", handler);
      detector.destroy();
    },
  };
}

/**
 * 滑动手势指令 - 用于Svelte组件
 */
export function swipeDirective(
  node: HTMLElement,
  options: SwipeOptions | ((event: SwipeEvent) => void),
) {
  const opts = typeof options === "function" ? {} : options;
  const callback = typeof options === "function" ? options : () => {};

  const detector = new GestureDetector(node, opts);

  const handler = (e: Event) => {
    const customEvent = e as CustomEvent<SwipeEvent>;
    callback(customEvent.detail);
  };

  node.addEventListener("swipe", handler);

  return {
    destroy() {
      node.removeEventListener("swipe", handler);
      detector.destroy();
    },
  };
}

/**
 * 检测是否为移动设备
 */
export function isMobile(): boolean {
  if (typeof window === "undefined") return false;
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent,
  );
}

/**
 * 检测触摸支持
 */
export function hasTouchSupport(): boolean {
  if (typeof window === "undefined") return false;
  return "ontouchstart" in window || navigator.maxTouchPoints > 0;
}

/**
 * 添加全局滑动手势支持
 * 适用于侧边栏开关
 */
export function enableGlobalSwipe(
  element: HTMLElement,
  onSwipeLeft?: () => void,
  onSwipeRight?: () => void,
  options: SwipeOptions = {},
) {
  const fullOptions = {
    threshold: 100, // 全局手势需要更大的阈值
    ...options,
  };

  return createSwipeListener(
    element,
    (event) => {
      switch (event.direction) {
        case "left":
          onSwipeLeft?.();
          break;
        case "right":
          onSwipeRight?.();
          break;
      }
    },
    fullOptions,
  );
}

/**
 * 聊天页面专用手势支持
 */
export function enableChatGestures(
  chatContainer: HTMLElement,
  callbacks: {
    onSwipeLeft?: () => void; // 切换到下一条消息
    onSwipeRight?: () => void; // 切换到上一条消息
    onSwipeUp?: () => void; // 加载更多消息
    onSwipeDown?: () => void; // 滚动到底部
  } = {},
  options: SwipeOptions = {},
) {
  return createSwipeListener(
    chatContainer,
    (event) => {
      const direction =
        event.direction.charAt(0).toUpperCase() + event.direction.slice(1);
      const callbackName = `onSwipe${direction}` as keyof typeof callbacks;
      const callback = callbacks[callbackName];
      callback?.();
    },
    {
      threshold: 75,
      ...options,
    },
  );
}
