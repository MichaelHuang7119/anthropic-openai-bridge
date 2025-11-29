<script lang="ts">
  import { theme } from '$stores/theme';
  import { language, tStore, languages, type Language } from '$stores/language';
  import { authService } from '$services/auth';
  import { onMount } from 'svelte';

  let { title = 'Anthropic OpenAI Bridge', subtitle = '', nav } = $props<{
    title?: string;
    subtitle?: string;
    nav?: () => any;
  }>();

  // 语言下拉菜单状态
  let showLanguageMenu = $state(false);

  // 下拉菜单容器引用
  let languageDropdownRef = $state<HTMLDivElement | null>(null);

  // 获取翻译函数（响应式）
  const t = $derived($tStore);

  function toggleTheme() {
    theme.toggle();
  }

  function selectLanguage(lang: Language) {
    language.set(lang);
    showLanguageMenu = false;
  }

  function handleLogout() {
    const message = t('common.logoutConfirm');
    if (confirm(message)) {
      authService.logout();
    }
  }

  // 点击外部关闭下拉菜单
  function handleClickOutside(event: MouseEvent) {
    if (showLanguageMenu && languageDropdownRef && !languageDropdownRef.contains(event.target as Node)) {
      showLanguageMenu = false;
    }
  }

  // 添加和移除文档级点击监听器
  onMount(() => {
    document.addEventListener('click', handleClickOutside);

    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  });
</script>

<header class="header">
  <div class="container">
    <div class="brand">
      <img src="/favicon.svg" alt="Anthropic OpenAI Bridge Logo" class="brand-icon" />
      <div class="brand-text">
        <h1>{title}</h1>
        {#if subtitle}
          <p class="subtitle">{subtitle}</p>
        {/if}
      </div>
    </div>
    <div class="header-actions">
      {#if nav}
        <nav class="nav">
          {@render nav()}
        </nav>
      {/if}
      <div class="language-selector" bind:this={languageDropdownRef}>
        <button
          class="language-toggle"
          onclick={() => showLanguageMenu = !showLanguageMenu}
          aria-label={t('common.toggleLanguage')}
          aria-expanded={showLanguageMenu}
          aria-haspopup="true"
        >
          <span class="language-text">
            {languages[$language]}
          </span>
          <span class="dropdown-arrow">▼</span>
        </button>

        {#if showLanguageMenu}
          <div class="language-dropdown" role="menu">
            {#each Object.entries(languages) as [code, name]}
              <button
                class="language-option"
                class:active={$language === code}
                onclick={() => selectLanguage(code as Language)}
                role="menuitem"
              >
                {name}
              </button>
            {/each}
          </div>
        {/if}
      </div>
      <button class="theme-toggle" onclick={toggleTheme} aria-label={t('common.toggleTheme')}>
        {#if $theme === 'dark'}
          <span class="theme-icon">☀️</span>
        {:else}
          <span class="theme-icon">🌙</span>
        {/if}
      </button>
      <button class="logout-button" onclick={handleLogout} aria-label={t('header.logout')}>
        {t('header.logout')}
      </button>
    </div>
  </div>
</header>

<style>
  .header {
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
    padding: 1rem 0;
    box-shadow: 0 2px 4px var(--card-shadow);
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .brand-icon {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .brand-text h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 350px;
  }

  @media (max-width: 1200px) {
    .brand-text h1 {
      max-width: 250px;
      font-size: 1.25rem;
    }
  }

  @media (max-width: 768px) {
    .brand-text h1 {
      max-width: 180px;
      font-size: 1.1rem;
    }
  }

  .subtitle {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .nav {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: nowrap;
  }

  /* 响应式调整 - 在较小屏幕上缩小间距 */
  @media (max-width: 1024px) {
    .nav {
      gap: 0.5rem;
    }
  }

  .theme-toggle {
    padding: 0.5rem;
    border-radius: 0.375rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 2.5rem;
    height: 2.5rem;
    transition: all 0.2s;
    background: transparent;
    border: none;
  }

  .theme-toggle:hover {
    background: rgba(127, 127, 127, 0.1);
    transform: scale(1.05);
  }

  :global([data-theme="dark"]) .theme-toggle:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .theme-icon {
    font-size: 1.25rem;
    line-height: 1;
  }

  .language-selector {
    position: relative;
  }

  .language-toggle {
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s;
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    min-width: 6.5rem;
    height: 2.5rem;
  }

  .language-toggle:hover {
    background: var(--bg-secondary);
    transform: scale(1.05);
  }

  .language-text {
    font-size: 0.875rem;
    font-weight: 500;
  }

  .dropdown-arrow {
    font-size: 0.625rem;
    transition: transform 0.2s;
  }

  :global([data-theme="dark"]) .language-toggle:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .language-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 0.5rem;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    box-shadow: 0 4px 12px var(--card-shadow);
    min-width: 9rem;
    max-width: 12rem;
    overflow-y: auto;
    max-height: 17.5rem; /* 显示5个选项 */
    z-index: 1000;
    scrollbar-width: thin;
    scrollbar-color: var(--border-color) transparent;
  }

  .language-dropdown::-webkit-scrollbar {
    width: 6px;
  }

  .language-dropdown::-webkit-scrollbar-track {
    background: transparent;
  }

  .language-dropdown::-webkit-scrollbar-thumb {
    background-color: var(--border-color);
    border-radius: 3px;
  }

  .language-dropdown::-webkit-scrollbar-thumb:hover {
    background-color: var(--text-secondary);
  }

  .language-option {
    display: block;
    width: 100%;
    padding: 0.75rem 1rem;
    text-align: left;
    background: none;
    border: none;
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.875rem;
    transition: background 0.15s;
    flex-shrink: 0;
  }

  .language-option:hover {
    background: var(--bg-secondary);
  }

  .language-option.active {
    background: var(--bg-tertiary);
    color: var(--primary-color);
    font-weight: 600;
  }

  .language-option + .language-option {
    border-top: 1px solid var(--border-color);
  }

  .logout-button {
    background: var(--danger-color);
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .logout-button:hover {
    background: var(--danger-color-dark, #c82333);
    transform: scale(1.05);
  }

  @media (max-width: 768px) {
    .container {
      padding: 0 1rem;
      flex-wrap: wrap;
    }

    .brand-icon {
      width: 32px;
      height: 32px;
    }

    .brand-text h1 {
      font-size: 1.25rem;
    }

    .subtitle {
      font-size: 0.8125rem;
    }

    .nav {
      gap: 0.5rem;
      order: 3;
      width: 100%;
      overflow-x: auto;
      padding: 0.5rem 0;
    }

    .header-actions {
      flex-wrap: wrap;
    }
  }

  @media (max-width: 480px) {
    .brand-icon {
      width: 28px;
      height: 28px;
    }

    .brand-text h1 {
      font-size: 1.125rem;
    }

    .language-toggle {
      min-width: 5.5rem;
      height: 2.25rem;
      padding: 0.375rem 0.75rem;
    }

    .language-dropdown {
      right: 0;
      min-width: 8rem;
      max-width: 11rem;
    }

    .theme-toggle {
      min-width: 2.25rem;
      height: 2.25rem;
      padding: 0.375rem;
    }

    .theme-icon {
      font-size: 1.125rem;
    }
  }
</style>