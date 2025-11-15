<script lang="ts">
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import Button from '$components/ui/Button.svelte';
  import Input from '$components/ui/Input.svelte';
  import { healthStatus, lastHealthCheck } from '$stores/health';
  import { healthService } from '$services/health';
  import type { ProviderHealth, CategoryHealth } from '$types/health';

  let loading = false;
  let hasData = false;
  
  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;
  
  // 搜索和筛选相关
  let searchQuery = '';
  let filterHealth: 'all' | 'healthy' | 'unhealthy' | 'disabled' = 'all';
  
  // 分页相关
  let currentPage = 1;
  const pageSize = 5;

  // 监听健康状态变化
  $: {
    // 检查是否有健康数据（来自localStorage或新检查）
    hasData = $healthStatus.providers && $healthStatus.providers.length > 0;
  }
  
  // 客户端过滤
  $: allFilteredProviders = $healthStatus.providers.filter(p => {
    // 搜索过滤
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      if (!p.name.toLowerCase().includes(query)) {
        return false;
      }
    }
    
    // 健康状态过滤
    if (filterHealth === 'healthy' && (!p.enabled || p.healthy !== true)) return false;
    if (filterHealth === 'unhealthy' && (p.enabled && p.healthy === false)) return false;
    if (filterHealth === 'disabled' && p.enabled) return false;
    
    return true;
  });
  
  // 分页计算
  $: totalCount = allFilteredProviders.length;
  $: totalPages = Math.ceil(totalCount / pageSize);
  
  // 确保当前页在有效范围内
  $: {
    if (totalPages === 0) {
      // 没有数据时，设置为第1页
      currentPage = 1;
    } else if (totalPages > 0 && currentPage > totalPages) {
      currentPage = totalPages;
    } else if (currentPage < 1) {
      currentPage = 1;
    }
  }
  
  // 当前页显示的数据
  $: filteredProviders = (() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return allFilteredProviders.slice(start, end);
  })();

  onMount(async () => {
    abortController = new AbortController();
    // 健康状态不会自动加载，仅在用户点击"刷新状态"时加载
    // 数据会自动从localStorage恢复
  });

  onDestroy(() => {
    // 取消所有进行中的请求
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
  });

  async function loadHealth() {
    if (!abortController) return;
    try {
      loading = true;
      const data = await healthService.getAll({ signal: abortController.signal });
      
      // 检查是否已被取消
      if (abortController.signal.aborted) return;
      
      healthStatus.set(data);
      lastHealthCheck.set(new Date());
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load health status:', error);
    } finally {
      if (!abortController?.signal.aborted) {
        loading = false;
      }
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
    try {
      // 后端现在返回 ISO 格式的 UTC 时间（如 "2024-01-01T12:00:00+00:00" 或 "2024-01-01T12:00:00.000000+00:00"）
      // Date 对象会自动处理 ISO 格式的时间字符串，包括时区转换
      let date: Date;
      
      if (time.includes('T')) {
        // ISO 格式，直接解析（Date 会自动处理时区）
        date = new Date(time);
      } else if (time.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
        // 格式为 "YYYY-MM-DD HH:MM:SS"（兼容旧格式），假设是 UTC 时间
        const dateStrToParse = time.replace(' ', 'T') + 'Z';
        date = new Date(dateStrToParse);
      } else {
        // 尝试直接解析
        date = new Date(time);
      }
      
      // 检查日期是否有效
      if (isNaN(date.getTime())) {
        return time; // 如果日期无效，返回原始字符串
      }
      
      // toLocaleString 默认会使用本地时区，自动将 UTC 时间转换为本地时间
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return time;
    }
  }

  function getCategoryLabel(category: string): string {
    const labels: Record<string, string> = {
      big: '大模型',
      middle: '中模型',
      small: '小模型'
    };
    return labels[category] || category;
  }

  function getCategoryStatus(provider: ProviderHealth, category: string): CategoryHealth | null {
    return provider.categories?.[category as keyof typeof provider.categories] || null;
  }

  function clearFilters() {
    searchQuery = '';
    filterHealth = 'all';
    currentPage = 1;
  }
  
  function handlePageChange(newPage: number) {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      currentPage = newPage;
    }
  }
</script>

