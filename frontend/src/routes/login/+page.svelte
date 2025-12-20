<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import Card from '$components/ui/Card.svelte';
  import Input from '$components/ui/Input.svelte';
  import Button from '$components/ui/Button.svelte';
  import { authService } from '$services/auth';
  import { toast } from '$stores/toast';
  import { tStore } from '$stores/language';

  // 获取翻译函数
  const t = $derived($tStore);

  let email = $state('');
  let password = $state('');
  let loading = $state(false);
  let showPassword = $state(false);

  // 如果已经登录，重定向到首页
  onMount(() => {
    if (browser && authService.isAuthenticated()) {
      goto('/');
    }
  });

  async function handleSubmit() {
    if (!email || !password) {
      toast.error(t('login.enterEmailPassword'));
      return;
    }

    loading = true;
    try {
      await authService.login(email, password);
      console.log('[Login] Login successful, token stored');

      // 验证 token 已存储
      if (browser) {
        const token = localStorage.getItem('auth_token');
        if (!token) {
          console.error('[Login] Token not found in localStorage after login!');
          toast.error(t('login.loginFailed'));
          return;
        }
        console.log('[Login] Token verified in localStorage');
      }

      toast.success(t('login.loginSuccess'));

      // 等待一小段时间确保 localStorage 写入完成
      await new Promise(resolve => setTimeout(resolve, 100));

      // 登录成功后跳转到首页，欢迎弹窗会在首页显示
      console.log('[Login] Redirecting to home page');
      await goto('/');
    } catch (error) {
      const message = error instanceof Error ? error.message : t('login.checkCredentials');
      toast.error(message);
    } finally {
      loading = false;
    }
  }

</script>

<div class="login-container">
  <div class="login-card">
    {#snippet title()}
      <h1 class="login-title">Anthropic OpenAI Bridge</h1>
      <p class="login-subtitle">{t('login.subtitle')}</p>
    {/snippet}

    <Card titleSlot={title}>
      <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="login-form">
        <div class="form-group">
          <label for="email">{t('login.email')}</label>
          <Input
            id="email"
            type="email"
            bind:value={email}
            placeholder={t('login.placeholderEmail')}
            required
            disabled={loading}
          />
        </div>

        <div class="form-group">
          <label for="password">{t('login.password')}</label>
          <div class="password-input-wrapper">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              bind:value={password}
              placeholder={t('login.placeholderPassword')}
              required
              disabled={loading}
              oninput={() => {}}
            />
            <button
              type="button"
              class="toggle-password"
              onclick={() => showPassword = !showPassword}
              disabled={loading}
              aria-label={showPassword ? t('login.togglePasswordHide') : t('login.togglePasswordShow')}
            >
              {#if showPassword}
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              {:else}
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              {/if}
            </button>
          </div>
        </div>

        <div class="form-actions">
          <Button
            type="submit"
            variant="primary"
            size="lg"
            disabled={loading}
            class="login-button"
          >
            {loading ? t('login.loggingIn') : t('login.login')}
          </Button>
        </div>
      </form>

      <div class="login-info">
        <p class="info-title">{t('login.defaultAdminTitle')}</p>
        <div class="info-content">
          <p><strong>{t('login.defaultEmail')}</strong>admin@example.com</p>
          <p><strong>{t('login.defaultPassword')}</strong>admin123</p>
        </div>
        <p class="info-note">{t('login.warnChangePassword')}</p>
      </div>
    </Card>
  </div>
</div>

<style>
  .login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    background: var(--bg-secondary, #f5f5f5);
  }

  .login-card {
    width: 100%;
    max-width: 450px;
  }

  .login-title {
    margin: 0 0 0.5rem 0;
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
    text-align: center;
  }

  .login-subtitle {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
    text-align: center;
  }

  .login-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    margin-top: 2rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
  }

  .password-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .password-input-wrapper :global(.input) {
    padding-right: 3rem;
  }

  .toggle-password {
    position: absolute;
    right: 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.25rem;
    color: var(--text-secondary, #6c757d);
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.25rem;
    transition: all 0.2s;
  }

  .toggle-password:hover:not(:disabled) {
    color: var(--text-primary, #495057);
    background: rgba(0, 0, 0, 0.05);
  }

  .toggle-password:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .toggle-password svg {
    width: 1.25rem;
    height: 1.25rem;
  }

  .form-actions {
    margin-top: 0.5rem;
  }

  .login-info {
    margin-top: 2rem;
    padding: 1.5rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
    border-left: 4px solid #007bff;
  }

  .info-title {
    margin: 0 0 1rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .info-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .info-content p {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  }

  .info-content strong {
    color: var(--text-primary, #1a1a1a);
  }

  .info-note {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--warning-color, #856404);
    font-weight: 500;
  }

  :global([data-theme="dark"]) .info-note {
    color: #d29922;
  }

  @media (max-width: 480px) {
    .login-container {
      padding: 1rem;
    }

    .login-title {
      font-size: 1.5rem;
    }
  }
</style>
