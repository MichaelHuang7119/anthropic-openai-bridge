<script lang="ts">
  import { onMount } from "svelte";
  import { onDestroy } from "svelte";
  import Button from "$components/ui/Button.svelte";
  import Card from "$components/ui/Card.svelte";
  import Badge from "$components/ui/Badge.svelte";
  import ProviderForm from "$components/ProviderForm.svelte";
  import ErrorMessageModal from "$components/ErrorMessageModal.svelte";
  import { providers } from "$stores/providers";
  import { providerService } from "$services/providers";
  import { toast } from "$stores/toast";
  import type { Provider } from "$types/provider";
  import Input from "$components/ui/Input.svelte";

  let showForm = false;
  let editingProvider: Provider | null = null;
  let loading = true;
  let saving = false;
  let providersList: Provider[] = [];
  let providersForEdit: Provider[] = []; // 包含真实API key的完整数据
  let showTestResult = false;
  let testResult: any = null;
  let testingProvider: string | null = null;

  // 优先级编辑相关
  let editingPriorityKey: string | null = null; // 格式: "name||api_format"
  let editingPriorityValue: number = 0;

  // 搜索和筛选相关
  let searchQuery = "";
  let filterEnabled: "all" | "enabled" | "disabled" = "all";

  // 分页相关
  let currentPage = 1;
  const pageSize = 10;

  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;

  $: providersList = $providers;

  // 客户端过滤和排序
  $: allFilteredProviders = providersList
    .filter((p) => {
      // 搜索过滤
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        if (
          !p.name.toLowerCase().includes(query) &&
          !p.base_url.toLowerCase().includes(query)
        ) {
          return false;
        }
      }

      // 状态过滤
      if (filterEnabled === "enabled" && !p.enabled) return false;
      if (filterEnabled === "disabled" && p.enabled) return false;

      return true;
    })
    .sort((a, b) => {
      // 按名称排序（不区分大小写）
      const nameCompare = a.name
        .toLowerCase()
        .localeCompare(b.name.toLowerCase());
      if (nameCompare !== 0) return nameCompare;

      // 如果名称相同，按 API 格式排序
      return (a.api_format || '').localeCompare(b.api_format || '');
    });

  // 分页计算
  $: totalCount = allFilteredProviders.length;
  $: totalPages = Math.ceil(totalCount / pageSize);

  // 确保当前页在有效范围内
  $: {
    if (totalPages === 0) {
      // 没有数据时，设置为第1页
      currentPage = 1;
    } else if (totalPages > 0 && currentPage > totalPages) {
      currentPage = totalPages;
    } else if (currentPage < 1) {
      currentPage = 1;
    }
  }

  // 当前页显示的数据
  $: filteredProviders = (() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return allFilteredProviders.slice(start, end);
  })();

  onMount(async () => {
    abortController = new AbortController();
    try {
      await loadProviders();
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      throw error;
    }
  });

  onDestroy(() => {
    // 取消所有进行中的请求
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
  });

  async function loadProviders() {
    if (!abortController) return;
    loading = true;
    try {
      const data = await providerService.getAll({
        signal: abortController.signal,
      });

      // 检查是否已被取消
      if (abortController.signal.aborted) return;

      providers.set(data);
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      console.error("Failed to load providers:", error);
      toast.error("加载供应商失败");
    } finally {
      if (!abortController?.signal.aborted) {
        loading = false;
      }
    }
  }

  function handleAdd() {
    editingProvider = null;
    showForm = true;
  }

  async function handleEdit(provider: Provider) {
    if (!abortController) return;
    try {
      // 每次编辑都重新获取最新的完整数据，确保显示最新的配置
      const editData = await providerService.getAllForEdit({
        signal: abortController.signal,
      });

      // 检查是否已被取消
      if (abortController.signal.aborted) return;

      // 更新缓存
      providersForEdit = editData;

      // 从最新数据中找到对应的供应商 (包含格式匹配)
      const fullProvider = providersForEdit.find(
        (p) => p.name === provider.name && p.api_format === provider.api_format,
      );
      if (!fullProvider) {
        toast.error("找不到该供应商的配置数据");
        return;
      }

      editingProvider = fullProvider;
      showForm = true;
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      console.error("Failed to load provider data for editing:", error);
      toast.error("加载编辑数据失败: " + (error as Error).message);
    }
  }

  async function handleToggleEnabled(provider: Provider) {
    const newEnabled = !provider.enabled;
    try {
      await providerService.toggleEnabled(
        provider.name,
        newEnabled,
        provider.api_format,
      );
      await loadProviders();
      toast.success(newEnabled ? "供应商已启用" : "供应商已禁用");
    } catch (error) {
      console.error("Failed to toggle provider status:", error);
      toast.error("操作失败: " + (error as Error).message);
    }
  }

  async function handleDelete(provider: Provider) {
    if (!confirm(`确定要删除供应商 "${provider.name}" 吗？`)) {
      return;
    }

    try {
      await providerService.delete(provider.name, provider.api_format);
      // 清空编辑数据缓存
      providersForEdit = [];
      await loadProviders();
      toast.success("删除成功");
    } catch (error) {
      console.error("Failed to delete provider:", error);
      toast.error("删除失败: " + (error as Error).message);
    }
  }

  async function handleTest(provider: Provider) {
    testingProvider = provider.name;
    try {
      const result = await providerService.test(provider.name);
      testResult = result;
      showTestResult = true;

      // Also show a summary toast
      if (result.healthy) {
        toast.success(`测试完成\n总体状态: 健康`);
      } else {
        toast.error(`测试完成\n总体状态: 不健康`);
      }
    } catch (error) {
      console.error("Failed to test provider:", error);
      toast.error("测试失败: " + (error as Error).message);
      testingProvider = null;
    }
  }

  function closeTestResult() {
    showTestResult = false;
    testResult = null;
    testingProvider = null;
  }

  function handleOverlayClick(event: Event) {
    // Only close if clicking directly on the overlay (not on modal content)
    if (event.target === event.currentTarget) {
      closeTestResult();
    }
  }

  function handleFormOverlayClick(_event: MouseEvent) {
    // 禁用点击遮罩层关闭弹窗，只能通过关闭按钮关闭
    // Do nothing - modal can only be closed via close/cancel buttons
  }

  async function copyToClipboard(text: string) {
    if (typeof window === "undefined") return;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        toast.success("已复制到剪贴板");
      } else {
        // Fallback for older browsers
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
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

  function copyTestResult() {
    if (!testResult) return;

    const lines: string[] = [];
    lines.push(`测试结果 - ${testingProvider}`);
    lines.push(`总体状态: ${testResult.healthy ? "健康" : "不健康"}`);
    if (testResult.responseTime !== null) {
      lines.push(`响应时间: ${testResult.responseTime}ms`);
    }
    lines.push("");
    lines.push("类别健康状态:");

    if (testResult.categories) {
      for (const [category, status] of Object.entries(testResult.categories)) {
        const catStatus = status as any;
        lines.push(
          `  ${getCategoryLabel(category)}: ${catStatus.healthy ? "健康" : "不健康"}`,
        );
        if (catStatus.responseTime !== null) {
          lines.push(`    响应时间: ${catStatus.responseTime}ms`);
        }
        if (catStatus.workingModel) {
          lines.push(`    可用模型: ${catStatus.workingModel}`);
        }
        if (catStatus.error) {
          lines.push(`    错误: ${catStatus.error}`);
        }
      }
    }

    copyToClipboard(lines.join("\n"));
  }

  function getCategoryLabel(category: string): string {
    const labels: Record<string, string> = {
      big: "大模型",
      middle: "中模型",
      small: "小模型",
    };
    return labels[category] || category;
  }

  function truncateError(errorMessage: string, maxLength: number = 50): string {
    if (!errorMessage) return "";
    if (errorMessage.length <= maxLength) return errorMessage;
    return errorMessage.substring(0, maxLength) + "...";
  }

  // 错误信息模态框相关
  let showErrorModal = false;
  let selectedError: string = "";
  let selectedErrorTitle: string = "";

  function showErrorMessage(category: string, error: string) {
    selectedErrorTitle = `错误信息 - ${testingProvider} - ${getCategoryLabel(category)}`;
    selectedError = error;
    showErrorModal = true;
  }

  function closeErrorModal() {
    showErrorModal = false;
    selectedError = "";
    selectedErrorTitle = "";
  }

  async function handleSave(saveData: {
    provider: Provider;
    api_format?: string;
  }) {
    try {
      saving = true;

      // Extract provider data and api_format
      const { provider: providerData, api_format } = saveData;

      if (editingProvider) {
        // Pass api_format for precise provider identification
        await providerService.update(
          editingProvider.name,
          providerData,
          api_format,
        );
      } else {
        await providerService.create(providerData);
      }
      showForm = false;
      editingProvider = null;
      // 清空编辑数据缓存，强制下次编辑时重新加载最新数据
      providersForEdit = [];
      // 刷新供应商列表
      await loadProviders();
      toast.success("保存成功");
    } catch (error) {
      console.error("Failed to save provider:", error);
      toast.error("保存失败: " + (error as Error).message);
    } finally {
      saving = false;
    }
  }

  function handleCancel() {
    showForm = false;
    editingProvider = null;
  }

  function clearFilters() {
    searchQuery = "";
    filterEnabled = "all";
    currentPage = 1;
  }

  function handlePageChange(newPage: number) {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      currentPage = newPage;
    }
  }

  function handleEditPriority(provider: Provider) {
    const key = `${provider.name}||${provider.api_format}`;
    editingPriorityKey = key;
    editingPriorityValue = provider.priority;
  }

  function handleCancelEditPriority() {
    editingPriorityKey = null;
    editingPriorityValue = 0;
  }

  async function handleSavePriority(provider: Provider) {
    const key = `${provider.name}||${provider.api_format}`;
    if (editingPriorityKey !== key) return;

    // 验证优先级值
    if (editingPriorityValue < 0) {
      toast.error("优先级不能为负数");
      return;
    }

    try {
      saving = true;

      // 获取包含完整 API Key 的供应商数据
      const editData = await providerService.getAllForEdit({
        signal: abortController?.signal,
      });

      // 找到对应的供应商
      const fullProvider = editData.find(
        (p) => p.name === provider.name && p.api_format === provider.api_format,
      );

      if (!fullProvider) {
        toast.error("找不到该供应商的配置数据");
        return;
      }

      // 更新优先级，使用完整的供应商数据
      const updatedData = {
        ...fullProvider,
        priority: editingPriorityValue,
      };

      await providerService.update(
        provider.name,
        updatedData,
        provider.api_format,
      );
      toast.success("优先级更新成功");
      await loadProviders();
      handleCancelEditPriority();
    } catch (error) {
      console.error("Failed to update priority:", error);
      toast.error("更新失败: " + (error as Error).message);
    } finally {
      saving = false;
    }
  }
