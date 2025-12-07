<script lang="ts">
  import Card from '$components/ui/Card.svelte';
  import Button from '$components/ui/Button.svelte';
  import { language, tStore, languages, type Language } from '$stores/language';
  import { theme } from '$stores/theme';
  import { toast } from '$stores/toast';
  import { authService } from '$services/auth';
  import { getThemeShortcutsText } from '$lib/config/keyboardShortcuts';

  interface Props {
    show: boolean;
    onClose: () => void;
  }

  let { show, onClose }: Props = $props();

  // 获取翻译函数
  const t = $derived($tStore);

  // 当前活跃的设置标签页
  let activeTab = $state<'general' | 'security'>('general');

  // 语言选择
  let selectedLanguage = $state<Language>($language);

  // 语言选择器增强功能
  let showLanguageDropdown = $state(false);
  let languageSearchQuery = $state('');
  let languageDropdownRef = $state<HTMLDivElement | null>(null);

  // 密码修改
  let currentPassword = $state('');
  let newPassword = $state('');
  let confirmPassword = $state('');
  let changingPassword = $state(false);

  // 密码可见性状态
  let showCurrentPassword = $state(false);
  let showNewPassword = $state(false);
  let showConfirmPassword = $state(false);

  // 主题切换
  let isDarkTheme = $derived($theme === 'dark');

  // 模态框元素引用
  let modalElement: HTMLDivElement | null = $state(null);

  // 监听语言变化
  $effect(() => {
    selectedLanguage = $language;
  });

  // 过滤语言选项 - 使用当前系统语言显示语言名称
  let filteredLanguages = $derived(
    Object.entries(languages).filter(([code, _name]) => {
      const displayName = language.getLanguageName(code as Language);
      return (
        displayName.toLowerCase().includes(languageSearchQuery.toLowerCase()) ||
        code.toLowerCase().includes(languageSearchQuery.toLowerCase())
      );
    })
  );

  // 动态计算下拉框位置（智能方向定位）
  let dropdownPosition = $state({
    top: 0,
    left: 0,
    width: 0,
    direction: 'down' as 'down' | 'up'
  });

  $effect(() => {
    if (showLanguageDropdown && languageDropdownRef) {
      const button = languageDropdownRef.querySelector('.language-button') as HTMLElement;
      if (button) {
        const rect = button.getBoundingClientRect();
        const buttonBottom = rect.bottom + window.scrollY;
        const viewportHeight = window.innerHeight;

        // 预估下拉框高度（搜索框40px + 语言列表280px + 页脚40px + 边框40px = ~400px）
        const estimatedDropdownHeight = 400;

        // 检测是否需要向上显示
        const shouldShowUp = (viewportHeight - buttonBottom) < estimatedDropdownHeight;

        let position;
        if (shouldShowUp) {
          // 显示在按钮上方
          position = {
            top: rect.top + window.scrollY - estimatedDropdownHeight - 8,
            direction: 'up' as const
          };
        } else {
          // 显示在按钮下方（默认行为）
          position = {
            top: buttonBottom + 8,
            direction: 'down' as const
          };
        }

        dropdownPosition = {
          ...position,
          left: rect.left + window.scrollX,
          width: rect.width
        };
      }
    }
  });

  // 点击外部关闭语言下拉框
  function handleLanguageDropdownClickOutside(event: MouseEvent) {
    if (showLanguageDropdown && languageDropdownRef &&
        !languageDropdownRef.contains(event.target as Node)) {
      showLanguageDropdown = false;
      languageSearchQuery = '';
    }
  }

  // 处理键盘事件 (ESC关闭)
  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      closeModal();
    }
  }

  // 焦点管理 - 模态框打开时聚焦到第一个可聚焦元素
  $effect(() => {
    if (show && modalElement) {
      // 延迟聚焦，确保DOM已渲染
      setTimeout(() => {
        const firstFocusable = modalElement?.querySelector<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        firstFocusable?.focus();
      }, 0);
    }
  });

  async function handleLanguageChange(newLanguage: Language) {
    try {
      await language.set(newLanguage);
      toast.success(t('settings.languageUpdated'));
    } catch (error) {
      console.error('Failed to update language:', error);
      toast.error(t('settings.languageUpdateError'));
    }
  }

  function handleThemeToggle() {
    theme.toggle();
  }

  async function handlePasswordChange() {
    if (newPassword !== confirmPassword) {
      toast.error(t('settings.passwordMismatch'));
      return;
    }

    if (newPassword.length < 8) {
      toast.error(t('settings.passwordTooShort'));
      return;
    }

    changingPassword = true;
    try {
      await authService.changePassword(currentPassword, newPassword);
      toast.success(t('settings.passwordChanged'));

      // 清空表单
      currentPassword = '';
      newPassword = '';
      confirmPassword = '';
      activeTab = 'general';
    } catch (error: any) {
      console.error('Failed to change password:', error);
      toast.error(error.message || t('settings.passwordChangeError'));
    } finally {
      changingPassword = false;
    }
  }

  function closeModal() {
    onClose();
  }

  // 添加文档级点击监听
  $effect(() => {
    if (showLanguageDropdown) {
      document.addEventListener('click', handleLanguageDropdownClickOutside);
      return () => {
        document.removeEventListener('click', handleLanguageDropdownClickOutside);
      };
    }
  });
