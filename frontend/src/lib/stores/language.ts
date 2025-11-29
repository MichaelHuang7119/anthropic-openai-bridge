import { writable, derived } from "svelte/store";
import { browser } from "$app/environment";
import { preferencesService } from "$services/preferences";
import type { Language } from "$types/language";
import { authService } from "$services/auth";

// 导入翻译数据
import zhCn from "../i18n/zh-CN.json";
import enUs from "../i18n/en-US.json";
import jaJp from "../i18n/ja-JP.json";
import koKr from "../i18n/ko-KR.json";
import frFr from "../i18n/fr-FR.json";
import esEs from "../i18n/es-ES.json";
import deDe from "../i18n/de-DE.json";
import ruRu from "../i18n/ru-RU.json";
import ptBr from "../i18n/pt-BR.json";
import itIt from "../i18n/it-IT.json";
import nlNl from "../i18n/nl-NL.json";
import arSa from "../i18n/ar-SA.json";
import hiIn from "../i18n/hi-IN.json";
import thTh from "../i18n/th-TH.json";
import viVn from "../i18n/vi-VN.json";
import idId from "../i18n/id-ID.json";

// 支持的语言配置
export { type Language } from "$types/language";

export const languages: Record<Language, string> = {
  "zh-CN": "中文",
  "en-US": "English",
  "ja-JP": "日本語",
  "ko-KR": "한국어",
  "fr-FR": "Français",
  "es-ES": "Español",
  "de-DE": "Deutsch",
  "ru-RU": "Русский",
  "pt-BR": "Português",
  "it-IT": "Italiano",
  "nl-NL": "Nederlands",
  "ar-SA": "العربية",
  "hi-IN": "हिन्दी",
  "th-TH": "ไทย",
  "vi-VN": "Tiếng Việt",
  "id-ID": "Bahasa Indonesia",
};

// 默认语言
const DEFAULT_LANGUAGE: Language = "en-US";

// 翻译数据存储
const translations: Record<Language, any> = {
  "zh-CN": zhCn,
  "en-US": enUs,
  "ja-JP": jaJp,
  "ko-KR": koKr,
  "fr-FR": frFr,
  "es-ES": esEs,
  "de-DE": deDe,
  "ru-RU": ruRu,
  "pt-BR": ptBr,
  "it-IT": itIt,
  "nl-NL": nlNl,
  "ar-SA": arSa,
  "hi-IN": hiIn,
  "th-TH": thTh,
  "vi-VN": viVn,
  "id-ID": idId,
};

// 创建语言store
const languageStore = writable<Language>(DEFAULT_LANGUAGE);

// 创建翻译函数store
const tStore = derived(languageStore, (currentLang) => {
  return (key: string): string => {
    // 处理嵌套key（如 "nav.home"）
    const keys = key.split(".");
    let value = translations[currentLang];

    for (const k of keys) {
      if (value && typeof value === "object" && k in value) {
        value = value[k];
      } else {
        value = null;
        break;
      }
    }

    if (value) {
      return value as string;
    }

    // 如果当前语言没有翻译，尝试默认语言
    value = translations[DEFAULT_LANGUAGE];
    for (const k of keys) {
      if (value && typeof value === "object" && k in value) {
        value = value[k];
      } else {
        return key; // 找不到翻译，返回key
      }
    }

    return (value as string) || key;
  };
});

// 获取初始语言
const getInitialLanguage = (): Language => {
  // 优先从 document 的 data-language 属性读取（由 app.html 预设置）
  if (typeof document !== "undefined") {
    const docLang = document.documentElement.getAttribute(
      "data-language",
    ) as Language | null;
    if (docLang && languages[docLang]) {
      return docLang;
    }

    // 备用方案：从 localStorage 读取
    const stored = localStorage.getItem("language") as Language | null;
    if (stored && languages[stored]) {
      return stored;
    }

    // 不再自动检测浏览器语言
    // 清除缓存后应使用默认语言，而不是根据浏览器语言自动切换
  }

  // 如果没有设置，返回默认语言
  return DEFAULT_LANGUAGE;
};

