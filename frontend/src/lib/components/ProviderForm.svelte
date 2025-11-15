<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Button from './ui/Button.svelte';
  import Input from './ui/Input.svelte';
  import type { Provider, ProviderFormData } from '$types/provider';

  export let provider: Provider | null = null; // null for create, provider object for edit
  export let loading = false;

  const dispatch = createEventDispatcher<{
    save: Provider;
    cancel: void;
  }>();

  let formData: ProviderFormData = {
    name: '',
    enabled: true,
    priority: 1,
    api_key: '',
    base_url: '',
    api_version: null,
    timeout: 60,
    max_retries: 1,
    custom_headers: {},
    models: {
      big: [],
      middle: [],
      small: []
    }
  };

  // Initialize form data if editing
  if (provider) {
    formData = {
      name: provider.name,
      enabled: provider.enabled,
      priority: provider.priority,
      api_key: provider.api_key,
      base_url: provider.base_url,
      api_version: provider.api_version || null,
      timeout: provider.timeout,
      max_retries: provider.max_retries,
      custom_headers: { ...provider.custom_headers },
      models: {
        big: [...(provider.models.big || [])],
        middle: [...(provider.models.middle || [])],
        small: [...(provider.models.small || [])]
      }
    };
  }

  let errors: Record<string, string> = {};
  let showApiKey = false;

  function validateForm(): boolean {
    errors = {};

    if (!formData.name.trim()) {
      errors.name = '提供商名称不能为空';
    }

    if (!formData.api_key.trim()) {
      errors.api_key = 'API Key不能为空';
    }

    if (!formData.base_url.trim()) {
      errors.base_url = 'Base URL不能为空';
    } else if (!isValidUrl(formData.base_url)) {
      errors.base_url = '请输入有效的URL';
    }

    if (formData.timeout < 1) {
      errors.timeout = '超时时间必须大于0';
    }

    if (formData.max_retries < 0) {
      errors.max_retries = '重试次数不能小于0';
    }

    if (formData.priority < 1) {
      errors.priority = '优先级必须大于0';
    }

    // Check if at least one model category has models
    const hasModels = formData.models.big.length > 0
      || formData.models.middle.length > 0
      || formData.models.small.length > 0;

    if (!hasModels) {
      errors.models = '至少需要配置一个模型';
    }

    return Object.keys(errors).length === 0;
  }

  function isValidUrl(string: string): boolean {
    try {
      new URL(string);
      return true;
    } catch {
      return false;
    }
  }

  function handleSave() {
    if (!validateForm()) {
      return;
    }

    // Convert form data to Provider format
    // For display purposes, hide API key if it was pre-filled during edit
    const providerData: Provider = {
      ...formData,
      // Keep API key as-is (user might not want to change it)
      api_key: formData.api_key
    };

    dispatch('save', providerData);
  }

  function handleCancel() {
    dispatch('cancel');
  }

  // Model management functions
  function addModel(category: 'big' | 'middle' | 'small') {
    formData.models[category] = [...formData.models[category], ''];
  }

  function removeModel(category: 'big' | 'middle' | 'small', index: number) {
    formData.models[category] = formData.models[category].filter((_, i) => i !== index);
  }

  function updateModel(
    category: 'big' | 'middle' | 'small',
    index: number,
    value: string
  ) {
    formData.models[category][index] = value;
  }

  function moveModelUp(category: 'big' | 'middle' | 'small', index: number) {
    if (index <= 0) return;
    const models = [...formData.models[category]];
    [models[index], models[index - 1]] = [models[index - 1], models[index]];
    formData.models[category] = models;
  }

  // Custom headers management
  let newHeaderKey = '';
  let newHeaderValue = '';

  function addHeader() {
    if (newHeaderKey.trim() && newHeaderValue.trim()) {
      formData.custom_headers[newHeaderKey] = newHeaderValue;
      newHeaderKey = '';
      newHeaderValue = '';
    }
  }

  function removeHeader(key: string) {
    const { [key]: _, ...rest } = formData.custom_headers;
    formData.custom_headers = rest;
  }
</script>

