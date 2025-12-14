<script lang="ts">
  import { onMount } from "svelte";
  import ConversationSidebar from "$components/chat/ConversationSidebar.svelte";
  import ChatArea from "$components/chat/ChatArea.svelte";
  import {
    chatService,
    type Conversation,
    type ModelChoice,
  } from "$services/chatService";
  import { providerService } from "$services/providers";
  import { toast } from "$stores/toast";
  import { tStore } from "$stores/language";
  import { getSessionStore } from "$stores/chatSession";
  import { getOrCreateSessionId } from "$lib/utils/session";

  interface ProviderConfig {
    name: string;
    api_format: string;
    models: {
      big?: string[];
      middle?: string[];
      small?: string[];
    };
  }

  // 获取当前会话ID并创建会话store
  const sessionId = getOrCreateSessionId();
  const sessionStore = getSessionStore(sessionId);
  const sessionState = $derived($sessionStore);

  // 从会话状态中提取数据
  let conversations = $derived(sessionState.conversations);
  let currentConversation = $derived(sessionState.currentConversation);
  let isLoading = $derived(sessionState.isLoading);
  
  // Provider配置是全局的，不属于会话状态
  let providers = $state<ProviderConfig[]>([]);

  // Model selection state (shared between components)
  let selectedModels = $state<ModelChoice[]>([]);
  let selectedProviderName = $state<string>("");
  let selectedApiFormat = $state<string>("");
  let selectedModelName = $state<string>("");
  let selectedCategory = $state<string>("middle");
  let _selectedModelChoice: ModelChoice | null = null;

  let sidebar: ConversationSidebar;
  let chatArea: ChatArea;

  // 检测是否为移动端
  function isMobile(): boolean {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= 768;
  }

  let sidebarCollapsed = $state(false);

  // 在移动端默认折叠侧边栏
  $effect(() => {
    if (typeof window !== 'undefined') {
      sidebarCollapsed = isMobile();
    }
  });

  // 监听窗口大小变化，保持移动端折叠状态
  $effect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => {
      sidebarCollapsed = isMobile();
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  });

  // 获取翻译函数
  const t = $derived($tStore);

  // Force scroll to bottom when conversation changes
  $effect(() => {
    if (currentConversation) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        if (chatArea && typeof chatArea.scrollToBottom === 'function') {
          chatArea.scrollToBottom();
        }
      }, 100);
    }
  });

  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }

  onMount(async () => {
    try {
      sessionStore.update(state => ({ ...state, isLoading: true, error: null }));
      await Promise.all([loadConversations(), loadProviders()]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('common.error');
      sessionStore.update(state => ({ ...state, error: errorMessage }));
      showToast(t('common.error'), "error");
    } finally {
      sessionStore.update(state => ({ ...state, isLoading: false }));
    }
  });

  async function loadProviders() {
    try {
      const providersData = await providerService.getAll();
      providers = providersData
        .filter((p) => p.enabled && p.api_format)
        .map((p) => ({
          name: p.name,
          api_format: p.api_format!,
          models: p.models,
        }));
      console.log("Providers loaded:", $state.snapshot(providers));

      // Initialize default model selection if not already set
      if (providers.length > 0 && !selectedModelName) {
        selectedProviderName = providers[0].name;
        selectedApiFormat = providers[0].api_format;

        // Find first available model in any category
        for (const category of ["big", "middle", "small"]) {
          const models = providers[0].models[category as keyof typeof providers[0]["models"]];
          if (models && models.length > 0) {
            selectedModelName = models[0];
            console.log("Default model initialized:", selectedModelName);
            break;
          }
        }
      }
    } catch (err) {
      console.error("Failed to load providers:", err);
      throw err;
    }
  }

  async function loadConversations() {
    const conversationsData = await chatService.getConversations();
    sessionStore.update(state => ({ ...state, conversations: conversationsData }));

    // Load last conversation if exists
    if (conversationsData.length > 0) {
      const lastConversation = conversationsData[0];
      await selectConversation(lastConversation);
    }
  }

  async function handleModelSelected(event: CustomEvent) {
    const modelChoice = event.detail;
    // Update all fields to sync with ConversationSidebar
    selectedProviderName = modelChoice.providerName;
    selectedApiFormat = modelChoice.apiFormat;
    selectedModelName = modelChoice.model;
    _selectedModelChoice = modelChoice;
    console.log("Model selected:", modelChoice);
  }

  async function handleConversationSelected(event: CustomEvent) {
    const conversation = event.detail.conversation;
    if (!conversation) {
      sessionStore.update(state => ({ ...state, currentConversation: null }));
      return;
    }
    await selectConversation(conversation);
  }

  async function selectConversation(conversation: Conversation) {
    try {
      sessionStore.update(state => ({ ...state, isLoading: true, error: null }));
      console.log("Selecting conversation:", conversation.id);
      const conversationData = await chatService.getConversation(conversation.id);
      console.log("Current conversation loaded:", $state.snapshot(conversationData));
      sessionStore.update(state => ({ ...state, currentConversation: conversationData, isLoading: false }));

      // Initialize model selection state from conversation config
      // This ensures the model selector shows the correct values when loading an existing conversation
      // We always use models from the LAST question to match user expectations

      // Get models from the last user question and its assistant responses
      if (conversationData.messages && conversationData.messages.length > 0) {
        // Find the last user message
        const messages = conversationData.messages;
        const lastUserMessageIndex = [...messages].reverse().findIndex(m => m.role === "user");

        if (lastUserMessageIndex !== -1) {
          const actualIndex = messages.length - 1 - lastUserMessageIndex;
          const lastUserMessage = messages[actualIndex];

          // Find all assistant messages that came after this last user message
          const lastUserMessageDate = new Date(lastUserMessage.created_at || 0).getTime();
          const assistantMessagesForLastQuestion = messages.filter(msg => {
            if (msg.role !== "assistant") return false;
            const msgDate = new Date(msg.created_at || 0).getTime();
            return msgDate >= lastUserMessageDate;
          });

          // Extract models from these assistant messages
          // Keep all models (including duplicates) since each has different conversation results
          const modelsList: ModelChoice[] = [];

          assistantMessagesForLastQuestion.forEach(msg => {
            if (msg.provider_name && msg.api_format && msg.model) {
              modelsList.push({
                providerName: msg.provider_name,
                apiFormat: msg.api_format,
                model: msg.model,
              });
            }
          });

          // Set the models from the last question
          if (modelsList.length > 0) {
            // For single model conversation, use only the LAST model
            // For multi-model conversation, keep all models
            // Determine if this is a single or multi-model conversation
            const isSingleModel = assistantMessagesForLastQuestion.length === 1;

            if (isSingleModel) {
              // Single model: use only the last model
              const lastModel = modelsList[modelsList.length - 1];
              selectedModels = [lastModel];
              console.log("Loaded model from last question (single model mode):", lastModel);

              // Update single model selection for compatibility
              selectedProviderName = lastModel.providerName;
              selectedApiFormat = lastModel.apiFormat;
              selectedModelName = lastModel.model;
            } else {
              // Multi-model: keep all unique models
              // Remove duplicates based on model+provider+api_format
              const uniqueModels: ModelChoice[] = [];
              const seen = new Set<string>();

              modelsList.forEach(model => {
                const key = `${model.providerName}-${model.apiFormat}-${model.model}`;
                if (!seen.has(key)) {
                  seen.add(key);
                  uniqueModels.push(model);
                }
              });

              selectedModels = uniqueModels;
              console.log("Loaded models from last question (multi-model mode):", uniqueModels);

              // Update single model selection for compatibility (use first model)
              if (selectedModels.length > 0) {
                selectedProviderName = selectedModels[0].providerName;
                selectedApiFormat = selectedModels[0].apiFormat;
                selectedModelName = selectedModels[0].model;
              }
            }
          } else {
            // Fallback: use last assistant message
            const lastAssistantMessage = [...messages].reverse().find(m => m.role === "assistant");
            if (lastAssistantMessage) {
              selectedProviderName = lastAssistantMessage.provider_name || "";
              selectedApiFormat = lastAssistantMessage.api_format || "";
              selectedModelName = lastAssistantMessage.model || "";
              selectedModels = [{
                providerName: selectedProviderName,
                apiFormat: selectedApiFormat,
                model: selectedModelName,
              }];
              console.log("Loaded model from last assistant message (fallback):", selectedModels[0]);
            }
          }
        } else {
          // No user messages, use conversation-level model info
          if (conversationData.last_model) {
            selectedProviderName = conversationData.last_provider_name || "";
            selectedApiFormat = conversationData.last_api_format || "";
            selectedModelName = conversationData.last_model;
            selectedModels = [{
              providerName: selectedProviderName,
              apiFormat: selectedApiFormat,
              model: selectedModelName,
            }];
          } else if (conversationData.model) {
            selectedProviderName = conversationData.provider_name || "";
            selectedApiFormat = conversationData.api_format || "";
            selectedModelName = conversationData.model;
            selectedModels = [{
              providerName: selectedProviderName,
              apiFormat: selectedApiFormat,
              model: selectedModelName,
            }];
          }
        }
      } else {
        // Fall back to conversation-level model info
        if (conversationData.last_model) {
          selectedProviderName = conversationData.last_provider_name || "";
          selectedApiFormat = conversationData.last_api_format || "";
          selectedModelName = conversationData.last_model;
          selectedModels = [{
            providerName: selectedProviderName,
            apiFormat: selectedApiFormat,
            model: selectedModelName,
          }];
        } else if (conversationData.model) {
          selectedProviderName = conversationData.provider_name || "";
          selectedApiFormat = conversationData.api_format || "";
          selectedModelName = conversationData.model;
          selectedModels = [{
            providerName: selectedProviderName,
            apiFormat: selectedApiFormat,
            model: selectedModelName,
          }];
        }
      }

      console.log("Model selection initialized from conversation:", {
        selectedModels,
        selectedProviderName,
        selectedApiFormat,
        selectedModelName,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('common.error');
      console.error("Failed to select conversation:", err);
      showToast(t('common.error'), "error");
      sessionStore.update(state => ({ ...state, currentConversation: null, error: errorMessage, isLoading: false }));
    }
  }

  async function handleNewConversation(event: CustomEvent) {
    const { providerName, apiFormat, model } = event.detail;

    try {
      sessionStore.update(state => ({ ...state, isLoading: true, error: null }));

      console.log("Creating new conversation with:", { providerName, apiFormat, model });

      // Create new conversation
      const title = t('chat.newConversation');
      const newConversation = await chatService.createConversation(
        title,
        providerName,
        apiFormat,
        model,
      );

      console.log("New conversation created:", newConversation);

      // Reload conversations from backend to ensure consistency
      await loadConversations();

      // Automatically select the newly created conversation
      if (newConversation) {
        const conversationData = await chatService.getConversation(newConversation.id);
        console.log("New conversation selected:", conversationData);
        sessionStore.update(state => ({ ...state, currentConversation: conversationData }));
      }

      showToast(t('common.success'), "success");
      sessionStore.update(state => ({ ...state, isLoading: false }));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('common.error');
      console.error("Failed to create conversation:", err);
      showToast(t('common.error'), "error");
      sessionStore.update(state => ({ ...state, error: errorMessage, isLoading: false }));
    }
  }

  async function handleConversationUpdate(event: CustomEvent) {
    const updatedConversation = event.detail.conversation;

    // Update in list
    const updatedConversations = sessionState.conversations.map((c) =>
      c.id === updatedConversation.id ? { ...c, ...updatedConversation } : c,
    );

    sessionStore.update(state => ({
      ...state,
      conversations: updatedConversations,
      currentConversation: updatedConversation
    }));
  }

  function handleError(event: CustomEvent) {
    const errorMessage = event.detail.message;
    sessionStore.update(state => ({ ...state, error: errorMessage }));
    showToast(errorMessage || t('common.error'), "error");
  }

  function showToast(
    message: string,
    type: "success" | "error" | "info" = "info",
  ) {
    toast.show(message, type);
  }
</script>

<div class="chat-page">
  <div class="chat-container">
    <div class="sidebar {sidebarCollapsed ? 'collapsed' : ''}">
      <ConversationSidebar
        bind:this={sidebar}
        {conversations}
        currentConversationId={currentConversation?.id || null}
        {providers}
        bind:selectedProviderName={selectedProviderName}
        bind:selectedApiFormat
        bind:selectedModelName={selectedModelName}
        on:toggleSidebar={toggleSidebar}
        on:conversationSelected={handleConversationSelected}
        on:newConversation={handleNewConversation}
      />
    </div>

    <div class="main-content">
      <ChatArea
        bind:this={chatArea}
        conversation={currentConversation}
        bind:selectedModels={selectedModels}
        bind:selectedProviderName={selectedProviderName}
        bind:selectedApiFormat={selectedApiFormat}
        bind:selectedModelName={selectedModelName}
        bind:selectedCategory={selectedCategory}
        {sidebarCollapsed}
        on:toggleSidebar={toggleSidebar}
        on:conversationUpdate={handleConversationUpdate}
        on:error={handleError}
        on:modelSelected={handleModelSelected}
      />
    </div>
  </div>

  {#if isLoading && !currentConversation && conversations.length === 0}
    <div class="page-loading">
      <div class="spinner"></div>
      <p>{t('common.loading')}</p>
    </div>
  {/if}
</div>

<style>
  .chat-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-primary);
    overflow: hidden;
  }

  .chat-container {
    flex: 1;
    display: flex;
    overflow: hidden;
    min-height: 0;
    position: relative;
  }

  .sidebar {
    width: 280px;
    border-right: 1px solid var(--border-color);
    background: var(--bg-primary);
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    position: absolute;
    top: 0;
    left: 0;
    z-index: 10;
    transform: translateX(0);
    transition: transform 0.35s cubic-bezier(0.25, 0.1, 0.25, 1),
                box-shadow 0.35s;
  }

  .sidebar.collapsed {
    transform: translateX(-100%);
    box-shadow: none;
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-secondary);
    min-width: 0;
    position: relative;
    margin-left: 280px;
    transition: margin-left 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
  }

  .sidebar.collapsed + .main-content {
    margin-left: 0;
  }

  .page-loading {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    z-index: 1000;
    animation: fadeIn 0.2s ease-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .spinner {
    width: 48px;
    height: 48px;
    border: 4px solid rgba(255, 255, 255, 0.2);
    border-top: 4px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 1rem;
  }

  .page-loading p {
    font-size: 0.95rem;
    font-weight: 500;
    opacity: 0.9;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  /* Tablet styles */
  @media (max-width: 1024px) {
    .sidebar {
      width: 260px;
    }
  }

  /* Mobile styles */
  @media (max-width: 768px) {
    .chat-page {
      /* 移动端布局优化 - 移除固定高度，使用自适应高度 */
      height: auto;
      min-height: calc(100dvh - 120px); /* 减去Header高度（约80px）和footer高度（约40px） */
      position: relative;
      overflow: visible; /* 改为visible */
      /* 移动端安全区域适配 */
      padding-top: env(safe-area-inset-top);
      padding-bottom: env(safe-area-inset-bottom);
    }

    .chat-container {
      flex-direction: column;
      height: 100%;
      position: relative;
    }

    .sidebar {
      width: 100%;
      height: 45vh;
      max-height: 50vh;
      min-height: 200px;
      border-right: none;
      border-bottom: 2px solid var(--border-color);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      z-index: 20;
      /* 移动端侧边栏优化 */
      padding-bottom: env(safe-area-inset-bottom);
      /* 移动端滑动优化 */
      -webkit-overflow-scrolling: touch;
      overscroll-behavior: contain;
    }

    .main-content {
      flex: 1;
      min-height: 0;
      margin-left: 0; /* 移动端不需要偏移 */
      /* 移动端主内容区优化 */
      display: flex;
      flex-direction: column;
      height: calc(100% - 45vh);
      overflow: hidden;
      /* 移动端滚动优化 */
      -webkit-overflow-scrolling: touch;
    }

    /* 移动端侧边栏展开状态 */
    .sidebar.collapsed {
      transform: translateY(-100%);
      height: 0;
      min-height: 0;
      border-bottom: none;
      box-shadow: none;
    }

    .sidebar.collapsed + .main-content {
      height: 100%;
    }
  }

  /* Small mobile styles */
  @media (max-width: 480px) {
    .sidebar {
      height: 40vh;
      max-height: 45vh;
      min-height: 180px;
    }

    .main-content {
      height: calc(100% - 40vh);
    }

    /* 小屏幕优化 */
    .chat-page {
      padding: 0;
    }
  }

  /* 超小屏幕优化 */
  @media (max-width: 360px) {
    .sidebar {
      height: 38vh;
      max-height: 42vh;
      min-height: 160px;
    }

    .main-content {
      height: calc(100% - 38vh);
    }
  }

  /* 移动端横屏优化 */
  @media (max-width: 768px) and (orientation: landscape) {
    .sidebar {
      height: 65vh;
      max-height: 70vh;
      min-height: 150px;
    }

    .main-content {
      height: calc(100% - 65vh);
    }
  }
</style>