// 初始化
const initialLanguage = getInitialLanguage();

// 确保 document 的语言属性被正确设置
if (typeof document !== "undefined") {
  document.documentElement.setAttribute("data-language", initialLanguage);
  const langMap: Record<Language, string> = {
    "zh-CN": "zh-CN",
    "en-US": "en",
    "ja-JP": "ja",
    "ko-KR": "ko",
    "fr-FR": "fr",
    "es-ES": "es",
    "de-DE": "de",
    "ru-RU": "ru",
    "pt-BR": "pt-BR",
    "it-IT": "it",
    "nl-NL": "nl",
    "ar-SA": "ar",
    "hi-IN": "hi",
    "th-TH": "th",
    "vi-VN": "vi",
    "id-ID": "id",
  };
  document.documentElement.lang = langMap[initialLanguage] || "en";
}

// 设置语言存储
languageStore.set(initialLanguage);

// 导出tStore以供组件直接使用
export { tStore };

// 应用语言到文档
function applyLanguage(language: Language) {
  if (typeof document !== "undefined") {
    localStorage.setItem("language", language);
    document.documentElement.setAttribute("data-language", language);
    const langMap: Record<Language, string> = {
      "zh-CN": "zh-CN",
      "en-US": "en",
      "ja-JP": "ja",
      "ko-KR": "ko",
      "fr-FR": "fr",
      "es-ES": "es",
      "de-DE": "de",
      "ru-RU": "ru",
      "pt-BR": "pt-BR",
      "it-IT": "it",
      "nl-NL": "nl",
      "ar-SA": "ar",
      "hi-IN": "hi",
      "th-TH": "th",
      "vi-VN": "vi",
      "id-ID": "id",
    };
    document.documentElement.lang = langMap[language] || "en";
  }
}

// 导出language对象
export const language = {
  subscribe: languageStore.subscribe,
  set: async (language: Language) => {
    // 首先更新前端
    applyLanguage(language);
    languageStore.set(language);

    // 然后更新到后端（如果已登录）
    if (browser && authService.isAuthenticated()) {
      try {
        await preferencesService.updateLanguage(language);
      } catch (error) {
        console.error("Failed to update language preference:", error);
        // 即使后端更新失败，也保持前端的语言设置
      }
    }
  },
  // 循环切换语言（保持原有逻辑）
  toggle: async () => {
    const languageOrder: Language[] = [
      "zh-CN",
      "en-US",
      "ja-JP",
      "ko-KR",
      "fr-FR",
      "es-ES",
      "de-DE",
      "ru-RU",
      "pt-BR",
      "it-IT",
      "nl-NL",
      "ar-SA",
      "hi-IN",
      "th-TH",
      "vi-VN",
      "id-ID",
    ];
    const currentLang = getCurrentLanguage();
    const currentIndex = languageOrder.indexOf(currentLang);
    const nextIndex = (currentIndex + 1) % languageOrder.length;
    const newLanguage = languageOrder[nextIndex];

    // 使用 set 方法，会自动处理前端和后端更新
    await language.set(newLanguage);
  },
  // 初始化语言
  init: async () => {
    let language = getInitialLanguage();

    // 如果已登录，尝试从后端获取语言设置
    if (browser && authService.isAuthenticated()) {
      try {
        const response = await preferencesService.getLanguage();
        if (response.language && languages[response.language as Language]) {
          language = response.language as Language;
        }
      } catch (error) {
        console.error(
          "Failed to load language preference from backend:",
          error,
        );
        // 如果后端加载失败，使用本地存储的语言
      }
    }

    applyLanguage(language);
    languageStore.set(language);
  },
  // 获取翻译文本
  t: tStore,
};

// 获取当前语言
function getCurrentLanguage(): Language {
  let currentLang: Language = DEFAULT_LANGUAGE;
  languageStore.subscribe((lang) => {
    currentLang = lang;
  })();
  return currentLang;
}
