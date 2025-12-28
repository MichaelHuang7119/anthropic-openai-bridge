<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import { providerService } from "$services/providers";
  import type { ModelChoice } from "$services/chatService";
  import SlidingList from "$components/ui/SlidingList.svelte";
  import { tStore } from "$stores/language";

  interface Props {
    selectedModels?: ModelChoice[];
    selectedProviderName?: string;
    selectedApiFormat?: string;
    selectedModelName?: string;
    selectedCategory?: string;
    onModelSelected?: (modelChoice: ModelChoice) => void;
    onModelsSelected?: (modelChoices: ModelChoice[]) => void;
  }

  const dispatch = createEventDispatcher<{
    modelSelected: ModelChoice;
    modelsSelected: ModelChoice[];
  }>();

  let {
    selectedModels = $bindable([]),
    selectedProviderName = $bindable(""),
    selectedApiFormat = $bindable(""),
    selectedModelName = $bindable(""),
    selectedCategory = $bindable("middle"),
    onModelSelected: _onModelSelected,
    onModelsSelected: _onModelsSelected,
  }: Props = $props();

  // 检测是否为移动端 - 必须在模块作用域中定义
  function isMobile(): boolean {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= 768;
  }

  // 初始状态始终为折叠
  let isExpanded = $state(false);
  let selectorElement: HTMLDivElement;
  let editingIndex = $state<number | null>(null);

  // 检查是否在客户端
  let _isClient = $state(false);
  $effect(() => {
    if (typeof window !== 'undefined') {
      _isClient = true;
    }
  });

  // 在移动端也允许展开状态切换
  // 但移动端有特殊的展示方式（底部弹出）

  // 创建一个受控的展开状态
  let controlledIsExpanded = $derived(isExpanded);

  // 更新展开状态的函数
  function setExpanded(value: boolean) {
    isExpanded = value;
  }

  // 监听窗口大小变化
  $effect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => {
      // 窗口大小变化时，触发更新
      // 通过读取 controlledIsExpanded 来触发响应式更新
      void controlledIsExpanded;
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  });

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
    if (!selectedProviderName || !selectedApiFormat || !selectedCategory) {
      return [];
    }

    const provider = providers.find((p) => {
      return p.name === selectedProviderName && p.api_format === selectedApiFormat;
    });

    if (!provider) {
      // Only log if providers are loaded but provider not found (indicates a real issue)
      if (providers.length > 0) {
        console.warn("Provider not found:", {
          selectedProviderName,
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
    // Return models in the order stored in the backend (no sorting)
    return [...(models || [])];
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

  // Function to add current selection to selectedModels
  function addOrUpdateModel() {
    if (selectedProviderName && selectedApiFormat && selectedModelName) {
      if (editingIndex !== null) {
        // Update existing model
        const newModels = [...selectedModels];
        newModels[editingIndex] = {
          providerName: selectedProviderName,
          apiFormat: selectedApiFormat,
          model: selectedModelName,
        };
        selectedModels = newModels;
        dispatch("modelsSelected", selectedModels);
        console.log("Model updated at index", editingIndex, ":", $state.snapshot(newModels[editingIndex]));
      } else {
        // Add new model (allow duplicates to support testing same model with different parameters)
        // Assign modelInstanceIndex based on existing models with the same provider/apiFormat/model
        const existingModelsWithSameConfig = selectedModels.filter(m =>
          m.providerName === selectedProviderName &&
          m.apiFormat === selectedApiFormat &&
          m.model === selectedModelName
        );

        const modelInstanceIndex = existingModelsWithSameConfig.length;

        const modelChoice: ModelChoice = {
          providerName: selectedProviderName,
          apiFormat: selectedApiFormat,
          model: selectedModelName,
          modelInstanceIndex
        };

        selectedModels = [...selectedModels, modelChoice];
        dispatch("modelsSelected", selectedModels);
        console.log("Model added:", $state.snapshot(modelChoice), "Total models:", selectedModels.length);
      }

      // Reset form
      editingIndex = null;
      selectedProviderName = "";
      selectedApiFormat = "";
      selectedModelName = "";
      selectedCategory = "middle";
    }
  }

  // Function to remove model from selection
  function removeModelFromSelection(index: number) {
    selectedModels = selectedModels.filter((_, i) => i !== index);
    dispatch("modelsSelected", selectedModels);
    console.log("Model removed. Total models:", selectedModels.length);
  }

  // Function to edit a model
  function editModel(index: number) {
    const model = selectedModels[index];
    selectedProviderName = model.providerName;
    selectedApiFormat = model.apiFormat;
    selectedModelName = model.model;

    // Find and set the category
    const provider = providers.find(
      (p) => p.name === selectedProviderName && p.api_format === selectedApiFormat,
    );
    if (provider) {
      for (const category of modelCategories) {
        const models = provider.models[category as keyof ProviderConfig["models"]];
        if (models && models.includes(selectedModelName)) {
          selectedCategory = category;
          break;
        }
      }
    }

    editingIndex = index;
    // 在移动端不自动展开，桌面端才自动展开
    setExpanded(true);
    console.log("Editing model at index", index, ":", model);
  }

  // Function to cancel editing
  function cancelEdit() {
    editingIndex = null;
    selectedProviderName = "";
    selectedApiFormat = "";
    selectedModelName = "";
    selectedCategory = "middle";
    console.log("Canceled editing");

    // Don't close the dropdown, keep it expanded for further actions
  }

  // Auto-select first available model if current selection is invalid
  $effect(() => {
    if (
      availableModels.length > 0 &&
      (!selectedModelName || !availableModels.includes(selectedModelName))
    ) {
      selectedModelName = availableModels[0];
    }
  });

  // Effect to update category when model selection changes
  $effect(() => {
    if (providers.length > 0 && selectedProviderName && selectedApiFormat && selectedModelName) {
      const provider = providers.find(
        (p) =>
          p.name === selectedProviderName && p.api_format === selectedApiFormat,
      );

      if (provider) {
        // Find which category contains the selected model
        for (const category of modelCategories) {
          const models =
            provider.models[category as keyof ProviderConfig["models"]];
          if (models && models.includes(selectedModelName)) {
            selectedCategory = category;
            console.log(
              `Model "${selectedModelName}" found in category "${category}"`,
            );
            break;
          }
        }
      }
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

      console.log("ModelSelector: Loaded providers:", $state.snapshot(providers));

      if (providers.length > 0) {
        // If provider/format/model are already set (from conversation), validate and find category
        if (selectedProviderName && selectedApiFormat && selectedModelName) {
          const provider = providers.find(
            (p) =>
              p.name === selectedProviderName && p.api_format === selectedApiFormat,
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
                `Model "${selectedModelName}" not found in provider "${selectedProviderName}", using defaults`,
              );
              selectedProviderName = "";
              selectedApiFormat = "";
              selectedModelName = "";
            }
          } else {
            // Provider not found or not enabled, fall back to defaults
            console.warn(
              `Provider "${selectedProviderName}" (${selectedApiFormat}) not found or not enabled, using defaults`,
            );
            selectedProviderName = "";
            selectedApiFormat = "";
            selectedModelName = "";
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

  // Effect to set defaults when sortedProviders changes
  // Only set defaults if all values are empty (not initialized by parent)
  $effect(() => {
    if (sortedProviders.length > 0) {
      // Only set defaults if nothing is set yet (not initialized by parent)
      if (!selectedProviderName && !selectedApiFormat && !selectedModelName) {
        selectedProviderName = sortedProviders[0].name;
        selectedApiFormat = sortedProviders[0].api_format;

        const provider =
          providers.find(
            (p) =>
              p.name === selectedProviderName &&
              p.api_format === selectedApiFormat,
          ) || sortedProviders[0];

        for (const category of modelCategories) {
          const models =
            provider.models[category as keyof ProviderConfig["models"]];
          if (models && models.length > 0) {
            selectedCategory = category;
            selectedModelName = models[0];
            console.log("Default model set to:", selectedModelName);
            break;
          }
        }
      }
    }
  });

  // 点击外部关闭弹窗
  $effect(() => {
    if (!isExpanded) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (selectorElement && !selectorElement.contains(event.target as Node)) {
        setExpanded(false);
      }
    };

    // 延迟添加监听器，避免立即触发
    const timer = setTimeout(() => {
      document.addEventListener('click', handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('click', handleClickOutside);
    };
  });

  function toggleExpanded(event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    setExpanded(!isExpanded);
  }

  // Handle provider selection
  function handleProviderChange(providerValue: string) {
    const [name, apiFormat] = providerValue.split("||");
    selectedProviderName = name;
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

  // Format model display text
  function formatModelDisplay(model: ModelChoice): string {
    return `${model.providerName}(${model.apiFormat})/${model.model}`;
  }
</script>

<div class="model-selector" bind:this={selectorElement}>
  <!-- Collapsed Header - Always Visible -->
  <div class="selector-header" onclick={toggleExpanded} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && toggleExpanded()}>
    <div class="header-content">
      <span class="header-label">
        {#if selectedModels.length > 0}
          {t('modelSelector.modelsSelected')} ({selectedModels.length})
        {:else}
          {t('modelSelector.modelsSelected')}
        {/if}
      </span>
      <span class="header-value">
        {#if selectedModels.length > 0}
          <div class="selected-models-preview">
            {#if selectedModels.length === 1}
              <span class="selected-model-tag">
                {formatModelDisplay(selectedModels[0])}
              </span>
            {:else}
              <!-- 显示第一个模型，其余显示为 +n -->
              <span class="selected-model-tag">
                {formatModelDisplay(selectedModels[0])}
              </span>
              <span class="more-models">+{selectedModels.length - 1}</span>
            {/if}
          </div>
        {:else}
          <span class="placeholder">{t('modelSelector.placeholderSelectProvider')}</span>
        {/if}
      </span>
    </div>
  </div>

  <!-- Expanded Content -->
  {#if controlledIsExpanded}
    <div class="expanded-content">
      {#if loading}
        <div class="loading">{t('modelSelector.loadingModels')}</div>
      {:else if error}
        <div class="error">{error}</div>
      {:else if providers.length > 0}
        <!-- Selected Models List -->
        {#if selectedModels.length > 0}
          <div class="selected-models-section">
            <h4 class="section-title">{t('modelSelector.selectedModels')}</h4>
            <div class="selected-models-list">
              {#each selectedModels as model, i}
                <div class="selected-model-item">
                  <span class="model-display">{formatModelDisplay(model)}</span>
                  <div class="model-actions">
                    <button class="edit-model-btn" onclick={(e) => { e.stopPropagation(); editModel(i); }} title={t('modelSelector.editModel')} disabled={editingIndex === i}>
                      ✏️
                    </button>
                    <button class="remove-model-btn" onclick={(e) => { e.stopPropagation(); removeModelFromSelection(i); }} title={t('modelSelector.removeModel')}>
                      ×
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Model Selection Form -->
        <div class="selector-row">
          <div class="selector-group provider-group">
            <label for="provider-select">{t('modelSelector.provider')}</label>
            <SlidingList
              options={providerOptions}
              value={`${selectedProviderName}||${selectedApiFormat}`}
              placeholder={t('modelSelector.selectProvider')}
              onChange={handleProviderChange}
              searchable={true}
              searchPlaceholder={t('common.searchProvider')}
              maxHeight="40vh"
              isInBottomSheet={isMobile() && isExpanded}
            />
          </div>

          <div class="selector-group category-group">
            <label for="category-select">{t('modelSelector.category')}</label>
            <SlidingList
              options={categoryOptions}
              value={selectedCategory}
              placeholder={t('modelSelector.selectCategory')}
              onChange={handleCategoryChange}
              maxHeight="30vh"
              isInBottomSheet={isMobile() && isExpanded}
            />
          </div>

          <div class="selector-group model-group">
            <label for="model-select">{t('modelSelector.model')}</label>
            <SlidingList
              options={modelOptions}
              value={selectedModelName}
              placeholder={availableModels.length === 0 ? t('modelSelector.noModels') : t('modelSelector.selectModel')}
              onChange={handleModelChange}
              searchable={true}
              searchPlaceholder={t('common.searchModel')}
              maxHeight="40vh"
              isInBottomSheet={isMobile() && isExpanded}
            />
          </div>
        </div>

        <!-- Add/Update Model Buttons -->
        {#if selectedProviderName && selectedApiFormat && selectedModelName}
          <div class="action-buttons">
            <button class="add-model-btn" onclick={(e) => { e.stopPropagation(); addOrUpdateModel(); }}>
              {#if editingIndex !== null}
                {t('modelSelector.updateModel')}: {selectedModelName}
              {:else}
                {t('modelSelector.addModel')}: {selectedModelName}
              {/if}
            </button>
            {#if editingIndex !== null}
              <button class="cancel-edit-btn" onclick={(e) => { e.stopPropagation(); cancelEdit(); }}>
                {t('common.cancel')}
              </button>
            {/if}
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
    gap: 0.5rem;
    padding: 0.1875rem 1rem 0.1875rem 0.5rem;
    cursor: pointer;
    user-select: none;
    border-radius: 0.375rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.2s ease;
    width: fit-content;
    max-width: calc(100vw - 4rem);
    position: relative;
    line-height: 1.2;
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
    font-size: 0.65rem;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
    flex-shrink: 0;
    line-height: 1.2;
  }

  .header-value {
    font-size: 0.8125rem;
    color: var(--text-primary);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: calc(100vw - 10rem);
    line-height: 1.2;
  }

  .placeholder {
    color: var(--text-tertiary);
    font-style: italic;
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
    padding: 1rem 2.5rem 0.25rem 1rem;
    min-width: 600px;
    width: max-content;
    max-width: calc(100vw - 2rem);
    z-index: 9999;
    /* 确保弹窗内容不会溢出 */
    overflow: visible;
    /* 增强滚动体验 */
    -webkit-overflow-scrolling: touch;
    scroll-behavior: smooth;
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

  /* 桌面端滚动条样式 */
  .expanded-content::-webkit-scrollbar {
    height: 10px;
  }

  .expanded-content::-webkit-scrollbar-track {
    background: var(--bg-tertiary);
    border-radius: 5px;
  }

  .expanded-content::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 5px;
    border: 2px solid var(--bg-tertiary);
  }

  .expanded-content::-webkit-scrollbar-thumb:hover {
    background: var(--primary-color);
  }

  .selector-row {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
    /* 移除内部滚动，由弹窗容器处理滚动 */
    flex-wrap: nowrap;
    overflow: visible;
    padding: 0.5rem 0;
    position: relative;
    /* 为滚动优化 - 防止收缩，确保内容可见 */
    min-width: max-content;
  }

  .selector-group {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 240px; /* 桌面端稍微缩小 */
    flex: 0 0 auto; /* 防止收缩，保持固定宽度 */
    width: 240px; /* 设置固定宽度 */
    scroll-snap-align: start;
  }

  .selector-group label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
  }

  .selected-models-section {
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
  }

  .section-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
  }

  .selected-models-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-height: 200px;
    overflow-y: auto;
    padding-right: 0.5rem;
  }

  /* Custom scrollbar for selected models list */
  .selected-models-list::-webkit-scrollbar {
    width: 6px;
  }

  .selected-models-list::-webkit-scrollbar-track {
    background: var(--bg-tertiary);
    border-radius: 3px;
  }

  .selected-models-list::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;
  }

  .selected-models-list::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
  }

  .selected-model-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
  }

  .model-display {
    font-size: 0.8rem;
    color: var(--text-primary);
    flex: 1;
  }

  .model-actions {
    display: flex;
    gap: 0.25rem;
    align-items: center;
  }

  .edit-model-btn {
    background: none;
    border: none;
    font-size: 1rem;
    cursor: pointer;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    transition: all 0.2s;
    line-height: 1;
  }

  .edit-model-btn:hover:not(:disabled) {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
  }

  .edit-model-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .remove-model-btn {
    background: none;
    border: none;
    color: var(--text-tertiary);
    font-size: 1.2rem;
    cursor: pointer;
    padding: 0 0.25rem;
    border-radius: 0.25rem;
    transition: all 0.2s;
    line-height: 1;
  }

  .remove-model-btn:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  .action-buttons {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.25rem;
    margin-bottom: 0;
  }

  .add-model-btn {
    flex: 1;
    padding: 0.75rem;
    background: rgba(34, 197, 94, 0.1);
    color: var(--success-color, #22c55e);
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .add-model-btn:hover {
    background: rgba(34, 197, 94, 0.15);
    color: var(--success-color, #22c55e);
    border-color: rgba(34, 197, 94, 0.4);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.2);
  }

  .cancel-edit-btn {
    flex: 0 0 auto;
    padding: 0.75rem 1rem;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .cancel-edit-btn:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border-color: var(--text-tertiary);
  }

  .selected-models-preview {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-wrap: nowrap; /* 防止换行 */
    /* 添加水平滚动以防溢出 */
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
  }

  .selected-model-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.25rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    font-size: 0.8rem;
    color: var(--text-secondary);
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex-shrink: 0; /* 防止收缩 */
    line-height: 1;
  }

  .more-models {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.5rem;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap; /* 防止换行 */
    flex-shrink: 0;
    line-height: 1;
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
      padding: 0.1875rem 0.5rem;
      padding-right: 1.75rem; /* 为右侧图标留出更多空间 */
      width: 100%; /* 让header占据全部可用宽度，而不是fit-content */
      max-width: calc(100vw - 3rem); /* 显著增加右边界间距（48px） */
      /* 移动端自适应高度，不设置固定最小高度 */
      min-height: 0;
      height: auto;
      /* 确保内容不会超出边界 */
      box-sizing: border-box;
      line-height: 1.2;
    }

    .model-selector {
      /* 确保容器也不会超出边界 */
      max-width: calc(100vw - 0.75rem); /* 右侧留出边距 */
      padding-right: 0.75rem; /* 增加右侧内边距 */
      box-sizing: border-box;
    }

    .header-content {
      max-width: calc(100vw - 5rem); /* 调整右侧间距，与header保持一致 */
    }

    .header-label {
      font-size: 0.625rem;
      line-height: 1.2;
    }

    .header-value {
      font-size: 0.8125rem;
      max-width: calc(100vw - 5rem); /* 调整右侧间距，与header保持一致 */
      line-height: 1.2;
      /* 确保已选模型预览区域突破父容器限制 */
    }

    .header-label {
      font-size: 0.6875rem; /* 恢复默认标签字体大小 */
      line-height: normal; /* 恢复默认行高 */
    }

    /* 移动端展开内容 - 改为底部弹出式 */
    .expanded-content {
      position: fixed;
      top: 8rem; /* 进一步增大与导航栏的间距：Header(56px) + 模型选择器(56px) + 额外176px */
      left: 0;
      right: 0;
      margin: 0;
      border-radius: 1rem 1rem 0 0;
      /* 限制弹窗宽度，保持与其他区域一致的边界 */
      width: 100vw;
      max-width: 100vw;
      min-width: 100vw;
      padding: 1.5rem 1rem 0.5rem;
      padding-left: max(1rem, env(safe-area-inset-left)); /* 考虑安全区域 */
      padding-right: max(1rem, env(safe-area-inset-right)); /* 考虑安全区域 */
      padding-bottom: max(0.5rem, env(safe-area-inset-bottom)); /* 考虑安全区域 */
      box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.25);
      z-index: 9999; /* 最高层级，确保在最上层 */
      animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      /* 移动端内部内容滚动，弹窗本身不滚动 */
      overflow-x: visible;
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
      scroll-behavior: smooth;
      touch-action: auto; /* 改为auto，允许页面滚动 */
      /* 确保内容不会超出边界 */
      box-sizing: border-box;
      /* 让弹窗高度根据内容自适应，而不是延伸到屏幕底部 */
      max-height: calc(100vh - 8rem);
    }

    @keyframes slideUp {
      from {
        opacity: 0;
        transform: translateY(100%);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .selector-row {
      /* 移动端移除内部滚动，由弹窗容器处理 */
      flex-wrap: nowrap;
      overflow: visible;
      gap: 0.625rem; /* 稍微减少间距 */
      padding: 0.75rem 0.5rem 0.75rem 0.5rem;
      margin: 0;
      /* 确保内容宽度与弹窗内容区域一致，考虑安全区域 */
      width: calc(100vw - 2rem - max(0, env(safe-area-inset-left)) - max(0, env(safe-area-inset-right)));
      max-width: calc(100vw - 2rem - max(0, env(safe-area-inset-left)) - max(0, env(safe-area-inset-right)));
      /* 移除scroll-snap-align，防止干扰滚动 */
    }

    .selector-group {
      /* 移动端选择器自适应宽度，平分容器空间 */
      flex: 1 1 0; /* flex-grow: 1, flex-shrink: 1, flex-basis: 0% */
      min-width: 120px; /* 最小宽度，确保可读性 */
      width: 0; /* 让flex分配空间 */
      /* 确保选择器组不会超出边界 */
      max-width: 100%;
    }

    /* 确保选择器组内的SlidingList也被限制宽度 */
    .selector-group :global(.sliding-list) {
      width: 100%;
      max-width: 100%;
    }

    /* 确保已选模型列表区域与选择器行宽度一致 */
    .selected-models-section {
      width: calc(100vw - 2rem - max(0, env(safe-area-inset-left)) - max(0, env(safe-area-inset-right)));
      max-width: calc(100vw - 2rem - max(0, env(safe-area-inset-left)) - max(0, env(safe-area-inset-right)));
      overflow-x: hidden; /* 防止内容超出 */
    }

    /* 确保按钮区域与选择器行宽度一致 */
    .action-buttons {
      width: calc(100vw - 2rem - max(0, env(safe-area-inset-left)) - max(0, env(safe-area-inset-right)));
      max-width: calc(100vw - 2rem - max(0, env(safe-area-inset-left)) - max(0, env(safe-area-inset-right)));
      overflow-x: hidden; /* 防止内容超出 */
    }

    /* 确保选择器行内的内容也不会超出边界 */
    .selector-row * {
      box-sizing: border-box;
    }

    /* 移动端滚动条样式 */
    .expanded-content::-webkit-scrollbar {
      height: 6px;
    }

    .expanded-content::-webkit-scrollbar-track {
      background: transparent;
    }

    .expanded-content::-webkit-scrollbar-thumb {
      background: var(--primary-color);
      border-radius: 3px;
      opacity: 0.5;
    }

    /* 移动端按钮优化 */
    .add-model-btn,
    .cancel-edit-btn {
      min-height: 40px;
      font-size: 0.875rem;
    }

    /* 移动端模型列表优化 */
    .selected-models-list {
      max-height: 150px;
    }
  }

  @media (max-width: 480px) {
    .selector-header {
      padding: 0.1875rem 0.5rem;
      padding-right: 1.75rem; /* 为右侧图标留出更多空间 */
      width: 100%; /* 让header占据全部可用宽度，而不是fit-content */
      max-width: calc(100vw - 5rem); /* 显著增加右边界间距（80px） */
      min-height: 0;
      height: auto;
      /* 确保内容不会超出边界 */
      box-sizing: border-box;
      line-height: 1.2;
    }

    .model-selector {
      /* 确保容器也不会超出边界 */
      max-width: calc(100vw - 0.75rem); /* 右侧留出边距 */
      padding-right: 0.75rem; /* 增加右侧内边距 */
      box-sizing: border-box;
    }

    .header-content {
      max-width: calc(100vw - 5rem); /* 调整右侧间距，与header保持一致 */
    }

    .header-value {
      font-size: 0.8125rem;
      max-width: calc(100vw - 5rem); /* 调整右侧间距，与header保持一致 */
    }

    .selected-models-preview {
      /* 在移动端使用更灵活的显示策略 */
      display: flex;
      gap: 0.25rem;
      align-items: center;
      flex-wrap: nowrap; /* 防止换行 */
      margin-top: 0;
      /* 允许水平滚动，避免被父容器截断 */
      overflow-x: auto;
      overflow-y: hidden;
      -webkit-overflow-scrolling: touch;
      /* 保持与header一致的右边界间距 */
      max-width: calc(100vw - 3rem);
      width: 100%;
      /* 确保标签不会被隐藏 */
      flex-shrink: 0;
    }

    .selected-model-tag {
      /* 确保模型标签在移动端也不会被压缩 */
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.0625rem 0.375rem;
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      border-radius: 0.375rem;
      font-size: 0.8rem;
      color: var(--text-secondary);
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex-shrink: 0; /* 防止收缩 */
      line-height: 1;
    }

    .more-models {
      /* 确保 "+n" 标签在移动端可见 */
      display: inline-flex;
      align-items: center;
      padding: 0.25rem 0.5rem;
      background: var(--bg-tertiary);
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
      border-radius: 0.375rem;
      font-size: 0.75rem;
      font-weight: 600;
      white-space: nowrap; /* 防止换行 */
      flex-shrink: 0;
      line-height: 1;
    }

    /* 超小屏幕保持底部弹出式 */
    .expanded-content {
      border-radius: 0.75rem 0.75rem 0 0;
      max-height: calc(100vh - 10rem);
      padding: 1rem 0.75rem calc(0.5rem + env(safe-area-inset-bottom));
      padding-left: max(0.75rem, env(safe-area-inset-left));
      padding-right: max(0.75rem, env(safe-area-inset-right));
      /* 进一步增大与导航栏的间距 */
      top: 10rem;
      margin-top: 1rem;
    }

    .selector-row {
      /* 超小屏幕移除内部滚动，进一步缩小间距 */
      gap: 0.5rem;
      padding: 0.5rem 0.25rem 0.5rem 0.25rem;
      min-width: max-content;
      /* 修正宽度计算，考虑安全区域 */
      width: calc(100vw - 1.5rem - max(0, env(safe-area-inset-left)) - max(0, env(safe-area-inset-right)));
      max-width: calc(100vw - 1.5rem - max(0, env(safe-area-inset-left)) - max(0, env(safe-area-inset-right)));
    }

    .selector-group {
      /* 超小屏幕选择器也使用自适应宽度 */
      flex: 1 1 0; /* flex-grow: 1, flex-shrink: 1, flex-basis: 0% */
      min-width: 120px; /* 最小宽度 */
      width: 0; /* 让flex分配空间 */
      /* 确保选择器组不会超出边界 */
      max-width: 100%;
    }

    /* 超小屏幕按钮优化 */
    .action-buttons {
      flex-direction: column;
      gap: 0.5rem;
    }

    .add-model-btn,
    .cancel-edit-btn {
      width: 100%;
      min-height: 40px;
      font-size: 0.875rem;
    }
  }
</style>
