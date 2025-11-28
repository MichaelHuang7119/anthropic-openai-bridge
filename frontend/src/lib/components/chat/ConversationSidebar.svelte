<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import {
    chatService,
    type Conversation,
    type ModelChoice,
  } from "$services/chatService";
  import { theme } from "$stores/theme";

  interface ProviderConfig {
    name: string;
    api_format: string;
    models: {
      big?: string[];
      middle?: string[];
      small?: string[];
    };
  }

  interface Props {
    selectedProviderName?: string;
    selectedApiFormat?: string;
    selectedModelValue?: string;
    conversations?: Conversation[];
    currentConversationId?: number | null;
    providers?: ProviderConfig[];
    onConversationSelected?: (conversation: Conversation) => void;
    onNewConversation?: (
      providerName: string,
      apiFormat: string,
      model: string,
    ) => void;
  }

  let {
    selectedProviderName = $bindable(""),
    selectedApiFormat = $bindable(""),
    selectedModelValue = $bindable(""),
    conversations = $bindable([]),
    currentConversationId = $bindable(null),
    providers = [],
    onConversationSelected,
    onNewConversation,
  }: Props = $props();

  const dispatch = createEventDispatcher<{
    conversationSelected: { conversation: Conversation };
    newConversation: { providerName: string; apiFormat: string; model: string };
  }>();

  // Local state
  let loading = $state(false);
  let error = $state<string | null>(null);
  let deletingId = $state<number | null>(null);

  onMount(async () => {
    try {
      loading = true;
      await loadConversations();

      // Select default model when providers are loaded
      if (providers.length > 0 && !selectedModelValue) {
        selectedProviderName = providers[0].name;
        selectedApiFormat = providers[0].api_format;

        // Find first available model in any category
        for (const category of ["big", "middle", "small"]) {
          const models =
            providers[0].models[category as keyof ProviderConfig["models"]];
          if (models && models.length > 0) {
            selectedModelValue = models[0];
            break;
          }
        }
      }
    } catch (err) {
      error = err instanceof Error ? err.message : "加载失败";
      console.error("Failed to load conversations:", err);
    } finally {
      loading = false;
    }
  });

  function setDefaultModelSelection() {
    if (providers.length > 0) {
      selectedProviderName = providers[0].name;
      selectedApiFormat = providers[0].api_format;

      // Find first available model in any category
      for (const category of ["big", "middle", "small"]) {
        const models =
          providers[0].models[category as keyof ProviderConfig["models"]];
        if (models && models.length > 0) {
          selectedModelValue = models[0];
          break;
        }
      }
    }
  }

  async function loadConversations() {
    try {
      conversations = await chatService.getConversations();
    } catch (err) {
      console.error("Failed to load conversations:", err);
      throw err;
    }
  }

  function selectConversation(conversation: Conversation) {
    currentConversationId = conversation.id;
    dispatch("conversationSelected", { conversation });
  }

  async function handleDelete(conversationId: number, event: Event) {
    event.stopPropagation();

    if (!confirm("确定要删除这个对话吗？")) {
      return;
    }

    deletingId = conversationId;
    try {
      await chatService.deleteConversation(conversationId);
      conversations = conversations.filter((c) => c.id !== conversationId);

      if (currentConversationId === conversationId) {
        currentConversationId = null;
        dispatch("conversationSelected", { conversation: null as any });
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
      alert("删除失败");
    } finally {
      deletingId = null;
    }
  }

  function handleNewConversation() {
    if (!selectedProviderName || !selectedApiFormat || !selectedModelValue) {
      alert("请先配置模型");
      return;
    }

    dispatch("newConversation", {
      providerName: selectedProviderName,
      apiFormat: selectedApiFormat,
      model: selectedModelValue,
    });
  }

function formatDate(dateString: string): string {
  try {
    if (!dateString) return "未知时间";

    // 直接解析ISO时间字符串（包含时区信息）
    const date = new Date(dateString);

    // 验证解析是否成功
    if (isNaN(date.getTime())) {
      console.warn("无法解析时间:", dateString);
      return dateString;
    }

    // 调试日志（临时）
    console.log(`时间解析 - 原始: ${dateString}, 解析后: ${date.toLocaleString("zh-CN", {timeZone: "Asia/Shanghai"})}`);

    // 获取当前北京时间用于比较
    const now = new Date();
    const nowInBeijing = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Shanghai" }));

    // 获取北京时间用于显示和比较
    const dateInBeijing = new Date(date.toLocaleString("en-US", { timeZone: "Asia/Shanghai" }));

    // 判断是否是今天（北京时间）
    const today = new Date(nowInBeijing.getFullYear(), nowInBeijing.getMonth(), nowInBeijing.getDate());
    const messageDate = new Date(dateInBeijing.getFullYear(), dateInBeijing.getMonth(), dateInBeijing.getDate());
    const diffTime = today.getTime() - messageDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      // 今天：显示北京时间 HH:MM
      const timeStr = date.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Shanghai"
      });
      console.log(`今天时间显示: ${timeStr}`);
      return timeStr;
    } else if (diffDays === 1) {
      return "昨天";
    } else if (diffDays < 7) {
      return `${diffDays}天前`;
    } else {
      // 超过7天：显示完整日期（北京时间）
      return date.toLocaleDateString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZone: "Asia/Shanghai"
      });
    }
  } catch (error) {
    console.error("时间格式化错误:", error, dateString);
    return dateString;
  }
}

  // Format model name for display
  function formatModelName(model: string | null): string {
    if (!model) return "未知模型";
    if (model.includes("/")) {
      return model.split("/")[1] || model;
    }
    return model;
  }
