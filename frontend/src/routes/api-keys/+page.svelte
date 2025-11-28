<script lang="ts">
  import { onMount } from "svelte";
  import { onDestroy } from "svelte";
  import { browser } from "$app/environment";
  import { tick } from "svelte";
  import Button from "$components/ui/Button.svelte";
  import Card from "$components/ui/Card.svelte";
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  import Badge from "$components/ui/Badge.svelte";
  import Input from "$components/ui/Input.svelte";
  import { apiKeysService } from "$services/apiKeys";
  import { toast } from "$stores/toast";
  import {
    saveFullApiKey,
    getFullApiKey,
    hasFullApiKey,
    removeFullApiKey,
  } from "$services/apiKeyStorage";
  import type {
    APIKey,
    CreateAPIKeyRequest,
    UpdateAPIKeyRequest,
  } from "$types/apiKey";
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  import type { APIKeyListResponse } from "$services/apiKeys";

  let loading = true;
  let apiKeys: APIKey[] = [];
  let allAPIKeysData: APIKey[] = []; // 存储所有已加载的数据
  let showCreateForm = false;
  let editingKey: APIKey | null = null;
  let saving = false;
  let newKey: CreateAPIKeyRequest = { name: "" };
  let editForm: UpdateAPIKeyRequest = {};
  let expandedKeyIds: Set<string> = new Set(); // 存储已展开显示完整Key的ID
  let fullApiKeysCache: Record<number, string> = {}; // 缓存完整 API Key（使用对象而不是Map）
  let loadingFullKeys: Set<number> = new Set(); // 正在加载完整 Key 的 ID 集合

  // 筛选和分页（响应式）
  $: filteredAPIKeys = (() => {
    let filtered = allAPIKeysData;

    // 搜索过滤
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = filtered.filter((key) =>
        key.name.toLowerCase().includes(query),
      );
    }

    // 状态过滤
    if (filterStatus === "active") {
      filtered = filtered.filter((key) => key.is_active);
    } else if (filterStatus === "inactive") {
      filtered = filtered.filter((key) => !key.is_active);
    }

    // 更新分页信息
    totalCount = filtered.length;
    totalPages = Math.ceil(totalCount / pageSize);

    // 确保当前页在有效范围内
    if (totalPages === 0) {
      currentPage = 1;
    } else if (totalPages > 0 && currentPage > totalPages) {
      currentPage = totalPages;
    } else if (currentPage < 1) {
      currentPage = 1;
    }

    // 分页切片
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return filtered.slice(start, end);
  })();

  // 当前页显示的数据（响应式）
  $: apiKeys = filteredAPIKeys;

  // 分页相关
  let currentPage = 1;
  const pageSize = 10;
  let totalPages = 1;
  let totalCount = 0;
  let loadingKeys = false;

  // 筛选相关
  let searchQuery = "";
  let filterStatus: "all" | "active" | "inactive" = "all";

  // 防抖定时器
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;

  onDestroy(() => {
    // 取消所有进行中的请求
    if (abortController) {
      abortController.abort();
      abortController = null;
    }

    // 清理防抖定时器
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  });

  onMount(async () => {
    abortController = new AbortController();
    try {
      await loadAPIKeys();
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      throw error;
    }
  });

  async function loadAPIKeys() {
    if (!abortController) return;
    loadingKeys = true;
    try {
      // 加载所有数据（使用较大的 limit）
      const params: any = {
        limit: 1000, // 加载更多数据以支持客户端分页
        offset: 0,
      };

      // 注意：搜索和状态筛选改为客户端处理，不发送到服务器
      // 这样可以支持客户端实时搜索和分页

      const result = await apiKeysService.getAll(params, {
        signal: abortController.signal,
      });

      // 检查是否已被取消
      if (abortController.signal.aborted) return;

      console.debug("[API Keys] Response:", result);
      allAPIKeysData = Array.isArray(result?.data) ? result.data : [];

      console.debug("[API Keys] Loaded:", allAPIKeysData.length, "keys");

      // 响应式语句会自动更新 filteredAPIKeys、totalCount、totalPages 和 apiKeys
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      console.error("Failed to load API keys:", error);
      toast.error("加载 API Key 列表失败");
      // 确保 allAPIKeysData 始终是数组
      allAPIKeysData = [];
    } finally {
      if (!abortController?.signal.aborted) {
        loading = false;
        loadingKeys = false;
      }
    }
  }

  function handleSearch() {
    // 防抖：300ms 后执行
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      currentPage = 1; // 搜索时重置到第一页
      // 不需要重新加载数据，响应式语句会自动更新
    }, 300);
  }

  function handleFilterChange() {
    currentPage = 1; // 筛选时重置到第一页
    // 不需要重新加载数据，响应式语句会自动更新
  }

  function handlePageChange(newPage: number) {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      currentPage = newPage;
      // 不需要重新加载数据，响应式语句会自动更新 apiKeys
    }
  }

  function clearFilters() {
    searchQuery = "";
    filterStatus = "all";
    currentPage = 1;
    // 不需要重新加载数据，响应式语句会自动更新
  }

  function handleCreate() {
    newKey = { name: "" };
    showCreateForm = true;
  }

  async function handleSaveCreate() {
    if (!newKey.name.trim()) {
      toast.error("请输入用户名");
      return;
    }

    saving = true;
    try {
      // 构建请求数据
      const requestData: CreateAPIKeyRequest = {
        name: newKey.name.trim(),
      };

      console.log("Sending request:", requestData);
      const response = await apiKeysService.create(requestData);
      // 保存完整 key 到 localStorage
      saveFullApiKey(response.id, response.api_key);
      toast.success("API Key 创建成功");
      await loadAPIKeys();
      handleCloseCreateForm();
    } catch (error) {
      console.error("Failed to create API key:", error);
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      toast.error("创建失败: " + errorMessage);
    } finally {
      saving = false;
    }
  }

  function handleCloseCreateForm() {
    showCreateForm = false;
    newKey = { name: "" };
  }

  function handleEdit(key: APIKey) {
    editingKey = key;
    editForm = {
      name: key.name,
      is_active: key.is_active,
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
      // 构建请求数据
      const requestData: UpdateAPIKeyRequest = {
        name: editForm.name,
        is_active: editForm.is_active,
      };

      await apiKeysService.update(editingKey.id, requestData);
      toast.success("更新成功");
      await loadAPIKeys();
      handleCancelEdit();
    } catch (error) {
      console.error("Failed to update API key:", error);
      toast.error("更新失败: " + (error as Error).message);
    } finally {
      saving = false;
    }
  }

  async function handleDelete(key: APIKey) {
    const message =
      `确定要删除 API Key "${key.name}" 吗？\n\n` +
      `删除后该 Key 将立即失效，且无法恢复。\n` +
      `如果 Key 已丢失，删除后可以重新创建。`;

    if (!confirm(message)) {
      return;
    }

    try {
      await apiKeysService.delete(key.id);
      // 删除 localStorage 中保存的完整 key
      removeFullApiKey(key.id);
      toast.success("删除成功");
      await loadAPIKeys();
    } catch (error) {
      console.error("Failed to delete API key:", error);
      toast.error("删除失败: " + (error as Error).message);
    }
  }

  async function handleToggleActive(key: APIKey) {
    try {
      await apiKeysService.update(key.id, { is_active: !key.is_active });
      toast.success(key.is_active ? "已禁用" : "已启用");
      await loadAPIKeys();
    } catch (error) {
      console.error("Failed to toggle API key status:", error);
      toast.error("操作失败: " + (error as Error).message);
    }
  }

  async function copyToClipboard(text: string) {
    if (!browser) return;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        toast.success("已复制到剪贴板");
      } else {
        // 降级方案
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
        toast.success("已复制到剪贴板");
      }
    } catch (error) {
      console.error("Failed to copy:", error);
      toast.error("复制失败，请手动复制");
    }
  }

  /**
   * 复制完整 API Key
   */
  async function copyFullKey(key: APIKey) {
    const fullKey = await ensureFullApiKey(key.id);
    if (!fullKey) {
      toast.error("无法获取完整 Key。如果 Key 已丢失，请删除后重新创建。");
      return;
    }
    await copyToClipboard(fullKey);
  }

  /**
   * 确保获取完整的 API Key（优先使用缓存，否则从后端获取）
   * @param keyId API Key ID
   * @returns 完整的 API Key
   */
  async function ensureFullApiKey(keyId: number): Promise<string | null> {
    // 优先使用内存缓存
    if (fullApiKeysCache[keyId]) {
      return fullApiKeysCache[keyId];
    }

    // 尝试从 localStorage 或后端获取
    const fullKey = await getFullApiKey(keyId);
    if (fullKey) {
      // 保存到内存缓存
      fullApiKeysCache[keyId] = fullKey;
      // 创建新对象以触发响应式更新
      fullApiKeysCache = { ...fullApiKeysCache };
      // 等待 DOM 更新
      await tick();
    }
    return fullKey;
  }

  /**
   * 检查是否有完整 API Key（使用本地检查）
   * @param keyId API Key ID
   * @returns 是否有完整 API Key
   */
  function hasFullKeyLocal(keyId: number): boolean {
    return !!fullApiKeysCache[keyId] || hasFullApiKey(keyId);
  }

  /**
   * 切换展开/收起完整 Key 显示
   */
  async function toggleExpanded(keyId: string) {
    const keyIdNum = parseInt(keyId);

    if (expandedKeyIds.has(keyId)) {
      // 收起
      expandedKeyIds.delete(keyId);
    } else {
      // 展开
      expandedKeyIds.add(keyId);

      // 如果没有完整 Key，则异步获取
      if (!fullApiKeysCache[keyIdNum]) {
        loadingFullKeys.add(keyIdNum);
        loadingFullKeys = new Set(loadingFullKeys); // 触发响应式更新

        try {
          await ensureFullApiKey(keyIdNum);
        } finally {
          loadingFullKeys.delete(keyIdNum);
          loadingFullKeys = new Set(loadingFullKeys); // 触发响应式更新
        }
      }
    }
    // 强制更新
    expandedKeyIds = new Set(expandedKeyIds);
  }

  /**
   * 获取显示的 API Key 文本（完整或前缀）
   * 响应式函数，当依赖项变化时会自动重新计算
   */
  $: getDisplayKeyText = (keyId: number, keyPrefix: string) => {
    const keyIdStr = keyId.toString();

    if (expandedKeyIds.has(keyIdStr)) {
      // 如果正在加载，显示加载状态
      if (loadingFullKeys.has(keyId)) {
        return "正在加载...";
      }

      // 如果已展开，优先使用内存缓存
      const cachedKey = fullApiKeysCache[keyId];
      if (cachedKey) {
        return cachedKey;
      }

      // 如果内存缓存中没有，尝试从 localStorage 获取
      if (typeof localStorage !== "undefined") {
        const localKey = localStorage.getItem(`api_key_full_${keyId}`);
        if (localKey) {
          return localKey;
        }
      }

      // 如果都没有，返回前缀（稍后会通过异步加载更新）
      return keyPrefix + "...";
    }
    return keyPrefix + "...";
  };

  function formatDate(dateStr?: string): string {
    if (!dateStr) return "-";
    try {
      // SQLite 返回的时间格式通常是 "YYYY-MM-DD HH:MM:SS"，没有时区信息
      // 假设它是 UTC 时间，添加 'Z' 后缀以确保正确解析
      let dateStrToParse = dateStr;
      if (dateStr.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
        // 格式为 "YYYY-MM-DD HH:MM:SS"，假设是 UTC 时间
        dateStrToParse = dateStr.replace(" ", "T") + "Z";
      } else if (dateStr.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/)) {
        // 格式为 "YYYY-MM-DDTHH:MM:SS"，假设是 UTC 时间
        dateStrToParse = dateStr + "Z";
      }

      const date = new Date(dateStrToParse);

      // 检查日期是否有效
      if (isNaN(date.getTime())) {
        return dateStr; // 如果日期无效，返回原始字符串
      }

      // 使用明确的时区和格式选项
      return date.toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
    } catch {
      return dateStr;
    }
  }
