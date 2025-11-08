<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import Button from '$components/ui/Button.svelte';
  import { statsService } from '$services/stats';
  import type { PerformanceSummary, RequestLog, TokenUsage } from '$services/stats';
  import { toast } from '$stores/toast';

  let loading = true;
  let summary: PerformanceSummary | null = null;
  let requests: RequestLog[] = [];
  let tokenUsage: TokenUsage[] = [];
  let showRequests = false;
  let dateFilter = '7d'; // 7d, 30d, all

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    try {
      loading = true;
      const startTime = Date.now();
      
      // 加载性能摘要
      summary = await statsService.getSummary();
      
      // 加载请求日志（最近100条）
      requests = await statsService.getRequests({ limit: 100 });
      
      // 加载 Token 使用统计
      const dateRange = getDateRange();
      const usageData = await statsService.getTokenUsage({
        date_from: dateRange.from,
        date_to: dateRange.to
      });
      tokenUsage = usageData.summary;
      
      // 确保至少显示 300ms 的加载动画
      const elapsed = Date.now() - startTime;
      if (elapsed < 300) {
        await new Promise(resolve => setTimeout(resolve, 300 - elapsed));
      }
    } catch (error) {
      console.error('Failed to load stats:', error);
      toast.error('加载性能数据失败');
    } finally {
      loading = false;
    }
  }

  function getDateRange(): { from: string; to: string } {
    const to = new Date();
    const from = new Date();
    
    if (dateFilter === '7d') {
      from.setDate(from.getDate() - 7);
    } else if (dateFilter === '30d') {
      from.setDate(from.getDate() - 30);
    } else {
      // all
      from.setFullYear(2020, 0, 1);
    }
    
    return {
      from: from.toISOString().split('T')[0],
      to: to.toISOString().split('T')[0]
    };
  }

  function formatNumber(num: number): string {
    return new Intl.NumberFormat('zh-CN').format(num);
  }

  function formatCurrency(amount: number): string {
    return `$${amount.toFixed(4)}`;
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleString('zh-CN');
  }

  function getStatusBadge(statusCode: number) {
    if (statusCode >= 200 && statusCode < 300) {
      return { type: 'success' as const, text: '成功' };
    } else if (statusCode >= 400 && statusCode < 500) {
      return { type: 'warning' as const, text: '客户端错误' };
    } else if (statusCode >= 500) {
      return { type: 'danger' as const, text: '服务器错误' };
    }
    return { type: 'info' as const, text: `HTTP ${statusCode}` };
  }
</script>