<div class="container">
  <div class="page-header">
    <div class="actions">
      <Button variant="primary" on:click={loadHealth} disabled={loading} title="刷新状态" class="icon-button {loading ? 'spinning' : ''}">
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
      <p>刷新中...</p>
    </div>
  {:else if hasData}
    <div class="summary-card">
      <Card title="监控信息">
        <div class="summary-items">
          <div class="summary-item">
            <span class="label">最后检查时间:</span>
            <span class="value">{$lastHealthCheck ? (() => {
              try {
                // lastHealthCheck 存储为 ISO 字符串（UTC），需要转换为本地时区显示
                let date: Date;
                if ($lastHealthCheck instanceof Date) {
                  date = $lastHealthCheck;
                } else if (typeof $lastHealthCheck === 'string') {
                  // ISO 字符串会被正确解析为 UTC 时间
                  date = new Date($lastHealthCheck);
                } else {
                  return '从未检查';
                }
                
                if (isNaN(date.getTime())) {
                  return '从未检查';
                }
                
                // Date 对象内部存储的是 UTC 时间戳
                // toLocaleString 会自动转换为本地时区，不需要指定 timeZone
                // 但为了确保一致性，我们明确指定格式选项
                return date.toLocaleString('zh-CN', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit'
                });
              } catch {
                return '从未检查';
              }
            })() : '从未检查'}</span>
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

    <!-- 搜索和筛选 -->
    <Card>
      <div class="filters">
        <div class="filter-row">
          <div class="filter-group search-group">
            <Input
              type="text"
              bind:value={searchQuery}
              placeholder="搜索供应商名称..."
            />
          </div>
          
          <div class="filter-group">
            <label for="health-filter-status">状态:</label>
            <select id="health-filter-status" class="filter-select" bind:value={filterHealth}>
              <option value="all">全部</option>
              <option value="healthy">健康</option>
              <option value="unhealthy">不健康</option>
              <option value="disabled">已禁用</option>
            </select>
          </div>
          
          <Button variant="secondary" size="sm" on:click={clearFilters} title="清除筛选" class="clear-button">
            清除
          </Button>
        </div>
      </div>
    </Card>

    <div class="table-container">
      <table class="health-table">
        <thead>
          <tr>
            <th>供应商名称</th>
            <th>健康状态</th>
            <th>类别健康状态</th>
            <th>启用状态</th>
            <th>优先级</th>
            <th>最后检查</th>
            <th>错误信息</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredProviders as provider}
            {@const status = getStatusBadge(provider)}
            <tr class={!provider.enabled ? 'disabled-row' : ''}>
              <td class="name-cell">
                <span class="provider-name">{provider.name}</span>
              </td>
              <td>
                <Badge type={status.type}>{status.text}</Badge>
              </td>
              <td class="categories-cell">
                {#if provider.categories}
                  <div class="categories-list">
                    {#each ['big', 'middle', 'small'] as category}
                      {@const catStatus = getCategoryStatus(provider, category)}
                      {#if catStatus !== null}
                        <div class="category-item">
                          <span class="category-label">{getCategoryLabel(category)}:</span>
                          <Badge type={catStatus.healthy ? 'success' : 'danger'}>
                            {catStatus.healthy ? '健康' : '不健康'}
                          </Badge>
                          {#if catStatus.healthy && catStatus.responseTime !== null}
                            <span class="category-response-time">({catStatus.responseTime}ms)</span>
                          {/if}
                        </div>
                      {/if}
                    {/each}
                  </div>
                {:else}
                  <span class="categories-na">-</span>
                {/if}
              </td>
              <td>
                <Badge type={provider.enabled ? 'success' : 'secondary'}>
                  {provider.enabled ? '已启用' : '已禁用'}
                </Badge>
              </td>
              <td class="priority-cell">
                <span class="priority-value">{provider.priority}</span>
              </td>
              <td class="last-check-cell">
                <span class="last-check-value">{formatTime(provider.lastCheck)}</span>
              </td>
              <td class="error-cell">
                {#if provider.error}
                  <span class="error-value">
                    {provider.error}
                  </span>
                {:else}
                  <span class="error-na">-</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- 分页控件 -->
    {#if totalPages > 1}
      <div class="pagination">
        <div class="pagination-info">
          共 {totalCount} 条记录，第 {currentPage} / {totalPages} 页
        </div>
        <div class="pagination-controls">
          <Button 
            variant="secondary" 
            size="sm" 
            disabled={currentPage === 1}
            on:click={() => handlePageChange(currentPage - 1)}
            title="上一页"
            class="icon-button"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
          </Button>
          <span class="page-info">{currentPage} / {totalPages}</span>
          <Button 
            variant="secondary" 
            size="sm" 
            disabled={currentPage === totalPages}
            on:click={() => handlePageChange(currentPage + 1)}
            title="下一页"
            class="icon-button"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </Button>
        </div>
      </div>
    {/if}

    {#if filteredProviders.length === 0 && hasData}
      <div class="empty">
        <p>没有匹配的供应商</p>
      </div>
    {/if}
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
    color: var(--text-secondary, #666);
  }

  .value {
    color: var(--text-primary, #1a1a1a);
  }

  .filters {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0;
  }

  .filter-row {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
    width: 100%;
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .filter-group.search-group {
    min-width: 250px;
    flex: 1;
  }
  
  .filter-group.search-group :global(input) {
    width: 100%;
    height: 2.5rem;
  }

  .filter-group label {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
    white-space: nowrap;
    font-weight: 500;
    margin: 0;
  }

  .filter-select {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 0.375rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
    cursor: pointer;
    min-width: 150px;
    height: 2.5rem;
  }

  .filter-select:focus {
    outline: 2px solid var(--primary-color, #007bff);
    outline-offset: 2px;
  }

  .clear-button {
    margin-left: auto;
    align-self: center;
    height: 2.5rem;
    flex-shrink: 0;
  }

  .filter-info {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
    padding-top: 0.5rem;
    border-top: 1px solid var(--border-color, #e9ecef);
  }

  .pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding: 1rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
  }

  .pagination-info {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .page-info {
    font-size: 0.875rem;
    color: var(--text-primary, #495057);
    min-width: 60px;
    text-align: center;
  }

  .table-container {
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow-x: auto;
    margin-top: 1rem;
  }

  .health-table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .health-table thead {
    background: var(--bg-tertiary, #f8f9fa);
    border-bottom: 2px solid var(--border-color, #dee2e6);
  }

  .health-table th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary, #495057);
    white-space: nowrap;
  }

  .health-table th:first-child {
    width: 180px;
  }

  .health-table th:nth-child(2) {
    width: 120px;
  }

  .health-table th:nth-child(3) {
    width: 200px;
  }

  .health-table th:nth-child(4) {
    width: 100px;
  }

  .health-table th:nth-child(5) {
    width: 80px;
  }

  .health-table th:nth-child(6) {
    width: 180px;
  }

  .health-table th:last-child {
    width: 250px;
  }

  .health-table tbody tr {
    border-bottom: 1px solid var(--border-color, #dee2e6);
    transition: background-color 0.2s;
  }

  .health-table tbody tr:hover {
    background: var(--bg-tertiary, #f8f9fa);
  }

  .health-table tbody tr.disabled-row {
    opacity: 0.6;
  }

  .health-table td {
    padding: 1rem;
    vertical-align: middle;
    white-space: nowrap;
  }

  .name-cell {
    padding: 1rem 0.75rem;
  }

  .provider-name {
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .priority-cell {
    text-align: center;
  }

  .priority-value {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    background: var(--bg-tertiary, #e9ecef);
    border-radius: 0.25rem;
    font-weight: 500;
    color: var(--text-primary, #495057);
  }

  .last-check-cell {
    color: var(--text-secondary, #6c757d);
    font-size: 0.8125rem;
    white-space: nowrap;
  }

  .error-cell {
    max-width: 250px;
  }

  .error-value {
    display: inline-block;
    max-width: 100%;
    color: var(--danger-color, #dc3545);
    font-size: 0.8125rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .error-na {
    color: var(--text-secondary, #adb5bd);
    font-style: italic;
  }

  .categories-cell {
    padding: 0.75rem 1rem;
  }

  .categories-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .category-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
  }

  .category-label {
    color: var(--text-secondary, #666);
    font-weight: 500;
    min-width: 50px;
  }

  .category-response-time {
    color: var(--text-secondary, #666);
    font-size: 0.75rem;
  }

  .categories-na {
    color: var(--text-secondary, #adb5bd);
    font-style: italic;
  }

  .loading,
  .empty {
    text-align: center;
    padding: 3rem;
    color: var(--text-secondary, #666);
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
      width: 150px;
    }

    .health-table th:nth-child(4) {
      width: 80px;
    }

    .health-table th:nth-child(5) {
      width: 60px;
    }

    .health-table th:nth-child(6) {
      width: 120px;
    }

    .health-table th:last-child {
      width: 140px;
    }
  }
</style>

