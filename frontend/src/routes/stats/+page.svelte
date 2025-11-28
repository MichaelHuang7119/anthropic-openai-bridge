<script lang="ts">
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import Button from '$components/ui/Button.svelte';
  import Input from '$components/ui/Input.svelte';
  import Chart from '$components/ui/Chart.svelte';
  import ErrorMessageModal from '$components/ErrorMessageModal.svelte';
  import { statsService } from '$services/stats';
  import { providerService } from '$services/providers';
  import type { PerformanceSummary, RequestLog, TokenUsage } from '$services/stats';
  import type { Provider } from '$types/provider';
  import { toast } from '$stores/toast';

  let loading = true;
  let summary: PerformanceSummary | null = null;
  let requests: RequestLog[] = [];
  let tokenUsage: TokenUsage[] = [];
  let dateFilter = '7d'; // 7d, 30d, all
  
  // 请求日志数据（存储所有已加载的数据）
  let allRequestsData: RequestLog[] = [];
  
  // 请求日志分页相关
  let currentPage = 1;
  const pageSize = 5;
  let totalPages = 1;
  let totalCount = 0;
  let loadingRequests = false;
  
  // 请求日志显示数据（响应式，根据分页切片）
  $: requests = (() => {
    if (allRequestsData.length === 0) return [];
    
    // 客户端分页切片
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return allRequestsData.slice(start, end);
  })();
  
  // Token使用详情分页相关
  let tokenUsagePage = 1;
  const tokenUsagePageSize = 5;
  let tokenUsageTotalPages = 1;
  let tokenUsageTotalCount = 0;
  
  // 供应商统计筛选相关
  let providerStatsSearch = '';
  
  // 供应商统计分页相关
  let providerStatsPage = 1;
  const providerStatsPageSize = 5;
  let providerStatsTotalPages = 1;
  let providerStatsTotalCount = 0;
  
  // Token使用详情筛选相关
  let tokenUsageProviderFilter = '';
  let tokenUsageModelFilter = '';
  
  // 请求日志筛选相关
  let filterProvider = '';
  let filterModel = '';
  let filterStatus: 'all' | 'success' | 'failed' = 'all';
  let providers: Provider[] = [];
  let _availableModels: string[] = [];
  
  // 防抖定时器
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  
  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;

  onMount(async () => {
    abortController = new AbortController();
    try {
      await Promise.all([loadData(), loadProviders()]);
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
    
    // 清理防抖定时器
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  });

  async function loadProviders() {
    if (!abortController) return;
    try {
      providers = await providerService.getAll();
      // 提取所有模型
      const modelSet = new Set<string>();
      providers.forEach(p => {
        Object.values(p.models).flat().forEach(m => modelSet.add(m));
      });
      _availableModels = Array.from(modelSet).sort();
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load providers:', error);
    }
  }

  async function loadData() {
    if (!abortController) return;
    try {
      loading = true;
      
      const dateRange = getDateRange();
      const signal = abortController.signal;
      
      // 并行加载所有数据以提高性能
      const [summaryData, usageData] = await Promise.all([
        statsService.getSummary({ signal }),
        statsService.getTokenUsage({
          date_from: dateRange.from,
          date_to: dateRange.to
        }, { signal }),
        loadRequests(true) // 重置并加载最初的100条记录
      ]);
      
      // 检查是否已被取消
      if (signal.aborted) return;
      
      summary = summaryData;
      tokenUsage = usageData.summary;
      tokenUsageTotalCount = tokenUsage.length;
      tokenUsageTotalPages = Math.ceil(tokenUsageTotalCount / tokenUsagePageSize);
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load stats:', error);
      toast.error('加载性能数据失败');
    } finally {
      if (!abortController?.signal.aborted) {
        loading = false;
      }
    }
  }

  // 供应商统计过滤和分页（响应式）
  $: filteredProviderStats = (() => {
    if (!summary) return [];
    const entries = Object.entries(summary.provider_stats);
    let filtered = entries;
    
    if (providerStatsSearch.trim()) {
      const searchLower = providerStatsSearch.toLowerCase();
      filtered = entries.filter(([provider]) => provider.toLowerCase().includes(searchLower));
    }
    
    // 更新分页信息
    providerStatsTotalCount = filtered.length;
    providerStatsTotalPages = Math.ceil(providerStatsTotalCount / providerStatsPageSize);
    
    // 如果当前页超出范围或没有数据，重置到第一页
    if (providerStatsTotalPages === 0 || (providerStatsPage > providerStatsTotalPages && providerStatsTotalPages > 0)) {
      providerStatsPage = 1;
    }
    
    // 分页切片
    const start = (providerStatsPage - 1) * providerStatsPageSize;
    const end = start + providerStatsPageSize;
    return filtered.slice(start, end);
  })();

  function handleProviderStatsSearchChange() {
    providerStatsPage = 1;
  }
  
  function handleProviderStatsPageChange(newPage: number) {
    if (newPage >= 1 && newPage <= providerStatsTotalPages && newPage !== providerStatsPage) {
      providerStatsPage = newPage;
    }
  }
  
  function clearProviderStatsFilters() {
    providerStatsSearch = '';
    providerStatsPage = 1;
  }

  // Token使用详情过滤和分页（响应式）
  $: filteredTokenUsage = (() => {
    let filtered = tokenUsage;
    
    if (tokenUsageProviderFilter.trim()) {
      const filterLower = tokenUsageProviderFilter.toLowerCase().trim();
      filtered = filtered.filter(u => 
        u.provider_name.toLowerCase().includes(filterLower)
      );
    }
    
    if (tokenUsageModelFilter.trim()) {
      const filterLower = tokenUsageModelFilter.toLowerCase().trim();
      filtered = filtered.filter(u => 
        u.model.toLowerCase().includes(filterLower)
      );
    }
    
    tokenUsageTotalCount = filtered.length;
    tokenUsageTotalPages = Math.ceil(tokenUsageTotalCount / tokenUsagePageSize);
    
    // 如果当前页超出范围或没有数据，重置到第一页
    if (tokenUsageTotalPages === 0 || (tokenUsagePage > tokenUsageTotalPages && tokenUsageTotalPages > 0)) {
      tokenUsagePage = 1;
    }
    
    const start = (tokenUsagePage - 1) * tokenUsagePageSize;
    const end = start + tokenUsagePageSize;
    return filtered.slice(start, end);
  })();
  
  function handleTokenUsageFilterChange() {
    // 客户端过滤，实时搜索，不需要防抖
    tokenUsagePage = 1;
  }

  function handleTokenUsagePageChange(newPage: number) {
    if (newPage >= 1 && newPage <= tokenUsageTotalPages && newPage !== tokenUsagePage) {
      tokenUsagePage = newPage;
    }
  }

  function clearTokenUsageFilters() {
    tokenUsageProviderFilter = '';
    tokenUsageModelFilter = '';
    tokenUsagePage = 1;
  }

  // 添加状态变量来跟踪是否已加载所有记录
  let hasLoadedAll = false;
  let offset = 0;
  const initialLimit = 100;
  const loadMoreLimit = 1000;

  async function loadRequests(reset = true) {
    if (!abortController) return;
    try {
      if (reset) {
        loadingRequests = true;
        offset = 0;
        hasLoadedAll = false;
      } else {
        loadingRequests = true;
      }

      const dateRange = getDateRange();

      const params: any = {
        limit: reset ? initialLimit : loadMoreLimit,
        offset: reset ? 0 : offset,
        date_from: dateRange.from,
        date_to: dateRange.to
      };
      
      // 状态筛选仍然发送到服务器
      if (filterStatus === 'success') {
        params.status_code = 200;
      } else if (filterStatus === 'failed') {
        // 失败状态：400+ 的状态码（使用范围查询）
        params.status_min = 400;
      }

      // 注意：不发送 provider_name 和 model 参数，改为客户端搜索
      const result = await statsService.getRequests(params, { signal: abortController.signal });

      // 检查是否已被取消
      if (abortController.signal.aborted) return;

      const newRequests = result.data;

      // 对新获取的请求进行客户端过滤
      let filteredNewRequests = newRequests;
      if (filterProvider.trim()) {
        const filterLower = filterProvider.toLowerCase().trim();
        filteredNewRequests = filteredNewRequests.filter(r =>
          r.provider_name.toLowerCase().includes(filterLower)
        );
      }

      if (filterModel.trim()) {
        const filterLower = filterModel.toLowerCase().trim();
        filteredNewRequests = filteredNewRequests.filter(r =>
          r.model.toLowerCase().includes(filterLower)
        );
      }

      if (reset) {
        // 重置时替换所有数据
        allRequestsData = filteredNewRequests;
      } else {
        // 添加新数据到现有数据
        allRequestsData = [...allRequestsData, ...filteredNewRequests];
      }

      // 更新偏移量用于下一次请求
      offset += newRequests.length;

      // 检查是否已加载完所有服务器数据（没有更多数据返回）
      if (newRequests.length < params.limit) {
        hasLoadedAll = true;
      }

      // 客户端分页计算
      totalCount = allRequestsData.length;
      totalPages = Math.ceil(totalCount / pageSize);

      // 确保当前页在有效范围内
      if (totalPages === 0) {
        // 没有数据时，设置为第1页
        currentPage = 1;
      } else if (totalPages > 0 && currentPage > totalPages) {
        currentPage = totalPages;
      } else if (currentPage < 1) {
        currentPage = 1;
      }

      // requests 会通过响应式语句自动更新
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load requests:', error);
      toast.error('加载请求日志失败');
    } finally {
      if (!abortController?.signal.aborted) {
        loadingRequests = false;
      }
    }
  }


  function handleFilterChange() {
    // 防抖：300ms 后执行
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      loadRequests(true); // 重置并重新加载最初的100条记录
    }, 300);
  }

  function handlePageChange(newPage: number) {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      currentPage = newPage;
      // 不需要重新加载数据，响应式语句会自动更新 requests
    }
  }

  async function loadMore() {
    if (hasLoadedAll || loadingRequests) return;
    await loadRequests(false); // 不重置数据，而是加载更多
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
    try {
      // SQLite 返回的时间格式通常是 "YYYY-MM-DD HH:MM:SS"，没有时区信息
      // 假设它是 UTC 时间，添加 'Z' 后缀以确保正确解析
      let dateStrToParse = dateStr;
      if (dateStr.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
        // 格式为 "YYYY-MM-DD HH:MM:SS"，假设是 UTC 时间
        dateStrToParse = dateStr.replace(' ', 'T') + 'Z';
      } else if (dateStr.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/)) {
        // 格式为 "YYYY-MM-DDTHH:MM:SS"，假设是 UTC 时间
        dateStrToParse = dateStr + 'Z';
      }
      
      const date = new Date(dateStrToParse);
      const now = new Date();
      
      // 检查日期是否有效
      if (isNaN(date.getTime())) {
        return dateStr; // 如果日期无效，返回原始字符串
      }
      
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      
      // 如果是今天，显示相对时间
      if (diffMins < 1) {
        return '刚刚';
      } else if (diffMins < 60) {
        return `${diffMins}分钟前`;
      } else if (diffHours < 24) {
        // 检查是否是同一天（使用本地时区）
        const dateDay = date.getDate();
        const nowDay = now.getDate();
        const dateMonth = date.getMonth();
        const nowMonth = now.getMonth();
        const dateYear = date.getFullYear();
        const nowYear = now.getFullYear();
        
        if (dateYear === nowYear && dateMonth === nowMonth && dateDay === nowDay) {
          return `${diffHours}小时前`;
        }
      }
      
      // 如果大于等于1天且小于7天，显示天数
      if (diffDays >= 1 && diffDays < 7) {
        return `${diffDays}天前`;
      }
      
      // 否则显示完整时间，使用明确的时区选项
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      });
    } catch {
      return dateStr;
    }
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

  function clearFilters() {
    filterProvider = '';
    filterModel = '';
    filterStatus = 'all';
    currentPage = 1;
    handleFilterChange();
  }

  function truncateError(errorMessage: string, maxLength: number = 50): string {
    if (!errorMessage) return '';
    if (errorMessage.length <= maxLength) return errorMessage;
    return errorMessage.substring(0, maxLength) + '...';
  }

  // 错误信息模态框相关
  let showErrorModal = false;
  let selectedError: string = '';
  let selectedRequestInfo: string = '';

  function showErrorMessage(request: RequestLog) {
    selectedRequestInfo = `请求 ID: ${request.request_id || 'N/A'} | 供应商: ${request.provider_name || 'N/A'} | 模型: ${request.model || 'N/A'}`;
    selectedError = request.error_message || '';
    showErrorModal = true;
  }

  function closeErrorModal() {
    showErrorModal = false;
    selectedError = '';
    selectedRequestInfo = '';
  }

  // 供应商Token使用饼图数据
  $: providerTokenChartData = (() => {
    if (!summary) return null;

    const providers = Object.entries(summary.provider_stats);
    const totalTokensData = providers.map(([name, stats]) => ({
      name,
      value: stats.total_tokens
    }));

    return {
      labels: totalTokensData.map(d => d.name),
      datasets: [
        {
          label: 'Token 使用量',
          data: totalTokensData.map(d => d.value),
          backgroundColor: [
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 99, 132, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)',
            'rgba(199, 199, 199, 0.7)',
            'rgba(83, 102, 255, 0.7)',
            'rgba(255, 99, 255, 0.7)',
            'rgba(99, 255, 132, 0.7)'
          ],
          borderColor: [
            'rgba(54, 162, 235, 1)',
            'rgba(255, 99, 132, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)',
            'rgba(199, 199, 199, 1)',
            'rgba(83, 102, 255, 1)',
            'rgba(255, 99, 255, 1)',
            'rgba(99, 255, 132, 1)'
          ],
          borderWidth: 1
        }
      ]
    };
  })();

  // Token使用趋势图数据
  $: tokenUsageTrendChartData = (() => {
    if (!tokenUsage || tokenUsage.length === 0) return null;

    // 按日期聚合数据
    const dateMap = new Map();
    tokenUsage.forEach(usage => {
      const date = usage.date;
      if (!dateMap.has(date)) {
        dateMap.set(date, {
          date,
          totalTokens: 0,
          totalCost: 0,
          requestCount: 0
        });
      }
      const data = dateMap.get(date);
      data.totalTokens += usage.total_input_tokens + usage.total_output_tokens;
      data.totalCost += usage.total_cost_estimate;
      data.requestCount += usage.request_count;
    });

    const sortedDates = Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));

    return {
      labels: sortedDates.map(d => d.date),
      datasets: [
        {
          label: 'Token 使用量',
          data: sortedDates.map(d => d.totalTokens),
          borderColor: 'rgba(54, 162, 235, 1)',
          backgroundColor: 'rgba(54, 162, 235, 0.2)',
          tension: 0.4,
          fill: true
        },
        {
          label: '成本估算',
          data: sortedDates.map(d => d.totalCost),
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 0.2)',
          tension: 0.4,
          fill: true,
          yAxisID: 'y1'
        }
      ]
    };
  })();

  // Token使用柱状图数据（按供应商）
  $: tokenUsageBarChartData = (() => {
    if (!tokenUsage || tokenUsage.length === 0) return null;

    // 按供应商聚合数据
    const providerMap = new Map();
    tokenUsage.forEach(usage => {
      const provider = usage.provider_name;
      if (!providerMap.has(provider)) {
        providerMap.set(provider, {
          provider,
          totalTokens: 0,
          totalCost: 0
        });
      }
      const data = providerMap.get(provider);
      data.totalTokens += usage.total_input_tokens + usage.total_output_tokens;
      data.totalCost += usage.total_cost_estimate;
    });

    const sortedProviders = Array.from(providerMap.values())
      .sort((a, b) => b.totalTokens - a.totalTokens)
      .slice(0, 10); // 只显示前10个供应商

    return {
      labels: sortedProviders.map(d => d.provider),
      datasets: [
        {
          label: 'Token 使用量',
          data: sortedProviders.map(d => d.totalTokens),
          backgroundColor: 'rgba(54, 162, 235, 0.7)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }
      ]
    };
  })();
</script>

<div class="container">
  <div class="page-header">
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
        <!-- 图表展示 -->
        {#if providerTokenChartData}
          <div class="charts-section">
            <h3 class="chart-title">Token 使用占比</h3>
            <div class="chart-wrapper">
              <Chart
                type="pie"
                data={providerTokenChartData}
                options={{
                  plugins: {
                    legend: {
                      position: 'right',
                      labels: {
                        color: 'var(--text-primary)',
                        padding: 15,
                        font: {
                          size: 12
                        }
                      }
                    },
                    tooltip: {
                      callbacks: {
                        label: (context) => {
                          const label = context.label || '';
                          const value = formatNumber(context.parsed as number);
                          const total = (context.dataset.data as number[]).reduce((a, b) => a + b, 0);
                          const percentage = total > 0 ? ((context.parsed as number / total) * 100).toFixed(2) : 0;
                          return `${label}: ${value} (${percentage}%)`;
                        }
                      }
                    }
                  }
                }}
                height={350}
              />
            </div>
          </div>
        {/if}

        <div class="filters">
            <div class="filter-row">
              <div class="filter-group search-group">
                <Input
                  type="text"
                  bind:value={providerStatsSearch}
                  on:input={handleProviderStatsSearchChange}
                  placeholder="搜索供应商名称..."
                />
              </div>

              <Button variant="secondary" size="sm" on:click={clearProviderStatsFilters} title="清除筛选" class="clear-button">
                清除
              </Button>
            </div>
          </div>

          {#if filteredProviderStats.length > 0}
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
                  {#each filteredProviderStats as [provider, stats]}
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
            
            <!-- 供应商统计分页控件 -->
            {#if providerStatsTotalPages > 1}
              <div class="pagination">
                <div class="pagination-info">
                  共 {providerStatsTotalCount} 条记录，第 {providerStatsPage} / {providerStatsTotalPages} 页
                </div>
                <div class="pagination-controls">
                  <Button 
                    variant="secondary" 
                    size="sm" 
                    disabled={providerStatsPage === 1}
                    on:click={() => handleProviderStatsPageChange(providerStatsPage - 1)}
                    title="上一页"
                    class="icon-button"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                  </Button>
                  <span class="page-info">{providerStatsPage} / {providerStatsTotalPages}</span>
                  <Button 
                    variant="secondary" 
                    size="sm" 
                    disabled={providerStatsPage === providerStatsTotalPages}
                    on:click={() => handleProviderStatsPageChange(providerStatsPage + 1)}
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
          {:else}
            <div class="empty">
              <p>没有匹配的供应商</p>
            </div>
          {/if}
      </Card>
    {/if}

    <!-- Token 使用详情 -->
    {#if tokenUsage.length > 0}
      <Card title="Token 使用详情" subtitle="按日期和供应商统计">
        <!-- 图表展示 -->
        <div class="charts-section">
          {#if tokenUsageTrendChartData}
            <h3 class="chart-title">Token 使用趋势</h3>
            <div class="chart-wrapper">
              <Chart
                type="line"
                data={tokenUsageTrendChartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  interaction: {
                    mode: 'index',
                    intersect: false
                  },
                  plugins: {
                    legend: {
                      position: 'top',
                      labels: {
                        color: 'var(--text-primary)',
                        padding: 15,
                        font: {
                          size: 12
                        }
                      }
                    },
                    tooltip: {
                      callbacks: {
                        label: (context) => {
                          const label = context.dataset.label || '';
                          const value = context.parsed.y || 0;
                          const formattedValue = label === '成本估算' ? formatCurrency(value) : formatNumber(value);
                          return `${label}: ${formattedValue}`;
                        }
                      }
                    }
                  },
                  scales: {
                    x: {
                      ticks: {
                        color: 'var(--text-secondary)'
                      },
                      grid: {
                        color: 'var(--border-color)'
                      }
                    },
                    y: {
                      type: 'linear',
                      display: true,
                      position: 'left',
                      ticks: {
                        color: 'var(--text-secondary)',
                        callback: (value) => formatNumber(value as number)
                      },
                      grid: {
                        color: 'var(--border-color)'
                      }
                    },
                    y1: {
                      type: 'linear',
                      display: true,
                      position: 'right',
                      ticks: {
                        color: 'var(--text-secondary)',
                        callback: (value) => formatCurrency(value as number)
                      },
                      grid: {
                        drawOnChartArea: false
                      }
                    }
                  }
                }}
                height={350}
              />
            </div>
          {/if}

          {#if tokenUsageBarChartData}
            <h3 class="chart-title">供应商 Token 使用排行</h3>
            <div class="chart-wrapper">
              <Chart
                type="bar"
                data={tokenUsageBarChartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      display: false
                    },
                    tooltip: {
                      callbacks: {
                        label: (context) => {
                          return `Token 使用量: ${formatNumber(context.parsed.y || 0)}`;
                        }
                      }
                    }
                  },
                  scales: {
                    x: {
                      ticks: {
                        color: 'var(--text-secondary)',
                        maxRotation: 45,
                        minRotation: 45
                      },
                      grid: {
                        color: 'var(--border-color)'
                      }
                    },
                    y: {
                      ticks: {
                        color: 'var(--text-secondary)',
                        callback: (value) => formatNumber(value as number)
                      },
                      grid: {
                        color: 'var(--border-color)'
                      }
                    }
                  }
                }}
                height={350}
              />
            </div>
          {/if}
        </div>

        <div class="filters">
            <div class="filter-row">
              <div class="filter-group">
                <label for="token-provider-filter">供应商:</label>
                <Input
                  id="token-provider-filter"
                  type="text"
                  placeholder="搜索供应商..."
                  bind:value={tokenUsageProviderFilter}
                  on:input={handleTokenUsageFilterChange}
                />
              </div>

              <div class="filter-group">
                <label for="token-model-filter">模型:</label>
                <Input
                  id="token-model-filter"
                  type="text"
                  placeholder="搜索模型..."
                  bind:value={tokenUsageModelFilter}
                  on:input={handleTokenUsageFilterChange}
                />
              </div>

              <Button variant="secondary" size="sm" on:click={clearTokenUsageFilters} title="清除筛选" class="clear-button">
                清除
              </Button>
            </div>
          </div>
          
          {#if filteredTokenUsage.length > 0}
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
                  {#each filteredTokenUsage as usage}
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
            
            <!-- Token使用详情分页控件 -->
            {#if tokenUsageTotalPages > 1}
              <div class="pagination">
                <div class="pagination-info">
                  共 {tokenUsageTotalCount} 条记录，第 {tokenUsagePage} / {tokenUsageTotalPages} 页
                </div>
                <div class="pagination-controls">
                  <Button 
                    variant="secondary" 
                    size="sm" 
                    disabled={tokenUsagePage === 1}
                    on:click={() => handleTokenUsagePageChange(tokenUsagePage - 1)}
                    title="上一页"
                    class="icon-button"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                  </Button>
                  <span class="page-info">{tokenUsagePage} / {tokenUsageTotalPages}</span>
                  <Button 
                    variant="secondary" 
                    size="sm" 
                    disabled={tokenUsagePage === tokenUsageTotalPages}
                    on:click={() => handleTokenUsagePageChange(tokenUsagePage + 1)}
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
          {:else}
            <div class="empty">
              <p>没有匹配的记录</p>
            </div>
          {/if}
      </Card>
    {/if}

    <!-- 请求日志 -->
    <Card title="请求日志" subtitle="API请求记录">
      <!-- 筛选器 -->
      <div class="filters">
          <div class="filter-row">
            <div class="filter-group">
              <label for="request-provider-filter">供应商:</label>
              <Input
                id="request-provider-filter"
                type="text"
                placeholder="搜索供应商..."
                bind:value={filterProvider}
                on:input={handleFilterChange}
              />
            </div>

            <div class="filter-group">
              <label for="request-model-filter">模型:</label>
              <Input
                id="request-model-filter"
                type="text"
                placeholder="搜索模型..."
                bind:value={filterModel}
                on:input={handleFilterChange}
              />
            </div>

            <div class="filter-group">
              <label for="request-status-filter">状态:</label>
              <select id="request-status-filter" class="filter-select" bind:value={filterStatus} on:change={handleFilterChange}>
                <option value="all">全部</option>
                <option value="success">成功</option>
                <option value="failed">失败</option>
              </select>
            </div>
            
            <Button variant="secondary" size="sm" on:click={clearFilters} title="清除筛选" class="clear-button">
              清除
            </Button>
          </div>
        </div>

        {#if loadingRequests}
          <div class="loading-requests">
            <p>加载中...</p>
          </div>
        {:else if requests.length > 0}
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
                {#each requests as request (request.id)}
                  {@const badge = getStatusBadge(request.status_code)}
                  <tr>
                    <td class="time-cell">{formatDate(request.created_at)}</td>
                    <td class="provider-name">{request.provider_name}</td>
                    <td class="model-cell">{request.model}</td>
                    <td>
                      <Badge type={badge.type}>{badge.text}</Badge>
                    </td>
                    <td>{request.response_time_ms ? `${request.response_time_ms.toFixed(0)}ms` : '-'}</td>
                    <td>{request.input_tokens ? formatNumber(request.input_tokens) : '-'}</td>
                    <td>{request.output_tokens ? formatNumber(request.output_tokens) : '-'}</td>
                    <td class="error-cell">
                      {#if request.error_message}
                        {@const truncated = truncateError(request.error_message)}
                        <span
                          class="error-preview clickable"
                          role="button"
                          tabindex="0"
                          on:click={() => showErrorMessage(request)}
                          on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && showErrorMessage(request)}
                          title="点击查看完整错误信息"
                        >
                          {truncated}
                        </span>
                      {:else}
                        <span class="no-error">-</span>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          <!-- 分页控件 -->
          <div class="pagination">
            <div class="pagination-info">
              共 {formatNumber(totalCount)} 条记录，第 {currentPage} / {totalPages} 页
            </div>
            <div class="pagination-controls">
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage === 1 || loadingRequests}
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
                disabled={currentPage === totalPages || loadingRequests}
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

          <!-- 加载更多按钮 -->
          {#if !hasLoadedAll}
            <div class="load-more-container">
              <Button
                variant="secondary"
                on:click={loadMore}
                disabled={loadingRequests}
                class="load-more-button"
                title="新增1000条记录"
              >
                {#if loadingRequests}
                  <svg class="loading-spinner" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  <span>加载中...</span>
                {:else}
                  <svg class="more-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M5 12h14" />
                    <path d="M12 5v14" />
                  </svg>
                  <span>查看更多</span>
                {/if}
              </Button>
            </div>
          {/if}
        {:else}
          <div class="empty-requests">
            <p>暂无请求记录</p>
          </div>
        {/if}
    </Card>
  {:else}
    <div class="empty">
      <p>暂无性能数据</p>
    </div>
  {/if}
</div>

<!-- Error Message Modal -->
<ErrorMessageModal
  show={showErrorModal}
  errorMessage={selectedError}
  title={selectedRequestInfo ? `错误信息 - ${selectedRequestInfo}` : '错误信息'}
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
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
  }

  .stats-table {
    width: 100%;
    min-width: 900px;
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
    white-space: nowrap;
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

  .time-cell {
    white-space: nowrap;
    font-size: 0.8125rem;
  }

  .model-cell {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
    font-size: 0.8125rem;
  }

  .error-cell {
    min-width: 200px;
    max-width: 300px;
    font-size: 0.8125rem;
    overflow: hidden;
  }

  .error-preview {
    font-size: 0.875rem;
    color: var(--danger-color, #dc3545);
    line-height: 1.4;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .error-preview.clickable {
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
  }

  .error-preview.clickable:hover {
    color: var(--danger-color, #dc3545);
    opacity: 0.8;
  }

  .no-error {
    color: var(--text-tertiary);
  }


  .filters {
    display: flex;
    flex-direction: column;
    gap: 0;
    padding: 1rem;
    background: var(--bg-tertiary);
    border-radius: 0.5rem;
    margin-bottom: 1rem;
  }

  .filter-row {
    display: flex;
    gap: 0.75rem;
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
    color: var(--text-secondary);
    white-space: nowrap;
    font-weight: 500;
    margin: 0;
  }

  .filter-select {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    min-width: 150px;
    height: 2.5rem;
  }

  .filter-select:focus {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding: 1rem;
    background: var(--bg-tertiary);
    border-radius: 0.5rem;
  }

  .pagination-info {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .page-info {
    font-size: 0.875rem;
    color: var(--text-primary);
    min-width: 60px;
    text-align: center;
  }

  .loading-requests,
  .empty-requests {
    text-align: center;
    padding: 2rem;
    color: var(--text-secondary);
  }

  .load-more-container {
    display: flex;
    justify-content: center;
    margin-top: 1rem;
    padding: 1rem;
  }

  .loading-spinner {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
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

  /* 图表样式 */
  .charts-section {
    display: flex;
    flex-direction: column;
    gap: 2rem;
    margin-bottom: 1.5rem;
  }

  .chart-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 1rem;
    padding-left: 0.5rem;
    border-left: 3px solid var(--primary-color);
  }

  .chart-wrapper {
    background: var(--bg-primary);
    padding: 1.5rem;
    border-radius: 0.5rem;
    border: 1px solid var(--border-color);
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

    .filters {
      flex-direction: column;
      align-items: stretch;
    }

    .filter-group {
      width: 100%;
    }

    .filter-select {
      flex: 1;
    }

    .pagination {
      flex-direction: column;
      gap: 1rem;
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
