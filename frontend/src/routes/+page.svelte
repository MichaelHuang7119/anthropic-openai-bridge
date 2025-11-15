<script lang="ts">
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import Button from '$components/ui/Button.svelte';
  import { providers, providerStats } from '$stores/providers';
  import { healthStatus, lastHealthCheck } from '$stores/health';
  import { providerService } from '$services/providers';
  import { authService } from '$services/auth';
  import { toast } from '$stores/toast';
  import Input from '$components/ui/Input.svelte';

  let loading = true;
  let currentUrl = '';
  let copySuccess = false;
  
  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;
  
  // 供应商概览搜索和筛选
  let providerSearchQuery = '';
  let providerFilterEnabled: 'all' | 'enabled' | 'disabled' = 'all';
  const maxDisplayProviders = 5; // 首页最多显示5个
  
  // 客户端过滤
  $: filteredProvidersForPreview = $providers.filter(p => {
    // 搜索过滤
    if (providerSearchQuery.trim()) {
      const query = providerSearchQuery.toLowerCase();
      if (!p.name.toLowerCase().includes(query) && 
          !p.base_url.toLowerCase().includes(query)) {
        return false;
      }
    }
    
    // 状态过滤
    if (providerFilterEnabled === 'enabled' && !p.enabled) return false;
    if (providerFilterEnabled === 'disabled' && p.enabled) return false;
    
    return true;
  }).slice(0, maxDisplayProviders);
  
  // 计算是否有更多供应商（优化：复用过滤逻辑）
  $: allFilteredProviders = $providers.filter(p => {
    if (providerSearchQuery.trim()) {
      const query = providerSearchQuery.toLowerCase();
      if (!p.name.toLowerCase().includes(query) && 
          !p.base_url.toLowerCase().includes(query)) {
        return false;
      }
    }
    if (providerFilterEnabled === 'enabled' && !p.enabled) return false;
    if (providerFilterEnabled === 'disabled' && p.enabled) return false;
    return true;
  });
  
  $: hasMoreProviders = filteredProvidersForPreview.length < allFilteredProviders.length;

  onMount(async () => {
    // 确保已认证后再加载数据
    if (!authService.isAuthenticated()) {
      return;
    }

    abortController = new AbortController();
    try {
      // 获取当前 URL
      if (browser) {
        currentUrl = window.location.origin;
      }

      // 加载供应商
      const providersData = await providerService.getAll({ signal: abortController.signal });
      
      // 检查是否已被取消
      if (abortController.signal.aborted) return;
      
      providers.set(providersData);

      // 不自动加载健康状态 - 仅在用户手动刷新时加载
      // 健康状态检查会消耗API调用和token
      // 但如果store中已有健康数据，则显示
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load dashboard data:', error);
      toast.error('加载数据失败');
    } finally {
      if (!abortController?.signal.aborted) {
        loading = false;
      }
    }
  });

  onDestroy(() => {
    // 取消所有进行中的请求
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
  });

  async function copyToClipboard(text: string) {
    if (!browser) return;
    
    // 优先使用现代 Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        copySuccess = true;
        toast.success('已复制到剪贴板');
        setTimeout(() => {
          copySuccess = false;
        }, 2000);
        return;
      } catch (error) {
        console.error('Clipboard API failed:', error);
        // 继续尝试降级方案
      }
    }
    
    // 降级方案：使用传统的 execCommand
    try {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);
      
      if (successful) {
        copySuccess = true;
        toast.success('已复制到剪贴板');
        setTimeout(() => {
          copySuccess = false;
        }, 2000);
      } else {
        throw new Error('execCommand failed');
      }
    } catch (error) {
      console.error('Failed to copy:', error);
      toast.error('复制失败，请手动复制');
    }
  }

  // 计算健康状态统计（基于store中的数据）
  $: healthyCount = $healthStatus.providers.filter(p => p.healthy === true).length;
  $: unhealthyCount = $healthStatus.providers.filter(p => p.healthy === false).length;
  $: hasHealthData = $healthStatus.providers.length > 0 && healthyCount + unhealthyCount > 0;

  // 使用后端返回的总体状态，而不是自己计算
  $: overallStatus = $healthStatus.status;
  $: statusBadgeType = 
    overallStatus === 'healthy' ? 'success' as const : 
    overallStatus === 'partial' ? 'warning' as const : 
    overallStatus === 'unhealthy' ? 'danger' as const : 
    'info' as const;
  $: statusBadgeText = 
    overallStatus === 'healthy' ? '健康' : 
    overallStatus === 'partial' ? '部分健康' : 
    overallStatus === 'unhealthy' ? '不健康' : 
    '未检查';

  $: anthropicBaseUrl = currentUrl || 'http://localhost:5175';
  $: configCommand = `export ANTHROPIC_BASE_URL=${anthropicBaseUrl}\nexport ANTHROPIC_API_KEY="any-value"`;
