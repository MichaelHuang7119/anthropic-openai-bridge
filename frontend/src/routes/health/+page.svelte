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
    <div class="summary-card">
      <Card title="监控信息">
        <div class="summary-items">
          <div class="summary-item">
            <span class="label">最后检查时间:</span>
            <span class="value">{$lastHealthCheck ? $lastHealthCheck.toLocaleString('zh-CN') : '从未检查'}</span>
          </div>
          <div class="summary-item">
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

    <div class="table-container">
      <table class="health-table">
        <thead>
          <tr>
            <th>供应商名称</th>
            <th>健康状态</th>
            <th>启用状态</th>
            <th>优先级</th>
            <th>响应时间</th>
            <th>最后检查</th>
            <th>错误信息</th>
          </tr>
        </thead>
        <tbody>
          {#each $healthStatus.providers as provider}
            {@const status = getStatusBadge(provider)}
            <tr class={!provider.enabled ? 'disabled-row' : ''}>
              <td class="name-cell">
                <span class="provider-name">{provider.name}</span>
              </td>
              <td>
                <Badge type={status.type}>{status.text}</Badge>
              </td>
              <td>
                <Badge type={provider.enabled ? 'success' : 'secondary'}>
                  {provider.enabled ? '已启用' : '已禁用'}
                </Badge>
              </td>
              <td class="priority-cell">
                <span class="priority-value">{provider.priority}</span>
              </td>
              <td class="response-time-cell">
                {#if provider.responseTime !== null}
                  <span class="response-time-value">{provider.responseTime}ms</span>
                {:else}
                  <span class="response-time-na">-</span>
                {/if}
              </td>
              <td class="last-check-cell">
                <span class="last-check-value">{formatTime(provider.lastCheck)}</span>
              </td>
              <td class="error-cell">
                {#if provider.error}
                  <span class="error-value" title={provider.error}>{provider.error}</span>
                {:else}
                  <span class="error-na">-</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
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

  .summary-card {
    margin-bottom: 2rem;
  }

  .summary-items {
    display: flex;
    gap: 2rem;
  }

  .summary-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .label {
    font-weight: 500;
    color: #666;
  }

  .value {
    color: #1a1a1a;
  }

  .table-container {
    background: white;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .health-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .health-table thead {
    background: #f8f9fa;
    border-bottom: 2px solid #dee2e6;
  }

  .health-table th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    color: #495057;
    white-space: nowrap;
  }

  .health-table th:first-child {
    width: 180px;
  }

  .health-table th:nth-child(2) {
    width: 120px;
  }

  .health-table th:nth-child(3) {
    width: 100px;
  }

  .health-table th:nth-child(4) {
    width: 80px;
  }

  .health-table th:nth-child(5) {
    width: 100px;
  }

  .health-table th:nth-child(6) {
    width: 180px;
  }

  .health-table th:last-child {
    width: 250px;
  }

  .health-table tbody tr {
    border-bottom: 1px solid #dee2e6;
    transition: background-color 0.2s;
  }

  .health-table tbody tr:hover {
    background: #f8f9fa;
  }

  .health-table tbody tr.disabled-row {
    opacity: 0.6;
  }

  .health-table td {
    padding: 1rem;
    vertical-align: middle;
  }

  .name-cell {
    padding: 1rem 0.75rem;
  }

  .provider-name {
    font-weight: 600;
    color: #1a1a1a;
  }

  .priority-cell {
    text-align: center;
  }

  .priority-value {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    background: #e9ecef;
    border-radius: 0.25rem;
    font-weight: 500;
    color: #495057;
  }

  .response-time-cell {
    text-align: center;
  }

  .response-time-value {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    background: #d1ecf1;
    border-radius: 0.25rem;
    font-weight: 500;
    color: #0c5460;
  }

  .response-time-na {
    color: #adb5bd;
    font-style: italic;
  }

  .last-check-cell {
    color: #6c757d;
    font-size: 0.8125rem;
    white-space: nowrap;
  }

  .error-cell {
    max-width: 250px;
  }

  .error-value {
    display: inline-block;
    max-width: 100%;
    color: #dc3545;
    font-size: 0.8125rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .error-na {
    color: #adb5bd;
    font-style: italic;
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

  /* Responsive Design */
  @media (max-width: 1200px) {
    .health-table th:last-child {
      width: 200px;
    }
  }

  @media (max-width: 1024px) {
    .summary-items {
      flex-direction: column;
      gap: 1rem;
    }

    .health-table th:nth-child(6) {
      width: 150px;
    }

    .health-table th:last-child {
      width: 180px;
    }
  }

  @media (max-width: 768px) {
    .table-container {
      overflow-x: auto;
    }

    .health-table {
      min-width: 900px;
    }

    .health-table th,
    .health-table td {
      padding: 0.75rem 0.5rem;
      font-size: 0.8125rem;
    }

    .health-table th:last-child {
      width: 160px;
    }
  }

  @media (max-width: 480px) {
    .container {
      padding: 0 0.75rem;
    }

    .health-table th,
    .health-table td {
      padding: 0.5rem 0.375rem;
      font-size: 0.75rem;
    }

    .health-table th:first-child {
      width: 120px;
    }

    .health-table th:nth-child(2) {
      width: 100px;
    }

    .health-table th:nth-child(3) {
      width: 80px;
    }

    .health-table th:nth-child(4) {
      width: 60px;
    }

    .health-table th:nth-child(5) {
      width: 80px;
    }

    .health-table th:nth-child(6) {
      width: 120px;
    }

    .health-table th:last-child {
      width: 140px;
    }
  }
</style>