<div class="form">
  <div class="form-section">
    <h3>基本信息</h3>

    <div class="form-group">
      <label for="name">
        提供商名称 <span class="required">*</span>
      </label>
      <Input
        id="name"
        type="text"
        bind:value={formData.name}
        placeholder="例如: openai, anthropic"
        required
      />
      {#if errors.name}
        <span class="error">{errors.name}</span>
      {/if}
    </div>

    <div class="form-group">
      <label for="base_url">
        Base URL <span class="required">*</span>
      </label>
      <Input
        id="base_url"
        type="text"
        bind:value={formData.base_url}
        placeholder="https://api.openai.com/v1"
        required
      />
      {#if errors.base_url}
        <span class="error">{errors.base_url}</span>
      {/if}
    </div>

    <div class="form-group">
      <label for="api_key">
        API Key <span class="required">*</span>
      </label>
      <div class="password-input">
        <Input
          id="api_key"
          type={showApiKey ? 'text' : 'password'}
          bind:value={formData.api_key}
          placeholder="输入API Key"
          required
        />
        <button
          type="button"
          class="toggle-password"
          on:click={() => showApiKey = !showApiKey}
          title={showApiKey ? '隐藏API Key' : '显示API Key'}
        >
          {#if showApiKey}
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
              <line x1="1" y1="1" x2="23" y2="23"></line>
            </svg>
          {:else}
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
          {/if}
        </button>
      </div>
      {#if errors.api_key}
        <span class="error">{errors.api_key}</span>
      {/if}
    </div>

    <div class="form-group">
      <label for="api_version">
        API版本 (可选)
      </label>
      <Input
        id="api_version"
        type="text"
        bind:value={formData.api_version}
        placeholder="例如: v1"
      />
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="timeout">
          超时时间 (秒) <span class="required">*</span>
        </label>
        <Input
          id="timeout"
          type="number"
          bind:value={formData.timeout}
          min="1"
          required
        />
        {#if errors.timeout}
          <span class="error">{errors.timeout}</span>
        {/if}
      </div>

      <div class="form-group">
        <label for="max_retries">
          最大重试次数 <span class="required">*</span>
        </label>
        <Input
          id="max_retries"
          type="number"
          bind:value={formData.max_retries}
          min="0"
          required
        />
        {#if errors.max_retries}
          <span class="error">{errors.max_retries}</span>
        {/if}
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="priority">
          优先级 <span class="required">*</span>
        </label>
        <Input
          id="priority"
          type="number"
          bind:value={formData.priority}
          min="1"
          required
        />
        <small>数字越小优先级越高 (1为最高)</small>
        {#if errors.priority}
          <span class="error">{errors.priority}</span>
        {/if}
      </div>
    </div>
  </div>

  <div class="form-section">
    <h3>模型配置</h3>
    <small>至少配置一个模型，推荐配置所有三个类别</small>

    {#if errors.models}
      <span class="error">{errors.models}</span>
    {/if}

    <!-- Large Models -->
    <div class="model-section">
      <div class="model-header">
        <label>大模型 (Big Models)</label>
        <Button size="sm" on:click={() => addModel('big')} title="添加大模型" class="icon-button">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </Button>
      </div>
      <div class="model-list">
        {#each formData.models.big as model, index}
          <div class="model-item">
            <Input
              type="text"
              bind:value={formData.models.big[index]}
              placeholder="模型名称或ID"
            />
            <div class="model-actions">
              <Button
                variant="secondary"
                size="sm"
                on:click={() => moveModelUp('big', index)}
                disabled={index === 0}
                title="上移"
                class="icon-button"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="18 15 12 9 6 15"></polyline>
                </svg>
              </Button>
              <Button
                variant="danger"
                size="sm"
                on:click={() => removeModel('big', index)}
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
          </div>
        {/each}
        {#if formData.models.big.length === 0}
          <p class="empty-models">暂无大模型</p>
        {/if}
      </div>
    </div>

    <!-- Middle Models -->
    <div class="model-section">
      <div class="model-header">
        <label>中模型 (Middle Models)</label>
        <Button size="sm" on:click={() => addModel('middle')} title="添加中模型" class="icon-button">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </Button>
      </div>
      <div class="model-list">
        {#each formData.models.middle as model, index}
          <div class="model-item">
            <Input
              type="text"
              bind:value={formData.models.middle[index]}
              placeholder="模型名称或ID"
            />
            <div class="model-actions">
              <Button
                variant="secondary"
                size="sm"
                on:click={() => moveModelUp('middle', index)}
                disabled={index === 0}
                title="上移"
                class="icon-button"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="18 15 12 9 6 15"></polyline>
                </svg>
              </Button>
              <Button
                variant="danger"
                size="sm"
                on:click={() => removeModel('middle', index)}
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
          </div>
        {/each}
        {#if formData.models.middle.length === 0}
          <p class="empty-models">暂无中模型</p>
        {/if}
      </div>
    </div>

    <!-- Small Models -->
    <div class="model-section">
      <div class="model-header">
        <label>小模型 (Small Models)</label>
        <Button size="sm" on:click={() => addModel('small')} title="添加小模型" class="icon-button">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </Button>
      </div>
      <div class="model-list">
        {#each formData.models.small as model, index}
          <div class="model-item">
            <Input
              type="text"
              bind:value={formData.models.small[index]}
              placeholder="模型名称或ID"
            />
            <div class="model-actions">
              <Button
                variant="secondary"
                size="sm"
                on:click={() => moveModelUp('small', index)}
                disabled={index === 0}
                title="上移"
                class="icon-button"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="18 15 12 9 6 15"></polyline>
                </svg>
              </Button>
              <Button
                variant="danger"
                size="sm"
                on:click={() => removeModel('small', index)}
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
          </div>
        {/each}
        {#if formData.models.small.length === 0}
          <p class="empty-models">暂无小模型</p>
        {/if}
      </div>
    </div>
  </div>

  <div class="form-section">
    <h3>自定义请求头 (可选)</h3>
    <small>添加自定义HTTP请求头</small>

    <div class="headers-input">
      <Input
        type="text"
        bind:value={newHeaderKey}
        placeholder="Header名称"
      />
      <Input
        type="text"
        bind:value={newHeaderValue}
        placeholder="Header值"
      />
      <Button size="sm" on:click={addHeader} title="添加请求头" class="icon-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </Button>
    </div>

    {#if Object.keys(formData.custom_headers).length > 0}
      <div class="headers-list">
        {#each Object.entries(formData.custom_headers) as [key, value]}
          <div class="header-item">
            <span class="header-key">{key}:</span>
            <span class="header-value">{value}</span>
            <Button
              variant="danger"
              size="sm"
              on:click={() => removeHeader(key)}
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
        {/each}
      </div>
    {/if}
  </div>

  <div class="form-actions">
    <Button variant="secondary" on:click={handleCancel} disabled={loading} title="取消" class="icon-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </Button>
    <Button type="submit" on:click={handleSave} disabled={loading} title={loading ? '保存中...' : '保存'} class="icon-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
        <polyline points="17 21 17 13 7 13 7 21"></polyline>
        <polyline points="7 3 7 8 15 8"></polyline>
      </svg>
    </Button>
  </div>
</div>

<style>
  .form {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .form-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .form-section h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .form-section small {
    color: var(--text-secondary, #666);
    font-size: 0.875rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .form-group label {
    font-weight: 500;
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
  }

  .required {
    color: var(--danger-color, #dc3545);
  }

  .error {
    color: var(--danger-color, #dc3545);
    font-size: 0.875rem;
  }

  .model-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .model-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .model-header label {
    font-weight: 500;
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
  }

  .model-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .model-item {
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
  }

  .model-item :global(.input) {
    flex: 1;
  }

  .model-actions {
    display: flex;
    gap: 0.25rem;
    flex-wrap: nowrap;
  }

  .empty-models {
    color: var(--text-secondary, #999);
    font-size: 0.875rem;
    font-style: italic;
    margin: 0;
    padding: 0.5rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.25rem;
  }

  .headers-input {
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    gap: 0.5rem;
  }

  .headers-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1rem;
  }

  .header-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.25rem;
  }

  .header-key {
    font-weight: 500;
    color: var(--text-primary, #495057);
  }

  .header-value {
    color: var(--text-secondary, #666);
    flex: 1;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-color, #dee2e6);
  }

  .password-input {
    position: relative;
    display: flex;
    align-items: center;
  }

  .password-input :global(.input) {
    padding-right: 3rem;
  }

  .toggle-password {
    position: absolute;
    right: 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.25rem;
    color: var(--text-secondary, #6c757d);
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.25rem;
    transition: color 0.2s, background-color 0.2s;
  }

  .toggle-password:hover {
    color: var(--text-primary, #495057);
    background: rgba(0, 0, 0, 0.05);
  }

  :global([data-theme="dark"]) .toggle-password:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .toggle-password svg {
    width: 1.25rem;
    height: 1.25rem;
  }

  @media (max-width: 768px) {
    .form-row {
      grid-template-columns: 1fr;
    }

    .headers-input {
      grid-template-columns: 1fr;
    }
  }
</style>
