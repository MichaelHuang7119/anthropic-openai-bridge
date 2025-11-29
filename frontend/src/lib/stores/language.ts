import { writable, derived } from "svelte/store";
// import { browser } from "$app/environment";

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

export type Language =
  | "zh-CN"
  | "en-US"
  | "ja-JP"
  | "ko-KR"
  | "fr-FR"
  | "es-ES"
  | "de-DE"
  | "ru-RU"
  | "pt-BR"
  | "it-IT"
  | "nl-NL"
  | "ar-SA"
  | "hi-IN"
  | "th-TH"
  | "vi-VN"
  | "id-ID";

// 支持的语言配置
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
const DEFAULT_LANGUAGE: Language = "zh-CN";

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

    // 备用方案：检测浏览器语言
    const browserLang =
      typeof navigator !== "undefined" ? navigator.language : "";
    if (browserLang.startsWith("zh")) {
      return "zh-CN";
    } else if (browserLang.startsWith("en")) {
      return "en-US";
    } else if (browserLang.startsWith("ja")) {
      return "ja-JP";
    } else if (browserLang.startsWith("ko")) {
      return "ko-KR";
    } else if (browserLang.startsWith("fr")) {
      return "fr-FR";
    } else if (browserLang.startsWith("es")) {
      return "es-ES";
    } else if (browserLang.startsWith("de")) {
      return "de-DE";
    } else if (browserLang.startsWith("ru")) {
      return "ru-RU";
    } else if (browserLang.startsWith("pt")) {
      return "pt-BR";
    } else if (browserLang.startsWith("it")) {
      return "it-IT";
    } else if (browserLang.startsWith("nl")) {
      return "nl-NL";
    } else if (browserLang.startsWith("ar")) {
      return "ar-SA";
    } else if (browserLang.startsWith("hi")) {
      return "hi-IN";
    } else if (browserLang.startsWith("th")) {
      return "th-TH";
    } else if (browserLang.startsWith("vi")) {
      return "vi-VN";
    } else if (browserLang.startsWith("id")) {
      return "id-ID";
    }
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

// 导出language对象
export const language = {
  subscribe: languageStore.subscribe,
  set: (language: Language) => {
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
    languageStore.set(language);
  },
  // 循环切换语言（保持原有逻辑）
  toggle: () => {
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
    languageStore.update((current) => {
      const currentIndex = languageOrder.indexOf(current);
      const nextIndex = (currentIndex + 1) % languageOrder.length;
      const newLanguage = languageOrder[nextIndex];
      if (typeof document !== "undefined") {
        localStorage.setItem("language", newLanguage);
        document.documentElement.setAttribute("data-language", newLanguage);
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
        document.documentElement.lang = langMap[newLanguage] || "en";
      }
      return newLanguage;
    });
  },
  // 初始化语言
  init: () => {
    const language = getInitialLanguage();
    if (typeof document !== "undefined") {
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
    languageStore.set(language);
  },
  // 获取翻译文本
  t: tStore,
};