</script>

<div class="container">
  <div class="page-header">
    <Button on:click={handleCreate} title="创建 API Key" class="icon-button">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
      </svg>
    </Button>
  </div>

  {#if loading}
    <div class="loading">
      <p>加载中...</p>
    </div>
  {:else}
    <Card>
      <!-- 搜索和筛选 -->
      <div class="filters">
        <div class="filter-row">
          <div class="filter-group search-group">
            <Input
              type="text"
              bind:value={searchQuery}
              on:input={handleSearch}
              placeholder="搜索用户名..."
            />
          </div>

          <div class="filter-group">
            <label for="api-key-filter-status">状态:</label>
            <select
              id="api-key-filter-status"
              class="filter-select"
              bind:value={filterStatus}
              on:change={handleFilterChange}
            >
              <option value="all">全部</option>
              <option value="active">已启用</option>
              <option value="inactive">已禁用</option>
            </select>
          </div>

          <Button
            variant="secondary"
            size="sm"
            on:click={clearFilters}
            title="清除筛选"
            class="clear-button"
          >
            清除
          </Button>
        </div>
      </div>

      {#if loadingKeys}
        <div class="loading-keys">
          <p>加载中...</p>
        </div>
      {:else if !apiKeys || apiKeys.length === 0}
        <div class="empty">
          <p>暂无 API Key</p>
        </div>
      {:else}
        <div class="table-container">
          <table class="api-keys-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>Key</th>
                <th style="text-align: center;">状态</th>
                <th>创建时间</th>
                <th>最后使用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {#each apiKeys as key}
                <tr class={!key.is_active ? "disabled-row" : ""}>
                  <td class="name-cell">
                    {#if editingKey?.id === key.id}
                      <Input
                        type="text"
                        bind:value={editForm.name}
                        placeholder="用户"
                      />
                    {:else}
                      <span class="key-name">{key.name}</span>
                    {/if}
                  </td>
                  <td class="prefix-cell">
                    <div class="key-display-wrapper">
                      <div
                        class="key-prefix-container"
                        title={expandedKeyIds.has(key.id.toString())
                          ? "可使用左右方向键或鼠标拖动查看完整 Key"
                          : ""}
                      >
                        <code
                          class="key-prefix {expandedKeyIds.has(
                            key.id.toString(),
                          )
                            ? 'expanded'
                            : ''}"
                        >
                          {getDisplayKeyText(key.id, key.key_prefix)}
                        </code>
                      </div>
                      {#if hasFullKeyLocal(key.id)}
                        <Button
                          variant="secondary"
                          size="sm"
                          on:click={() => toggleExpanded(key.id.toString())}
                          title={expandedKeyIds.has(key.id.toString())
                            ? "收起"
                            : "查看完整 Key"}
                          class="icon-button eye-button"
                        >
                          {#if expandedKeyIds.has(key.id.toString())}
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              width="14"
                              height="14"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              stroke-width="2"
                              stroke-linecap="round"
                              stroke-linejoin="round"
                            >
                              <path
                                d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
                              ></path>
                              <line x1="1" y1="1" x2="23" y2="23"></line>
                            </svg>
                          {:else}
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              width="14"
                              height="14"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              stroke-width="2"
                              stroke-linecap="round"
                              stroke-linejoin="round"
                            >
                              <path
                                d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
                              ></path>
                              <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                          {/if}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          on:click={() => copyFullKey(key)}
                          title="复制完整 Key"
                          class="icon-button copy-button"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <rect
                              x="9"
                              y="9"
                              width="13"
                              height="13"
                              rx="2"
                              ry="2"
                            ></rect>
                            <path
                              d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                            ></path>
                          </svg>
                        </Button>
                      {:else}
                        <span
                          class="key-unavailable"
                          title="完整 Key 不可用，如果 Key 已丢失，请删除后重新创建"
                          >⚠️</span
                        >
                      {/if}
                    </div>
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
                      <label class="toggle-switch">
                        <input
                          type="checkbox"
                          checked={key.is_active}
                          on:change={() => handleToggleActive(key)}
                        />
                        <span class="toggle-slider"></span>
                      </label>
                    {/if}
                  </td>
                  <td class="date-cell">
                    <span class="date-text">{formatDate(key.created_at)}</span>
                  </td>
                  <td class="date-cell">
                    <span class="date-text">{formatDate(key.last_used_at)}</span
                    >
                  </td>
                  <td class="actions-cell">
                    {#if editingKey?.id === key.id}
                      <div class="edit-actions">
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={saving}
                          on:click={handleSaveEdit}
                          title={saving ? "保存中..." : "保存"}
                          class="icon-button"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <path
                              d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"
                            ></path>
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
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
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
                          on:click={() => handleEdit(key)}
                          title="编辑"
                          class="icon-button"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <path
                              d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                            ></path>
                            <path
                              d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                            ></path>
                          </svg>
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          on:click={() => handleDelete(key)}
                          title="删除"
                          class="icon-button"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path
                              d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                            ></path>
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
      {/if}

      <!-- 分页控件 -->
      {#if !loadingKeys && apiKeys && apiKeys.length > 0 && totalPages > 1}
        <div class="pagination">
          <div class="pagination-info">
            共 {totalCount} 条记录，第 {currentPage} / {totalPages} 页
          </div>
          <div class="pagination-controls">
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === 1 || loadingKeys}
              on:click={() => handlePageChange(currentPage - 1)}
              title="上一页"
              class="icon-button"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
            </Button>
            <span class="page-info">{currentPage} / {totalPages}</span>
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === totalPages || loadingKeys}
              on:click={() => handlePageChange(currentPage + 1)}
              title="下一页"
              class="icon-button"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </Button>
          </div>
        </div>
      {/if}
    </Card>
  {/if}
</div>

<!-- Create API Key Modal -->
{#if showCreateForm}
  <div
    class="modal-overlay"
    role="button"
    tabindex="0"
    on:click={() => {}}
    on:keydown={() => {}}
  >
    <div
      class="modal-content"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      <h2>创建 API Key</h2>

      <form on:submit|preventDefault={handleSaveCreate} class="create-form">
        <div class="info-box">
          <p><strong>💡 提示</strong></p>
          <p>
            API Key 将由系统自动生成（格式：sk-前缀 + 64个字符），您只需为此 Key
            起个用户名即可。
          </p>
        </div>

        <div class="form-group">
          <label for="key-name">
            用户 <span class="required">*</span>
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

        <div class="modal-actions">
          <Button
            type="submit"
            variant="primary"
            disabled={saving}
            title={saving ? "创建中..." : "创建"}
            class="icon-button"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
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
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </Button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .page-header {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-bottom: 2rem;
  }

  .loading,
  .empty,
  .loading-keys {
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

  .filters {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0;
    background: var(--bg-tertiary);
    border-radius: 0.5rem;
    margin-bottom: 1rem;
  }

  .filter-row {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
    width: 100%;
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .filter-group.search-group {
    min-width: 250px;
    flex: 1;
  }

  .filter-group.search-group :global(input) {
    width: 100%;
    height: 2.5rem;
  }

  .filter-group label {
    font-size: 0.875rem;
    color: var(--text-secondary);
    white-space: nowrap;
    font-weight: 500;
    margin: 0;
  }

  .filter-select {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    min-width: 150px;
    height: 2.5rem;
  }

  .filter-select:focus {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding: 1rem;
    background: var(--bg-tertiary);
    border-radius: 0.5rem;
  }

  .pagination-info {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .page-info {
    font-size: 0.875rem;
    color: var(--text-primary);
    min-width: 60px;
    text-align: center;
  }

  .table-container {
    overflow-x: auto;
  }

  .api-keys-table {
    width: 100%;
    min-width: max-content;
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
    white-space: nowrap;
  }

  .name-cell {
    min-width: 150px;
  }

  .key-name {
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
  }

  .prefix-cell {
    font-family: "Monaco", "Menlo", "Ubuntu Mono", "Consolas", monospace;
    min-width: 280px;
    width: 280px; /* 固定宽度，刚好容纳前缀 + 省略号 */
  }

  .key-display-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
  }

  .key-prefix-container {
    /* 固定宽度容器 */
    width: 180px;
    /* 隐藏溢出内容 */
    overflow: hidden;
    /* 支持水平滚动 */
    overflow-x: auto;
    overflow-y: hidden;
    /* 隐藏滚动条（Firefox） */
    scrollbar-width: none;
    /* 隐藏滚动条（IE 和 Edge） */
    -ms-overflow-style: none;
  }

  /* 隐藏滚动条（Chrome、Safari） */
  .key-prefix-container::-webkit-scrollbar {
    display: none;
  }

  .key-prefix {
    background: var(--bg-tertiary, #f8f9fa);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.8125rem;
    color: var(--text-primary, #495057);
    /* 始终单行显示，隐藏时使用省略号 */
    white-space: nowrap;
    /* 未展开时显示省略号 */
    text-overflow: ellipsis;
    /* 强制固定宽度，与容器保持一致 */
    width: 100%;
    display: inline-block;
    box-sizing: border-box;
  }

  /* 当 key 被展开时，不使用省略号，但仍然单行显示 */
  .key-prefix.expanded {
    text-overflow: clip; /* 移除省略号，显示完整内容 */
  }

  .key-unavailable {
    color: var(--text-secondary, #6c757d);
    font-size: 0.875rem;
    cursor: help;
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

  :global([data-theme="dark"])
    :global(.toggle-active-button.toggle-active:hover:not(:disabled)) {
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

  :global([data-theme="dark"])
    :global(.toggle-active-button.toggle-inactive:hover:not(:disabled)) {
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

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
    }

    .api-keys-table {
      min-width: 800px;
    }

    .actions-wrapper {
      flex-direction: column;
      gap: 0.25rem;
    }

    .prefix-cell {
      min-width: 260px;
      width: 260px; /* 移动端稍微缩小 */
    }

    .key-prefix-container {
      width: 260px;
      min-width: 260px;
      max-width: 260px;
    }

    .key-prefix {
      font-size: 0.75rem;
      padding: 0.2rem 0.4rem;
      /* 强制固定宽度，与容器保持一致 */
      width: 100%;
      display: inline-block;
      box-sizing: border-box;
    }
  }
</style>
