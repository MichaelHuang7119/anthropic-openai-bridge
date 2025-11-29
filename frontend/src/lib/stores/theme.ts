import { writable } from "svelte/store";
import { browser } from "$app/environment";

export type Theme = "light" | "dark";
export type ColorTheme = "orange" | "blue" | "green" | "purple" | "pink";

// 颜色主题配置
export const colorThemes: Record<ColorTheme, string> = {
  blue: "蓝色",
  orange: "橙红色",
  green: "绿色",
  purple: "紫色",
  pink: "粉色",
};

// 默认颜色主题
const DEFAULT_COLOR_THEME: ColorTheme = "blue";

function createThemeStore() {
  // 默认主题：从 localStorage 读取，如果没有则使用系统偏好
  const getInitialTheme = (): Theme => {
    if (!browser) return "light";

    const stored = localStorage.getItem("theme") as Theme | null;
    if (stored === "light" || stored === "dark") {
      return stored;
    }

    // 检查系统偏好
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }

    return "light";
  };

  // 获取颜色主题
  const getInitialColorTheme = (): ColorTheme => {
    if (!browser) return DEFAULT_COLOR_THEME;

    const stored = localStorage.getItem("color-theme") as ColorTheme | null;
    if (stored && colorThemes[stored]) {
      // 如果存储的是旧的orange主题，则清除并使用新默认值
      if (stored === "orange") {
        localStorage.removeItem("color-theme");
        return DEFAULT_COLOR_THEME;
      }
      return stored;
    }

    return DEFAULT_COLOR_THEME;
  };

  const { subscribe, set, update } = writable<Theme>(getInitialTheme());
  const { set: setColor } = writable<ColorTheme>(getInitialColorTheme());

  return {
    subscribe,
    set: (theme: Theme) => {
      if (browser) {
        localStorage.setItem("theme", theme);
        document.documentElement.setAttribute("data-theme", theme);
      }
      set(theme);
    },
    toggle: () => {
      update((current) => {
        const newTheme = current === "light" ? "dark" : "light";
        if (browser) {
          localStorage.setItem("theme", newTheme);
          document.documentElement.setAttribute("data-theme", newTheme);
        }
        return newTheme;
      });
    },
    // 颜色主题方法
    setColorTheme: (colorTheme: ColorTheme) => {
      if (browser) {
        localStorage.setItem("color-theme", colorTheme);
        document.documentElement.setAttribute("data-color-theme", colorTheme);
      }
      setColor(colorTheme);
    },
    init: () => {
      if (browser) {
        const theme = getInitialTheme();
        document.documentElement.setAttribute("data-theme", theme);
        set(theme);

        const colorTheme = getInitialColorTheme();
        document.documentElement.setAttribute("data-color-theme", colorTheme);
        setColor(colorTheme);

        // 监听系统主题变化
        window
          .matchMedia("(prefers-color-scheme: dark)")
          .addEventListener("change", (e) => {
            const stored = localStorage.getItem("theme");
            if (!stored) {
              const newTheme = e.matches ? "dark" : "light";
              document.documentElement.setAttribute("data-theme", newTheme);
              set(newTheme);
            }
          });
      }
    },
  };
}

export const theme = createThemeStore();