</script>

<div class="container">
  <div class="page-header">
    <Button on:click={handleAdd} title="添加供应商" class="icon-button">
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
  {:else if providersList.length === 0}
    <div class="empty">
      <p>暂无供应商配置</p>
      <Button on:click={handleAdd} title="添加第一个供应商" class="icon-button">
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
  {:else}
    <!-- 搜索和筛选 -->
    <Card>
      <div class="filters">
        <div class="filter-row">
          <div class="filter-group search-group">
            <Input
              type="text"
              bind:value={searchQuery}
              placeholder="搜索供应商名称或URL..."
            />
          </div>

          <div class="filter-group">
            <label for="provider-filter-status">状态:</label>
            <select
              id="provider-filter-status"
              class="filter-select"
              bind:value={filterEnabled}
            >
              <option value="all">全部</option>
              <option value="enabled">已启用</option>
              <option value="disabled">已禁用</option>
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
    </Card>

    {#if filteredProviders.length === 0}
      <div class="empty">
        <p>没有匹配的供应商</p>
      </div>
    {:else}
      <div class="table-container">
        <table class="providers-table">
          <thead>
            <tr>
              <th>名称</th>
              <th style="text-align: center;">状态</th>
              <th>Base URL</th>
              <th>API格式</th>
              <th style="text-align: center;">优先级</th>
              <th>模型数量</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredProviders as provider}
              <tr>
                <td class="name-cell">
                  <div class="name-wrapper">
                    <span class="provider-name" title={provider.name}>
                      {provider.name}
                    </span>
                  </div>
                </td>
                <td class="status-cell">
                  <label class="toggle-switch">
                    <input
                      type="checkbox"
                      checked={provider.enabled}
                      on:change={() => handleToggleEnabled(provider)}
                    />
                    <span class="toggle-slider"></span>
                  </label>
                </td>
                <td class="url-cell">
                  <span class="url-text" title={provider.base_url}
                    >{provider.base_url}</span
                  >
                </td>
                <td class="format-cell">
                  <Badge
                    type={provider.api_format === "anthropic"
                      ? "warning"
                      : "info"}
                  >
                    {provider.api_format === "anthropic"
                      ? "Anthropic"
                      : "OpenAI"}
                  </Badge>
                </td>
                <td class="priority-cell">
                  {#if editingPriorityKey === `${provider.name}||${provider.api_format}`}
                    <div class="priority-edit-wrapper">
                      <input
                        type="number"
                        class="priority-input"
                        bind:value={editingPriorityValue}
                        min="0"
                        step="1"
                      />
                      <div class="priority-actions">
                        <button
                          class="priority-btn save-btn"
                          on:click={() => handleSavePriority(provider)}
                          disabled={saving}
                          title="保存"
                        >
                          ✓
                        </button>
                        <button
                          class="priority-btn cancel-btn"
                          on:click={handleCancelEditPriority}
                          disabled={saving}
                          title="取消"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  {:else}
                    <div class="priority-display">
                      <span class="priority-value">{provider.priority}</span>
                      <button
                        class="priority-edit-icon"
                        on:click={() => handleEditPriority(provider)}
                        title="编辑优先级"
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
                          <path
                            d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                          ></path>
                          <path
                            d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                          ></path>
                        </svg>
                      </button>
                    </div>
                  {/if}
                </td>
                <td class="models-cell">
                  <div class="models-badge">
                    <Badge type="info"
                      >大 {provider.models.big?.length || 0}</Badge
                    >
                    <Badge type="info"
                      >中 {provider.models.middle?.length || 0}</Badge
                    >
                    <Badge type="info"
                      >小 {provider.models.small?.length || 0}</Badge
                    >
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
                      on:click={() => handleDelete(provider)}
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
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- 分页控件 -->
      {#if totalPages > 1}
        <div class="pagination">
          <div class="pagination-info">
            共 {totalCount} 条记录，第 {currentPage} / {totalPages} 页
          </div>
          <div class="pagination-controls">
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === 1}
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
              disabled={currentPage === totalPages}
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
    {/if}
  {/if}
</div>

<!-- Provider Form Modal -->
{#if showForm}
  <div
    class="modal-overlay"
    role="button"
    tabindex="0"
    on:click={handleFormOverlayClick}
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
      <h2>{editingProvider ? "编辑供应商" : "添加供应商"}</h2>
      <ProviderForm
        provider={editingProvider}
        apiFormat={editingProvider?.api_format}
        loading={saving}
        on:save={(e) => handleSave(e.detail)}
        on:cancel={handleCancel}
      />
    </div>
  </div>
{/if}

<!-- Test Result Modal -->
{#if showTestResult && testResult}
  <div
    class="modal-overlay"
    role="button"
    tabindex="0"
    on:click={handleOverlayClick}
    on:keydown={(e) => e.key === "Escape" && handleOverlayClick(e)}
  >
    <div
      class="modal-content test-result-modal"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      <div class="test-result-header">
        <h2>测试结果 - {testingProvider}</h2>
        <div class="header-actions">
          <Button
            variant="secondary"
            size="sm"
            on:click={copyTestResult}
            title="复制结果"
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
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
              ></path>
            </svg>
          </Button>
          <Button
            variant="secondary"
            size="sm"
            on:click={closeTestResult}
            title="关闭"
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
      </div>

      <div class="test-summary">
        <div class="summary-item">
          <span class="summary-label">总体状态:</span>
          <Badge type={testResult.healthy ? "success" : "danger"}>
            {testResult.healthy ? "健康" : "不健康"}
          </Badge>
        </div>
        {#if testResult.responseTime !== null}
          <div class="summary-item">
            <span class="summary-label">响应时间:</span>
            <span class="summary-value">{testResult.responseTime}ms</span>
          </div>
        {/if}
      </div>

      <div class="categories-section">
        <h3>类别健康状态</h3>
        <div class="categories-list">
          {#each Object.entries(testResult.categories || {}) as [category, status]}
            {@const catStatus = status as any}
            <div class="category-item">
              <div class="category-header">
                <span class="category-name">{getCategoryLabel(category)}</span>
                <Badge type={catStatus.healthy ? "success" : "danger"}>
                  {catStatus.healthy ? "健康" : "不健康"}
                </Badge>
              </div>

              {#if catStatus.healthy}
                <div class="category-details">
                  {#if catStatus.responseTime !== null}
                    <div class="detail-item">
                      <span class="detail-label">响应时间:</span>
                      <span class="detail-value"
                        >{catStatus.responseTime}ms</span
                      >
                    </div>
                  {/if}
                  {#if catStatus.workingModel}
                    <div class="detail-item">
                      <span class="detail-label">可用模型:</span>
                      <span class="detail-value code"
                        >{catStatus.workingModel}</span
                      >
                    </div>
                  {/if}
                  {#if catStatus.testedModels && catStatus.testedModels.length > 0}
                    <div class="detail-item">
                      <span class="detail-label">已测试模型:</span>
                      <span class="detail-value"
                        >{catStatus.testedModels.length} 个</span
                      >
                    </div>
                  {/if}
                </div>
              {:else}
                <div class="category-details">
                  {#if catStatus.error}
                    {@const truncated = truncateError(catStatus.error)}
                    {@const isTruncated = catStatus.error.length > 50}
                    <div class="detail-item error">
                      <span class="detail-label">错误:</span>
                      <span
                        class="detail-value error-value clickable"
                        role="button"
                        tabindex="0"
                        on:click={() =>
                          showErrorMessage(category, catStatus.error)}
                        on:keydown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            showErrorMessage(category, catStatus.error);
                          }
                        }}
                        title={isTruncated ? "点击查看完整错误信息" : ""}
                      >
                        {truncated}
                      </span>
                    </div>
                  {/if}
                  {#if catStatus.testedModels && catStatus.testedModels.length > 0}
                    <div class="detail-item">
                      <span class="detail-label">已测试模型:</span>
                      <span class="detail-value"
                        >{catStatus.testedModels.length} 个</span
                      >
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      </div>

      <div class="test-result-actions">
        <Button variant="primary" on:click={closeTestResult}>关闭</Button>
      </div>
    </div>
  </div>
{/if}

<!-- Error Message Modal -->
<ErrorMessageModal
  show={showErrorModal}
  errorMessage={selectedError}
  title={selectedErrorTitle}
  on:close={closeErrorModal}
/>

<style>
  .page-header {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-bottom: 2rem;
  }

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

  .filters {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0;
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
    color: var(--text-secondary, #666);
    white-space: nowrap;
    font-weight: 500;
    margin: 0;
  }

  .filter-select {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 0.375rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
    cursor: pointer;
    min-width: 150px;
    height: 2.5rem;
  }

  .filter-select:focus {
    outline: 2px solid var(--primary-color, #007bff);
    outline-offset: 2px;
  }

  .pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding: 1rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
  }

  .pagination-info {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .page-info {
    font-size: 0.875rem;
    color: var(--text-primary, #495057);
    min-width: 60px;
    text-align: center;
  }

  .table-container {
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow-x: auto;
    margin-top: 1rem;
  }

  .providers-table {
    width: 100%;
    min-width: max-content;
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
    white-space: nowrap;
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

  .name-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .status-cell {
    text-align: center;
    padding: 1rem;
  }

  /* Toggle Switch Styles */
  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
    flex-shrink: 0;
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

  .priority-display {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }

  .priority-value {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    background: var(--bg-tertiary, #e9ecef);
    border-radius: 0.25rem;
    font-weight: 500;
    color: var(--text-primary, #495057);
  }

  .priority-edit-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem;
    background: transparent;
    border: none;
    color: var(--text-secondary, #6c757d);
    cursor: pointer;
    border-radius: 0.25rem;
    transition: all 0.2s;
    opacity: 0.6;
  }

  .priority-edit-icon:hover {
    opacity: 1;
    background: var(--bg-tertiary, #e9ecef);
    color: var(--primary-color, #007bff);
  }

  .priority-edit-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    justify-content: center;
  }

  .priority-input {
    width: 70px;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--primary-color, #007bff);
    border-radius: 0.25rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
    text-align: center;
    font-weight: 500;
  }

  .priority-input:focus {
    outline: none;
    border-color: var(--primary-color, #007bff);
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.2);
  }

  .priority-actions {
    display: flex;
    gap: 0.25rem;
  }

  .priority-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: bold;
    transition: all 0.2s;
  }

  .priority-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .save-btn {
    background: var(--success-color, #28a745);
    color: white;
  }

  .save-btn:hover:not(:disabled) {
    background: #218838;
    transform: scale(1.05);
  }

  .cancel-btn {
    background: var(--danger-color, #dc3545);
    color: white;
  }

  .cancel-btn:hover:not(:disabled) {
    background: #c82333;
    transform: scale(1.05);
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

  /* Test Result Modal Styles */
  .test-result-modal {
    max-width: 700px;
  }

  .test-result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .test-result-header h2 {
    margin: 0;
  }

  .header-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .test-summary {
    display: flex;
    gap: 2rem;
    padding: 1rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .summary-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .summary-label {
    font-weight: 500;
    color: var(--text-secondary, #666);
  }

  .summary-value {
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .categories-section {
    margin-bottom: 1.5rem;
  }

  .categories-section h3 {
    margin: 0 0 1rem 0;
    font-size: 1.125rem;
    color: var(--text-primary, #1a1a1a);
  }

  .categories-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .category-item {
    padding: 1rem;
    background: var(--card-bg, white);
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 0.5rem;
  }

  .category-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .category-name {
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
    font-size: 1rem;
  }

  .category-details {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-size: 0.875rem;
  }

  .detail-item {
    display: flex;
    gap: 0.5rem;
  }

  .detail-item.error {
    color: var(--danger-color, #dc3545);
  }

  .detail-label {
    font-weight: 500;
    color: var(--text-secondary, #666);
    min-width: 80px;
  }

  .detail-value {
    color: var(--text-primary, #1a1a1a);
    white-space: nowrap;
    word-break: break-word;
    overflow-wrap: break-word;
  }

  .detail-item.error .detail-value {
    color: var(--danger-color, #dc3545);
  }

  .error-value {
    display: block;
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .error-value.clickable {
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
  }

  .error-value.clickable:hover {
    color: var(--danger-color, #dc3545);
    opacity: 0.8;
  }

  .detail-value.code {
    font-family: monospace;
    font-size: 0.8125rem;
    background: var(--bg-tertiary, #f8f9fa);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
  }

  .category-details {
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
  }

  .detail-value {
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
  }

  .test-result-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-color, #dee2e6);
  }
</style>
