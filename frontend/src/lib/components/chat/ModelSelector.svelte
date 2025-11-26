<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { chatService, type ModelChoice } from '$services/chatService';
  import { providerService } from '$services/providers';
  import { theme } from '$stores/theme';

  export let selectedModel: ModelChoice | null = null;
  export let selectedProvider: string = '';
  export let selectedApiFormat: string = '';
  export let selectedModelName: string = '';
  export let selectedCategory: string = 'middle';

  const dispatch = createEventDispatcher<{
    modelSelected: ModelChoice;
  }>();

  interface ProviderConfig {
    name: string;
    api_format: string;
    models: {
      big?: string[];
      middle?: string[];
      small?: string[];
    };
  }

  let providers: ProviderConfig[] = [];
  let modelCategories: string[] = ['big', 'middle', 'small'];

  let loading = true;
  let error: string | null = null;

  // Get available models for current selection
  // Depends on: selectedCategory, selectedProvider, selectedApiFormat
  $: availableModels = selectedCategory && getAvailableModels();

  function getAvailableModels(): string[] {
    if (!selectedProvider || !selectedApiFormat) return [];

    const provider = providers.find(p => p.name === selectedProvider && p.api_format === selectedApiFormat);
    if (!provider) return [];

    const models = provider.models[selectedCategory as keyof ProviderConfig['models']];
    return models || [];
  }

  // Update model selection when dropdowns change
  $: selectedProvider, selectedApiFormat, selectedModelName, updateModelSelection()

  function updateModelSelection() {
    const modelChoice: ModelChoice = {
      providerName: selectedProvider,
      apiFormat: selectedApiFormat,
      model: selectedModelName
    };
    selectedModel = modelChoice;
    dispatch('modelSelected', modelChoice);
  }

  onMount(async () => {
    try {
      loading = true;
      const providersData = await providerService.getAll();

      // Filter enabled providers
      providers = providersData.filter((p: ProviderConfig) => p.enabled);

      if (providers.length > 0) {
        // Set defaults
        selectedProvider = providers[0].name;
        selectedApiFormat = providers[0].api_format;

        // Find first available model
        for (const category of modelCategories) {
          const models = providers[0].models[category as keyof ProviderConfig['models']];
          if (models && models.length > 0) {
            selectedCategory = category;
            selectedModelName = models[0];
            break;
          }
        }
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load providers';
      console.error('Failed to load providers:', err);
    } finally {
      loading = false;
    }
  });

  function handleProviderChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedProvider = select.value;

    // Reset model selection
    const provider = providers.find(p => p.name === selectedProvider);
    if (provider) {
      selectedApiFormat = provider.api_format;

      // Find first available model
      for (const category of modelCategories) {
        const models = provider.models[category as keyof ProviderConfig['models']];
        if (models && models.length > 0) {
          selectedCategory = category;
          selectedModelName = models[0];
          return;
        }
      }
    }
  }

  function handleModelChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedModelName = select.value;
  }
</script>

<div class="model-selector">
  {#if loading}
    <div class="loading">加载模型配置中...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if providers.length > 0}
    <div class="selector-row">
      <div class="selector-group">
        <label for="provider-select">供应商</label>
        <select
          id="provider-select"
          class="select"
          bind:value={selectedProvider}
          on:change={handleProviderChange}
        >
          {#each providers as provider}
            <option value={provider.name}>
              {provider.name} ({provider.api_format})
            </option>
          {/each}
        </select>
      </div>

      <div class="selector-group">
        <label for="category-select">模型类别</label>
        <select id="category-select" class="select" bind:value={selectedCategory}>
          <option value="big">大模型</option>
          <option value="middle">中等模型</option>
          <option value="small">小模型</option>
        </select>
      </div>

      <div class="selector-group">
        <label for="model-select">具体模型</label>
        <select
          id="model-select"
          class="select"
          bind:value={selectedModelName}
          on:change={handleModelChange}
        >
          {#each availableModels as model}
            <option value={model}>{model}</option>
          {:else}
            <option value="">暂无可用模型</option>
          {/each}
        </select>
      </div>
    </div>

    {#if selectedModel}
      <div class="model-info">
        <span class="provider">供应商: <strong>{selectedModel.providerName}</strong></span>
        <span class="format">API格式: <strong>{selectedModel.apiFormat}</strong></span>
        <span class="model">模型: <strong>{selectedModel.model}</strong></span>
      </div>
    {/if}
  {:else}
    <div class="error">未找到可用的供应商配置</div>
  {/if}
</div>

<style>
  .model-selector {
    padding: 1rem;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
  }

  .selector-row {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
    flex-wrap: wrap;
  }

  .selector-group {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 200px;
    flex: 1;
  }

  .selector-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
  }

  .select {
    padding: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    background: var(--bg-secondary);
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .select:hover {
    border-color: var(--primary-color);
  }

  .select:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
  }

  .model-info {
    margin-top: 0.75rem;
    padding: 0.75rem;
    background: var(--bg-secondary);
    border-radius: 0.375rem;
    font-size: 0.75rem;
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
  }

  .model-info span {
    color: var(--text-secondary);
  }

  .model-info strong {
    color: var(--text-primary);
    font-weight: 600;
  }

  .loading, .error {
    padding: 1rem;
    text-align: center;
    border-radius: 0.375rem;
  }

  .loading {
    color: var(--text-secondary);
  }

  .error {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.2);
  }

  @media (max-width: 768px) {
    .selector-row {
      flex-direction: column;
      gap: 0.75rem;
    }

    .selector-group {
      min-width: 100%;
    }

    .model-info {
      flex-direction: column;
      gap: 0.5rem;
    }
  }
</style>
