<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import Button from '$components/ui/Button.svelte';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import Input from '$components/ui/Input.svelte';
  import { apiKeysService } from '$services/apiKeys';
  import { toast } from '$stores/toast';
  import type { APIKey, CreateAPIKeyRequest, UpdateAPIKeyRequest } from '$types/apiKey';

  let loading = true;
  let apiKeys: APIKey[] = [];
  let showCreateForm = false;
  let editingKey: APIKey | null = null;
  let saving = false;
  let newKey: CreateAPIKeyRequest = { name: '', email: '' };
  let editForm: UpdateAPIKeyRequest = {};
  let createdApiKey: string | null = null; // 存储新创建的完整 API Key
  let copySuccess = false;

  onMount(async () => {
    await loadAPIKeys();
  });

  async function loadAPIKeys() {
    loading = true;
    try {
      apiKeys = await apiKeysService.getAll();
    } catch (error) {
      console.error('Failed to load API keys:', error);
      toast.error('加载 API Key 列表失败');
    } finally {
      loading = false;
    }
  }

  function handleCreate() {
    newKey = { name: '', email: '' };
    createdApiKey = null;
    showCreateForm = true;
  }

  async function handleSaveCreate() {
    if (!newKey.name.trim()) {
      toast.error('请输入用户名');
      return;
    }

    saving = true;
    try {
      // 构建请求数据，确保 email 为空字符串时转换为 undefined
      const requestData: CreateAPIKeyRequest = {
        name: newKey.name.trim()
      };
      
      // 只有当 email 有值且不为空时才添加
      if (newKey.email && newKey.email.trim()) {
        requestData.email = newKey.email.trim();
      }
      
      console.log('Sending request:', requestData);
      const response = await apiKeysService.create(requestData);
      createdApiKey = response.api_key; // 保存完整 Key（只在创建时显示）
      toast.success('API Key 创建成功');
      await loadAPIKeys();
      // 不关闭表单，让用户复制 Key
    } catch (error) {
      console.error('Failed to create API key:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      toast.error('创建失败: ' + errorMessage);
    } finally {
      saving = false;
    }
  }

  function handleCloseCreateForm() {
    showCreateForm = false;
    createdApiKey = null;
    newKey = { name: '', email: '' };
  }

  function handleEdit(key: APIKey) {
    editingKey = key;
    editForm = {
      name: key.name,
      email: key.email || '',
      is_active: key.is_active
    };
  }

  function handleCancelEdit() {
    editingKey = null;
    editForm = {};
  }

  async function handleSaveEdit() {
    if (!editingKey) return;

    saving = true;
    try {
      // 构建请求数据，确保 email 为空字符串时不包含在请求中
      const requestData: UpdateAPIKeyRequest = {
        name: editForm.name,
        is_active: editForm.is_active
      };
      
      // 只有当 email 有值且不为空时才添加
      // 如果 email 为空字符串，不包含该字段（后端会保持原值）
      if (editForm.email && editForm.email.trim()) {
        requestData.email = editForm.email.trim();
      }
      // 如果 email 为空字符串，不设置该字段，后端不会更新邮箱字段
      
      await apiKeysService.update(editingKey.id, requestData);
      toast.success('更新成功');
      await loadAPIKeys();
      handleCancelEdit();
    } catch (error) {
      console.error('Failed to update API key:', error);
      toast.error('更新失败: ' + (error as Error).message);
    } finally {
      saving = false;
    }
  }

  async function handleDelete(key: APIKey) {
    const message = `确定要删除 API Key "${key.name}" 吗？\n\n` +
      `删除后该 Key 将立即失效，且无法恢复。\n` +
      `如果 Key 已丢失，删除后可以重新创建。`;
    
    if (!confirm(message)) {
      return;
    }

    try {
      await apiKeysService.delete(key.id);
      toast.success('删除成功');
      await loadAPIKeys();
    } catch (error) {
      console.error('Failed to delete API key:', error);
      toast.error('删除失败: ' + (error as Error).message);
    }
  }

  async function handleToggleActive(key: APIKey) {
    try {
      await apiKeysService.update(key.id, { is_active: !key.is_active });
      toast.success(key.is_active ? '已禁用' : '已启用');
      await loadAPIKeys();
    } catch (error) {
      console.error('Failed to toggle API key status:', error);
      toast.error('操作失败: ' + (error as Error).message);
    }
  }

  async function copyToClipboard(text: string) {
    if (!browser) return;
    
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        copySuccess = true;
        toast.success('已复制到剪贴板');
        setTimeout(() => {
          copySuccess = false;
        }, 2000);
      } else {
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        copySuccess = true;
        toast.success('已复制到剪贴板');
        setTimeout(() => {
          copySuccess = false;
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to copy:', error);
      toast.error('复制失败，请手动复制');
    }
  }

  function formatDate(dateStr?: string): string {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('zh-CN');
    } catch {
      return dateStr;
    }
  }
</script>

<div class="container">
  <div class="page-header">
    <h1 class="page-title">API Key 管理</h1>
    <Button on:click={handleCreate} title="创建 API Key" class="icon-button">
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
  {:else if apiKeys.length === 0}
    <div class="empty">
      <p>暂无 API Key</p>
      <Button on:click={handleCreate} title="创建第一个 API Key" class="icon-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </Button>
    </div>
  {:else}
    <Card>
      <div class="table-container">
        <table class="api-keys-table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>Key 前缀</th>
              <th>邮箱</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>最后使用</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {#each apiKeys as key}
              <tr class={!key.is_active ? 'disabled-row' : ''}>
                <td class="name-cell">
                  {#if editingKey?.id === key.id}
                    <Input
                      type="text"
                      bind:value={editForm.name}
                      placeholder="用户名"
                    />
                  {:else}
                    <span class="key-name">{key.name}</span>
                  {/if}
                </td>
                <td class="prefix-cell">
                  <code class="key-prefix">{key.key_prefix}</code>
                </td>
                <td class="email-cell">
                  {#if editingKey?.id === key.id}
                    <Input
                      type="email"
                      bind:value={editForm.email}
                      placeholder="邮箱（可选）"
                    />
                  {:else}
                    <span class="email-text">{key.email || '-'}</span>
                  {/if}
                </td>
                <td class="status-cell">
                  {#if editingKey?.id === key.id}
                    <label class="toggle-switch">
                      <input
                        type="checkbox"
                        bind:checked={editForm.is_active}
                      />
                      <span class="toggle-slider"></span>
                    </label>
                  {:else}
                    <Badge type={key.is_active ? 'success' : 'secondary'}>
                      {key.is_active ? '已启用' : '已禁用'}
                    </Badge>
                  {/if}
                </td>
                <td class="date-cell">
                  <span class="date-text">{formatDate(key.created_at)}</span>
                </td>
                <td class="date-cell">
                  <span class="date-text">{formatDate(key.last_used_at)}</span>
                </td>
                <td class="actions-cell">
                  {#if editingKey?.id === key.id}
                    <div class="edit-actions">
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={saving}
                        on:click={handleSaveEdit}
                        title={saving ? '保存中...' : '保存'}
                        class="icon-button"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                          <polyline points="17 21 17 13 7 13 7 21"></polyline>
                          <polyline points="7 3 7 8 15 8"></polyline>
                        </svg>
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={saving}
                        on:click={handleCancelEdit}
                        title="取消"
                        class="icon-button"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18"></line>
                          <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                      </Button>
                    </div>
                  {:else}
                    <div class="actions-wrapper">
                      <Button
                        variant="secondary"
                        size="sm"
                        on:click={() => handleToggleActive(key)}
                        title={key.is_active ? '禁用' : '启用'}
                        class="icon-button toggle-active-button {key.is_active ? 'toggle-active' : 'toggle-inactive'}"
                      >
                        {#if key.is_active}
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
                          </svg>
                        {:else}
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polygon points="5 3 19 12 5 21 5 3"></polygon>
                          </svg>
                        {/if}
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        on:click={() => handleEdit(key)}
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
                        on:click={() => handleDelete(key)}
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
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </Card>
  {/if}
</div>

<!-- Create API Key Modal -->
{#if showCreateForm}
  <div class="modal-overlay" on:click={handleCloseCreateForm}>
    <div class="modal-content" on:click|stopPropagation>
      <h2>创建 API Key</h2>
      
      {#if createdApiKey}
        <div class="created-key-section">
          <div class="warning-box">
            <p><strong>⚠️ 重要提示</strong></p>
            <p>API Key 创建后无法再次查看完整 Key，请立即复制并妥善保管！</p>
            <p style="margin-top: 0.5rem; font-size: 0.8125rem;">关闭此窗口后，您将无法再次查看此 Key。如果丢失，需要删除后重新创建。</p>
          </div>
          <div class="key-display">
            <label>API Key：</label>
            <div class="key-input-wrapper">
              <code class="full-key">{createdApiKey}</code>
              <Button
                variant="secondary"
                size="sm"
                on:click={() => copyToClipboard(createdApiKey!)}
                title={copySuccess ? '已复制' : '复制'}
                class="icon-button"
              >
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
          </div>
          <div class="modal-actions">
            <Button 
              variant="secondary" 
              on:click={() => {
                if (confirm('确定要关闭吗？关闭后将无法再次查看此 API Key。')) {
                  handleCloseCreateForm();
                }
              }}
              title="我已复制，关闭"
              class="icon-button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </Button>
            <Button variant="primary" on:click={handleCloseCreateForm} title="完成" class="icon-button">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </Button>
          </div>
        </div>
      {:else}
        <form on:submit|preventDefault={handleSaveCreate} class="create-form">
          <div class="info-box">
            <p><strong>💡 提示</strong></p>
            <p>API Key 将由系统自动生成（格式：sk-前缀 + 64个字符），您只需为此 Key 起个用户名即可。</p>
          </div>

          <div class="form-group">
            <label for="key-name">
              用户名 <span class="required">*</span>
            </label>
            <Input
              id="key-name"
              type="text"
              bind:value={newKey.name}
              placeholder="例如：Alice"
              required
            />
            <p class="form-hint">用于标识此 API Key 所属用户</p>
          </div>

          <div class="form-group">
            <label for="key-email">邮箱（可选）</label>
            <Input
              id="key-email"
              type="email"
              bind:value={newKey.email}
              placeholder="user@example.com"
            />
            <p class="form-hint">用于标识和管理此 API Key</p>
          </div>

          <div class="modal-actions">
            <Button
              type="submit"
              variant="primary"
              disabled={saving}
              title={saving ? '创建中...' : '创建'}
              class="icon-button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={saving}
              on:click={handleCloseCreateForm}
              title="取消"
              class="icon-button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </Button>
          </div>
        </form>
      {/if}
    </div>
  </div>
{/if}

<style>
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .page-title {
    margin: 0;
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .loading,
  .empty {
    text-align: center;
    padding: 4rem;
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .empty p {
    color: var(--text-secondary, #666);
    margin-bottom: 1rem;
  }

  .table-container {
    overflow-x: auto;
  }

  .api-keys-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .api-keys-table thead {
    background: var(--bg-tertiary, #f8f9fa);
    border-bottom: 2px solid var(--border-color, #dee2e6);
  }

  .api-keys-table th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary, #495057);
    white-space: nowrap;
  }

  .api-keys-table tbody tr {
    border-bottom: 1px solid var(--border-color, #dee2e6);
    transition: background-color 0.2s;
  }

  .api-keys-table tbody tr:hover {
    background: var(--bg-tertiary, #f8f9fa);
  }

  .api-keys-table tbody tr.disabled-row {
    opacity: 0.6;
  }

  .api-keys-table td {
    padding: 1rem;
    vertical-align: middle;
  }

  .name-cell {
    min-width: 150px;
  }

  .key-name {
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
  }

  .prefix-cell {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  }

  .key-prefix {
    background: var(--bg-tertiary, #f8f9fa);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.8125rem;
    color: var(--text-primary, #495057);
  }

  .email-cell {
    min-width: 180px;
  }

  .email-text {
    color: var(--text-secondary, #6c757d);
  }

  .status-cell {
    text-align: center;
  }

  .date-cell {
    min-width: 150px;
  }

  .date-text {
    color: var(--text-secondary, #6c757d);
    font-size: 0.8125rem;
  }

  .actions-cell {
    min-width: 200px;
  }

  .actions-wrapper {
    display: flex;
    gap: 0.375rem;
  }

  .edit-actions {
    display: flex;
    gap: 0.375rem;
  }

  .actions-wrapper :global(.btn),
  .edit-actions :global(.btn) {
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

  /* 启用/禁用按钮特殊样式 */
  :global(.toggle-active-button.toggle-active) {
    background: var(--danger-color, #dc3545) !important;
    color: white !important;
    border-color: var(--danger-color, #dc3545) !important;
  }

  :global([data-theme="dark"]) :global(.toggle-active-button.toggle-active) {
    background: #da3633 !important;
    border-color: #da3633 !important;
  }

  :global(.toggle-active-button.toggle-active:hover:not(:disabled)) {
    background: var(--danger-color, #f85149) !important;
    opacity: 0.9;
  }

  :global([data-theme="dark"]) :global(.toggle-active-button.toggle-active:hover:not(:disabled)) {
    background: #f85149 !important;
  }

  :global(.toggle-active-button.toggle-inactive) {
    background: var(--success-color, #28a745) !important;
    color: white !important;
    border-color: var(--success-color, #28a745) !important;
    border: 1px solid var(--success-color, #28a745) !important;
  }

  :global([data-theme="dark"]) :global(.toggle-active-button.toggle-inactive) {
    background: #238636 !important;
    color: white !important;
    border-color: #238636 !important;
    border: 1px solid #238636 !important;
  }

  :global(.toggle-active-button.toggle-inactive:hover:not(:disabled)) {
    background: var(--success-color, #28a745) !important;
    color: white !important;
    border-color: var(--success-color, #28a745) !important;
    border: 1px solid var(--success-color, #28a745) !important;
  }

  :global([data-theme="dark"]) :global(.toggle-active-button.toggle-inactive:hover:not(:disabled)) {
    background: #238636 !important;
    border-color: #238636 !important;
    border: 1px solid #238636 !important;
    color: white !important;
  }

  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--bg-tertiary, #ccc);
    transition: 0.3s;
    border-radius: 24px;
    border: 1px solid var(--border-color, transparent);
  }

  :global([data-theme="dark"]) .toggle-slider {
    background-color: #21262d;
    border-color: #30363d;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }

  :global([data-theme="dark"]) .toggle-slider:before {
    background-color: #c9d1d9;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  }

  .toggle-switch input:checked + .toggle-slider {
    background-color: var(--success-color, #28a745);
    border-color: var(--success-color, #28a745);
  }

  :global([data-theme="dark"]) .toggle-switch input:checked + .toggle-slider {
    background-color: #238636;
    border-color: #238636;
  }

  .toggle-switch input:checked + .toggle-slider:before {
    transform: translateX(20px);
  }

  .toggle-switch:hover .toggle-slider {
    opacity: 0.9;
  }

  .toggle-switch input:disabled + .toggle-slider {
    opacity: 0.5;
    cursor: not-allowed;
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

  :global([data-theme="dark"]) .modal-overlay {
    background: rgba(0, 0, 0, 0.7);
  }

  .modal-content {
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    max-width: 600px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    padding: 2rem;
  }

  .modal-content h2 {
    margin: 0 0 1.5rem 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .create-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
  }

  .required {
    color: var(--danger-color, #dc3545);
  }

  .form-hint {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--text-secondary, #6c757d);
  }

  .info-box {
    padding: 1rem;
    background: #e7f3ff;
    border: 1px solid #b3d9ff;
    border-radius: 0.5rem;
    border-left: 4px solid #0066cc;
    margin-bottom: 1.5rem;
  }

  :global([data-theme="dark"]) .info-box {
    background: rgba(88, 166, 255, 0.1);
    border-color: rgba(88, 166, 255, 0.3);
    border-left-color: #58a6ff;
  }

  .info-box p {
    margin: 0.5rem 0;
    font-size: 0.875rem;
    color: #004085;
  }

  :global([data-theme="dark"]) .info-box p {
    color: var(--text-primary);
  }

  .info-box p:first-child {
    margin-top: 0;
    font-weight: 600;
  }

  .info-box p:last-child {
    margin-bottom: 0;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1rem;
  }

  .created-key-section {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .warning-box {
    padding: 1rem;
    background: #fff3cd;
    border: 1px solid #ffc107;
    border-radius: 0.5rem;
    border-left: 4px solid #ffc107;
  }

  :global([data-theme="dark"]) .warning-box {
    background: rgba(210, 153, 34, 0.15);
    border-color: rgba(210, 153, 34, 0.4);
    border-left-color: #d29922;
  }

  .warning-box p {
    margin: 0.5rem 0;
    font-size: 0.875rem;
    color: #856404;
  }

  :global([data-theme="dark"]) .warning-box p {
    color: var(--text-primary);
  }

  .warning-box p:first-child {
    margin-top: 0;
    font-weight: 600;
  }

  .key-display {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .key-display label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
  }

  .key-input-wrapper {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .full-key {
    flex: 1;
    background: var(--bg-tertiary, #f8f9fa);
    padding: 0.75rem;
    border-radius: 0.25rem;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
    font-size: 0.875rem;
    word-break: break-all;
    border: 1px solid var(--border-color, #dee2e6);
    color: var(--text-primary, #1a1a1a);
  }

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
    }

    .page-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 1rem;
    }

    .api-keys-table {
      min-width: 800px;
    }

    .actions-wrapper {
      flex-direction: column;
      gap: 0.25rem;
    }

    .key-input-wrapper {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
