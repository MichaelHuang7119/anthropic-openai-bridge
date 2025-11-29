<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import { providerService } from "$services/providers";
  import type { ModelChoice } from "$services/chatService";
  import SlidingList from "$components/ui/SlidingList.svelte";
  import { tStore } from "$stores/language";

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

  let isExpanded = $state(false);
  let selectorElement: HTMLDivElement;

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

  // 获取翻译函数
  const t = $derived($tStore);

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

  // Format providers as options (name in normal color, api_format in light gray)
  let providerOptions = $derived(
    sortedProviders.map(p => ({
      value: `${p.name}||${p.api_format}`,
      label: p.name,
      coloredPart: {
        text: p.api_format,
        color: 'var(--text-tertiary)',
        opacity: 0.7
      },
      description: undefined
    }))
  );

  // Format categories as options
  let categoryOptions = $derived([
    { value: 'big', label: t('modelSelector.bigModel') },
    { value: 'middle', label: t('modelSelector.middleModel') },
    { value: 'small', label: t('modelSelector.smallModel') }
  ]);

  // Format models as options
  let modelOptions = $derived(
    availableModels.map(m => ({
      value: m,
      label: m
    }))
  );

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

  // Handle click outside to collapse
  function handleDocumentClick(event: MouseEvent) {
    if (isExpanded && selectorElement) {
      // Check if click is outside the selector element
      if (!selectorElement.contains(event.target as Node)) {
        isExpanded = false;
      }
    }
  }

  // Add click outside handler when component mounts
  $effect(() => {
    if (isExpanded) {
      document.addEventListener('click', handleDocumentClick);
      return () => {
        document.removeEventListener('click', handleDocumentClick);
      };
    }
  });

  function toggleExpanded(event?: MouseEvent) {
    if (event) {
      event.stopPropagation();
    }
    isExpanded = !isExpanded;
  }

  // Handle provider selection
  function handleProviderChange(providerValue: string) {
    const [name, apiFormat] = providerValue.split("||");
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

  // Handle category selection
  function handleCategoryChange(categoryValue: string) {
    selectedCategory = categoryValue;

    // Reset model to first available one in the new category
    if (availableModels.length > 0) {
      selectedModelName = availableModels[0];
    }
  }

  // Handle model selection
  function handleModelChange(modelValue: string) {
    selectedModelName = modelValue;
  }
</script>

<div class="model-selector" bind:this={selectorElement}>
  <!-- Collapsed Header - Always Visible -->
  <div class="selector-header" onclick={toggleExpanded} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && toggleExpanded()}>
    <div class="header-content">
      <span class="header-label">{t('modelSelector.provider')}</span>
      <span class="header-value">
        {#if selectedProvider}
          <strong>{selectedProvider}</strong>
          {#if selectedApiFormat}
            <span class="api-format">{selectedApiFormat}</span>
          {/if}
        {:else}
          <span class="placeholder">{t('modelSelector.placeholderSelectProvider')}</span>
        {/if}
      </span>
    </div>
    <div class="expand-icon" class:expanded={isExpanded}>
      ▼
    </div>
  </div>

  <!-- Expanded Content -->
  {#if isExpanded}
    <div class="expanded-content">
      {#if loading}
        <div class="loading">{t('modelSelector.loadingModels')}</div>
      {:else if error}
        <div class="error">{error}</div>
      {:else if providers.length > 0}
        <div class="selector-row">
          <div class="selector-group">
            <label for="provider-select">{t('modelSelector.provider')}</label>
            <SlidingList
              options={providerOptions}
              value={`${selectedProvider}||${selectedApiFormat}`}
              placeholder={t('modelSelector.selectProvider')}
              onChange={handleProviderChange}
            />
          </div>

          <div class="selector-group">
            <label for="category-select">{t('modelSelector.category')}</label>
            <SlidingList
              options={categoryOptions}
              value={selectedCategory}
              placeholder={t('modelSelector.selectCategory')}
              onChange={handleCategoryChange}
            />
          </div>

          <div class="selector-group">
            <label for="model-select">{t('modelSelector.model')}</label>
            <SlidingList
              options={modelOptions}
              value={selectedModelName}
              placeholder={availableModels.length === 0 ? t('modelSelector.noModels') : t('modelSelector.selectModel')}
              onChange={handleModelChange}
            />
          </div>
        </div>

        {#if selectedModel}
          <div class="model-info">
            <span class="provider"
              >{t('modelSelector.provider')}: <strong>{selectedModel.providerName}</strong></span
            >
            <span class="format"
              >{t('modelSelector.apiFormat')}: <strong>{selectedModel.apiFormat}</strong></span
            >
            <span class="model">{t('modelSelector.model')}: <strong>{selectedModel.model}</strong></span>
          </div>
        {/if}
      {:else}
        <div class="error">{t('common.error')}</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .model-selector {
    position: relative;
  }

  /* Collapsed Header */
  .selector-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 2rem 0.5rem 0.75rem;
    cursor: pointer;
    user-select: none;
    border-radius: 0.5rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.2s ease;
    width: fit-content;
    max-width: calc(100vw - 4rem);
    position: relative;
  }

  .selector-header:hover {
    background: var(--bg-tertiary);
    border-color: var(--primary-color);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
    transform: translateY(-1px);
  }

  .selector-header:focus {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .header-content {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 0 1 auto;
    min-width: 0;
    max-width: calc(100vw - 8rem);
  }

  .header-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .header-value {
    font-size: 0.85rem;
    color: var(--text-primary);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: calc(100vw - 10rem);
  }

  .header-value strong {
    font-weight: 600;
    color: var(--text-primary);
  }

  .api-format {
    color: var(--text-tertiary);
    font-weight: 400;
    opacity: 0.7;
  }

  .placeholder {
    color: var(--text-tertiary);
    font-style: italic;
  }

  .expand-icon {
    position: absolute;
    right: 0.75rem;
    font-size: 0.7rem;
    color: var(--text-tertiary);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    flex-shrink: 0;
  }

  .expand-icon.expanded {
    transform: rotate(180deg);
  }

  /* Expanded Content */
  .expanded-content {
    position: absolute;
    top: 100%;
    left: 0;
    margin-top: 0.5rem;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15), 0 2px 8px rgba(0, 0, 0, 0.1);
    animation: slideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    padding: 1rem 2.5rem 1rem 1rem;
    min-width: 600px;
    width: max-content;
    max-width: calc(100vw - 2rem);
    z-index: 100;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
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
    min-width: 220px;
    flex: 1;
  }

  .selector-group label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
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
    .selector-header {
      padding: 0.5rem 0.625rem;
      max-width: calc(100vw - 2rem);
    }

    .header-value {
      font-size: 0.8rem;
      max-width: 150px;
    }

    .header-label {
      font-size: 0.65rem;
    }

    .expanded-content {
      min-width: calc(100vw - 2rem);
      max-width: calc(100vw - 2rem);
      width: calc(100vw - 2rem);
    }

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
