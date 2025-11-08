<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import Button from '$components/ui/Button.svelte';
  import { providers, providerStats } from '$stores/providers';
  import { healthStatus, lastHealthCheck } from '$stores/health';
  import { providerService } from '$services/providers';
  import { toast } from '$stores/toast';

  let loading = true;
  let currentUrl = '';
  let copySuccess = false;

  onMount(async () => {
    try {
      // 获取当前 URL
      if (browser) {
        currentUrl = window.location.origin;
      }

      // 加载供应商
      const providersData = await providerService.getAll();
      providers.set(providersData);

      // 不自动加载健康状态 - 仅在用户手动刷新时加载
      // 健康状态检查会消耗API调用和token
      // 但如果store中已有健康数据，则显示
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      toast.error('加载数据失败');
    } finally {
      loading = false;
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
    overallStatus === 'healthy' ? 'success' : 
    overallStatus === 'partial' ? 'warning' : 
    overallStatus === 'unhealthy' ? 'danger' : 
    'info';
  $: statusBadgeText = 
    overallStatus === 'healthy' ? '健康' : 
    overallStatus === 'partial' ? '部分健康' : 
    overallStatus === 'unhealthy' ? '不健康' : 
    '未检查';

  $: anthropicBaseUrl = currentUrl || 'http://localhost:5175';
  $: configCommand = `export ANTHROPIC_BASE_URL=${anthropicBaseUrl}\nexport ANTHROPIC_API_KEY="any-value"`;
</script>

<div class="container">
  <h1 class="page-title">仪表盘</h1>

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
            <span class="value">{$lastHealthCheck ? $lastHealthCheck.toLocaleString() : '未检查'}</span>
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
              <Button variant="secondary" size="sm" on:click={() => copyToClipboard(configCommand)}>
                {copySuccess ? '已复制' : '复制'}
              </Button>
            </div>
            <pre class="code-block"><code>export ANTHROPIC_BASE_URL={anthropicBaseUrl}
export ANTHROPIC_API_KEY="any-value"</code></pre>
          </div>
          <div class="config-note">
            <p><strong>方式一：</strong>在 Claude Code 设置中配置环境变量</p>
            <p><strong>方式二：</strong>在启动 Claude Code 前执行上述命令</p>
            <p class="note-text">💡 提示：当前服务地址为 <code>{anthropicBaseUrl}</code>，已自动填充到配置中</p>
          </div>
        </div>
      </Card>
    </div>

    <div class="providers-preview">
      <div class="preview-header">
        <h2>供应商概览</h2>
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
              {#each $providers.slice(0, 5) as provider}
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

        {#if $providers.length > 5}
          <div class="view-more">
            <a href="/providers" class="btn-link">查看全部 {$providers.length} 个供应商 →</a>
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>

<style>
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 600;
    margin: 0 0 2rem 0;
    color: #1a1a1a;
  }

  .loading {
    text-align: center;
    padding: 4rem;
    color: #666;
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
    color: #666;
    font-size: 0.875rem;
  }

  .value {
    font-size: 1.5rem;
    font-weight: 600;
  }

  .value.success {
    color: #28a745;
  }

  .value.danger {
    color: #dc3545;
  }

  .value.link {
    color: #007bff;
    font-size: 1rem;
    font-weight: 500;
    text-decoration: none;
  }

  .value.link:hover {
    text-decoration: underline;
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
    color: #1a1a1a;
  }

  .providers-preview {
    margin-top: 2rem;
  }

  .preview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .providers-preview h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 0;
  }

  .view-all {
    color: #007bff;
    text-decoration: none;
    font-weight: 500;
    font-size: 0.875rem;
  }

  .view-all:hover {
    text-decoration: underline;
  }

  .empty-state {
    text-align: center;
    padding: 3rem;
    background: white;
    border-radius: 0.5rem;
  }

  .empty-state p {
    color: #666;
    margin-bottom: 1rem;
  }

  .add-link {
    color: #007bff;
    text-decoration: none;
    font-weight: 500;
  }

  .add-link:hover {
    text-decoration: underline;
  }

  .table-container {
    background: white;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .providers-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .providers-table thead {
    background: #f8f9fa;
    border-bottom: 2px solid #dee2e6;
  }

  .providers-table th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    color: #495057;
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
    border-bottom: 1px solid #dee2e6;
    transition: background-color 0.2s;
  }

  .providers-table tbody tr:hover {
    background: #f8f9fa;
  }

  .providers-table tbody tr.disabled-row {
    opacity: 0.6;
  }

  .providers-table td {
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

  .url-cell {
    max-width: 250px;
  }

  .url-text {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #6c757d;
    font-size: 0.8125rem;
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

  .view-more {
    text-align: center;
    margin-top: 1.5rem;
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
    color: #666;
    font-size: 0.875rem;
    line-height: 1.6;
  }

  .config-code {
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: #e9ecef;
    border-bottom: 1px solid #e0e0e0;
  }

  .code-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: #495057;
  }

  .code-block {
    margin: 0;
    padding: 1rem;
    background: #fff;
    overflow-x: auto;
  }

  .code-block code {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
    font-size: 0.875rem;
    color: #1a1a1a;
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

  .config-note p {
    margin: 0;
    font-size: 0.875rem;
    color: #004085;
    line-height: 1.6;
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

  .note-text {
    margin-top: 0.5rem;
    font-weight: 500;
  }
</style>