<div class="container">
  <div class="page-header">
    <h1 class="page-title">性能监控</h1>
    <div class="actions">
      <select class="date-filter" bind:value={dateFilter} on:change={loadData}>
        <option value="7d">最近7天</option>
        <option value="30d">最近30天</option>
        <option value="all">全部</option>
      </select>
      <Button variant="primary" on:click={loadData} disabled={loading} title={loading ? '加载中...' : '刷新'} class="icon-button {loading ? 'spinning' : ''}">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"></polyline>
          <polyline points="1 20 1 14 7 14"></polyline>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
        </svg>
      </Button>
    </div>
  </div>

  {#if loading}
    <div class="loading">
      <p>加载中...</p>
    </div>
  {:else if summary}
    <!-- 性能摘要 -->
    <div class="summary-grid">
      <Card title="请求统计" subtitle="总体请求情况">
        <div class="stat-items">
          <div class="stat-item">
            <span class="label">总请求数</span>
            <span class="value">{formatNumber(summary.total_requests)}</span>
          </div>
          <div class="stat-item">
            <span class="label">成功请求</span>
            <span class="value success">{formatNumber(summary.successful_requests)}</span>
          </div>
          <div class="stat-item">
            <span class="label">失败请求</span>
            <span class="value danger">{formatNumber(summary.failed_requests)}</span>
          </div>
          <div class="stat-item">
            <span class="label">成功率</span>
            <span class="value">{summary.success_rate.toFixed(2)}%</span>
          </div>
          <div class="stat-item">
            <span class="label">平均响应时间</span>
            <span class="value">{summary.avg_response_time_ms.toFixed(0)}ms</span>
          </div>
        </div>
      </Card>

      <Card title="Token 使用" subtitle="Token 消耗统计">
        <div class="stat-items">
          <div class="stat-item">
            <span class="label">输入 Token</span>
            <span class="value">{formatNumber(summary.token_usage.total_input_tokens)}</span>
          </div>
          <div class="stat-item">
            <span class="label">输出 Token</span>
            <span class="value">{formatNumber(summary.token_usage.total_output_tokens)}</span>
          </div>
          <div class="stat-item">
            <span class="label">总 Token</span>
            <span class="value">{formatNumber(summary.token_usage.total_input_tokens + summary.token_usage.total_output_tokens)}</span>
          </div>
          <div class="stat-item">
            <span class="label">估算成本</span>
            <span class="value">{formatCurrency(summary.token_usage.total_cost_estimate)}</span>
          </div>
        </div>
      </Card>
    </div>

    <!-- 供应商统计 -->
    {#if Object.keys(summary.provider_stats).length > 0}
      <Card title="供应商统计" subtitle="各供应商性能指标">
        <div class="table-container">
          <table class="stats-table">
            <thead>
              <tr>
                <th>供应商</th>
                <th>总请求</th>
                <th>成功</th>
                <th>失败</th>
                <th>成功率</th>
                <th>Token 消耗</th>
                <th>成本估算</th>
              </tr>
            </thead>
            <tbody>
              {#each Object.entries(summary.provider_stats) as [provider, stats]}
                <tr>
                  <td class="provider-name">{provider}</td>
                  <td>{formatNumber(stats.total)}</td>
                  <td class="success">{formatNumber(stats.success)}</td>
                  <td class="danger">{formatNumber(stats.failed)}</td>
                  <td>{stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(2) : 0}%</td>
                  <td>{formatNumber(stats.total_tokens)}</td>
                  <td>{formatCurrency(stats.total_cost)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </Card>
    {/if}

    <!-- Token 使用详情 -->
    {#if tokenUsage.length > 0}
      <Card title="Token 使用详情" subtitle="按日期和供应商统计">
        <div class="table-container">
          <table class="stats-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>供应商</th>
                <th>模型</th>
                <th>请求数</th>
                <th>输入 Token</th>
                <th>输出 Token</th>
                <th>总 Token</th>
                <th>成本估算</th>
              </tr>
            </thead>
            <tbody>
              {#each tokenUsage as usage}
                <tr>
                  <td>{usage.date}</td>
                  <td class="provider-name">{usage.provider_name}</td>
                  <td>{usage.model}</td>
                  <td>{formatNumber(usage.request_count)}</td>
                  <td>{formatNumber(usage.total_input_tokens)}</td>
                  <td>{formatNumber(usage.total_output_tokens)}</td>
                  <td>{formatNumber(usage.total_input_tokens + usage.total_output_tokens)}</td>
                  <td>{formatCurrency(usage.total_cost_estimate)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </Card>
    {/if}

    <!-- 请求日志 -->
    <Card title="请求日志" subtitle="最近的API请求记录">
      <div class="request-controls">
        <Button variant="secondary" on:click={() => showRequests = !showRequests}>
          {showRequests ? '隐藏日志' : '显示日志'}
        </Button>
      </div>
      
      {#if showRequests}
        <div class="table-container">
          <table class="stats-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>供应商</th>
                <th>模型</th>
                <th>状态</th>
                <th>响应时间</th>
                <th>输入 Token</th>
                <th>输出 Token</th>
                <th>错误</th>
              </tr>
            </thead>
            <tbody>
              {#each requests as request}
                {@const badge = getStatusBadge(request.status_code)}
                <tr>
                  <td>{formatDate(request.created_at)}</td>
                  <td class="provider-name">{request.provider_name}</td>
                  <td>{request.model}</td>
                  <td>
                    <Badge type={badge.type}>{badge.text}</Badge>
                  </td>
                  <td>{request.response_time_ms ? `${request.response_time_ms.toFixed(0)}ms` : '-'}</td>
                  <td>{request.input_tokens ? formatNumber(request.input_tokens) : '-'}</td>
                  <td>{request.output_tokens ? formatNumber(request.output_tokens) : '-'}</td>
                  <td class="error-cell">{request.error_message || '-'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <p class="info-text">点击"显示日志"查看详细的请求记录</p>
      {/if}
    </Card>
  {:else}
    <div class="empty">
      <p>暂无性能数据</p>
    </div>
  {/if}
</div>

<style>
  .actions {
    display: flex;
    gap: 0.75rem;
    align-items: center;
  }

  .date-filter {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
  }

  .date-filter:focus {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .stat-items {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .stat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border-color);
  }

  .stat-item:last-child {
    border-bottom: none;
  }

  .stat-item .label {
    color: var(--text-secondary);
    font-size: 0.875rem;
  }

  .stat-item .value {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .stat-item .value.success {
    color: var(--success-color);
  }

  .stat-item .value.danger {
    color: var(--danger-color);
  }

  .table-container {
    overflow-x: auto;
    margin-top: 1rem;
  }

  .stats-table {
    width: 100%;
    border-collapse: collapse;
    background: var(--bg-primary);
  }

  .stats-table th {
    background: var(--bg-tertiary);
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary);
    border-bottom: 2px solid var(--border-color);
    white-space: nowrap;
  }

  .stats-table td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-secondary);
  }

  .stats-table tbody tr:hover {
    background: var(--bg-tertiary);
  }

  .stats-table .provider-name {
    font-weight: 500;
    color: var(--text-primary);
  }

  .stats-table .success {
    color: var(--success-color);
  }

  .stats-table .danger {
    color: var(--danger-color);
  }

  .error-cell {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.8125rem;
  }

  .request-controls {
    margin-bottom: 1rem;
  }

  .info-text {
    color: var(--text-secondary);
    font-size: 0.875rem;
    text-align: center;
    padding: 2rem;
  }

  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary);
  }

  .empty {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary);
  }

  @media (max-width: 768px) {
    .summary-grid {
      grid-template-columns: 1fr;
    }

    .stats-table {
      font-size: 0.8125rem;
    }

    .stats-table th,
    .stats-table td {
      padding: 0.5rem 0.75rem;
    }
  }

  @media (max-width: 480px) {
    .stats-table {
      font-size: 0.75rem;
    }

    .stats-table th,
    .stats-table td {
      padding: 0.5rem 0.5rem;
    }
  }
</style>

