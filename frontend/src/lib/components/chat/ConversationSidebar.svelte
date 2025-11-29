<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import { chatService, type Conversation } from "$services/chatService";

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
    onToggleSidebar?: () => void;
  }

  let {
    selectedProviderName = $bindable(""),
    selectedApiFormat = $bindable(""),
    selectedModelValue = $bindable(""),
    conversations = $bindable([]),
    currentConversationId = $bindable(null),
    providers = [],
    onConversationSelected: _onConversationSelected,
    onNewConversation: _onNewConversation,
    onToggleSidebar: _onToggleSidebar,
  }: Props = $props();

  const dispatch = createEventDispatcher<{
    conversationSelected: { conversation: Conversation };
    newConversation: { providerName: string; apiFormat: string; model: string };
    toggleSidebar: void;
  }>();

  // Local state
  let loading = $state(false);
  let error = $state<string | null>(null);
  let deletingId = $state<number | null>(null);
  let editingId = $state<number | null>(null);
  let editingTitle = $state<string>("");
  let searchQuery = $state<string>("");
  let visibleCount = $state<number>(50); // Initial number of conversations to show
  let openMenuId = $state<number | null>(null); // Track which menu is open

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

  function _setDefaultModelSelection() {
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
      filteredConversations = conversations; // Initialize filtered conversations
      resetVisibleCount(); // Reset pagination when conversations are loaded
    } catch (err) {
      console.error("Failed to load conversations:", err);
      throw err;
    }
  }

  // Filter conversations based on search query
  let filteredConversations = $state<Conversation[]>([]);

  $effect(() => {
    if (!searchQuery.trim()) {
      filteredConversations = conversations;
    } else {
      const query = searchQuery.toLowerCase();
      filteredConversations = conversations.filter(
        (conv) =>
          conv.title?.toLowerCase().includes(query) ||
          formatModelName(conv.last_model || conv.model).toLowerCase().includes(query),
      );
    }
  });

  // Get conversations to display (with pagination for lazy loading)
  let displayConversations = $state<Conversation[]>([]);

  $effect(() => {
    displayConversations = filteredConversations.slice(0, visibleCount);
  });

  function handleScroll(event: Event) {
    const target = event.target as HTMLDivElement;
    const { scrollTop, scrollHeight, clientHeight } = target;

    // Load more when user scrolls near bottom (within 100px)
    if (scrollTop + clientHeight >= scrollHeight - 100) {
      if (visibleCount < filteredConversations.length) {
        visibleCount = Math.min(visibleCount + 50, filteredConversations.length);
      }
    }
  }

  function resetVisibleCount() {
    visibleCount = 50;
  }

  // Reset visible count when search query changes
  $effect(() => {
    resetVisibleCount();
  });

  function startEdit(conversation: Conversation, event: Event) {
    event.stopPropagation();
    editingId = conversation.id;
    editingTitle = conversation.title || "无标题";
  }

  function cancelEdit() {
    editingId = null;
    editingTitle = "";
  }

  function toggleMenu(conversationId: number, event: Event) {
    event.stopPropagation();
    openMenuId = openMenuId === conversationId ? null : conversationId;
  }

  function closeMenu() {
    openMenuId = null;
  }

  // Close menu when clicking outside
  function handleClickOutside(event: Event) {
    const target = event.target as Element;
    if (!target.closest('.conversation-item')) {
      closeMenu();
    }
  }

  $effect(() => {
    if (openMenuId) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  });

  async function saveEdit(conversation: Conversation, event?: Event) {
    if (event) {
      event.stopPropagation();
    }

    if (!editingTitle.trim()) {
      alert("标题不能为空");
      return;
    }

    if (editingTitle === conversation.title) {
      cancelEdit();
      return;
    }

    try {
      const updatedConversation = await chatService.updateConversation(
        conversation.id,
        editingTitle.trim(),
      );

      // Update local list with the response from API
      conversations = conversations.map((c) =>
        c.id === conversation.id
          ? { ...c, title: updatedConversation.title }
          : c
      );

      cancelEdit();
    } catch (err) {
      console.error("Failed to update conversation:", err);
      alert("重命名失败");
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
    <button class="collapse-btn" onclick={() => dispatch("toggleSidebar")} title="折叠侧边栏">
      <span class="hamburger-icon">
        <span class="line line-1"></span>
        <span class="line line-2"></span>
        <span class="line line-3"></span>
      </span>
    </button>
    <input
      type="text"
      class="search-input"
      placeholder="搜索对话..."
      bind:value={searchQuery}
    />
    <button class="new-btn" onclick={handleNewConversation} title="新建对话">
      +
    </button>
  </div>

  <div class="conversations-list" onscroll={handleScroll}>
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
    {:else if displayConversations.length === 0}
      <div class="empty">
        <p>没有找到匹配的对话</p>
      </div>
    {:else}
      {#each displayConversations as conversation}
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
            <div class="title-row">
              {#if editingId === conversation.id}
                <input
                  class="title-input"
                  bind:value={editingTitle}
                  onkeydown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      saveEdit(conversation);
                    } else if (e.key === "Escape") {
                      e.preventDefault();
                      cancelEdit();
                    }
                  }}
                  onblur={(_e) => {
                    // Delay blur to allow Enter key to be processed first
                    setTimeout(() => {
                      if (editingId === conversation.id) {
                        saveEdit(conversation);
                      }
                    }, 100);
                  }}
                />
                <div class="title-actions">
                  <button
                    class="action-btn save-btn"
                    onclick={(e) => saveEdit(conversation, e)}
                    title="保存"
                  >
                    ✓
                  </button>
                  <button
                    class="action-btn cancel-btn"
                    onclick={(e) => {
                      e.stopPropagation();
                      cancelEdit();
                    }}
                    title="取消"
                  >
                    ×
                  </button>
                </div>
              {:else}
                <h3 class="title">{conversation.title || "无标题"}</h3>
                <div class="right-area">
                  <span class="time">{formatDate(conversation.updated_at)}</span>
                  <div class="menu-container">
                    <button
                      class="menu-btn"
                      onclick={(e) => toggleMenu(conversation.id, e)}
                      title="更多操作"
                    >
                      ⋯
                    </button>
                    {#if openMenuId === conversation.id}
                      <div class="dropdown-menu">
                        <button
                          class="menu-item"
                          onclick={(e) => {
                            e.stopPropagation();
                            closeMenu();
                            startEdit(conversation, e);
                          }}
                        >
                          重命名
                        </button>
                        <button
                          class="menu-item delete {deletingId === conversation.id
                            ? 'deleting'
                            : ''}"
                          onclick={(e) => {
                            e.stopPropagation();
                            closeMenu();
                            handleDelete(conversation.id, e);
                          }}
                          disabled={deletingId === conversation.id}
                        >
                          删除
                        </button>
                      </div>
                    {/if}
                  </div>
                </div>
              {/if}
            </div>
            <div class="meta">
              <span class="model">{formatModelName(conversation.last_model || conversation.model)}</span>
            </div>
          </div>
        </div>
      {/each}
      {#if displayConversations.length > 0 && displayConversations.length < filteredConversations.length}
        <div class="lazy-loading-indicator">
          <p>已显示 {displayConversations.length} / {filteredConversations.length} 个对话</p>
        </div>
      {/if}
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
    overflow: hidden;
  }

  .sidebar-header {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: padding 0.2s ease;
  }

  .search-input {
    flex: 1;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    font-size: 0.875rem;
    color: var(--text-primary);
    background: var(--bg-secondary);
    outline: none;
    transition: all 0.2s ease;
    min-width: 0;
  }

  .search-input:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
    background: var(--bg-primary);
  }

  .search-input::placeholder {
    color: var(--text-tertiary);
  }

  .collapse-btn {
    padding: 0.5rem;
    background: transparent;
    color: var(--text-secondary);
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
    flex-shrink: 0;
  }

  .collapse-btn:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
  }

  .collapse-btn:active {
    transform: scale(0.98);
  }

  .hamburger-icon {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 18px;
    height: 14px;
  }

  .hamburger-icon .line {
    display: block;
    height: 2px;
    background: currentColor;
    border-radius: 1px;
    transition: all 0.2s ease;
  }

  .hamburger-icon .line-1 {
    width: 100%;
  }

  .hamburger-icon .line-2 {
    width: 65%;
    align-self: flex-end;
  }

  .hamburger-icon .line-3 {
    width: 100%;
  }

  .collapse-btn:hover .hamburger-icon .line {
    background: var(--text-primary);
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

  .title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
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
    flex: 1;
  }

  .title-input {
    flex: 1;
    min-width: 0;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--primary-color);
    border-radius: 0.25rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
    background: var(--bg-secondary);
    outline: none;
  }

  .title-input:focus {
    box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.3);
  }

  .title-actions {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
  }

  .action-btn {
    padding: 0.25rem 0.5rem;
    background: transparent;
    border: none;
    cursor: pointer;
    border-radius: 0.25rem;
    transition: all 0.2s;
    min-width: 24px;
    min-height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.875rem;
  }

  .action-btn.save-btn {
    color: #10b981;
  }

  .action-btn.save-btn:hover {
    background: rgba(16, 185, 129, 0.1);
  }

  .action-btn.cancel-btn {
    color: var(--text-tertiary);
  }

  .action-btn.cancel-btn:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  .right-area {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .time {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    white-space: nowrap;
  }

  .active .time {
    color: rgba(255, 255, 255, 0.8);
  }

  .meta {
    display: flex;
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

  .menu-container {
    position: relative;
  }

  .menu-btn {
    opacity: 0;
    transition: opacity 0.2s;
    padding: 0.375rem 0.5rem;
    background: transparent;
    border: none;
    cursor: pointer;
    border-radius: 0.25rem;
    min-width: 24px;
    min-height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.125rem;
    color: var(--text-tertiary);
    line-height: 1;
  }

  .conversation-item:hover .menu-btn {
    opacity: 1;
  }

  .menu-btn:hover {
    background: rgba(66, 153, 225, 0.1);
    color: var(--primary-color);
  }

  .dropdown-menu {
    position: absolute;
    right: 0;
    top: 100%;
    margin-top: 0.25rem;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 10;
    min-width: 100px;
    overflow: hidden;
  }

  .menu-item {
    padding: 0.5rem 0.75rem;
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 0.875rem;
    color: var(--text-primary);
    text-align: left;
    width: 100%;
    white-space: nowrap;
  }

  .menu-item:hover {
    background: var(--bg-secondary);
  }

  .menu-item.delete:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  .menu-item.deleting {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .lazy-loading-indicator {
    padding: 1rem;
    text-align: center;
    color: var(--text-tertiary);
    font-size: 0.75rem;
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