</script>

{#if show}
  <div
    class="modal-overlay"
    role="dialog"
    aria-modal="true"
    aria-label={t('settings.title')}
    tabindex="-1"
    bind:this={modalElement}
    onkeydown={handleKeydown}
    onclick={closeModal}
  >
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <!-- The click and keyboard handlers prevent the modal from closing when clicking inside -->
    <div
      class="modal-content"
      role="document"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <div class="modal-header">
        <h2>{t('settings.title')}</h2>
        <button class="close-button" onclick={closeModal} aria-label={t('common.close')}>
          ×
        </button>
      </div>

      <div class="modal-body">
        <div class="tabs" role="tablist" aria-label={t('settings.tabList')}>
          <button
            class="tab"
            class:active={activeTab === 'general'}
            onclick={() => (activeTab = 'general')}
            role="tab"
            aria-selected={activeTab === 'general'}
            aria-controls="general-tab-panel"
            id="general-tab"
          >
            {t('settings.general')}
          </button>
          <button
            class="tab"
            class:active={activeTab === 'security'}
            onclick={() => (activeTab = 'security')}
            role="tab"
            aria-selected={activeTab === 'security'}
            aria-controls="security-tab-panel"
            id="security-tab"
          >
            {t('settings.security')}
          </button>
        </div>

        <div class="tab-content">
          {#if activeTab === 'general'}
            <Card title={t('settings.generalSettings')} aria-labelledby="general-tab" role="tabpanel" id="general-tab-panel">
              <div class="setting-item">
                <label for="language-select">{t('settings.language')}</label>
                <!-- 增强语言选择器 - 支持搜索和大量选项 -->
                <div class="language-selector" bind:this={languageDropdownRef}>
                  <button
                    id="language-select"
                    class="language-button"
                    onclick={() => showLanguageDropdown = !showLanguageDropdown}
                    aria-haspopup="listbox"
                    aria-expanded={showLanguageDropdown}
                    aria-label={t('settings.language')}
                  >
                    <span class="language-name">{language.getLanguageName(selectedLanguage)}</span>
                    <span class="language-code">{selectedLanguage}</span>
                    <svg
                      class="dropdown-icon"
                      class:rotated={showLanguageDropdown}
                      xmlns="http://www.w3.org/2000/svg"
                      width="16" height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </button>

                  {#if showLanguageDropdown}
                    <!-- 使用portal技术，让下拉框可以超出模态框 -->
                    <div
                      class="language-dropdown-portal-layer"
                      class:direction-up={dropdownPosition.direction === 'up'}
                      style="--dropdown-top: {dropdownPosition.top}px; --dropdown-left: {dropdownPosition.left}px; --dropdown-width: {dropdownPosition.width}px;"
                    >
                      <div class="language-dropdown" role="listbox" aria-label={t('settings.language')}>
                        <!-- 方向指示器 -->
                        <div class="dropdown-arrow {dropdownPosition.direction}"></div>

                        <div class="language-search-container">
                          <input
                            type="text"
                            class="language-search"
                            bind:value={languageSearchQuery}
                            placeholder={t('settings.searchLanguage')}
                            aria-label={t('settings.searchLanguage')}
                          />
                          <svg
                            class="search-icon"
                            xmlns="http://www.w3.org/2000/svg"
                            width="16" height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                          </svg>
                        </div>

                        <div class="language-list">
                          {#if filteredLanguages.length === 0}
                            <div class="no-results">
                              {t('settings.noLanguagesFound')}
                            </div>
                          {:else}
                            {#each filteredLanguages as [code, _name]}
                              <button
                                class="language-option"
                                class:selected={selectedLanguage === code}
                                onclick={() => {
                                  selectedLanguage = code as Language;
                                  handleLanguageChange(code as Language);
                                  showLanguageDropdown = false;
                                  languageSearchQuery = '';
                                }}
                                role="option"
                                aria-selected={selectedLanguage === code}
                              >
                                <span class="language-name">{language.getLanguageName(code as Language)}</span>
                                <span class="language-code">{code}</span>
                                {#if selectedLanguage === code}
                                  <svg
                                    class="check-icon"
                                    xmlns="http://www.w3.org/2000/svg"
                                    width="16" height="16"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    stroke-width="2"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                  >
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                  </svg>
                                {/if}
                              </button>
                            {/each}
                          {/if}
                        </div>

                        <div class="language-footer">
                          <span class="language-count">
                            {filteredLanguages.length} / {Object.keys(languages).length} {t('settings.languages')}
                          </span>
                        </div>
                      </div>
                    </div>
                  {/if}
                </div>
              </div>

              <div class="setting-item">
                <label for="theme-toggle">{t('settings.theme')}</label>
                <button
                  id="theme-toggle"
                  class="theme-toggle-button"
                  onclick={handleThemeToggle}
                  aria-label={t('common.toggleTheme')}
                >
                  {#if isDarkTheme}
                    <span class="theme-icon">☀️</span>
                    <span class="theme-text">{t('settings.lightMode')}</span>
                  {:else}
                    <span class="theme-icon">🌙</span>
                    <span class="theme-text">{t('settings.darkMode')}</span>
                  {/if}
                </button>
                <span class="help-text">{t('settings.themeHelp')}</span>
                <span class="shortcut-hint">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                    <path d="M2 17l10 5 10-5M2 12l10 5 10-5"></path>
                  </svg>
                  <span class="shortcut-text">
                    <span class="shortcut-list">
                      {#each getThemeShortcutsText() as shortcut, index}
                        <span class="shortcut-item">
                          <strong>{shortcut}</strong>
                        </span>
                        {#if index < getThemeShortcutsText().length - 1}
                          <span class="shortcut-separator">or</span>
                        {/if}
                      {/each}
                    </span>
                    <span class="shortcut-desc">{t('settings.toggleThemeShortcut')}</span>
                  </span>
                </span>
              </div>
            </Card>
          {:else if activeTab === 'security'}
            <Card title={t('settings.changePassword')} aria-labelledby="security-tab" role="tabpanel" id="security-tab-panel">
              <div class="form-group">
                <label for="current-password">{t('settings.currentPassword')}</label>
                <div class="password-field">
                  <input
                    id="current-password"
                    type={showCurrentPassword ? 'text' : 'password'}
                    bind:value={currentPassword}
                    placeholder={t('settings.enterCurrentPassword')}
                    class="password-input-field"
                    aria-label={t('settings.currentPassword')}
                  />
                  <button
                    type="button"
                    class="password-visibility-toggle"
                    onclick={() => showCurrentPassword = !showCurrentPassword}
                    aria-label={showCurrentPassword ? t('settings.hidePassword') : t('settings.showPassword')}
                  >
                    {#if showCurrentPassword}
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                      </svg>
                    {:else}
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                    {/if}
                  </button>
                </div>
              </div>

              <div class="form-group">
                <label for="new-password">{t('settings.newPassword')}</label>
                <div class="password-field">
                  <input
                    id="new-password"
                    type={showNewPassword ? 'text' : 'password'}
                    bind:value={newPassword}
                    placeholder={t('settings.enterNewPassword')}
                    class="password-input-field"
                    aria-label={t('settings.newPassword')}
                    aria-describedby="new-password-help"
                  />
                  <button
                    type="button"
                    class="password-visibility-toggle"
                    onclick={() => showNewPassword = !showNewPassword}
                    aria-label={showNewPassword ? t('settings.hidePassword') : t('settings.showPassword')}
                  >
                    {#if showNewPassword}
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                      </svg>
                    {:else}
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                    {/if}
                  </button>
                </div>
                <span id="new-password-help" class="help-text">{t('settings.passwordMinLength')}</span>
              </div>

              <div class="form-group">
                <label for="confirm-password">{t('settings.confirmNewPassword')}</label>
                <div class="password-field">
                  <input
                    id="confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    bind:value={confirmPassword}
                    placeholder={t('settings.confirmNewPassword')}
                    class="password-input-field"
                    aria-label={t('settings.confirmNewPassword')}
                  />
                  <button
                    type="button"
                    class="password-visibility-toggle"
                    onclick={() => showConfirmPassword = !showConfirmPassword}
                    aria-label={showConfirmPassword ? t('settings.hidePassword') : t('settings.showPassword')}
                  >
                    {#if showConfirmPassword}
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                      </svg>
                    {:else}
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                    {/if}
                  </button>
                </div>
              </div>

              <Button
                variant="primary"
                on:click={handlePasswordChange}
                disabled={changingPassword || !currentPassword || !newPassword || !confirmPassword}
              >
                {changingPassword ? t('common.loading') : t('settings.changePassword')}
              </Button>
            </Card>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
  }

  .modal-content {
    background: var(--bg-primary, white);
    border-radius: 0.75rem;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1),
      0 10px 10px -5px rgba(0, 0, 0, 0.04);
    max-width: 700px;
    width: 100%;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.5rem;
    border-bottom: 1px solid var(--border-color, #e5e7eb);
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .close-button {
    background: transparent;
    border: none;
    font-size: 2rem;
    line-height: 1;
    cursor: pointer;
    color: var(--text-secondary, #6b7280);
    padding: 0;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.375rem;
    transition: all 0.2s;
  }

  .close-button:hover {
    background: var(--bg-tertiary, #f3f4f6);
    color: var(--text-primary, #1a1a1a);
  }

  .modal-body {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    max-height: calc(90vh - 5rem);
  }

  .tabs {
    display: flex;
    gap: 0.5rem;
    padding: 1rem 1.5rem 0;
    border-bottom: 1px solid var(--border-color, #e5e7eb);
    overflow-x: auto;
  }

  .tab {
    padding: 0.75rem 1.5rem;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary, #6b7280);
    white-space: nowrap;
    transition: all 0.2s;
  }

  .tab:hover {
    color: var(--primary-color, #3b82f6);
  }

  .tab.active {
    color: var(--primary-color, #3b82f6);
    border-bottom-color: var(--primary-color, #3b82f6);
  }

  .tab-content {
    padding: 1.5rem;
    overflow-y: auto;
    flex: 1;
  }

  .setting-item {
    margin-bottom: 1.5rem;
  }

  .setting-item:last-child {
    margin-bottom: 0;
  }

  .setting-item label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
  }

  /* 增强语言选择器样式 */
  .language-selector {
    position: relative;
    width: 100%;
  }

  .language-button {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border: 1px solid var(--border-color, #d1d5db);
    border-radius: 0.375rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #1a1a1a);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
  }

  .language-button:hover {
    border-color: var(--primary-color, #3b82f6);
    background: var(--bg-secondary, #f9fafb);
  }

  .language-button:focus {
    outline: none;
    border-color: var(--primary-color, #3b82f6);
    box-shadow: 0 0 0 3px rgba(var(--primary-color-rgb), 0.1);
  }

  .language-name {
    flex: 1;
    font-weight: 500;
  }

  .language-code {
    font-size: 0.75rem;
    color: var(--text-secondary, #6b7280);
    font-family: "Courier New", monospace;
    padding: 0.125rem 0.5rem;
    background: var(--bg-tertiary, #f3f4f6);
    border-radius: 0.25rem;
  }

  .dropdown-icon {
    transition: transform 0.2s;
    color: var(--text-secondary, #6b7280);
  }

  .dropdown-icon.rotated {
    transform: rotate(180deg);
  }

  /* 使用Portal技术，让下拉框超出模态框边界 */
  .language-dropdown-portal-layer {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 9998;
    pointer-events: none;
  }

  .language-dropdown-portal-layer .language-dropdown {
    position: fixed;
    pointer-events: auto;
    /* 使用CSS变量动态计算位置 */
    top: var(--dropdown-top, 0);
    left: var(--dropdown-left, 0);
    width: var(--dropdown-width);
    background: var(--bg-primary, white);
    border: 1px solid var(--border-color, #d1d5db);
    border-radius: 0.5rem;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    max-height: 400px;
    display: flex;
    flex-direction: column;
    animation: dropdownFade 0.15s ease-out;
  }

  /* 向下显示（默认） */
  .language-dropdown-portal-layer:not(.direction-up) .language-dropdown {
    margin-top: 0.5rem;
  }

  /* 向上显示 */
  .language-dropdown-portal-layer.direction-up .language-dropdown {
    margin-bottom: 0.5rem;
  }

  /* Portal 下拉框内部所有元素的样式 - 使用 :global() 穿透作用域 */
  :global(.language-dropdown-portal-layer .language-dropdown) .language-search-container {
    position: relative;
    padding: 0.75rem;
    border-bottom: 1px solid var(--border-color, #d1d5db);
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-search {
    width: 100%;
    padding: 0.5rem 2.5rem 0.5rem 0.75rem;
    border: 1px solid var(--border-color, #d1d5db);
    border-radius: 0.375rem;
    background: var(--bg-secondary, #f9fafb);
    color: var(--text-primary, #1a1a1a);
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-search:focus {
    outline: none;
    border-color: var(--primary-color, #3b82f6);
    background: var(--bg-primary, white);
    box-shadow: 0 0 0 3px rgba(var(--primary-color-rgb), 0.1);
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .search-icon {
    position: absolute;
    right: 1.25rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-secondary, #6b7280);
    pointer-events: none;
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-list {
    flex: 1;
    overflow-y: auto;
    max-height: 280px;
    padding: 0.5rem 0;
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-option {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.625rem 1rem;
    border: none;
    background: transparent;
    color: var(--text-primary, #1a1a1a);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.15s;
    text-align: left;
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-option:hover {
    background: var(--bg-secondary, #f9fafb);
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-option.selected {
    background: rgba(var(--primary-color-rgb), 0.1);
    color: var(--primary-color, #3b82f6);
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-option.selected .language-code {
    background: rgba(var(--primary-color-rgb), 0.15);
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-name {
    flex: 1;
    font-weight: 500;
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-code {
    font-size: 0.75rem;
    color: var(--text-secondary, #6b7280);
    font-family: "Courier New", monospace;
    padding: 0.125rem 0.5rem;
    background: var(--bg-tertiary, #f3f4f6);
    border-radius: 0.25rem;
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .check-icon {
    margin-left: auto;
    flex-shrink: 0;
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-footer {
    padding: 0.5rem 1rem;
    border-top: 1px solid var(--border-color, #d1d5db);
    background: var(--bg-tertiary, #f9fafb);
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .language-count {
    font-size: 0.75rem;
    color: var(--text-secondary, #6b7280);
  }

  :global(.language-dropdown-portal-layer .language-dropdown) .no-results {
    padding: 2rem 1rem;
    text-align: center;
    color: var(--text-secondary, #6b7280);
    font-size: 0.875rem;
  }

  /* 向下动画 */
  @keyframes dropdownFadeDown {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* 向上动画 */
  @keyframes dropdownFadeUp {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* 应用不同的动画方向 */
  .language-dropdown-portal-layer:not(.direction-up) .language-dropdown {
    animation: dropdownFadeDown 0.15s ease-out;
  }

  .language-dropdown-portal-layer.direction-up .language-dropdown {
    animation: dropdownFadeUp 0.15s ease-out;
  }

  /* 方向指示器箭头 */
  .dropdown-arrow {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    z-index: 1;
  }

  /* 向下箭头 - 在下拉框顶部 */
  .language-dropdown-portal-layer:not(.direction-up) .dropdown-arrow.down {
    top: -8px;
    border-bottom: 8px solid var(--border-color, #d1d5db);
  }

  .language-dropdown-portal-layer:not(.direction-up) .dropdown-arrow.down::after {
    content: '';
    position: absolute;
    top: 1px;
    left: -8px;
    width: 0;
    height: 0;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-bottom: 8px solid var(--bg-primary, white);
  }

  /* 向上箭头 - 在下拉框底部 */
  .language-dropdown-portal-layer.direction-up .dropdown-arrow.up {
    bottom: -8px;
    border-top: 8px solid var(--border-color, #d1d5db);
  }

  .language-dropdown-portal-layer.direction-up .dropdown-arrow.up::after {
    content: '';
    position: absolute;
    bottom: 1px;
    left: -8px;
    width: 0;
    height: 0;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-top: 8px solid var(--bg-primary, white);
  }

  .language-search-container {
    position: relative;
    padding: 0.75rem;
    border-bottom: 1px solid var(--border-color, #d1d5db);
  }

  .language-search {
    width: 100%;
    padding: 0.5rem 2.5rem 0.5rem 0.75rem;
    border: 1px solid var(--border-color, #d1d5db);
    border-radius: 0.375rem;
    background: var(--bg-secondary, #f9fafb);
    color: var(--text-primary, #1a1a1a);
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .language-search:focus {
    outline: none;
    border-color: var(--primary-color, #3b82f6);
    background: var(--bg-primary, white);
    box-shadow: 0 0 0 3px rgba(var(--primary-color-rgb), 0.1);
  }

  .search-icon {
    position: absolute;
    right: 1.25rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-secondary, #6b7280);
    pointer-events: none;
  }

  .language-list {
    flex: 1;
    overflow-y: auto;
    max-height: 280px;
    padding: 0.5rem 0;
  }

  .language-option {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.625rem 1rem;
    border: none;
    background: transparent;
    color: var(--text-primary, #1a1a1a);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.15s;
    text-align: left;
  }

  .language-option:hover {
    background: var(--bg-secondary, #f9fafb);
  }

  .language-option.selected {
    background: rgba(var(--primary-color-rgb), 0.1);
    color: var(--primary-color, #3b82f6);
  }

  .language-option.selected .language-code {
    background: rgba(var(--primary-color-rgb), 0.15);
  }

  .check-icon {
    margin-left: auto;
    flex-shrink: 0;
  }

  .language-footer {
    padding: 0.5rem 1rem;
    border-top: 1px solid var(--border-color, #d1d5db);
    background: var(--bg-tertiary, #f9fafb);
  }

  .language-count {
    font-size: 0.75rem;
    color: var(--text-secondary, #6b7280);
  }

  .no-results {
    padding: 2rem 1rem;
    text-align: center;
    color: var(--text-secondary, #6b7280);
    font-size: 0.875rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
    font-size: 0.875rem;
  }

  .help-text {
    display: block;
    margin-top: 0.5rem;
    font-size: 0.8125rem;
    color: var(--text-secondary, #6b7280);
  }

  .theme-toggle-button {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    border: 1px solid var(--border-color, #d1d5db);
    border-radius: 0.5rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #1a1a1a);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
    min-height: 2.75rem;
  }

  .theme-toggle-button:hover {
    background: var(--bg-secondary, #f9fafb);
    border-color: var(--primary-color, #3b82f6);
    transform: translateY(-1px);
  }

  .theme-icon {
    font-size: 1.25rem;
    line-height: 1;
  }

  .theme-text {
    font-weight: 500;
  }

  .shortcut-hint {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
    padding: 0.5rem;
    background: var(--bg-tertiary, #f3f4f6);
    border-radius: 0.375rem;
    color: var(--text-secondary, #6b7280);
    font-size: 0.8125rem;
  }

  .shortcut-hint svg {
    flex-shrink: 0;
    opacity: 0.6;
  }

  .shortcut-text {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .shortcut-list {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .shortcut-item strong {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.5rem;
    height: 1.5rem;
    padding: 0 0.375rem;
    background: var(--bg-secondary, #e5e7eb);
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-primary, #374151);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  .shortcut-separator {
    color: var(--text-secondary, #9ca3af);
    font-size: 0.75rem;
    font-weight: 500;
  }

  .shortcut-desc {
    color: var(--text-secondary, #6b7280);
    font-size: 0.75rem;
  }

  @media (max-width: 640px) {
    .shortcut-hint {
      font-size: 0.75rem;
    }

    .shortcut-desc {
      display: block;
      width: 100%;
      margin-left: 0;
      margin-top: 0.25rem;
    }
  }

  /* 密码输入框样式 */
  .password-field {
    position: relative;
    display: flex;
    align-items: center;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    transition: all 0.2s ease;
  }

  .password-field:focus-within {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(var(--primary-color-rgb), 0.1);
  }

  .password-input-field {
    flex: 1;
    padding: 0.75rem 3rem 0.75rem 1rem;
    border: none;
    background: transparent;
    color: var(--text-primary);
    font-size: 1rem;
    font-family: inherit;
    outline: none;
  }

  .password-input-field::placeholder {
    color: var(--text-secondary);
    opacity: 0.7;
  }

  .password-visibility-toggle {
    position: absolute;
    right: 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.375rem;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    border-radius: 0.375rem;
    opacity: 0.7;
  }

  .password-visibility-toggle:hover {
    opacity: 1;
    color: var(--text-primary);
    background: var(--bg-secondary);
  }

  .password-visibility-toggle:active {
    transform: scale(0.95);
  }

  .password-visibility-toggle:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .password-visibility-toggle svg {
    display: block;
    transition: all 0.2s;
  }

  @media (max-width: 640px) {
    .modal-content {
      max-height: 95vh;
    }

    .modal-header {
      padding: 1rem;
    }

    .modal-header h2 {
      font-size: 1.25rem;
    }

    .tabs {
      padding: 0.75rem 1rem 0;
    }

    .tab {
      padding: 0.5rem 1rem;
      font-size: 0.8125rem;
    }

    .tab-content {
      padding: 1rem;
    }
  }
</style>
