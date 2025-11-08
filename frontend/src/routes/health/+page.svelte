<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import Button from '$components/ui/Button.svelte';
  import { healthStatus, lastHealthCheck } from '$stores/health';
  import { healthService } from '$services/health';
  import type { ProviderHealth } from '$types/health';

  let loading = false;
  let hasData = false;

  // 监听健康状态变化
  $: {
    // 检查是否有健康数据（来自localStorage或新检查）
    hasData = $healthStatus.providers && $healthStatus.providers.length > 0;
  }

  onMount(async () => {
    // 健康状态不会自动加载，仅在用户点击"刷新状态"时加载
    // 数据会自动从localStorage恢复
  });

  async function loadHealth() {
    try {
      loading = true;
      const data = await healthService.getAll();
      healthStatus.set(data);
      lastHealthCheck.set(new Date());
    } catch (error) {
      console.error('Failed to load health status:', error);
    } finally {
      loading = false;
    }
  }

  function getStatusBadge(provider: ProviderHealth) {
    if (!provider.enabled) {
      return { type: 'secondary' as const, text: '已禁用' };
    }
    if (provider.healthy === true) {
      return { type: 'success' as const, text: '健康' };
    }
    if (provider.healthy === false) {
      return { type: 'danger' as const, text: '不健康' };
    }
    return { type: 'warning' as const, text: '未知' };
  }

  function formatTime(time: string | null) {
    if (!time) return '从未检查';
    return new Date(time).toLocaleString('zh-CN');
  }
</script>

<div class="container">
  <div class="header">
    <div class="title-section">
      <h1 class="page-title">健康监控</h1>
      <p class="subtitle">仅在手动点击时检查，零自动请求，最大化节省API调用和token消耗</p>
    </div>
    <div class="actions">
      <Button variant="primary" on:click={loadHealth} disabled={loading}>
        {loading ? '刷新中...' : '刷新状态'}
      </Button>
    </div>
  </div>

  <div class="info-banner">
    <div class="banner-content">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <span>健康检查仅在手动点击"刷新状态"按钮时进行，页面不会自动检查供应商健康状态</span>
    </div>
  </div>

  {#if loading}
    <div class="loading">
      <p>刷新中...</p>
    </div>
  {:else if hasData}
    <div class="info-card">
      <Card title="监控信息">
        <div class="info-items">
          <div class="info-item">
            <span class="label">最后检查时间:</span>
            <span class="value">{$lastHealthCheck ? $lastHealthCheck.toLocaleString('zh-CN') : '从未检查'}</span>
          </div>
          <div class="info-item">
            <span class="label">总体状态:</span>
            <Badge type={
              $healthStatus.status === 'healthy' ? 'success' : 
              $healthStatus.status === 'partial' ? 'warning' : 
              $healthStatus.status === 'unhealthy' ? 'danger' : 
              'info'
            }>
              {
                $healthStatus.status === 'healthy' ? '健康' : 
                $healthStatus.status === 'partial' ? '部分健康' : 
                $healthStatus.status === 'unhealthy' ? '不健康' : 
                '未检查'
              }
            </Badge>
          </div>
        </div>
      </Card>
    </div>

    <div class="providers-list">
      {#each $healthStatus.providers as provider}
        {@const status = getStatusBadge(provider)}
        <Card>
          <div slot="title">
            <div class="provider-header">
              <h3>{provider.name}</h3>
              <Badge type={status.type}>{status.text}</Badge>
            </div>
          </div>

          <div class="provider-details">
            <div class="detail-item">
              <span class="label">优先级:</span>
              <span class="value">{provider.priority}</span>
            </div>
            <div class="detail-item">
              <span class="label">状态:</span>
              <Badge type={provider.enabled ? 'success' : 'secondary'}>
                {provider.enabled ? '已启用' : '已禁用'}
              </Badge>
            </div>
            <div class="detail-item">
              <span class="label">最后检查:</span>
              <span class="value">{formatTime(provider.lastCheck)}</span>
            </div>
            {#if provider.responseTime !== null}
              <div class="detail-item">
                <span class="label">响应时间:</span>
                <span class="value">{provider.responseTime}ms</span>
              </div>
            {/if}
            {#if provider.error}
              <div class="detail-item error">
                <span class="label">错误信息:</span>
                <span class="value">{provider.error}</span>
              </div>
            {/if}
          </div>
        </Card>
      {/each}
    </div>

    {#if $healthStatus.providers.length === 0}
      <div class="empty">
        <p>暂无供应商配置</p>
      </div>
    {/if}
  {/if}
</div>

<style>
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .title-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .page-title {
    margin: 0;
    font-size: 2rem;
    font-weight: 600;
    color: #1a1a1a;
  }

  .subtitle {
    margin: 0;
    font-size: 0.875rem;
    color: #6c757d;
  }

  .actions {
    display: flex;
    gap: 1rem;
  }

  .info-banner {
    background: #e7f3ff;
    border: 1px solid #b3d9ff;
    border-radius: 0.5rem;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
  }

  .banner-content {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: #004085;
    font-size: 0.875rem;
  }

  .banner-content svg {
    flex-shrink: 0;
  }

  .info-card {
    margin-bottom: 2rem;
  }

  .info-items {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .label {
    font-weight: 500;
    color: #666;
  }

  .value {
    color: #1a1a1a;
  }

  .providers-list {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .provider-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .provider-header h3 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
  }

  .provider-details {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
  }

  .detail-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .detail-item.error {
    grid-column: 1 / -1;
  }

  .detail-item.error .value {
    color: #dc3545;
    word-break: break-word;
  }

  .loading,
  .empty {
    text-align: center;
    padding: 3rem;
    color: #666;
  }

  .loading p,
  .empty p {
    margin: 0;
    font-size: 1.125rem;
  }
</style>

