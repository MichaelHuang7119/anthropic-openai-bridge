<script lang="ts">
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import Card from '$components/ui/Card.svelte';
  import Button from '$components/ui/Button.svelte';
  import { configService } from '$services/config';
  import { toast } from '$stores/toast';
  import type { GlobalConfig } from '$types/config';
  import { tStore } from '$stores/language';
  import { authService } from '$services/auth';

  let loading = $state(true);
  let hasPermission = $state(true);
  let saving = $state(false);
  let config: GlobalConfig = $state({
    fallback_strategy: 'priority',
    circuit_breaker: {
      failure_threshold: 5,
      recovery_timeout: 60
    },
    retry_on_zero_output_tokens: true,
    retry_on_zero_output_tokens_retries: 3
  });

  // 获取翻译函数
  const t = $derived($tStore);

  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;

  onMount(async () => {
    // 检查权限
    if (!authService.hasPermission('config')) {
      hasPermission = false;
      loading = false;
      toast.error(t('common.accessDenied'));
      // 延迟跳转，让用户看到 toast
      setTimeout(() => goto('/chat'), 1000);
      return;
    }

    abortController = new AbortController();
    try {
      await loadConfig();
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      throw error;
    }
  });

  onDestroy(() => {
    // 取消所有进行中的请求
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
  });

  async function loadConfig() {
    if (!abortController) return;
    loading = true;
    try {
      config = await configService.get({ signal: abortController.signal });
      
      // 检查是否已被取消
      if (abortController.signal.aborted) return;
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load config:', error);
      toast.error(t('config.loadFailed'));
    } finally {
      if (!abortController?.signal.aborted) {
        loading = false;
      }
    }
  }

  async function handleSave() {
    saving = true;
    try {
      await configService.update(config);
      toast.success(t('config.saved'));
    } catch (error) {
      console.error('Failed to save config:', error);
      toast.error(t('config.error') + ': ' + (error as Error).message);
    } finally {
      saving = false;
    }
  }

  function handleReset() {
    if (!confirm(t('config.confirmResetConfig'))) {
      return;
    }
    loadConfig();
  }
</script>

