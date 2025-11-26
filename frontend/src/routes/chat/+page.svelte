<script lang="ts">
  import { onMount } from 'svelte';
  import ModelSelector from '$components/chat/ModelSelector.svelte';
  import ConversationSidebar from '$components/chat/ConversationSidebar.svelte';
  import ChatArea from '$components/chat/ChatArea.svelte';
  import { chatService, type Conversation, type ConversationDetail, type ModelChoice } from '$services/chatService';
  import { Toast } from '$components/ui';
  import { theme } from '$stores/theme';
  import { authService } from '$services/auth';

  let conversations: Conversation[] = [];
  let currentConversation: ConversationDetail | null = null;

  // Model selection state (shared between components)
  let selectedProvider: string = '';
  let selectedApiFormat: string = '';
  let selectedModelName: string = '';
  let selectedCategory: string = 'middle';
  let selectedModelChoice: ModelChoice | null = null;

  let isLoading = false;
  let error: string | null = null;
  let toast: { message: string; type: 'success' | 'error' | 'info' } | null = null;

  let sidebar: ConversationSidebar;
  let chatArea: ChatArea;

  onMount(async () => {
    try {
      isLoading = true;
      await loadConversations();
    } catch (err) {
      error = err instanceof Error ? err.message : '初始化失败';
      showToast('初始化失败', 'error');
    } finally {
      isLoading = false;
    }
  });

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
    console.log('Model selected:', modelChoice);
  }

  async function handleConversationSelected(event: CustomEvent) {
    const conversation = event.detail.conversation;
    await selectConversation(conversation);
  }

  async function selectConversation(conversation: Conversation) {
    try {
      isLoading = true;
      currentConversation = await chatService.getConversation(conversation.id);

      // Set model selection based on conversation
      if (currentConversation?.model) {
        // Extract provider info from conversation if possible
        // Default to assuming it's the first provider/model
        selectedProvider = currentConversation.provider_name || '';
        selectedApiFormat = currentConversation.api_format || 'openai';
        selectedModelName = currentConversation.model;
      }
    } catch (err) {
      error = err instanceof Error ? err.message : '加载对话失败';
      console.error('Failed to select conversation:', err);
      showToast('加载对话失败', 'error');
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
      const title = '新对话';
      const conversation = await chatService.createConversation(
        title,
        providerName,
        apiFormat,
        model
      );

      // Add to list
      conversations = [conversation, ...conversations];

      // Select the new conversation
      await selectConversation(conversation);

      showToast('新对话已创建', 'success');
    } catch (err) {
      error = err instanceof Error ? err.message : '创建对话失败';
      console.error('Failed to create conversation:', err);
      showToast('创建对话失败', 'error');
    } finally {
      isLoading = false;
    }
  }

  async function handleConversationUpdate(event: CustomEvent) {
    const updatedConversation = event.detail.conversation;

    // Update in list
    conversations = conversations.map(c =>
      c.id === updatedConversation.id ? { ...c, ...updatedConversation } : c
    );

    currentConversation = updatedConversation;
  }

  function handleError(event: CustomEvent) {
    error = event.detail.message;
    showToast(error, 'error');
  }

  function showToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
    toast = { message, type };
    setTimeout(() => {
      toast = null;
    }, 3000);
  }
</script>

<div class="chat-page">
  <ModelSelector on:modelSelected={handleModelSelected} />

  <div class="chat-container">
    <div class="sidebar">
      <ConversationSidebar
        bind:this={sidebar}
        conversations={conversations}
        currentConversationId={currentConversation?.id || null}
        bind:selectedProviderName={selectedProvider}
        bind:selectedApiFormat={selectedApiFormat}
        bind:selectedModelValue={selectedModel}
        on:conversationSelected={handleConversationSelected}
        on:newConversation={handleNewConversation}
      />
    </div>

    <div class="main-content">
      <ChatArea
        bind:this={chatArea}
        conversation={currentConversation}
        selectedModel={selectedModel}
        on:conversationUpdate={handleConversationUpdate}
        on:error={handleError}
      />
    </div>
  </div>

  {#if toast}
    <Toast message={toast.message} type={toast.type} />
  {/if}

  {#if isLoading && !currentConversation}
    <div class="page-loading">
      <div class="spinner" />
      <p>加载中...</p>
    </div>
  {/if}
</div>

<style>
  .chat-page {
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .chat-container {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .sidebar {
    width: 320px;
    border-right: 1px solid var(--border-color);
    background: var(--bg-primary);
    overflow: hidden;
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .page-loading {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    z-index: 1000;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(255, 255, 255, 0.3);
    border-top: 4px solid white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  :global(html, body) {
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
  }

  @media (max-width: 768px) {
    .chat-container {
      flex-direction: column;
    }

    .sidebar {
      width: 100%;
      height: 300px;
      border-right: none;
      border-bottom: 1px solid var(--border-color);
    }

    .main-content {
      flex: 1;
    }
  }
</style>
