<script lang="ts">
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import Button from '$components/ui/Button.svelte';
  import Input from '$components/ui/Input.svelte';
  import ErrorMessageModal from '$components/ErrorMessageModal.svelte';
  import StatCard from '$lib/components/ui/StatCard.svelte';
  import RealTimeIndicator from '$lib/components/ui/RealTimeIndicator.svelte';
  import Chart from '$lib/components/ui/Chart.svelte';
  import { healthStatus, lastHealthCheck } from '$stores/health';
  import { healthService } from '$services/health';
  import type { ProviderHealth, CategoryHealth } from '$types/health';
  import { tStore, language } from '$stores/language';

  let loading = $state(false);
  let hasData = $state(false);

  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;

  // 获取翻译函数
  const t = $derived($tStore);
  const currentLanguage = $derived($language);
  
  // 搜索和筛选相关
  let searchQuery = $state('');
  let filterHealth: 'all' | 'healthy' | 'unhealthy' | 'disabled' = $state('all');

  // 分页相关
  let currentPage = $state(1);
  const pageSize = 5;

  // 监听健康状态变化
  $effect(() => {
    // 检查是否有健康数据（来自localStorage或新检查）
    hasData = $healthStatus.providers && $healthStatus.providers.length > 0;
  });
  
  // 客户端过滤
  let allFilteredProviders = $derived($healthStatus.providers.filter(p => {
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
  }));

  // 分页计算
  let totalCount = $derived(allFilteredProviders.length);
  let totalPages = $derived(Math.ceil(totalCount / pageSize));

  // 确保当前页在有效范围内
  $effect(() => {
    if (totalPages === 0) {
      // 没有数据时，设置为第1页
      currentPage = 1;
    } else if (totalPages > 0 && currentPage > totalPages) {
      currentPage = totalPages;
    } else if (currentPage < 1) {
      currentPage = 1;
    }
  });

  // 当前页显示的数据
  let filteredProviders = $derived(allFilteredProviders.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  ));

  onMount(async () => {
    abortController = new AbortController();
    // 页面加载时不自动进行新的健康检查
    // 首先检查localStorage中是否有数据
    // 如果没有，则从后端数据库加载最新的健康检查记录
    try {
      // 检查是否有健康数据（来自localStorage）
      const hasLocalData = $healthStatus.providers && $healthStatus.providers.length > 0;

      if (!hasLocalData) {
        // 没有本地数据，从后端数据库获取最新的健康检查记录
        console.log('No local health data found, loading from backend database...');
        const latestData = await healthService.getLatest({ signal: abortController.signal });

        // 检查是否已被取消
        if (abortController.signal.aborted) return;

        // 如果后端有数据，则使用后端数据
        if (latestData.providers && latestData.providers.length > 0) {
          healthStatus.set(latestData);
          lastHealthCheck.set(new Date(latestData.timestamp));
          console.log('Loaded health data from backend database');
        } else {
          console.log('No health data available in backend database');
        }
      } else {
        console.log('Using local health data from localStorage');
      }
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load health status:', error);
      // 即使加载失败，也保持localStorage中的数据
    }
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

  // 计算统计数据（使用所有过滤后的数据，不是分页数据）
  let healthyCount = $derived(allFilteredProviders.filter(p => p.healthy === true).length);
  let unhealthyCount = $derived(allFilteredProviders.filter(p => p.healthy === false).length);
  let disabledCount = $derived(allFilteredProviders.filter(p => !p.enabled).length);

  // 图表数据
  let healthDistributionChartData = $derived({
    labels: [t('health.healthy'), t('health.unhealthy'), t('health.disabled')],
    datasets: [{
      data: [healthyCount, unhealthyCount, disabledCount],
      backgroundColor: ['#28a745', '#dc3545', '#6c757d'],
      borderWidth: 0
    }]
  });

  // 响应时间趋势数据（模拟数据）
  let responseTimeChartData = $derived({
    labels: Array.from({ length: 7 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (6 - i));
      return date.toLocaleDateString();
    }),
    datasets: [{
      label: t('health.responseTime'),
      data: Array.from({ length: 7 }, () => Math.floor(Math.random() * 500) + 100),
      borderColor: '#5a9cff',
      backgroundColor: 'rgba(90, 156, 255, 0.1)',
      tension: 0.4
    }]
  });

  function getStatusBadge(provider: ProviderHealth) {
    if (!provider.enabled) {
      return { type: 'secondary' as const, text: t('health.disabled') };
    }
    if (provider.healthy === true) {
      return { type: 'success' as const, text: t('health.healthy') };
    }
    if (provider.healthy === false) {
      return { type: 'danger' as const, text: t('health.unhealthy') };
    }
    return { type: 'warning' as const, text: t('health.unknown') };
  }

  function formatTime(time: string | null) {
    if (!time) return t('health.neverChecked');
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

      // 根据当前语言选择 locale
      const locale = currentLanguage === 'zh-CN' ? 'zh-CN' : 'en-US';

      // toLocaleString 默认会使用本地时区，自动将 UTC 时间转换为本地时间
      return date.toLocaleString(locale, {
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
      big: t('providerForm.bigModels'),
      middle: t('providerForm.middleModels'),
      small: t('providerForm.smallModels')
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

  function truncateError(errorMessage: string, maxLength: number = 50): string {
    if (!errorMessage) return '';
    if (errorMessage.length <= maxLength) return errorMessage;
    return errorMessage.substring(0, maxLength) + '...';
  }

  // 错误信息模态框相关
  let showErrorModal = $state(false);
  let selectedError: string = $state('');
  let selectedProviderName: string = $state('');

  function showErrorMessage(providerName: string, error: string) {
    selectedProviderName = providerName;
    selectedError = error;
    showErrorModal = true;
  }

  function closeErrorModal() {
    showErrorModal = false;
    selectedError = '';
    selectedProviderName = '';
  }
</script>

<div class="container">
  <div class="page-header">
    <div class="actions">
      <Button variant="primary" onclick={loadHealth} disabled={loading} title={t('health.checkNow')} class="icon-button {loading ? 'spinning' : ''}">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
      </Button>
    </div>
  </div>

  {#if loading}
    <div class="loading">
      <p>{t('health.checking')}</p>
    </div>
  {:else if hasData}
    <!-- 总体状态概览 -->
    <div class="status-overview">
      <div class="status-card card-animated">
        <div class="status-indicator">
          <div class="status-dot active"></div>
          <div class="status-pulse"></div>
        </div>
        <div class="status-content">
          <h2 class="status-title">{t('health.systemHealth')}</h2>
          <p class="status-subtitle">
            {
              $healthStatus.status === 'healthy' ? t('health.allSystemsOperational') :
              $healthStatus.status === 'partial' ? t('health.partialOperational') :
              $healthStatus.status === 'unhealthy' ? t('health.systemIssues') :
              t('health.notChecked')
            }
          </p>
        </div>
        <div class="status-score">
          <span class="score-value">{healthyCount + unhealthyCount > 0 ? Math.round((healthyCount / (healthyCount + unhealthyCount)) * 100) : 0}</span>
          <span class="score-label">{t('health.healthScore')}</span>
        </div>
      </div>
    </div>

    <!-- 实时状态指示器 -->
    <div class="realtime-status">
      <RealTimeIndicator
        status={$healthStatus.status === 'healthy' ? 'online' : $healthStatus.status === 'unhealthy' ? 'offline' : 'warning'}
        text={$healthStatus.status === 'healthy' ? t('health.systemOnline') : $healthStatus.status === 'unhealthy' ? t('health.systemOffline') : t('health.systemWarning')}
        size="md"
        animated={true}
      />
    </div>

    <!-- 关键指标 -->
    <div class="stats-grid">
      <StatCard
        title={t('health.healthy')}
        value={healthyCount}
        type="success"
        icon="check-circle"
      />
      <StatCard
        title={t('health.unhealthy')}
        value={unhealthyCount}
        type="danger"
        icon="x-circle"
      />
      <StatCard
        title={t('health.disabled')}
        value={disabledCount}
        type="default"
        icon="power"
      />
      <StatCard
        title={t('health.totalProviders')}
        value={totalCount}
        type="info"
        icon="server"
      />
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <Card title={t('health.responseTimeTrend')} variant="elevated">
        <Chart type="line" data={responseTimeChartData} />
      </Card>

      <Card title={t('health.healthDistribution')} variant="elevated">
        <Chart type="doughnut" data={healthDistributionChartData} />
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
              placeholder={t('providers.searchPlaceholder')}
            />
          </div>

          <div class="filter-group">
            <label for="health-filter-status">{t('health.status')}:</label>
            <select id="health-filter-status" class="filter-select" bind:value={filterHealth}>
              <option value="all">{t('common.all')}</option>
              <option value="healthy">{t('health.healthy')}</option>
              <option value="unhealthy">{t('health.unhealthy')}</option>
              <option value="disabled">{t('health.disabled')}</option>
            </select>
          </div>

          <Button variant="secondary" size="sm" onclick={clearFilters} title={t('health.clearFilters')} class="clear-button">
            {t('common.clear')}
          </Button>
        </div>
      </div>
    </Card>

    <div class="table-container">
      <table class="health-table">
        <thead>
          <tr>
            <th>{t('providers.name')}</th>
            <th>{t('providers.apiFormat')}</th>
            <th>{t('health.healthStatus')}</th>
            <th>{t('health.categoryHealthStatus')}</th>
            <th>{t('health.enabledStatus')}</th>
            <th>{t('health.priority')}</th>
            <th>{t('health.lastCheck')}</th>
            <th>{t('health.errorMessage')}</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredProviders as provider}
            {@const status = getStatusBadge(provider)}
            <tr class={!provider.enabled ? 'disabled-row' : ''}>
              <td class="name-cell">
                <span class="provider-name">{provider.name}</span>
              </td>
              <td class="format-cell">
                <Badge type={provider.api_format === 'anthropic' ? 'warning' : 'info'}>
                  {provider.api_format === 'anthropic' ? 'Anthropic' : 'OpenAI'}
                </Badge>
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
                            {catStatus.healthy ? t('health.healthy') : t('health.unhealthy')}
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
                  {provider.enabled ? t('providers.enabled') : t('providers.disabled')}
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
                  {@const truncated = truncateError(provider.error)}
                  <span
                    class="error-value clickable"
                    role="button"
                    tabindex="0"
                    onclick={() => showErrorMessage(provider.name, provider.error || '')}
                    onkeydown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        showErrorMessage(provider.name, provider.error || '');
                      }
                    }}
                    title={t('health.viewError')}
                  >
                    {truncated}
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
          {t('health.paginationInfo')
            .replace('{totalCount}', String(totalCount))
            .replace('{currentPage}', String(currentPage))
            .replace('{totalPages}', String(totalPages))}
        </div>
        <div class="pagination-controls">
          <Button
            variant="secondary"
            size="sm"
            disabled={currentPage === 1}
            onclick={() => handlePageChange(currentPage - 1)}
            title={t('common.previousPage')}
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
            onclick={() => handlePageChange(currentPage + 1)}
            title={t('common.nextPage')}
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
        <p>{t('providers.noMatch')}</p>
      </div>
    {/if}
  {/if}
</div>

<!-- Error Message Modal -->
<ErrorMessageModal
  show={showErrorModal}
  errorMessage={selectedError}
  title={`${t('health.errorMessage')} - ${selectedProviderName}`}
  on:close={closeErrorModal}
/>

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

  .realtime-status {
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: center;
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
    width: 100px;
  }

  .health-table th:nth-child(3) {
    width: 120px;
  }

  .health-table th:nth-child(4) {
    width: 200px;
  }

  .health-table th:nth-child(5) {
    width: 100px;
  }

  .health-table th:nth-child(6) {
    width: 80px;
  }

  .health-table th:nth-child(7) {
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
    min-width: 150px;
    max-width: 250px;
    overflow: hidden;
  }

  .error-value {
    display: block;
    width: 100%;
    color: var(--danger-color, #dc3545);
    font-size: 0.8125rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .error-value.clickable {
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
  }

  .error-value.clickable:hover {
    color: var(--danger-color, #dc3545);
    opacity: 0.8;
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

  /* 状态概览 */
  .status-overview {
    margin-bottom: var(--space-4);
  }

  .status-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-xl);
    padding: var(--space-8);
    display: flex;
    align-items: center;
    gap: var(--space-6);
  }

  .status-indicator {
    position: relative;
    width: 4rem;
    height: 4rem;
  }

  .status-dot {
    width: 100%;
    height: 100%;
    border-radius: var(--radius-full);
    background: var(--success);
  }

  .status-dot.active {
    box-shadow: 0 0 0 4px rgba(40, 167, 69, 0.2);
  }

  .status-pulse {
    position: absolute;
    inset: 0;
    border-radius: var(--radius-full);
    background: var(--success);
    opacity: 0.3;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
      opacity: 0.3;
    }
    50% {
      transform: scale(1.2);
      opacity: 0;
    }
    100% {
      transform: scale(1);
      opacity: 0.3;
    }
  }

  .status-content {
    flex: 1;
  }

  .status-title {
    font-size: var(--font-size-2xl);
    font-weight: var(--font-weight-bold);
    color: var(--text-primary);
    margin: 0 0 var(--space-2) 0;
  }

  .status-subtitle {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
    margin: 0;
  }

  .status-score {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .score-value {
    font-size: var(--font-size-4xl);
    font-weight: var(--font-weight-bold);
    color: var(--success);
    line-height: 1;
  }

  .score-label {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-top: var(--space-1);
  }

  /* 统计网格 */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--space-4);
    margin-bottom: var(--space-6);
  }

  /* 图表网格 */
  .charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: var(--space-6);
    margin-bottom: var(--space-6);
  }

  /* Responsive Design */
  @media (max-width: 1200px) {
    .health-table th:last-child {
      width: 200px;
    }
  }

  @media (max-width: 1024px) {
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

