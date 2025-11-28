<script lang="ts">
  import { onMount } from "svelte";
  import ModelSelector from "$components/chat/ModelSelector.svelte";
  import ConversationSidebar from "$components/chat/ConversationSidebar.svelte";
  import ChatArea from "$components/chat/ChatArea.svelte";
  import {
    chatService,
    type Conversation,
    type ConversationDetail,
    type ModelChoice,
  } from "$services/chatService";
  import { providerService } from "$services/providers";
  import { theme } from "$stores/theme";
  import { authService } from "$services/auth";
  import { toast } from "$stores/toast";

  interface ProviderConfig {
    name: string;
    api_format: string;
    models: {
      big?: string[];
      middle?: string[];
      small?: string[];
    };
  }

  let conversations: Conversation[] = [];
  let currentConversation: ConversationDetail | null = null;
  let providers: ProviderConfig[] = [];

  // Model selection state (shared between components)
  let selectedProvider: string = "";
  let selectedApiFormat: string = "";
  let selectedModelName: string = "";
  let selectedCategory: string = "middle";
  let selectedModelChoice: ModelChoice | null = null;

  let isLoading = false;
  let error: string | null = null;

  let sidebar: ConversationSidebar;
  let chatArea: ChatArea;

  onMount(async () => {
    try {
      isLoading = true;
      await Promise.all([loadConversations(), loadProviders()]);
    } catch (err) {
      error = err instanceof Error ? err.message : "初始化失败";
      showToast("初始化失败", "error");
    } finally {
      isLoading = false;
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
      console.log("Providers loaded:", providers);
    } catch (err) {
      console.error("Failed to load providers:", err);
      throw err;
    }
  }

  async function loadConversations() {
    conversations = await chatService.getConversations();

    // Load last conversation if exists
    if (conversations.length > 0) {
      const lastConversation = conversations[0];
      await selectConversation(lastConversation);
    }
  }

  async function handleModelSelected(event: CustomEvent) {
    const modelChoice = event.detail;
    // Update all fields to sync with ConversationSidebar
    selectedProvider = modelChoice.providerName;
    selectedApiFormat = modelChoice.apiFormat;
    selectedModelName = modelChoice.model;
    selectedModelChoice = modelChoice;
    console.log("Model selected:", modelChoice);
  }

  async function handleConversationSelected(event: CustomEvent) {
    const conversation = event.detail.conversation;
    await selectConversation(conversation);
  }

  async function selectConversation(conversation: Conversation) {
    try {
      isLoading = true;
      console.log("Selecting conversation:", conversation.id);
      currentConversation = await chatService.getConversation(conversation.id);
      console.log("Current conversation loaded:", currentConversation);

      // Initialize model selection state from conversation config
      // This ensures the model selector shows the correct values when loading an existing conversation
      if (currentConversation.provider_name) {
        selectedProvider = currentConversation.provider_name;
      }
      if (currentConversation.api_format) {
        selectedApiFormat = currentConversation.api_format;
      }
      if (currentConversation.model) {
        selectedModelName = currentConversation.model;
      }

      console.log("Model selection initialized from conversation:", {
        provider: selectedProvider,
        apiFormat: selectedApiFormat,
        model: selectedModelName,
      });
    } catch (err) {
      error = err instanceof Error ? err.message : "加载对话失败";
      console.error("Failed to select conversation:", err);
      showToast("加载对话失败", "error");
      currentConversation = null;
    } finally {
      isLoading = false;
    }
  }

  async function handleNewConversation(event: CustomEvent) {
    const { providerName, apiFormat, model } = event.detail;

    try {
      isLoading = true;
      error = null;

      // Create new conversation
      const title = "新对话";
      const conversation = await chatService.createConversation(
        title,
        providerName,
        apiFormat,
        model,
      );

      // Add to list
      conversations = [conversation, ...conversations];

      // Select the new conversation
      await selectConversation(conversation);

      showToast("新对话已创建", "success");
    } catch (err) {
      error = err instanceof Error ? err.message : "创建对话失败";
      console.error("Failed to create conversation:", err);
      showToast("创建对话失败", "error");
    } finally {
      isLoading = false;
    }
  }

  async function handleConversationUpdate(event: CustomEvent) {
    const updatedConversation = event.detail.conversation;

    // Update in list
    conversations = conversations.map((c) =>
      c.id === updatedConversation.id ? { ...c, ...updatedConversation } : c,
    );

    currentConversation = updatedConversation;
  }

  function handleError(event: CustomEvent) {
    error = event.detail.message;
    showToast(error || "发生错误", "error");
  }

  function showToast(
    message: string,
    type: "success" | "error" | "info" = "info",
  ) {
    toast.show(message, type);
  }
</script>

<div class="chat-page">
  <ModelSelector
    bind:selectedProvider
    bind:selectedApiFormat
    bind:selectedModelName
    bind:selectedCategory
    on:modelSelected={handleModelSelected}
  />

  <div class="chat-container">
    <div class="sidebar">
      <ConversationSidebar
        bind:this={sidebar}
        {conversations}
        currentConversationId={currentConversation?.id || null}
        {providers}
        bind:selectedProviderName={selectedProvider}
        bind:selectedApiFormat
        bind:selectedModelValue={selectedModelName}
        on:conversationSelected={handleConversationSelected}
        on:newConversation={handleNewConversation}
      />
    </div>

    <div class="main-content">
      <ChatArea
        bind:this={chatArea}
        conversation={currentConversation}
        selectedModel={selectedModelName}
        {selectedProvider}
        {selectedApiFormat}
        on:conversationUpdate={handleConversationUpdate}
        on:error={handleError}
      />
    </div>
  </div>

  {#if isLoading && !currentConversation && conversations.length === 0}
    <div class="page-loading">
      <div class="spinner"></div>
      <p>加载中...</p>
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
    flex-shrink: 0;
    transition: width 0.3s ease;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-secondary);
    min-width: 0;
    position: relative;
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
      height: 100dvh; /* Use dynamic viewport height for mobile */
    }

    .chat-container {
      flex-direction: column;
    }

    .sidebar {
      width: 100%;
      height: 40vh;
      max-height: 400px;
      border-right: none;
      border-bottom: 2px solid var(--border-color);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .main-content {
      flex: 1;
      min-height: 0;
    }
  }

  /* Small mobile styles */
  @media (max-width: 480px) {
    .sidebar {
      height: 35vh;
      max-height: 300px;
    }
  }
</style>
