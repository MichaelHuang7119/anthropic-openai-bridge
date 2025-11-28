<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import { providerService } from "$services/providers";
  import type { ModelChoice } from "$services/chatService";

  interface Props {
    selectedModel?: ModelChoice | null;
    selectedProvider?: string;
    selectedApiFormat?: string;
    selectedModelName?: string;
    selectedCategory?: string;
    onModelSelected?: (modelChoice: ModelChoice) => void;
  }

  const dispatch = createEventDispatcher<{
    modelSelected: ModelChoice;
  }>();

  let {
    selectedModel = $bindable(null),
    selectedProvider = $bindable(""),
    selectedApiFormat = $bindable(""),
    selectedModelName = $bindable(""),
    selectedCategory = $bindable("middle"),
    onModelSelected: _onModelSelected,
  }: Props = $props();

  interface ProviderConfig {
    name: string;
    api_format: string;
    models: {
      big?: string[];
      middle?: string[];
      small?: string[];
    };
    enabled?: boolean;
  }

  let providers = $state<ProviderConfig[]>([]);
  let modelCategories = $state(["big", "middle", "small"]);

  let loading = $state(true);
  let error = $state<string | null>(null);

  // Computed sorted providers for display
  let sortedProviders: ProviderConfig[] = $derived(
    [...providers].sort((a, b) => {
      // Primary sort: by provider name (alphabetically, case-insensitive)
      const nameCompare = a.name
        .toLowerCase()
        .localeCompare(b.name.toLowerCase());
      if (nameCompare !== 0) return nameCompare;

      // Secondary sort: by API format (anthropic first, then openai)
      const formatOrder = { anthropic: 0, openai: 1 };
      const aOrder = formatOrder[a.api_format as keyof typeof formatOrder] ?? 2;
      const bOrder = formatOrder[b.api_format as keyof typeof formatOrder] ?? 2;
      return aOrder - bOrder;
    }),
  );

  // Get available models for current selection
  function getAvailableModels(): string[] {
    // Return empty array if selection is incomplete (normal during initialization)
    if (!selectedProvider || !selectedApiFormat || !selectedCategory) {
      return [];
    }

    const provider = providers.find((p) => {
      return p.name === selectedProvider && p.api_format === selectedApiFormat;
    });

    if (!provider) {
      // Only log if providers are loaded but provider not found (indicates a real issue)
      if (providers.length > 0) {
        console.warn("Provider not found:", {
          selectedProvider,
          selectedApiFormat,
          availableProviders: providers.map((p) => ({
            name: p.name,
            format: p.api_format,
          })),
        });
      }
      return [];
    }

    const models =
      provider.models[selectedCategory as keyof ProviderConfig["models"]];
    return models || [];
  }

  // Compute available models reactively
  let availableModels: string[] = $derived(getAvailableModels());

  // Reset model selection when provider, category, or available models change
  $effect(() => {
    // Auto-select first available model if current selection is invalid
    if (
      availableModels.length > 0 &&
      (!selectedModelName || !availableModels.includes(selectedModelName))
    ) {
      selectedModelName = availableModels[0];
    }

    // Dispatch model selection event
    if (selectedProvider && selectedApiFormat && selectedModelName) {
      const modelChoice: ModelChoice = {
        providerName: selectedProvider,
        apiFormat: selectedApiFormat,
        model: selectedModelName,
      };
      selectedModel = modelChoice;
      dispatch("modelSelected", modelChoice);
      console.log("Model selected:", modelChoice);
    }
  });

  onMount(async () => {
    try {
      loading = true;
      const providersData = await providerService.getAll();

      // Filter enabled providers
      providers = providersData
        .filter((p) => p.enabled && p.api_format)
        .map((p) => ({
          name: p.name,
          api_format: p.api_format!,
          models: p.models,
          enabled: p.enabled,
        }));

      if (providers.length > 0) {
        // If provider/format/model are already set (from conversation), validate and find category
        if (selectedProvider && selectedApiFormat && selectedModelName) {
          const provider = providers.find(
            (p) =>
              p.name === selectedProvider && p.api_format === selectedApiFormat,
          );

          if (provider) {
            // Find which category contains the selected model
            let foundCategory = false;
            for (const category of modelCategories) {
              const models =
                provider.models[category as keyof ProviderConfig["models"]];
              if (models && models.includes(selectedModelName)) {
                selectedCategory = category;
                foundCategory = true;
                console.log(
                  `Found model "${selectedModelName}" in category "${category}"`,
                );
                break;
              }
            }

            // If model not found in any category, fall back to defaults
            if (!foundCategory) {
              console.warn(
                `Model "${selectedModelName}" not found in provider "${selectedProvider}", using defaults`,
              );
              selectedProvider = "";
              selectedApiFormat = "";
              selectedModelName = "";
            }
          } else {
            // Provider not found or not enabled, fall back to defaults
            console.warn(
              `Provider "${selectedProvider}" (${selectedApiFormat}) not found or not enabled, using defaults`,
            );
            selectedProvider = "";
            selectedApiFormat = "";
            selectedModelName = "";
          }
        }

        // Set defaults if not already set or if validation failed
        if (!selectedProvider) {
          selectedProvider = providers[0].name;
        }
        if (!selectedApiFormat) {
          selectedApiFormat = providers[0].api_format;
        }

        // Find first available model if not set
        if (!selectedModelName) {
          const provider =
            providers.find(
              (p) =>
                p.name === selectedProvider &&
                p.api_format === selectedApiFormat,
            ) || providers[0];

          for (const category of modelCategories) {
            const models =
              provider.models[category as keyof ProviderConfig["models"]];
            if (models && models.length > 0) {
              selectedCategory = category;
              selectedModelName = models[0];
              break;
            }
          }
        }
      }
    } catch (err) {
      error = err instanceof Error ? err.message : "Failed to load providers";
      console.error("Failed to load providers:", err);
    } finally {
      loading = false;
    }
  });

  function handleProviderChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    const value = select.value;

    // Value format: "name||api_format"
    const [name, apiFormat] = value.split("||");
    selectedProvider = name;
    selectedApiFormat = apiFormat;

    // Reset model selection
    const provider = providers.find(
      (p) => p.name === name && p.api_format === apiFormat,
    );
    if (provider) {
      // Find first available model
      for (const category of modelCategories) {
        const models =
          provider.models[category as keyof ProviderConfig["models"]];
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

  function handleCategoryChange(event: Event) {
    // Category change already handled by bind:value, but we need to reset model selection
    const select = event.target as HTMLSelectElement;
    selectedCategory = select.value;

    // Reset model to first available one in the new category
    if (availableModels.length > 0) {
      selectedModelName = availableModels[0];
    }
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
          onchange={handleProviderChange}
        >
          {#each sortedProviders as provider}
            <option
              value={`${provider.name}||${provider.api_format}`}
              selected={selectedProvider === provider.name &&
                selectedApiFormat === provider.api_format}
            >
              {provider.name} ({provider.api_format})
            </option>
          {/each}
        </select>
      </div>

      <div class="selector-group">
        <label for="category-select">模型类别</label>
        <select
          id="category-select"
          class="select"
          bind:value={selectedCategory}
          onchange={handleCategoryChange}
        >
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
          onchange={handleModelChange}
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
        <span class="provider"
          >供应商: <strong>{selectedModel.providerName}</strong></span
        >
        <span class="format"
          >API格式: <strong>{selectedModel.apiFormat}</strong></span
        >
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

  .loading,
  .error {
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
