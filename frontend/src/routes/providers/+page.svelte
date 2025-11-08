<script lang="ts">
  import { onMount } from 'svelte';
  import Button from '$components/ui/Button.svelte';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import ProviderForm from '$components/ProviderForm.svelte';
  import { providers } from '$stores/providers';
  import { providerService } from '$services/providers';
  import { toast } from '$stores/toast';
  import type { Provider } from '$types/provider';

  let showForm = false;
  let editingProvider: Provider | null = null;
  let loading = true;
  let saving = false;
  let providersList: Provider[] = [];
  let providersForEdit: Provider[] = []; // 包含真实API key的完整数据

  $: providersList = $providers;

  onMount(async () => {
    await loadProviders();
  });

  async function loadProviders() {
    loading = true;
    try {
      const data = await providerService.getAll();
      providers.set(data);
    } catch (error) {
      console.error('Failed to load providers:', error);
      toast.error('加载供应商失败');
    } finally {
      loading = false;
    }
  }

  function handleAdd() {
    editingProvider = null;
    showForm = true;
  }

  async function handleEdit(provider: Provider) {
    // 检查是否已有编辑数据，如果没有则获取
    if (providersForEdit.length === 0) {
      try {
        const editData = await providerService.getAllForEdit();
        providersForEdit = editData;
      } catch (error) {
        console.error('Failed to load provider data for editing:', error);
        toast.error('加载编辑数据失败');
        return;
      }
    }

    // 从编辑数据中找到对应的供应商
    const fullProvider = providersForEdit.find(p => p.name === provider.name);
    editingProvider = fullProvider || provider;
    showForm = true;
  }

  async function handleDelete(provider: Provider) {
    if (!confirm(`确定要删除供应商 "${provider.name}" 吗？`)) {
      return;
    }

    try {
      await providerService.delete(provider.name);
      await loadProviders();
      toast.success('删除成功');
    } catch (error) {
      console.error('Failed to delete provider:', error);
      toast.error('删除失败: ' + (error as Error).message);
    }
  }

  async function handleTest(provider: Provider) {
    try {
      const result = await providerService.test(provider.name);
      if (result.healthy) {
        toast.success(`连接成功\n响应时间: ${result.responseTime}ms`);
      } else {
        toast.error(`连接失败\n${result.message}`);
      }
    } catch (error) {
      console.error('Failed to test provider:', error);
      toast.error('测试失败: ' + (error as Error).message);
    }
  }

  async function handleSave(providerData: Provider) {
    try {
      saving = true;
      if (editingProvider) {
        await providerService.update(editingProvider.name, providerData);
      } else {
        await providerService.create(providerData);
      }
      showForm = false;
      editingProvider = null;
      await loadProviders();
      toast.success('保存成功');
    } catch (error) {
      console.error('Failed to save provider:', error);
      toast.error('保存失败: ' + (error as Error).message);
    } finally {
      saving = false;
    }
  }

  function handleCancel() {
    showForm = false;
    editingProvider = null;
  }
</script>

