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
  <div class="header">
    <h1 class="page-title">供应商管理</h1>
    <Button on:click={handleAdd}>添加供应商</Button>
  </div>

  {#if loading}
    <div class="loading">
      <p>加载中...</p>
    </div>
  {:else if providersList.length === 0}
    <div class="empty">
      <p>暂无供应商配置</p>
      <Button on:click={handleAdd}>添加第一个供应商</Button>
    </div>
  {:else}
    <div class="providers-grid">
      {#each providersList as provider}
        <Card>
          <div slot="title">
            <div class="provider-title">
              <h3>{provider.name}</h3>
              <Badge type={provider.enabled ? 'success' : 'secondary'}>
                {provider.enabled ? '已启用' : '已禁用'}
              </Badge>
            </div>
          </div>

          <div class="provider-info">
            <div class="info-item">
              <span class="label">Base URL:</span>
              <span class="value">{provider.base_url}</span>
            </div>
            <div class="info-item">
              <span class="label">超时时间:</span>
              <span class="value">{provider.timeout}s</span>
            </div>
            <div class="info-item">
              <span class="label">优先级:</span>
              <span class="value">{provider.priority}</span>
            </div>
            <div class="info-item">
              <span class="label">模型:</span>
              <div class="models">
                <Badge type="info">大: {provider.models.big?.length || 0}</Badge>
                <Badge type="info">中: {provider.models.middle?.length || 0}</Badge>
                <Badge type="info">小: {provider.models.small?.length || 0}</Badge>
              </div>
            </div>
          </div>

          <div slot="footer" class="actions">
            <Button variant="secondary" size="sm" on:click={() => handleTest(provider)}>
              测试连接
            </Button>
            <Button variant="secondary" size="sm" on:click={() => handleEdit(provider)}>
              编辑
            </Button>
            <Button variant="danger" size="sm" on:click={() => handleDelete(provider)}>
              删除
            </Button>
          </div>
        </Card>
      {/each}
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
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 600;
    margin: 0;
    color: #1a1a1a;
  }

  .loading {
    text-align: center;
    padding: 4rem;
    color: #666;
  }

  .empty {
    text-align: center;
    padding: 4rem;
    background: white;
    border-radius: 0.5rem;
  }

  .empty p {
    color: #666;
    margin-bottom: 1rem;
  }

  .providers-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1.5rem;
  }

  .provider-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }

  .provider-title h3 {
    margin: 0;
    font-size: 1.125rem;
  }

  .provider-info {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .label {
    font-weight: 500;
    color: #666;
    font-size: 0.875rem;
  }

  .value {
    color: #1a1a1a;
    font-size: 0.875rem;
    word-break: break-all;
  }

  .models {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .actions {
    display: flex;
    gap: 0.5rem;
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
    background: white;
    border-radius: 0.5rem;
    max-width: 600px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    padding: 2rem;
  }

  .modal-content h2 {
    margin: 0 0 1rem 0;
    font-size: 1.5rem;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1.5rem;
  }
</style>