</script>

<div class="conversation-sidebar">
  <div class="sidebar-header">
    <h2>对话历史</h2>
    <button class="new-btn" onclick={handleNewConversation} title="新建对话">
      +
    </button>
  </div>

  <div class="conversations-list">
    {#if loading}
      <div class="loading">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>
    {:else if error}
      <div class="error">
        <p>加载失败: {error}</p>
        <button onclick={loadConversations}>重试</button>
      </div>
    {:else if conversations.length === 0}
      <div class="empty">
        <p>暂无对话记录</p>
        <button class="secondary" onclick={handleNewConversation}>
          开始新对话
        </button>
      </div>
    {:else}
      {#each conversations as conversation}
        <div
          class="conversation-item {currentConversationId === conversation.id
            ? 'active'
            : ''}"
          role="button"
          tabindex="0"
          onclick={() => selectConversation(conversation)}
          onkeydown={(e) =>
            (e.key === "Enter" || e.key === " ") &&
            selectConversation(conversation)}
        >
          <div class="conversation-info">
            <h3 class="title">{conversation.title || "无标题"}</h3>
            <div class="meta">
              <span class="model">{formatModelName(conversation.model)}</span>
              <span class="time">{formatDate(conversation.updated_at)}</span>
            </div>
          </div>
          <div class="actions">
            <button
              class="delete-btn {deletingId === conversation.id
                ? 'deleting'
                : ''}"
              onclick={(e) => handleDelete(conversation.id, e)}
              disabled={deletingId === conversation.id}
              title="删除对话"
            >
            </button>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .conversation-sidebar {
    width: 100%;
    background: var(--bg-primary);
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .sidebar-header {
    padding: 1.5rem 1.5rem 1rem;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .sidebar-header h2 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .new-btn {
    padding: 0.5rem;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: 32px;
    min-height: 32px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 400;
    line-height: 1;
    flex-shrink: 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .new-btn:hover {
    background: white;
    color: var(--primary-color) !important;
    transform: scale(1.1);
    box-shadow:
      0 4px 8px rgba(0, 0, 0, 0.15),
      0 0 0 2px var(--primary-color);
  }

  .new-btn:active {
    background: var(--bg-secondary);
    color: var(--primary-color) !important;
    transform: scale(0.98);
    box-shadow:
      0 1px 2px rgba(0, 0, 0, 0.1),
      inset 0 0 4px rgba(0, 0, 0, 0.1);
  }

  .new-btn:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5);
  }

  .conversations-list {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0.5rem;
    padding-bottom: 1rem;
    min-height: 0;
  }

  .loading,
  .empty,
  .error {
    padding: 2rem;
    text-align: center;
    color: var(--text-secondary);
  }

  .spinner {
    width: 24px;
    height: 24px;
    border: 2px solid var(--border-color);
    border-top: 2px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  .error button {
    margin-top: 1rem;
  }

  .empty button {
    margin-top: 1rem;
  }

  .conversation-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    margin: 0.25rem;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .conversation-item:hover {
    background: var(--bg-secondary);
  }

  .conversation-item.active {
    background: var(--primary-color);
    color: white;
  }

  .conversation-item.active .title,
  .conversation-item.active .meta {
    color: white;
  }

  .conversation-info {
    flex: 1;
    min-width: 0;
  }

  .title {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 500;
    line-height: 1.4;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.25rem;
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .model {
    font-family: "Courier New", monospace;
    color: var(--text-secondary);
  }

  .active .model {
    color: rgba(255, 255, 255, 0.8);
  }

  .actions {
    opacity: 0;
    transition: opacity 0.2s;
  }

  .conversation-item:hover .actions {
    opacity: 1;
  }

  .delete-btn {
    padding: 0.375rem;
    background: none;
    border: none;
    color: var(--text-tertiary);
    cursor: pointer;
    border-radius: 0.25rem;
    transition: all 0.2s;
    min-width: 24px;
    min-height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .delete-btn:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  .delete-btn.deleting {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .delete-btn::before {
    content: "×";
    font-size: 1.125rem;
    line-height: 1;
  }

  button {
    padding: 0.5rem 1rem;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  button:hover {
    background: var(--primary-hover);
  }

  button.secondary {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
  }

  button.secondary:hover {
    background: var(--bg-tertiary);
  }

  @media (max-width: 768px) {
    .conversation-sidebar {
      width: 100%;
    }
  }
</style>