</script>

<div class="container">

  {#if loading}
    <div class="loading">
      <p>加载中...</p>
    </div>
  {:else}
    <div class="stats-grid">
      <Card title="供应商统计" subtitle="供应商总体情况">
        <div slot="title">
          <Badge type="info">总计 {$providerStats.total}</Badge>
        </div>
        <div class="stat-items">
          <div class="stat-item">
            <span class="label">已启用</span>
            <span class="value success">{$providerStats.enabled}</span>
          </div>
          <div class="stat-item">
            <span class="label">已禁用</span>
            <span class="value danger">{$providerStats.disabled}</span>
          </div>
        </div>
      </Card>

      <Card title="健康状态" subtitle={hasHealthData ? '供应商健康状态概览' : '点击健康监控页面手动检查'}>
        <div slot="title">
          {#if hasHealthData}
            <Badge type={statusBadgeType}>{statusBadgeText}</Badge>
          {:else}
            <Badge type="info">未检查</Badge>
          {/if}
        </div>
        <div class="stat-items">
          <div class="stat-item">
            <span class="label">健康</span>
            <span class="value success">{healthyCount}</span>
          </div>
          <div class="stat-item">
            <span class="label">不健康</span>
            <span class="value danger">{unhealthyCount}</span>
          </div>
          {#if !hasHealthData}
            <div class="stat-item">
              <span class="label">操作</span>
              <a href="/health" class="value link">前往健康监控页面检查</a>
            </div>
          {/if}
        </div>
      </Card>

      <Card title="系统信息" subtitle="当前系统状态">
        <div class="sys-info">
          <div class="info-item">
            <span class="label">前端状态</span>
            <Badge type="success">运行中</Badge>
          </div>
          <div class="info-item">
            <span class="label">最后检查</span>
            <span class="value">{$lastHealthCheck ? (() => {
              try {
                const date = $lastHealthCheck instanceof Date ? $lastHealthCheck : new Date($lastHealthCheck);
                if (isNaN(date.getTime())) return '未检查';
                return date.toLocaleString('zh-CN', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                });
              } catch {
                return '未检查';
              }
            })() : '未检查'}</span>
          </div>
          <div class="info-item">
            <span class="label">检查模式</span>
            <span class="value">手动模式</span>
          </div>
        </div>
      </Card>
    </div>

    <div class="config-section">
      <Card title="Claude Code 配置" subtitle="在 Claude Code 中使用本服务">
        <div class="config-content">
          <p class="config-description">
            请在 Claude Code 中配置以下环境变量，然后启动 Claude Code 进行 Vibe Coding：
          </p>
          <div class="config-code">
            <div class="code-header">
              <span class="code-label">环境变量配置</span>
              <Button variant="secondary" size="sm" on:click={() => copyToClipboard(configCommand)} title={copySuccess ? '已复制' : '复制'} class="icon-button">
                {#if copySuccess}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                {:else}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                {/if}
              </Button>
            </div>
            <pre class="code-block"><code>export ANTHROPIC_BASE_URL={anthropicBaseUrl}
export ANTHROPIC_API_KEY="any-value"</code></pre>
          </div>
          <div class="config-note">
            <p><strong>方式一：</strong>在 Claude Code 设置中配置环境变量</p>
            <p><strong>方式二：</strong>在启动 Claude Code 前执行上述命令</p>
            <p class="note-text">💡 提示：当前服务地址为 <code>{anthropicBaseUrl}</code>，已自动填充到配置中</p>
            <div class="api-key-note">
              <p><strong>关于 ANTHROPIC_API_KEY：</strong></p>
              <ul>
                <li><strong>开发模式：</strong>如果后端启用了开发模式（<code>--dev</code>），API Key 可以是任意值，如 <code>"any-value"</code>、<code>"dev"</code>、<code>"test"</code> 等，或者设置为空字符串</li>
                <li><strong>生产模式：</strong>如果后端未启用开发模式，必须使用有效的 API Key（在"API Key 管理"页面创建）</li>
                <li><strong>检查模式：</strong>后端启动时会显示当前模式，开发模式会显示 <code>Development Mode: ✅ Enabled</code></li>
              </ul>
            </div>
          </div>
        </div>
      </Card>
    </div>

    <div class="providers-preview">
      <Card title="供应商概览" subtitle={$providers.length > 0 ? `共 ${$providers.length} 个供应商` : '暂无供应商配置'}>
        <div slot="titleActions">
          {#if $providers.length > 0}
            <a href="/providers" class="view-all">查看全部 →</a>
          {/if}
        </div>

        {#if $providers.length === 0}
          <div class="empty-state">
            <p>暂无供应商配置</p>
            <a href="/providers" class="add-link">立即添加 →</a>
          </div>
        {:else}
          <!-- 搜索和筛选 -->
          <div class="filters">
            <div class="filter-row">
              <div class="filter-group search-group">
                <Input
                  type="text"
                  bind:value={providerSearchQuery}
                  placeholder="搜索供应商名称或URL..."
                />
              </div>
              
              <div class="filter-group">
                <label for="provider-filter-status">状态:</label>
                <select id="provider-filter-status" class="filter-select" bind:value={providerFilterEnabled}>
                  <option value="all">全部</option>
                  <option value="enabled">已启用</option>
                  <option value="disabled">已禁用</option>
                </select>
              </div>
            </div>
          </div>
          
          {#if filteredProvidersForPreview.length > 0}
            <div class="table-container">
              <table class="providers-table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>状态</th>
                    <th>Base URL</th>
                    <th>模型数量</th>
                  </tr>
                </thead>
                <tbody>
                  {#each filteredProvidersForPreview as provider}
                    <tr class={!provider.enabled ? 'disabled-row' : ''}>
                      <td class="name-cell">
                        <span class="provider-name">{provider.name}</span>
                      </td>
                      <td>
                        <Badge type={provider.enabled ? 'success' : 'secondary'}>
                          {provider.enabled ? '已启用' : '已禁用'}
                        </Badge>
                      </td>
                      <td class="url-cell">
                        <span class="url-text" title={provider.base_url}>{provider.base_url}</span>
                      </td>
                      <td class="models-cell">
                        <div class="models-badge">
                          <Badge type="info">大 {provider.models.big?.length || 0}</Badge>
                          <Badge type="info">中 {provider.models.middle?.length || 0}</Badge>
                          <Badge type="info">小 {provider.models.small?.length || 0}</Badge>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>

            {#if hasMoreProviders}
              <div class="view-more">
                <a href="/providers" class="btn-link">查看全部 {$providers.length} 个供应商 →</a>
              </div>
            {/if}
          {:else}
            <div class="empty-state">
              <p>没有匹配的供应商</p>
            </div>
          {/if}
        {/if}
      </Card>
    </div>
  {/if}
</div>

<style>
  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary, #666);
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 3rem;
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
  }

  .label {
    color: var(--text-secondary, #666);
    font-size: 0.875rem;
  }

  .value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .value.success {
    color: var(--success-color, #28a745);
  }

  :global([data-theme="dark"]) .value.success {
    color: #238636;
  }

  .value.danger {
    color: var(--danger-color, #dc3545);
  }

  :global([data-theme="dark"]) .value.danger {
    color: #f85149;
  }

  .value.link {
    color: var(--link-color, var(--primary-color, #007bff));
    font-size: 1rem;
    font-weight: 500;
    text-decoration: none;
  }

  .value.link:hover {
    color: var(--link-hover-color, var(--primary-color, #0056b3));
    text-decoration: underline;
  }

  :global([data-theme="dark"]) .value.link {
    color: #58a6ff;
  }

  :global([data-theme="dark"]) .value.link:hover {
    color: #79c0ff;
  }

  .sys-info {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .sys-info .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .sys-info .value {
    font-size: 0.875rem;
    font-weight: 400;
    color: var(--text-primary, #1a1a1a);
  }

  .providers-preview {
    margin-top: 2rem;
  }

  .filters {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
    margin-bottom: 1rem;
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

  .view-all {
    color: var(--link-color, var(--primary-color, #007bff));
    text-decoration: none;
    font-weight: 500;
    font-size: 0.875rem;
    transition: color 0.2s;
  }

  .view-all:hover {
    color: var(--link-hover-color, var(--primary-color, #0056b3));
    text-decoration: underline;
  }

  :global([data-theme="dark"]) .view-all {
    color: #58a6ff;
  }

  :global([data-theme="dark"]) .view-all:hover {
    color: #79c0ff;
  }

  .empty-state {
    text-align: center;
    padding: 3rem;
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    border: 1px solid var(--border-color, #e0e0e0);
  }

  .empty-state p {
    color: var(--text-secondary, #666);
    margin-bottom: 1rem;
  }

  .add-link {
    color: var(--link-color, var(--primary-color, #007bff));
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
  }

  .add-link:hover {
    color: var(--link-hover-color, var(--primary-color, #0056b3));
    text-decoration: underline;
  }

  :global([data-theme="dark"]) .add-link {
    color: #58a6ff;
  }

  :global([data-theme="dark"]) .add-link:hover {
    color: #79c0ff;
  }

  .table-container {
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    border: 1px solid var(--border-color, #e0e0e0);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow-x: auto;
  }

  :global([data-theme="dark"]) .table-container {
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }

  .providers-table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .providers-table thead {
    background: var(--bg-tertiary, #f8f9fa);
    border-bottom: 2px solid var(--border-color, #dee2e6);
  }

  .providers-table th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary, #495057);
    white-space: nowrap;
  }

  .providers-table th:first-child {
    width: 150px;
  }

  .providers-table th:nth-child(2) {
    width: 100px;
  }

  .providers-table th:nth-child(3) {
    width: 250px;
  }

  .providers-table th:last-child {
    width: 180px;
  }

  .providers-table tbody tr {
    border-bottom: 1px solid var(--border-color, #dee2e6);
    transition: background-color 0.2s;
  }

  .providers-table tbody tr:hover {
    background: var(--bg-tertiary, #f8f9fa);
  }

  .providers-table tbody tr.disabled-row {
    opacity: 0.6;
  }

  .providers-table td {
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

  .url-cell {
    max-width: 250px;
  }

  .url-text {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-secondary, #6c757d);
    font-size: 0.8125rem;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  }

  .models-cell {
    padding: 0.75rem 1rem;
  }

  .models-badge {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
  }

  .models-badge :global(.badge) {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
  }

  .btn-link {
    color: #007bff;
    text-decoration: none;
    font-weight: 500;
  }

  .btn-link:hover {
    text-decoration: underline;
  }

  .config-section {
    margin-bottom: 3rem;
  }

  .config-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .config-description {
    margin: 0;
    color: var(--text-secondary, #666);
    font-size: 0.875rem;
    line-height: 1.6;
  }

  .config-code {
    background: var(--bg-tertiary, #f8f9fa);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--bg-tertiary, #e9ecef);
    border-bottom: 1px solid var(--border-color, #e0e0e0);
  }

  .code-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary, #495057);
  }

  .code-block {
    margin: 0;
    padding: 1rem;
    background: var(--code-bg, var(--bg-primary, #fff));
    overflow-x: auto;
  }

  .code-block code {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
    font-size: 0.875rem;
    color: var(--text-primary, #1a1a1a);
    white-space: pre;
  }

  .config-note {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 1rem;
    background: #e7f3ff;
    border-radius: 0.5rem;
    border-left: 4px solid #007bff;
  }

  :global([data-theme="dark"]) .config-note {
    background: rgba(88, 166, 255, 0.1);
    border-left-color: #58a6ff;
  }

  .config-note p {
    margin: 0;
    font-size: 0.875rem;
    color: #004085;
    line-height: 1.6;
  }

  :global([data-theme="dark"]) .config-note p {
    color: var(--text-primary);
  }

  .config-note code {
    background: #fff;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
    font-size: 0.875rem;
    color: #007bff;
    border: 1px solid #b3d9ff;
  }

  :global([data-theme="dark"]) .config-note code {
    background: var(--code-bg, var(--bg-tertiary));
    color: #58a6ff;
    border-color: rgba(88, 166, 255, 0.3);
  }

  .note-text {
    margin-top: 0.5rem;
    font-weight: 500;
  }

  .api-key-note {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #b3d9ff;
  }

  :global([data-theme="dark"]) .api-key-note {
    border-top-color: rgba(88, 166, 255, 0.3);
  }

  .api-key-note p {
    margin-bottom: 0.5rem;
    font-weight: 600;
  }

  .api-key-note ul {
    margin: 0.5rem 0 0 0;
    padding-left: 1.5rem;
    list-style-type: disc;
  }

  .api-key-note li {
    margin: 0.5rem 0;
    font-size: 0.875rem;
    color: #004085;
    line-height: 1.6;
  }

  :global([data-theme="dark"]) .api-key-note li {
    color: var(--text-primary);
  }

  .api-key-note li strong {
    color: #002752;
  }

  :global([data-theme="dark"]) .api-key-note li strong {
    color: var(--text-primary);
  }
</style>
