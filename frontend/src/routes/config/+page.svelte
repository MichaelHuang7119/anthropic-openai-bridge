<script lang="ts">
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import Card from '$components/ui/Card.svelte';
  import Button from '$components/ui/Button.svelte';
  import { configService } from '$services/config';
  import { toast } from '$stores/toast';
  import type { GlobalConfig } from '$types/config';
  import { tStore } from '$stores/language';

  let loading = $state(true);
  let saving = $state(false);
  let config: GlobalConfig = $state({
    fallback_strategy: 'priority',
    circuit_breaker: {
      failure_threshold: 5,
      recovery_timeout: 60
    }
  });

  // 获取翻译函数
  const t = $derived($tStore);

  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;

  onMount(async () => {
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
      <Button variant="secondary" on:click={handleReset} disabled={loading || saving} title={t('config.resetConfig')} class="icon-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"></polyline>
          <polyline points="1 20 1 14 7 14"></polyline>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
        </svg>
      </Button>
      <Button variant="primary" on:click={handleSave} disabled={loading || saving} title={saving ? t('config.saving') : t('config.save')} class="icon-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
          <polyline points="17 21 17 13 7 13 7 21"></polyline>
          <polyline points="7 3 7 8 15 8"></polyline>
        </svg>
      </Button>
    </div>
  </div>

  {#if loading}
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
</style>

