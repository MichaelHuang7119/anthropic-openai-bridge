<script lang="ts">
  import { tStore, language } from '$stores/language';

  let { key, params = {} }: { key: string; params?: Record<string, string | number> } = $props();

  // 响应式依赖 - 监听语言变化
  const _lang = $language;

  // 获取翻译函数 - 使用 $tStore 自动订阅
  const tFunc = $derived($tStore);

  // 获取翻译文本
  const translated = $derived.by(() => {
    let text = tFunc ? tFunc(key) : key;

    // 替换参数（如 "Hello {name}"）
    Object.keys(params).forEach((paramKey) => {
      text = text.replace(
        new RegExp(`{${paramKey}}`, 'g'),
        String(params[paramKey])
      );
    });

    return text;
  });
</script>

{translated}
