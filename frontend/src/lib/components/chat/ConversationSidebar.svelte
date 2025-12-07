<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import { chatService, type Conversation } from "$services/chatService";
  import { tStore, language } from "$stores/language";

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
    selectedModelName?: string;
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
    selectedModelName = $bindable(""),
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
  let selectedConversations = $state<Set<number>>(new Set()); // Track selected conversations for batch delete
  let showBatchActions = $state<boolean>(false); // Show/hide batch action buttons

  // Batch mode state
  let batchMode = $state<boolean>(false); // Enter/exit batch mode
  let longPressTimer = $state<ReturnType<typeof setTimeout> | null>(null); // For mobile long press
  let lastClickedId = $state<number | null>(null); // Track last clicked for Shift+click range selection

  // 获取翻译函数
  const t = $derived($tStore);

  // Get current language
  const currentLanguage = $derived($language);

  // Add global keyboard event listener for ESC key
  $effect(() => {
    if (batchMode) {
      const handleGlobalKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape' && batchMode) {
          clearAllSelections();
          batchMode = false;
        }
      };

      document.addEventListener('keydown', handleGlobalKeyDown);

      // Cleanup on component destroy or when batchMode changes
      return () => {
        document.removeEventListener('keydown', handleGlobalKeyDown);
      };
    }
  });

  onMount(async () => {
    try {
      loading = true;
      await loadConversations();
    } catch (err) {
      error = err instanceof Error ? err.message : t('common.error');
      console.error("Failed to load conversations:", err);
    } finally {
      loading = false;
    }
  });

  // Effect to initialize default model selection when providers are loaded
  // Note: We rely on ModelSelector to set the initial default selection
  // This component just tracks the selection state
  $effect(() => {
    if (providers.length > 0 && (!selectedProviderName || !selectedApiFormat || !selectedModelName)) {
      console.log("ConversationSidebar: Waiting for ModelSelector to initialize defaults...");
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
          selectedModelName = models[0];
          console.log("_setDefaultModelSelection:", {
            provider: selectedProviderName,
            format: selectedApiFormat,
            model: selectedModelName
          });
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

      // If no conversations remain and we have providers, ensure we have a valid model selection
      if (conversations.length === 0 && providers.length > 0) {
        // Reset all three fields to default
        selectedProviderName = providers[0].name;
        selectedApiFormat = providers[0].api_format;

        // Find first available model in any category
        for (const category of ["big", "middle", "small"]) {
          const models =
            providers[0].models[category as keyof ProviderConfig["models"]];
          if (models && models.length > 0) {
            selectedModelName = models[0];
            console.log("Reset model selection after deleting all conversations:", {
              provider: selectedProviderName,
              format: selectedApiFormat,
              model: selectedModelName
            });
            break;
          }
        }
      }
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
    editingTitle = conversation.title || t('chat.untitled');
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
      alert(t('common.error'));
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
      alert(t('common.error'));
    }
  }

  function selectConversation(conversation: Conversation) {
    currentConversationId = conversation.id;
    dispatch("conversationSelected", { conversation });
  }

  async function handleDelete(conversationId: number, event: Event) {
    event.stopPropagation();

    if (!confirm(t('chat.confirmDelete'))) {
      return;
    }

    deletingId = conversationId;
    try {
      await chatService.deleteConversation(conversationId);
      await loadConversations();

      if (currentConversationId === conversationId) {
        currentConversationId = null;
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
      alert(t('common.error'));
    } finally {
      deletingId = null;
    }
  }

  // Toggle batch mode
  function toggleBatchMode() {
    batchMode = !batchMode;
    if (!batchMode) {
      clearAllSelections();
    }
  }

  // Toggle conversation selection for batch operations
  function toggleConversationSelection(conversationId: number, event: Event) {
    event.stopPropagation();
    if (selectedConversations.has(conversationId)) {
      selectedConversations.delete(conversationId);
      selectedConversations = new Set(selectedConversations);
    } else {
      selectedConversations.add(conversationId);
      selectedConversations = new Set(selectedConversations);
    }
    showBatchActions = selectedConversations.size > 0;
  }

  // Handle conversation selection with Shift+click support (desktop)
  function handleConversationClick(conversation: Conversation, event: MouseEvent) {
    // If in batch mode and Shift is pressed, use range selection
    if (batchMode && event.shiftKey && lastClickedId !== null) {
      const currentIndex = displayConversations.findIndex(c => c.id === conversation.id);
      const lastIndex = displayConversations.findIndex(c => c.id === lastClickedId);

      if (currentIndex !== -1 && lastIndex !== -1) {
        const start = Math.min(currentIndex, lastIndex);
        const end = Math.max(currentIndex, lastIndex);

        // Select all conversations in the range
        const rangeIds = displayConversations.slice(start, end + 1).map(c => c.id);
        selectedConversations = new Set([...selectedConversations, ...rangeIds]);
        showBatchActions = selectedConversations.size > 0;
      }
    } else {
      // Normal click in batch mode
      if (batchMode) {
        toggleConversationSelection(conversation.id, event);
      } else {
        // Normal selection
        selectConversation(conversation);
      }
    }

    lastClickedId = conversation.id;
  }

  // Mobile long press handler - DISABLED to prevent interference with page scrolling
  function handleTouchStart(conversation: Conversation, _event: TouchEvent) {
    // Disabled - long press causes conflicts with page scrolling
    return;
  }

  function handleTouchEnd(conversation: Conversation, _event: TouchEvent) {
    // Disabled - long press causes conflicts with page scrolling
    return;
  }

  function handleTouchMove() {
    // Disabled - long press causes conflicts with page scrolling
    return;
  }

  function clearLongPressTimer() {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
  }

  // Clear all selections
  function clearAllSelections() {
    selectedConversations = new Set();
    showBatchActions = false;
  }

  // Batch delete selected conversations
  async function batchDeleteConversations() {
    if (selectedConversations.size === 0) {
      return;
    }

    if (!confirm(t('chat.confirmBatchDelete').replace('{count}', selectedConversations.size.toString()))) {
      return;
    }

    const idsToDelete = Array.from(selectedConversations);
    deletingId = idsToDelete[0]; // Set to first ID to show loading state

    try {
      // Delete conversations sequentially to avoid overwhelming the API
      for (const id of idsToDelete) {
        await chatService.deleteConversation(id);
      }
      await loadConversations();

      // Clear current conversation if it was deleted
      if (currentConversationId && selectedConversations.has(currentConversationId)) {
        currentConversationId = null;
      }

      // Clear selections
      clearAllSelections();

      console.log("Batch delete completed");
    } catch (err) {
      console.error("Failed to batch delete conversations:", err);
      alert(t('common.error'));
    } finally {
      deletingId = null;
    }
  }

  function handleNewConversation() {
    console.log("handleNewConversation called with:", {
      selectedProviderName,
      selectedApiFormat,
      selectedModelName,
      providersLength: providers.length,
    });

    if (!selectedProviderName || !selectedApiFormat || !selectedModelName) {
      const errorMsg = `Cannot create new conversation: missing model configuration (provider: ${selectedProviderName}, format: ${selectedApiFormat}, model: ${selectedModelName})`;
      console.error(errorMsg);
      alert(errorMsg);
      return;
    }

    dispatch("newConversation", {
      providerName: selectedProviderName,
      apiFormat: selectedApiFormat,
      model: selectedModelName,
    });
  }

function formatDate(dateString: string): string {
  try {
    if (!dateString) return t('common.error');

    // 直接解析ISO时间字符串（包含时区信息）
    const date = new Date(dateString);

    // 验证解析是否成功
    if (isNaN(date.getTime())) {
      console.warn("Cannot parse the time:", dateString);
      return dateString;
    }

    // 根据当前语言选择 locale
    const locale = currentLanguage === 'zh-CN' ? 'zh-CN' : 'en-US';

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
      const timeStr = date.toLocaleTimeString(locale, {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Shanghai"
      });
      return timeStr;
    } else if (diffDays === 1) {
      return t('chat.yesterday');
    } else if (diffDays < 7) {
      return t('chat.daysAgo').replace('{days}', diffDays.toString());
    } else {
      // 超过7天：显示完整日期（北京时间）
      return date.toLocaleDateString(locale, {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZone: "Asia/Shanghai"
      });
    }
  } catch (error) {
    console.error("Failed to format the time:", error, dateString);
    return dateString;
  }
}

  // Format model name for display
  function formatModelName(model: string | null): string {
    if (!model) return t('common.error');
    if (model.includes("/")) {
      return model.split("/")[1] || model;
    }
    return model;
  }
</script>

<div class="conversation-sidebar">
  <div class="sidebar-header">
    <button class="collapse-btn" onclick={() => dispatch("toggleSidebar")} title={t('chat.collapseSidebar')}>
      <span class="hamburger-icon">
        <span class="line line-1"></span>
        <span class="line line-2"></span>
        <span class="line line-3"></span>
      </span>
    </button>
    <input
      type="text"
      class="search-input"
      placeholder={t('chat.search')}
      bind:value={searchQuery}
    />
    <button
      class="batch-mode-btn {batchMode ? 'active' : ''}"
      onclick={toggleBatchMode}
      title={batchMode ? t('common.cancel') : t('chat.batchMode')}
    >
      {#if batchMode}
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="5" cy="5" r="1.5" fill="white"/>
          <circle cx="8" cy="5" r="1.5" fill="white"/>
          <circle cx="11" cy="5" r="1.5" fill="white"/>
          <circle cx="5" cy="8" r="1.5" fill="white"/>
          <circle cx="8" cy="8" r="1.5" fill="white"/>
          <circle cx="11" cy="8" r="1.5" fill="white"/>
          <circle cx="5" cy="11" r="1.5" fill="white"/>
          <circle cx="8" cy="11" r="1.5" fill="white"/>
          <circle cx="11" cy="11" r="1.5" fill="white"/>
        </svg>
      {:else}
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="4" y="4" width="2" height="2" rx="0.5" fill="currentColor"/>
          <rect x="7" y="4" width="2" height="2" rx="0.5" fill="currentColor"/>
          <rect x="10" y="4" width="2" height="2" rx="0.5" fill="currentColor"/>
          <rect x="4" y="7" width="2" height="2" rx="0.5" fill="currentColor"/>
          <rect x="7" y="7" width="2" height="2" rx="0.5" fill="currentColor"/>
          <rect x="10" y="7" width="2" height="2" rx="0.5" fill="currentColor"/>
          <rect x="4" y="10" width="2" height="2" rx="0.5" fill="currentColor"/>
          <rect x="7" y="10" width="2" height="2" rx="0.5" fill="currentColor"/>
          <rect x="10" y="10" width="2" height="2" rx="0.5" fill="currentColor"/>
        </svg>
      {/if}
    </button>
    <button class="new-btn" onclick={handleNewConversation} title={t('chat.newConversation')}>
      <span class="plus-icon">+</span>
    </button>
  </div>

  <!-- Batch actions bar -->
  {#if showBatchActions}
    <div class="batch-actions-bar">
      <span class="selected-count">{t('chat.selected').replace('{count}', selectedConversations.size.toString())}</span>
      <div class="batch-actions">
        <button class="batch-action-btn cancel" onclick={clearAllSelections}>
          {t('common.cancel')}
        </button>
        <button
          class="batch-action-btn delete"
          onclick={batchDeleteConversations}
          disabled={deletingId !== null}
        >
          {deletingId !== null ? t('common.deleting') : t('chat.delete')}
        </button>
      </div>
    </div>
  {/if}

  <div class="conversations-list" onscroll={handleScroll}>
    {#if loading}
      <div class="loading">
        <div class="spinner"></div>
        <p>{t('common.loading')}</p>
      </div>
    {:else if error}
      <div class="error">
        <p>{t('common.error')}: {error}</p>
        <button onclick={loadConversations}>{t('common.error')}</button>
      </div>
    {:else if conversations.length === 0}
      <div class="empty">
        <p>{t('chatArea.noMessages')}</p>
        <button class="secondary" onclick={handleNewConversation}>
          {t('chatArea.startConversation')}
        </button>
      </div>
    {:else if displayConversations.length === 0}
      <div class="empty">
        <p>{t('chat.search')}</p>
      </div>
    {:else}
      {#each displayConversations as conversation}
        <div
          class="conversation-item {currentConversationId === conversation.id
            ? 'active'
            : ''} {selectedConversations.has(conversation.id) ? 'selected' : ''} {batchMode ? 'batch-mode' : ''}"
          role="button"
          tabindex="0"
          onclick={(e) => handleConversationClick(conversation, e as MouseEvent)}
          onkeydown={(e) =>
            (e.key === "Enter" || e.key === " ") &&
            (!batchMode ? selectConversation(conversation) : toggleConversationSelection(conversation.id, e))}
          data-touch-events-disabled
        >
          {#if batchMode}
            <div class="checkbox-container">
              <input
                type="checkbox"
                class="conversation-checkbox"
                checked={selectedConversations.has(conversation.id)}
                onclick={(e) => toggleConversationSelection(conversation.id, e)}
              />
            </div>
          {/if}
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
                    title={t('common.save')}
                  >
                    ✓
                  </button>
                  <button
                    class="action-btn cancel-btn"
                    onclick={(e) => {
                      e.stopPropagation();
                      cancelEdit();
                    }}
                    title={t('common.cancel')}
                  >
                    ×
                  </button>
                </div>
              {:else}
                <h3 class="title">{conversation.title || t('chat.untitled')}</h3>
                <div class="right-area">
                  <span class="time">{formatDate(conversation.updated_at)}</span>
                  <div class="menu-container">
                    <button
                      class="menu-btn"
                      onclick={(e) => toggleMenu(conversation.id, e)}
                      title={t('common.edit')}
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
                          {t('chat.rename')}
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
                          {t('chat.delete')}
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
          <p>{displayConversations.length} / {filteredConversations.length}</p>
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
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
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
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    position: relative;
  }

  .plus-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    font-size: 1.5rem;
    font-weight: 400;
    line-height: 1;
    transform: translateY(-3px);
  }

  .new-btn:hover {
    background: var(--bg-tertiary);
    color: var(--primary-color);
    border-color: var(--primary-color);
    transform: scale(1.1);
  }

  .new-btn:active {
    background: var(--bg-tertiary);
    color: var(--primary-color);
    transform: scale(0.98);
    box-shadow:
      0 1px 2px rgba(0, 0, 0, 0.1),
      inset 0 0 4px rgba(0, 0, 0, 0.1);
  }

  .new-btn:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5);
  }

  .batch-mode-btn {
    padding: 0.5rem;
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
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

  .batch-mode-btn:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
    transform: scale(1.1);
  }

  .batch-mode-btn:active {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    transform: scale(0.98);
  }

  .batch-mode-btn.active {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
  }

  .batch-mode-btn.active:hover {
    background: var(--primary-hover);
    color: white;
    border-color: var(--primary-color);
  }

  .batch-mode-btn:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5);
  }

  .batch-mode-btn svg {
    display: block;
    width: 16px;
    height: 16px;
    transition: all 0.2s ease;
  }

  /* Batch actions bar */
  .batch-actions-bar {
    padding: 0.75rem 1rem;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    animation: slideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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

  .selected-count {
    font-size: 0.875rem;
    color: var(--text-secondary);
    font-weight: 500;
  }

  .batch-actions {
    display: flex;
    gap: 0.5rem;
  }

  .batch-action-btn {
    padding: 0.375rem 0.75rem;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .batch-action-btn.cancel {
    background: transparent;
    color: var(--text-secondary);
  }

  .batch-action-btn.cancel:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .batch-action-btn.delete {
    background: #ef4444;
    color: white;
  }

  .batch-action-btn.delete:hover:not(:disabled) {
    background: #dc2626;
  }

  .batch-action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
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
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
  }

  .conversation-item.active .title,
  .conversation-item.active .meta {
    color: var(--text-primary);
  }

  .conversation-item.selected {
    background: var(--bg-secondary);
    border: 2px solid var(--primary-color);
  }

  .conversation-item.active.selected {
    background: var(--primary-color);
    border-color: white;
  }

  /* Batch mode styles */
  .conversation-item.batch-mode {
    cursor: default;
  }

  .conversation-item.batch-mode:hover {
    background: var(--bg-secondary);
    transform: none;
  }

  .conversation-item.batch-mode.active:hover {
    background: var(--primary-color);
    transform: none;
  }

  .checkbox-container {
    display: flex;
    align-items: center;
    margin-right: 0.5rem;
    flex-shrink: 0;
  }

  .conversation-checkbox {
    width: 18px;
    height: 18px;
    cursor: pointer;
    accent-color: var(--primary-color);
  }

  .conversation-item.active .conversation-checkbox {
    accent-color: white;
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
    color: var(--text-tertiary);
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
    color: var(--text-secondary);
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
    background: rgba(255, 255, 255, 0.2);
    color: var(--primary-color);
  }

  /* 当对话项处于激活状态时，菜单按钮的样式 */
  .conversation-item.active .menu-btn {
    color: var(--text-tertiary);
  }

  .conversation-item.active .menu-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
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
