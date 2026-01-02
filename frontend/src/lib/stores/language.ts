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

// 语言名称翻译映射表 - 每个语言在其他语言中的显示名称
export const languageNamesTranslations: Record<
  Language,
  Record<Language, string>
> = {
  "zh-CN": {
    "zh-CN": "中文",
    "en-US": "英语",
    "ja-JP": "日语",
    "ko-KR": "韩语",
    "fr-FR": "法语",
    "es-ES": "西班牙语",
    "de-DE": "德语",
    "ru-RU": "俄语",
    "pt-BR": "葡萄牙语",
    "it-IT": "意大利语",
    "nl-NL": "荷兰语",
    "ar-SA": "阿拉伯语",
    "hi-IN": "印地语",
    "th-TH": "泰语",
    "vi-VN": "越南语",
    "id-ID": "印尼语",
  },
  "en-US": {
    "zh-CN": "Chinese",
    "en-US": "English",
    "ja-JP": "Japanese",
    "ko-KR": "Korean",
    "fr-FR": "French",
    "es-ES": "Spanish",
    "de-DE": "German",
    "ru-RU": "Russian",
    "pt-BR": "Portuguese",
    "it-IT": "Italian",
    "nl-NL": "Dutch",
    "ar-SA": "Arabic",
    "hi-IN": "Hindi",
    "th-TH": "Thai",
    "vi-VN": "Vietnamese",
    "id-ID": "Indonesian",
  },
  "ja-JP": {
    "zh-CN": "中国語",
    "en-US": "英語",
    "ja-JP": "日本語",
    "ko-KR": "韓国語",
    "fr-FR": "フランス語",
    "es-ES": "スペイン語",
    "de-DE": "ドイツ語",
    "ru-RU": "ロシア語",
    "pt-BR": "ポルトガル語",
    "it-IT": "イタリア語",
    "nl-NL": "オランダ語",
    "ar-SA": "アラビア語",
    "hi-IN": "ヒンディー語",
    "th-TH": "タイ語",
    "vi-VN": "ベトナム語",
    "id-ID": "インドネシア語",
  },
  "ko-KR": {
    "zh-CN": "중국어",
    "en-US": "영어",
    "ja-JP": "일본어",
    "ko-KR": "한국어",
    "fr-FR": "프랑스어",
    "es-ES": "스페인어",
    "de-DE": "독일어",
    "ru-RU": "러시아어",
    "pt-BR": "포르투갈어",
    "it-IT": "이탈리아어",
    "nl-NL": "네덜란드어",
    "ar-SA": "아랍어",
    "hi-IN": "힌디어",
    "th-TH": "태국어",
    "vi-VN": "베트남어",
    "id-ID": "인도네시아어",
  },
  "fr-FR": {
    "zh-CN": "Chinois",
    "en-US": "Anglais",
    "ja-JP": "Japonais",
    "ko-KR": "Coréen",
    "fr-FR": "Français",
    "es-ES": "Espagnol",
    "de-DE": "Allemand",
    "ru-RU": "Russe",
    "pt-BR": "Portugais",
    "it-IT": "Italien",
    "nl-NL": "Néerlandais",
    "ar-SA": "Arabe",
    "hi-IN": "Hindi",
    "th-TH": "Thaï",
    "vi-VN": "Vietnamien",
    "id-ID": "Indonésien",
  },
  "es-ES": {
    "zh-CN": "Chino",
    "en-US": "Inglés",
    "ja-JP": "Japonés",
    "ko-KR": "Coreano",
    "fr-FR": "Francés",
    "es-ES": "Español",
    "de-DE": "Alemán",
    "ru-RU": "Ruso",
    "pt-BR": "Portugués",
    "it-IT": "Italiano",
    "nl-NL": "Holandés",
    "ar-SA": "Árabe",
    "hi-IN": "Hindi",
    "th-TH": "Tailandés",
    "vi-VN": "Vietnamita",
    "id-ID": "Indonesio",
  },
  "de-DE": {
    "zh-CN": "Chinesisch",
    "en-US": "Englisch",
    "ja-JP": "Japanisch",
    "ko-KR": "Koreanisch",
    "fr-FR": "Französisch",
    "es-ES": "Spanisch",
    "de-DE": "Deutsch",
    "ru-RU": "Russisch",
    "pt-BR": "Portugiesisch",
    "it-IT": "Italienisch",
    "nl-NL": "Niederländisch",
    "ar-SA": "Arabisch",
    "hi-IN": "Hindi",
    "th-TH": "Thailändisch",
    "vi-VN": "Vietnamesisch",
    "id-ID": "Indonesisch",
  },
  "ru-RU": {
    "zh-CN": "Китайский",
    "en-US": "Английский",
    "ja-JP": "Японский",
    "ko-KR": "Корейский",
    "fr-FR": "Французский",
    "es-ES": "Испанский",
    "de-DE": "Немецкий",
    "ru-RU": "Русский",
    "pt-BR": "Португальский",
    "it-IT": "Итальянский",
    "nl-NL": "Голландский",
    "ar-SA": "Арабский",
    "hi-IN": "Хинди",
    "th-TH": "Тайский",
    "vi-VN": "Вьетнамский",
    "id-ID": "Индонезийский",
  },
  "pt-BR": {
    "zh-CN": "Chinês",
    "en-US": "Inglês",
    "ja-JP": "Japonês",
    "ko-KR": "Coreano",
    "fr-FR": "Francês",
    "es-ES": "Espanhol",
    "de-DE": "Alemão",
    "ru-RU": "Russo",
    "pt-BR": "Português",
    "it-IT": "Italiano",
    "nl-NL": "Holandês",
    "ar-SA": "Árabe",
    "hi-IN": "Hindi",
    "th-TH": "Tailandês",
    "vi-VN": "Vietnamita",
    "id-ID": "Indonésio",
  },
  "it-IT": {
    "zh-CN": "Cinese",
    "en-US": "Inglese",
    "ja-JP": "Giapponese",
    "ko-KR": "Coreano",
    "fr-FR": "Francese",
    "es-ES": "Spagnolo",
    "de-DE": "Tedesco",
    "ru-RU": "Russo",
    "pt-BR": "Portoghese",
    "it-IT": "Italiano",
    "nl-NL": "Olandese",
    "ar-SA": "Arabo",
    "hi-IN": "Hindi",
    "th-TH": "Tailandese",
    "vi-VN": "Vietnamita",
    "id-ID": "Indonesiano",
  },
  "nl-NL": {
    "zh-CN": "Chinees",
    "en-US": "Engels",
    "ja-JP": "Japans",
    "ko-KR": "Koreaans",
    "fr-FR": "Frans",
    "es-ES": "Spaans",
    "de-DE": "Duits",
    "ru-RU": "Russisch",
    "pt-BR": "Portugees",
    "it-IT": "Italiaans",
    "nl-NL": "Nederlands",
    "ar-SA": "Arabisch",
    "hi-IN": "Hindi",
    "th-TH": "Thais",
    "vi-VN": "Vietnamees",
    "id-ID": "Indonesisch",
  },
  "ar-SA": {
    "zh-CN": "الصينية",
    "en-US": "الإنجليزية",
    "ja-JP": "اليابانية",
    "ko-KR": "الكورية",
    "fr-FR": "الفرنسية",
    "es-ES": "الإسبانية",
    "de-DE": "الألمانية",
    "ru-RU": "الروسية",
    "pt-BR": "البرتغالية",
    "it-IT": "الإيطالية",
    "nl-NL": "الهولندية",
    "ar-SA": "العربية",
    "hi-IN": "الهندية",
    "th-TH": "التايلاندية",
    "vi-VN": "الفيتنامية",
    "id-ID": "الإندونيسية",
  },
  "hi-IN": {
    "zh-CN": "चीनी",
    "en-US": "अंग्रेज़ी",
    "ja-JP": "जापानी",
    "ko-KR": "कोरियाई",
    "fr-FR": "फ़्रेंच",
    "es-ES": "स्पेनिश",
    "de-DE": "जर्मन",
    "ru-RU": "रूसी",
    "pt-BR": "पुर्तगाली",
    "it-IT": "इतालवी",
    "nl-NL": "डच",
    "ar-SA": "अरबी",
    "hi-IN": "हिन्दी",
    "th-TH": "थाई",
    "vi-VN": "वियतनामी",
    "id-ID": "इंडोनेशियाई",
  },
  "th-TH": {
    "zh-CN": "ภาษาจีน",
    "en-US": "ภาษาอังกฤษ",
    "ja-JP": "ภาษาญี่ปุ่น",
    "ko-KR": "ภาษาเกาหลี",
    "fr-FR": "ภาษาฝรั่งเศส",
    "es-ES": "ภาษาสเปน",
    "de-DE": "ภาษาเยอรมัน",
    "ru-RU": "ภาษารัสเซีย",
    "pt-BR": "ภาษาโปรตุเกส",
    "it-IT": "ภาษาอิตาลี",
    "nl-NL": "ภาษาดัตช์",
    "ar-SA": "ภาษาอาหรับ",
    "hi-IN": "ภาษาฮินดี",
    "th-TH": "ภาษาไทย",
    "vi-VN": "ภาษาเวียดนาม",
    "id-ID": "ภาษาอินโดนีเซีย",
  },
  "vi-VN": {
    "zh-CN": "Tiếng Trung",
    "en-US": "Tiếng Anh",
    "ja-JP": "Tiếng Nhật",
    "ko-KR": "Tiếng Hàn",
    "fr-FR": "Tiếng Pháp",
    "es-ES": "Tiếng Tây Ban Nha",
    "de-DE": "Tiếng Đức",
    "ru-RU": "Tiếng Nga",
    "pt-BR": "Tiếng Bồ Đào Nha",
    "it-IT": "Tiếng Ý",
    "nl-NL": "Tiếng Hà Lan",
    "ar-SA": "Tiếng Ả Rập",
    "hi-IN": "Tiếng Hindi",
    "th-TH": "Tiếng Thái",
    "vi-VN": "Tiếng Việt",
    "id-ID": "Tiếng Indonesia",
  },
  "id-ID": {
    "zh-CN": "Tionghoa",
    "en-US": "Inggris",
    "ja-JP": "Jepang",
    "ko-KR": "Korea",
    "fr-FR": "Prancis",
    "es-ES": "Spanyol",
    "de-DE": "Jerman",
    "ru-RU": "Rusia",
    "pt-BR": "Portugis",
    "it-IT": "Italia",
    "nl-NL": "Belanda",
    "ar-SA": "Arab",
    "hi-IN": "Hindi",
    "th-TH": "Thai",
    "vi-VN": "Vietnam",
    "id-ID": "Indonesia",
  },
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
  return (key: string, params?: Record<string, string | number>): string => {
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
      let result = value as string;
      // 参数插值
      if (params) {
        for (const [paramKey, paramValue] of Object.entries(params)) {
          result = result.replace(
            new RegExp(`\\{${paramKey}\\}`, "g"),
            String(paramValue),
          );
        }
      }
      return result;
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

    let result = (value as string) || key;
    // 参数插值
    if (params) {
      for (const [paramKey, paramValue] of Object.entries(params)) {
        result = result.replace(
          new RegExp(`\\{${paramKey}\\}`, "g"),
          String(paramValue),
        );
      }
    }
    return result;
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
  // 获取语言在目标语言下的显示名称
  getLanguageName: (
    targetLanguage: Language,
    displayLanguage?: Language,
  ): string => {
    const currentDisplayLang = displayLanguage || getCurrentLanguage();
    return (
      languageNamesTranslations[currentDisplayLang]?.[targetLanguage] ||
      languages[targetLanguage]
    );
  },
};

// 获取当前语言
function getCurrentLanguage(): Language {
  let currentLang: Language = DEFAULT_LANGUAGE;
  languageStore.subscribe((lang) => {
    currentLang = lang;
  })();
  return currentLang;
}
