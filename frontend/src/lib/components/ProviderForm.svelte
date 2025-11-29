<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Button from './ui/Button.svelte';
  import Input from './ui/Input.svelte';
  import type { Provider, ProviderFormData } from '$types/provider';
  import { tStore } from '$stores/language';

  let { provider = null, loading = false, apiFormat = undefined } = $props<{
    provider: Provider | null;
    loading: boolean;
    apiFormat?: string;
  }>();

  const dispatch = createEventDispatcher<{
    save: { provider: Provider; api_format?: string };
    cancel: void;
  }>();

  let formData: ProviderFormData = $state({
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
    },
    api_format: 'openai' // Default to 'openai' for backward compatibility
  });

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
      },
      // Use the provided api_format or the provider's api_format, default to 'openai' if neither
      api_format: (provider.api_format || apiFormat || 'openai') as 'openai' | 'anthropic'
    };
  }

  let errors: Record<string, string> = $state({});
  let showApiKey = $state(false);

  // 获取翻译函数
  const t = $derived($tStore);

  // String versions for binding to Input components
  let timeoutStr = $state('60');
  let maxRetriesStr = $state('1');
  let priorityStr = $state('1');

  // Update string versions when formData changes
  $effect(() => {
    if (formData) {
      timeoutStr = formData.timeout.toString();
      maxRetriesStr = formData.max_retries.toString();
      priorityStr = formData.priority.toString();
    }
  });

  // Update api_format when apiFormat prop changes (for new providers)
  $effect(() => {
    if (!provider && apiFormat) {
      formData.api_format = apiFormat as 'openai' | 'anthropic';
    }
  });

  function validateForm(): boolean {
    errors = {};

    if (!formData.name.trim()) {
      errors.name = t("providerForm.providerNameRequired");
    }

    if (!formData.api_key.trim()) {
      errors.api_key = t("providerForm.apiKeyRequired");
    }

    if (!formData.base_url.trim()) {
      errors.base_url = t("providerForm.baseUrlRequired");
    } else if (!isValidUrl(formData.base_url)) {
      errors.base_url = t("providerForm.baseUrlInvalid");
    }

    if (formData.timeout < 1) {
      errors.timeout = t("providerForm.timeoutRequired");
    }

    if (formData.max_retries < 0) {
      errors.max_retries = t("providerForm.maxRetriesRequired");
    }

    if (formData.priority < 1) {
      errors.priority = t("providerForm.priorityRequired");
    }

    // Check if at least one model category has models
    const hasModels = formData.models.big.length > 0
      || formData.models.middle.length > 0
      || formData.models.small.length > 0;

    if (!hasModels) {
      errors.models = t("providerForm.modelConfigHelp");
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
    // Ensure api_format is explicitly set (use the value from formData, default to 'openai' only if truly missing)
    const apiFormat = formData.api_format && formData.api_format.trim() !== ''
      ? formData.api_format
      : 'openai';

    const providerData: Provider = {
      ...formData,
      // Keep API key as-is (user might not want to change it)
      api_key: formData.api_key,
      // Explicitly set api_format
      api_format: apiFormat
    };

    // Debug: log the api_format value being sent
    console.log('ProviderForm: Sending provider data with api_format =', providerData.api_format);
    console.log('ProviderForm: Full formData.api_format =', formData.api_format);

    // Pass the current editing api_format for precise identification
    const saveData = {
      provider: providerData,
      api_format: apiFormat || apiFormat
    };

    dispatch('save', saveData);
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

  function _updateModel(
    category: 'big' | 'middle' | 'small',
    index: number,
    value: string
  ) {
    formData.models[category][index] = value;
  }

  // Drag and drop functions
  let draggedIndex: number | null = $state(null);
  let draggedCategory: 'big' | 'middle' | 'small' | null = $state(null);

  function handleDragStart(
    category: 'big' | 'middle' | 'small',
    index: number,
    event: DragEvent
  ) {
    draggedIndex = index;
    draggedCategory = category;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', `${category}-${index}`);
    }
  }

  function handleDragOver(
    category: 'big' | 'middle' | 'small',
    index: number,
    event: DragEvent
  ) {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
  }

  function handleDrop(
    category: 'big' | 'middle' | 'small',
    index: number,
    event: DragEvent
  ) {
    event.preventDefault();

    if (
      draggedIndex === null ||
      draggedCategory === null ||
      draggedCategory !== category
    ) {
      return;
    }

    // Don't move if dropping on the same item
    if (draggedIndex === index) {
      return;
    }

    const models = [...formData.models[category]];
    const [draggedModel] = models.splice(draggedIndex, 1);
    models.splice(index, 0, draggedModel);
    formData.models[category] = models;

    // Reset drag state
    draggedIndex = null;
    draggedCategory = null;
  }

  function handleDragEnd() {
    draggedIndex = null;
    draggedCategory = null;
  }

  // Custom headers management
  let newHeaderKey = $state('');
  let newHeaderValue = $state('');

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

  // Header editing state
  let editingHeaderKey: string | null = $state(null);
  let editingHeaderKeyValue = $state('');
  let editingHeaderValueValue = $state('');

  function startEditHeader(key: string, value: string) {
    editingHeaderKey = key;
    editingHeaderKeyValue = key;
    editingHeaderValueValue = value;
  }

  function cancelEditHeader() {
    editingHeaderKey = null;
    editingHeaderKeyValue = '';
    editingHeaderValueValue = '';
  }

  function saveEditHeader(oldKey: string) {
    if (editingHeaderKeyValue.trim() && editingHeaderValueValue.trim()) {
      // If key changed, delete old key
      if (oldKey !== editingHeaderKeyValue) {
        delete formData.custom_headers[oldKey];
      }
      formData.custom_headers[editingHeaderKeyValue] = editingHeaderValueValue;
      editingHeaderKey = null;
      editingHeaderKeyValue = '';
      editingHeaderValueValue = '';
    }
  }
</script>

<div class="form">
  <div class="form-section">
    <h3>{t("providerForm.basicInfo")}</h3>

    <div class="form-group">
      <label for="name">
        {t("providerForm.providerName")} <span class="required">*</span>
      </label>
      <Input
        id="name"
        type="text"
        bind:value={formData.name}
        placeholder={t("providerForm.providerNamePlaceholder")}
        autocomplete="off"
        required
      />
      {#if errors.name}
        <span class="error">{errors.name}</span>
      {/if}
    </div>

    <div class="form-group">
      <label for="base_url">
        {t("providerForm.baseUrl")} <span class="required">*</span>
      </label>
      <Input
        id="base_url"
        type="text"
        bind:value={formData.base_url}
        placeholder={t("providerForm.baseUrlPlaceholder")}
        autocomplete="off"
        required
      />
      {#if errors.base_url}
        <span class="error">{errors.base_url}</span>
      {/if}
    </div>

    <div class="form-group">
      <label for="api_key">
        {t("providerForm.apiKey")} <span class="required">*</span>
      </label>
      <div class="password-input">
        <Input
          id="api_key"
          type={showApiKey ? 'text' : 'password'}
          bind:value={formData.api_key}
          placeholder={t("providerForm.apiKeyPlaceholder")}
          autocomplete="new-password"
          required
        />
        <button
          type="button"
          class="toggle-password"
          onclick={() => showApiKey = !showApiKey}
          title={showApiKey ? t("providerForm.hideApiKey") : t("providerForm.showApiKey")}
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
        {t("providerForm.apiVersion")}
      </label>
      <Input
        id="api_version"
        type="text"
        value={formData.api_version || ''}
        on:input={(e) => {
          const target = e.currentTarget as HTMLInputElement;
          formData.api_version = target.value || null;
        }}
        placeholder={t("providerForm.apiVersionPlaceholder")}
        autocomplete="off"
      />
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="timeout">
          {t("providerForm.timeout")} <span class="required">*</span>
        </label>
        <Input
          id="timeout"
          type="number"
          bind:value={timeoutStr}
          on:input={(e) => {
            const target = e.currentTarget as HTMLInputElement;
            timeoutStr = target.value;
            formData.timeout = parseInt(timeoutStr) || 60;
          }}
          autocomplete="off"
          required
        />
        {#if errors.timeout}
          <span class="error">{errors.timeout}</span>
        {/if}
      </div>

      <div class="form-group">
        <label for="max_retries">
          {t("providerForm.maxRetries")} <span class="required">*</span>
        </label>
        <Input
          id="max_retries"
          type="number"
          bind:value={maxRetriesStr}
          on:input={(e) => {
            const target = e.currentTarget as HTMLInputElement;
            maxRetriesStr = target.value;
            formData.max_retries = parseInt(maxRetriesStr) || 1;
          }}
          autocomplete="off"
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
          {t("providerForm.priority")} <span class="required">*</span>
        </label>
        <Input
          id="priority"
          type="number"
          bind:value={priorityStr}
          on:input={(e) => {
            const target = e.currentTarget as HTMLInputElement;
            priorityStr = target.value;
            formData.priority = parseInt(priorityStr) || 1;
          }}
          autocomplete="off"
          required
        />
        <small>{t("providerForm.priorityHelp")}</small>
        {#if errors.priority}
          <span class="error">{errors.priority}</span>
        {/if}
      </div>

      <div class="form-group">
        <label for="api_format">
          {t("providerForm.apiFormat")} <span class="required">*</span>
        </label>
        <select id="api_format" bind:value={formData.api_format} class="select-input" autocomplete="off">
          <option value="openai">{t("providerForm.apiFormatOpenAI")}</option>
          <option value="anthropic">{t("providerForm.apiFormatAnthropic")}</option>
        </select>
        <small>{t("providerForm.apiFormatHelp")}</small>
      </div>
    </div>
  </div>

  <div class="form-section">
    <h3>{t("providerForm.modelConfig")}</h3>
    <small>{t("providerForm.modelConfigHelp")}</small>

    {#if errors.models}
      <span class="error">{errors.models}</span>
    {/if}

    <!-- Large Models -->
    <div class="model-section">
      <div class="model-header">
        <h3>{t("providerForm.bigModels")}</h3>
        <Button size="sm" on:click={() => addModel('big')} title={t("providerForm.addBigModel")} class="icon-button">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </Button>
      </div>
      <div class="model-list">
        {#each formData.models.big as _model, index}
          <div
            class="model-item"
            class:dragging={draggedCategory === 'big' && draggedIndex === index}
            draggable="true"
            role="listitem"
            ondragstart={(e) => handleDragStart('big', index, e)}
            ondragover={(e) => handleDragOver('big', index, e)}
            ondrop={(e) => handleDrop('big', index, e)}
            ondragend={handleDragEnd}
          >
            <div class="drag-handle" title={t("providerForm.dragToSort")}>
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"></path>
              </svg>
            </div>
            <Input
              type="text"
              bind:value={formData.models.big[index]}
              placeholder={t("providerForm.modelNamePlaceholder")}
              autocomplete="off"
            />
            <div class="model-actions">
              <Button
                variant="danger"
                size="sm"
                on:click={() => removeModel('big', index)}
                title={t("providerForm.delete")}
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
          <p class="empty-models">{t("providerForm.noBigModels")}</p>
        {/if}
      </div>
    </div>

    <!-- Middle Models -->
    <div class="model-section">
      <div class="model-header">
        <h3>{t("providerForm.middleModels")}</h3>
        <Button size="sm" on:click={() => addModel('middle')} title={t("providerForm.addMiddleModel")} class="icon-button">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </Button>
      </div>
      <div class="model-list">
        {#each formData.models.middle as _model, index}
          <div
            class="model-item"
            class:dragging={draggedCategory === 'middle' && draggedIndex === index}
            draggable="true"
            role="listitem"
            ondragstart={(e) => handleDragStart('middle', index, e)}
            ondragover={(e) => handleDragOver('middle', index, e)}
            ondrop={(e) => handleDrop('middle', index, e)}
            ondragend={handleDragEnd}
          >
            <div class="drag-handle" title={t("providerForm.dragToSort")}>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="5" cy="7" r="1.5"></circle>
                <circle cx="5" cy="12" r="1.5"></circle>
                <circle cx="5" cy="17" r="1.5"></circle>
                <circle cx="12" cy="7" r="1.5"></circle>
                <circle cx="12" cy="12" r="1.5"></circle>
                <circle cx="12" cy="17" r="1.5"></circle>
              </svg>
            </div>
            <Input
              type="text"
              bind:value={formData.models.middle[index]}
              placeholder={t("providerForm.modelNamePlaceholder")}
              autocomplete="off"
            />
            <div class="model-actions">
              <Button
                variant="danger"
                size="sm"
                on:click={() => removeModel('middle', index)}
                title={t("providerForm.delete")}
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
          <p class="empty-models">{t("providerForm.noMiddleModels")}</p>
        {/if}
      </div>
    </div>

    <!-- Small Models -->
    <div class="model-section">
      <div class="model-header">
        <h3>{t("providerForm.smallModels")}</h3>
        <Button size="sm" on:click={() => addModel('small')} title={t("providerForm.addSmallModel")} class="icon-button">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </Button>
      </div>
      <div class="model-list">
        {#each formData.models.small as _model, index}
          <div
            class="model-item"
            class:dragging={draggedCategory === 'small' && draggedIndex === index}
            draggable="true"
            role="listitem"
            ondragstart={(e) => handleDragStart('small', index, e)}
            ondragover={(e) => handleDragOver('small', index, e)}
            ondrop={(e) => handleDrop('small', index, e)}
            ondragend={handleDragEnd}
          >
            <div class="drag-handle" title={t("providerForm.dragToSort")}>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="5" cy="7" r="1.5"></circle>
                <circle cx="5" cy="12" r="1.5"></circle>
                <circle cx="5" cy="17" r="1.5"></circle>
                <circle cx="12" cy="7" r="1.5"></circle>
                <circle cx="12" cy="12" r="1.5"></circle>
                <circle cx="12" cy="17" r="1.5"></circle>
              </svg>
            </div>
            <Input
              type="text"
              bind:value={formData.models.small[index]}
              placeholder={t("providerForm.modelNamePlaceholder")}
              autocomplete="off"
            />
            <div class="model-actions">
              <Button
                variant="danger"
                size="sm"
                on:click={() => removeModel('small', index)}
                title={t("providerForm.delete")}
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
          <p class="empty-models">{t("providerForm.noSmallModels")}</p>
        {/if}
      </div>
    </div>
  </div>

  <div class="form-section">
    <h3>{t("providerForm.customHeaders")}</h3>
    <small>{t("providerForm.customHeadersHelp")}</small>

    <div class="headers-input">
      <Input
        type="text"
        bind:value={newHeaderKey}
        placeholder={t("providerForm.headerName")}
        autocomplete="off"
      />
      <Input
        type="text"
        bind:value={newHeaderValue}
        placeholder={t("providerForm.headerValue")}
        autocomplete="off"
      />
      <Button size="sm" on:click={addHeader} title={t("providerForm.addHeader")} class="icon-button">
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
            {#if editingHeaderKey === key}
              <!-- 编辑模式 -->
              <Input
                type="text"
                bind:value={editingHeaderKeyValue}
                placeholder={t("providerForm.headerName")}
                autocomplete="off"
                class="header-edit-input"
              />
              <span class="header-separator">:</span>
              <Input
                type="text"
                bind:value={editingHeaderValueValue}
                placeholder={t("providerForm.headerValue")}
                autocomplete="off"
                class="header-edit-input"
              />
              <div class="header-edit-actions">
                <Button
                  variant="secondary"
                  size="sm"
                  on:click={() => saveEditHeader(key)}
                  title={t("providerForm.save")}
                  class="icon-button"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  on:click={cancelEditHeader}
                  title={t("providerForm.cancel")}
                  class="icon-button"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </Button>
              </div>
            {:else}
              <!-- 显示模式 -->
              <span class="header-key">{key}:</span>
              <span class="header-value">{value}</span>
              <div class="header-actions">
                <Button
                  variant="secondary"
                  size="sm"
                  on:click={() => startEditHeader(key, value)}
                  title={t("providerForm.edit")}
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
                  on:click={() => removeHeader(key)}
                  title={t("providerForm.delete")}
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
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <div class="form-actions">
    <Button variant="secondary" on:click={handleCancel} disabled={loading} title={t("providerForm.cancel")} class="icon-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </Button>
    <Button type="submit" on:click={handleSave} disabled={loading} title={loading ? t("providerForm.saving") : t("providerForm.save")} class="icon-button">
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

  .model-header h3 {
    font-weight: 500;
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
    margin: 0;
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

  .header-separator {
    color: var(--text-secondary, #666);
    user-select: none;
  }

  .header-actions {
    display: flex;
    gap: 0.25rem;
    margin-left: auto;
  }

  .header-edit-actions {
    display: flex;
    gap: 0.25rem;
    margin-left: auto;
  }

  .header-item :global(.header-edit-input) {
    flex: 1;
    min-width: 0;
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

  .select-input {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 0.375rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
    cursor: pointer;
    width: 100%;
    font-family: inherit;
  }

  .select-input:focus {
    outline: 2px solid var(--primary-color, #007bff);
    outline-offset: 2px;
    border-color: var(--primary-color, #007bff);
  }

  .drag-handle {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem;
    cursor: grab;
    color: var(--text-secondary, #999);
    transition: color 0.2s, background-color 0.2s;
    border-radius: 0.25rem;
    user-select: none;
    flex-shrink: 0;
  }

  .drag-handle:hover {
    color: var(--text-primary, #495057);
    background: var(--bg-tertiary, #f8f9fa);
  }

  .drag-handle:active {
    cursor: grabbing;
  }

  .drag-handle svg {
    width: 1.25rem;
    height: 1.25rem;
  }

  .model-item.dragging {
    opacity: 0.6;
    border: 1px dashed var(--primary-color, #007bff);
    background: var(--bg-tertiary, #f8f9fa);
  }

  .model-item[draggable="true"] {
    cursor: move;
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