<div class="container">
  <div class="page-header">
    <h1 class="page-title">供应商管理</h1>
    <Button on:click={handleAdd} title="添加供应商" class="icon-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
      </svg>
    </Button>
  </div>

  {#if loading}
    <div class="loading">
      <p>加载中...</p>
    </div>
  {:else if providersList.length === 0}
      <div class="empty">
      <p>暂无供应商配置</p>
      <Button on:click={handleAdd} title="添加第一个供应商" class="icon-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </Button>
    </div>
  {:else}
    <div class="table-container">
      <table class="providers-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>状态</th>
            <th>Base URL</th>
            <th>优先级</th>
            <th>模型数量</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
      {#each providersList as provider}
            <tr>
              <td class="name-cell">
                <div class="name-wrapper">
                  <span class="provider-name">{provider.name}</span>
                </div>
              </td>
              <td>
              <Badge type={provider.enabled ? 'success' : 'secondary'}>
                {provider.enabled ? '已启用' : '已禁用'}
              </Badge>
              </td>
              <td class="url-cell">
                <span class="url-text" title={provider.base_url}>{provider.base_url}</span>
              </td>
              <td class="priority-cell">
                <span class="priority-value">{provider.priority}</span>
              </td>
              <td class="models-cell">
                <div class="models-badge">
                  <Badge type="info">大 {provider.models.big?.length || 0}</Badge>
                  <Badge type="info">中 {provider.models.middle?.length || 0}</Badge>
                  <Badge type="info">小 {provider.models.small?.length || 0}</Badge>
            </div>
              </td>
              <td class="actions-cell">
                <div class="actions-wrapper">
                  <Button
                    variant="secondary"
                    size="sm"
                    on:click={() => handleTest(provider)}
                    title="测试连接"
                    class="icon-button"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
                    </svg>
            </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    on:click={() => handleEdit(provider)}
                    title="编辑"
                    class="icon-button"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
            </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    on:click={() => handleDelete(provider)}
                    title="删除"
                    class="icon-button"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      <line x1="10" y1="11" x2="10" y2="17"></line>
                      <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
            </Button>
          </div>
              </td>
            </tr>
      {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<!-- Provider Form Modal -->
{#if showForm}
  <div class="modal-overlay" on:click={handleCancel}>
    <div class="modal-content" on:click|stopPropagation>
      <h2>{editingProvider ? '编辑供应商' : '添加供应商'}</h2>
      <ProviderForm
        provider={editingProvider}
        loading={loading}
        on:save={(e) => handleSave(e.detail)}
        on:cancel={handleCancel}
      />
    </div>
  </div>
{/if}

<style>
  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary, #666);
  }

  .empty {
    text-align: center;
    padding: 4rem;
    background: var(--card-bg, white);
    border-radius: 0.5rem;
  }

  .empty p {
    color: var(--text-secondary, #666);
    margin-bottom: 1rem;
  }

  .table-container {
    background: var(--card-bg, white);
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

  .providers-table th:nth-child(4) {
    width: 80px;
  }

  .providers-table th:nth-child(5) {
    width: 180px;
  }

  .providers-table th:last-child {
    width: 220px;
  }

  .providers-table tbody tr {
    border-bottom: 1px solid var(--border-color, #dee2e6);
    transition: background-color 0.2s;
  }

  .providers-table tbody tr:hover {
    background: var(--bg-tertiary, #f8f9fa);
  }

  .providers-table td {
    padding: 1rem;
    vertical-align: middle;
  }

  .name-cell {
    padding: 1rem 0.75rem;
  }

  .name-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
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

  .actions-cell {
    padding: 0.75rem 1rem;
  }

  .actions-wrapper {
    display: flex;
    gap: 0.375rem;
  }

  .actions-wrapper :global(.btn) {
    font-size: 0.75rem;
    padding: 0.375rem 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .icon-button {
    padding: 0.5rem;
    min-width: auto;
    width: auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .icon-button :global(svg) {
    display: block;
    flex-shrink: 0;
  }

  /* 隐藏图标按钮中的文字节点 */
  .icon-button :global(span),
  .icon-button :global(text) {
    display: none !important;
  }

  /* Responsive Design */
  @media (max-width: 1024px) {
    .providers-table th:nth-child(3) {
      width: 200px;
    }

    .providers-table th:last-child {
      width: 200px;
    }
  }

  @media (max-width: 768px) {
    .table-container {
      overflow-x: auto;
    }

    .providers-table {
      min-width: 800px;
    }

    .providers-table th {
      padding: 0.75rem 0.5rem;
      font-size: 0.8125rem;
    }

    .providers-table td {
      padding: 0.75rem 0.5rem;
    }

    .actions-wrapper {
      flex-direction: column;
      gap: 0.25rem;
    }

    .actions-wrapper :global(.btn) {
      font-size: 0.6875rem;
      padding: 0.3125rem 0.625rem;
      white-space: nowrap;
    }
  }

  @media (max-width: 480px) {
    .providers-table th,
    .providers-table td {
      padding: 0.5rem 0.375rem;
      font-size: 0.75rem;
    }

    .models-badge {
      flex-direction: column;
      gap: 0.25rem;
    }

    .models-badge :global(.badge) {
      font-size: 0.6875rem;
    }
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    max-width: 600px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    padding: 2rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  }

  .modal-content h2 {
    margin: 0 0 1rem 0;
    font-size: 1.5rem;
    color: var(--text-primary, #1a1a1a);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1.5rem;
  }
</style>