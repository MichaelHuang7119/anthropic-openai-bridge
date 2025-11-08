<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '$components/ui/Card.svelte';
  import Button from '$components/ui/Button.svelte';
  import { configService } from '$services/config';
  import { toast } from '$stores/toast';
  import type { GlobalConfig } from '$types/config';

  let loading = true;
  let saving = false;
  let config: GlobalConfig = {
    fallback_strategy: 'priority',
    circuit_breaker: {
      failure_threshold: 5,
      recovery_timeout: 60
    }
  };

  onMount(async () => {
    await loadConfig();
  });

  async function loadConfig() {
    loading = true;
    try {
      config = await configService.get();
    } catch (error) {
      console.error('Failed to load config:', error);
      toast.error('加载配置失败');
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    try {
      await configService.update(config);
      toast.success('配置保存成功');
    } catch (error) {
      console.error('Failed to save config:', error);
      toast.error('保存配置失败: ' + (error as Error).message);
    } finally {
      saving = false;
    }
  }

  function handleReset() {
    if (!confirm('确定要重置配置吗？')) {
      return;
    }
    loadConfig();
  }
</script>

<div class="container">
  <div class="header">
    <h1 class="page-title">全局配置</h1>
    <div class="actions">
      <Button variant="secondary" on:click={handleReset} disabled={loading || saving}>
        重置
      </Button>
      <Button variant="primary" on:click={handleSave} disabled={loading || saving}>
        {saving ? '保存中...' : '保存配置'}
      </Button>
    </div>
  </div>

  {#if loading}
    <div class="loading">
      <p>加载中...</p>
    </div>
  {:else}
    <div class="config-grid">
      <Card title="回退策略">
        <div class="form-section">
          <div class="form-group">
            <label for="fallback-strategy">回退策略:</label>
            <select
              id="fallback-strategy"
              bind:value={config.fallback_strategy}
              class="form-control"
            >
              <option value="priority">优先级（按优先级顺序尝试）</option>
              <option value="random">随机（随机选择可用供应商）</option>
            </select>
            <p class="help-text">当主供应商不可用时，使用的回退策略</p>
          </div>
        </div>
      </Card>

      <Card title="熔断器配置">
        <div class="form-section">
          <div class="form-group">
            <label for="failure-threshold">失败阈值:</label>
            <input
              id="failure-threshold"
              type="number"
              min="1"
              max="20"
              bind:value={config.circuit_breaker.failure_threshold}
              class="form-control"
            />
            <p class="help-text">连续失败多少次后触发熔断（1-20次）</p>
          </div>

          <div class="form-group">
            <label for="recovery-timeout">恢复超时（秒）:</label>
            <input
              id="recovery-timeout"
              type="number"
              min="10"
              max="600"
              bind:value={config.circuit_breaker.recovery_timeout}
              class="form-control"
            />
            <p class="help-text">熔断后等待多长时间再尝试恢复（10-600秒）</p>
          </div>
        </div>
      </Card>
    </div>
  {/if}
</div>

<style>
  .container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .page-title {
    margin: 0;
    font-size: 2rem;
    font-weight: 600;
    color: #1a1a1a;
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
    color: #1a1a1a;
  }

  .form-control {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid #ddd;
    border-radius: 0.25rem;
    font-size: 1rem;
    transition: border-color 0.2s;
  }

  .form-control:focus {
    outline: none;
    border-color: #007bff;
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
  }

  .help-text {
    margin: 0.5rem 0 0 0;
    font-size: 0.875rem;
    color: #666;
  }

  .loading {
    text-align: center;
    padding: 3rem;
    color: #666;
  }

  .loading p {
    margin: 0;
    font-size: 1.125rem;
  }
</style>