<div class="container">
  <div class="page-header">
    <div class="actions">
      <Button variant="secondary" onclick={handleReset} disabled={loading || saving} title={t('config.resetConfig')} class="icon-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"></polyline>
          <polyline points="1 20 1 14 7 14"></polyline>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
        </svg>
      </Button>
      <Button variant="primary" onclick={handleSave} disabled={loading || saving} title={saving ? t('config.saving') : t('config.save')} class="icon-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
          <polyline points="17 21 17 13 7 13 7 21"></polyline>
          <polyline points="7 3 7 8 15 8"></polyline>
        </svg>
      </Button>
    </div>
  </div>

  {#if !hasPermission}
    <div class="access-denied">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
      </svg>
      <p>{t('common.accessDenied')}</p>
      <p class="redirect-hint">{t('common.redirecting')}</p>
    </div>
  {:else if loading}
    <div class="loading">
      <p>{t('config.loading')}</p>
    </div>
  {:else}
    <div class="config-grid">
      <Card title={t('config.fallbackStrategy')}>
        <div class="form-section">
          <div class="form-group">
            <label for="fallback-strategy">{t('config.fallbackStrategy')}:</label>
            <select
              id="fallback-strategy"
              bind:value={config.fallback_strategy}
              class="form-control"
            >
              <option value="priority">{t('config.priorityOption')}</option>
              <option value="random">{t('config.randomOption')}</option>
            </select>
            <p class="help-text">{t('config.fallbackStrategyDesc')}</p>
          </div>
        </div>
      </Card>

      <Card title={t('config.circuitBreaker')}>
        <div class="form-section">
          <div class="form-group">
            <label for="failure-threshold">{t('config.failureThreshold')}:</label>
            <input
              id="failure-threshold"
              type="number"
              min="1"
              max="20"
              bind:value={config.circuit_breaker.failure_threshold}
              class="form-control"
            />
            <p class="help-text">{t('config.failureThresholdHelp')}</p>
          </div>

          <div class="form-group">
            <label for="recovery-timeout">{t('config.recoveryTimeout')}:</label>
            <input
              id="recovery-timeout"
              type="number"
              min="10"
              max="600"
              bind:value={config.circuit_breaker.recovery_timeout}
              class="form-control"
            />
            <p class="help-text">{t('config.recoveryTimeoutHelp')}</p>
          </div>
        </div>
      </Card>

      <Card title={t('config.advancedSettings')}>
        <div class="form-section">
          <div class="form-group toggle-group">
            <div class="toggle-label">
              <label for="retry-zero-output">{t('config.retryOnZeroOutput')}</label>
              <p class="help-text">{t('config.retryOnZeroOutputDesc')}</p>
            </div>
            <label class="toggle-switch">
              <input
                type="checkbox"
                id="retry-zero-output"
                bind:checked={config.retry_on_zero_output_tokens}
              />
              <span class="toggle-slider"></span>
            </label>
          </div>

          {#if config.retry_on_zero_output_tokens}
            <div class="form-group">
              <label for="retry-zero-output-retries">{t('config.retryOnZeroOutputRetries')}:</label>
              <input
                id="retry-zero-output-retries"
                type="number"
                min="1"
                max="10"
                bind:value={config.retry_on_zero_output_tokens_retries}
                class="form-control"
              />
              <p class="help-text">{t('config.retryOnZeroOutputRetriesDesc')}</p>
            </div>
          {/if}
        </div>
      </Card>
    </div>
  {/if}
</div>

<style>
  .page-header {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-bottom: 2rem;
  }

  .actions {
    display: flex;
    gap: 1rem;
  }

  .access-denied {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    text-align: center;
    color: var(--text-secondary);
  }

  .access-denied svg {
    color: var(--danger-color, #dc3545);
    margin-bottom: 1rem;
  }

  .access-denied p {
    margin: 0;
    font-size: 1.25rem;
  }

  .access-denied .redirect-hint {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-top: 0.5rem;
  }

  .config-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
  }

  .form-section {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .form-group {
    margin-bottom: 0;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
  }

  .form-control {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--input-border, var(--border-color, #ddd));
    border-radius: 0.25rem;
    font-size: 1rem;
    transition: border-color 0.2s, background-color 0.2s, color 0.2s;
    background: var(--input-bg, var(--bg-primary, white));
    color: var(--text-primary, #1a1a1a);
  }

  .form-control:focus {
    outline: none;
    border-color: var(--input-border-focus, var(--primary-color, #007bff));
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
  }

  :global([data-theme="dark"]) .form-control:focus {
    box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.3);
  }

  /* 修复 select 下拉选项的白色背景闪跳问题 */
  .form-control option {
    background: var(--input-bg, var(--bg-primary, white));
    color: var(--text-primary, #1a1a1a);
  }

  :global([data-theme="dark"]) .form-control option {
    background: #0d1117;
    color: #c9d1d9;
  }

  .help-text {
    margin: 0.5rem 0 0 0;
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
  }

  .loading {
    text-align: center;
    padding: 3rem;
    color: var(--text-secondary, #666);
  }

  .loading p {
    margin: 0;
    font-size: 1.125rem;
  }

  /* Toggle switch styles */
  .toggle-group {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }

  .toggle-label {
    flex: 1;
  }

  .toggle-label label {
    margin-bottom: 0.25rem;
  }

  .toggle-label .help-text {
    margin-top: 0.25rem;
  }

  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 52px;
    height: 28px;
    flex-shrink: 0;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--toggle-off, #ccc);
    transition: 0.3s;
    border-radius: 28px;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 22px;
    width: 22px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  input:checked + .toggle-slider {
    background-color: var(--primary-color, #007bff);
  }

  input:checked + .toggle-slider:before {
    transform: translateX(24px);
  }

  input:focus + .toggle-slider {
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.2);
  }

  :global([data-theme="dark"]) input:focus + .toggle-slider {
    box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.4);
  }
</style>

