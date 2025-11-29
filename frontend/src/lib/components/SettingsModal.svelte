<script lang="ts">
  import Card from '$components/ui/Card.svelte';
  import Button from '$components/ui/Button.svelte';
  import { language, tStore, languages, type Language } from '$stores/language';
  import { theme } from '$stores/theme';
  import { toast } from '$stores/toast';
  import { authService } from '$services/auth';

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
                <select
                  id="language-select"
                  bind:value={selectedLanguage}
                  onchange={(e) => handleLanguageChange((e.target as HTMLSelectElement).value as Language)}
                  class="setting-select"
                  aria-label={t('settings.language')}
                >
                  {#each Object.entries(languages) as [code, name]}
                    <option value={code}>{name}</option>
                  {/each}
                </select>
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

  .setting-select {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--border-color, #d1d5db);
    border-radius: 0.375rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #1a1a1a);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .setting-select:focus {
    outline: none;
    border-color: var(--primary-color, #3b82f6);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
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
