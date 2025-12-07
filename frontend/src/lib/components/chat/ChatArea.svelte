<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { tick } from "svelte";
  import MessageBubble from "./MessageBubble.svelte";
  import MessageInput from "./MessageInput.svelte";
  import ModelSelector from "./ModelSelector.svelte";
  import {
    chatService,
    type ConversationDetail,
    type Message,
    type ModelChoice,
  } from "$services/chatService";
  import { authService } from "$services/auth";
  import { tStore } from "$stores/language";

  let {
    conversation = $bindable(null),
    selectedModels = $bindable([]),
    selectedProviderName = $bindable(""),
    selectedApiFormat = $bindable(""),
    selectedModelName = $bindable(""),
    selectedCategory = $bindable("middle"),
    sidebarCollapsed = $bindable(false),
  }: {
    conversation: ConversationDetail | null;
    selectedModels: ModelChoice[];
    selectedProviderName: string;
    selectedApiFormat: string;
    selectedModelName: string;
    selectedCategory: string;
    sidebarCollapsed: boolean;
  } = $props();

  const dispatch = createEventDispatcher<{
    conversationUpdate: { conversation: ConversationDetail };
    error: { message: string };
    modelSelected: ModelChoice;
    toggleSidebar: void;
  }>();

  function handleModelSelected(event: CustomEvent<ModelChoice>) {
    dispatch("modelSelected", event.detail);
  }

  // Group messages into user-assistant pairs for display
  function getMessageGroups() {
    const groups = [];
    let i = 0;

    while (i < messages.length) {
      const group = {
        userMessage: null as Message | null,
        assistantMessages: [] as Message[],
      };

      // Find user message
      if (messages[i].role === "user") {
        group.userMessage = messages[i];
        i++;
      }

      // Find all following assistant messages
      while (i < messages.length && messages[i].role === "assistant") {
        group.assistantMessages.push(messages[i]);
        i++;
      }

      // Only add group if it has content
      if (group.userMessage || group.assistantMessages.length > 0) {
        groups.push(group);
      }
    }

    return groups;
  }

  let messages: Message[] = $state([]);
  let isLoading = $state(false);
  let streamingMessages: Record<string, string> = $state({});
  let streamingThinkings: Record<string, string> = $state({});
  let streamingCompleted: Record<string, boolean> = $state({}); // Track completed streams
  let error: string | null = $state(null);
  let errorDetails: any = $state(null); // Store detailed error information
  let showErrorDetails = $state(false); // Toggle to show/hide error details
  let messagesContainer: HTMLDivElement;
  let userScrolledUp = $state(false); // Track if user manually scrolled up
  let isAtBottom = $state(true); // Track if user is at bottom

  // Extend Error interface to support additional properties
  interface ExtendedError extends Error {
    status?: number;
    statusText?: string;
    details?: any;
  }

  // 获取翻译函数
  const t = $derived($tStore);

  // Load messages when conversation changes
  $effect(() => {
    if (conversation) {
      console.log("ChatArea: conversation changed:", $state.snapshot(conversation));
      loadMessages();
    } else {
      // console.log("ChatArea: no conversation");
      messages = [];
    }
  });

  async function loadMessages() {
    if (!conversation) return;

    try {
      isLoading = true;
      error = null;
      errorDetails = null;

      const detail = await chatService.getConversation(conversation.id);
      messages = detail.messages || [];

      // Update model selector based on the last assistant message
      if (messages.length > 0) {
        // Find the last assistant message
        const lastAssistantMessage = [...messages].reverse().find(m => m.role === "assistant");

        if (lastAssistantMessage) {
          // Update model selector to show the model from the last assistant message
          selectedProviderName = lastAssistantMessage.provider_name || selectedProviderName;
          selectedApiFormat = lastAssistantMessage.api_format || selectedApiFormat;
          selectedModelName = lastAssistantMessage.model || selectedModelName;

          console.log("ChatArea: Updated model selector from last message:", {
            providerName: selectedProviderName,
            apiFormat: selectedApiFormat,
            model: selectedModelName
          });
        }
      }
    } catch (err) {
      error = err instanceof Error ? err.message : t('common.error');
      errorDetails = {
        message: err instanceof Error ? err.message : t('common.error'),
        timestamp: new Date().toISOString()
      };
      console.error("Failed to load messages:", err);
    } finally {
      isLoading = false;
      // Reset scroll state
      userScrolledUp = false;
      isAtBottom = true;

      // Scroll to bottom after loading with multiple attempts
      await tick();
      // Immediate scroll
      scrollToBottom();

      // Additional scroll after a short delay to ensure DOM is fully rendered
      setTimeout(() => {
        scrollToBottom();
      }, 50);
    }
  }

  // Check if user is near bottom of scroll container
  function checkIfAtBottom() {
    if (!messagesContainer) return true;

    const threshold = 100; // pixels from bottom
    const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    return distanceFromBottom < threshold;
  }

  // Handle scroll events to detect user scrolling up
  function handleScroll() {
    if (!messagesContainer) return;

    isAtBottom = checkIfAtBottom();

    // If user scrolled up from bottom, mark it
    if (!isAtBottom) {
      userScrolledUp = true;
    } else {
      userScrolledUp = false;
    }
  }

  // Auto-scroll to bottom only if user hasn't scrolled up
  $effect(() => {
    if (messages.length > 0 || Object.keys(streamingMessages).length > 0 || Object.keys(streamingThinkings).length > 0) {
      // For streaming messages, use requestAnimationFrame for smoother scrolling
      // For regular messages, use a small delay to ensure DOM is ready
      const scrollAction = () => {
        // Only auto-scroll if user is at bottom or hasn't manually scrolled up
        if (!userScrolledUp && isAtBottom) {
          scrollToBottom();
        }
      };

      // Use requestAnimationFrame for streaming messages, setTimeout for others
      if (Object.keys(streamingMessages).length > 0 || Object.keys(streamingThinkings).length > 0) {
        requestAnimationFrame(scrollAction);
      } else {
        setTimeout(scrollAction, 0);
      }
    }
  });

  function scrollToBottom() {
    if (messagesContainer) {
      // Get current scroll position before scrolling
      const wasAtBottom = isAtBottom;
      const maxScrollTop = messagesContainer.scrollHeight - messagesContainer.clientHeight;

      // Always scroll to the bottom
      messagesContainer.scrollTop = maxScrollTop;

      // Use requestAnimationFrame for smoother scrolling, especially for streaming
      requestAnimationFrame(() => {
        if (messagesContainer) {
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
      });

      // Update state only if we were already at bottom or this is a user action
      if (wasAtBottom || userScrolledUp === false) {
        userScrolledUp = false;
        isAtBottom = true;
      }
    }
  }

  async function handleSendMessage(event: { message: string }) {
    if (!conversation) {
      error = t('common.error');
      return;
    }

    if (!authService.isAuthenticated()) {
      error = t('common.error');
      return;
    }

    // Check if we have selected models or conversation model
    const modelsToUse = selectedModels.length > 0
      ? selectedModels
      : (selectedModelName || conversation.model
          ? [{
              providerName: selectedProviderName || conversation.provider_name || '',
              apiFormat: selectedApiFormat || conversation.api_format || '',
              model: selectedModelName || conversation.model || ''
            }]
          : []);

    if (modelsToUse.length === 0) {
      error = t('common.error');
      return;
    }

    const userMessage = event.message;
    error = null;

    // Reset scroll state when sending new message
    userScrolledUp = false;
    isAtBottom = true;

    console.log("ChatArea: Sending message to models:", modelsToUse);

    try {
      // Add user message to UI
      const userMsg: Message = {
        id: Date.now(),
        role: "user",
        content: userMessage,
        provider_name: modelsToUse[0].providerName || null,
        api_format: modelsToUse[0].apiFormat || null,
        model: null,
        input_tokens: null,
        output_tokens: null,
        created_at: new Date().toISOString(),
      };
      messages = [...messages, userMsg];

      // Scroll to user message immediately
      await tick();
      scrollToBottom();

      // Add to database
      console.log("ChatArea: Adding message to database:", {
        conversationId: conversation.id,
        role: "user",
        content: userMessage,
      });
      await chatService.addMessage(
        conversation.id,
        "user",
        userMessage,
        null!,
        undefined, // thinking
        undefined, // inputTokens
        undefined, // outputTokens
        undefined, // provider
        undefined, // apiFormat
      );

      // Initialize streaming state for all models
      streamingMessages = {};
      streamingThinkings = {};
      streamingCompleted = {};
      modelsToUse.forEach(model => {
        const modelKey = `${model.providerName}-${model.apiFormat}-${model.model}`;
        streamingMessages[modelKey] = "";
        streamingThinkings[modelKey] = "";
        streamingCompleted[modelKey] = false;
      });
      isLoading = true;

      // Send to all selected models
      const promises = modelsToUse.map(async (model) => {
        const modelKey = `${model.providerName}-${model.apiFormat}-${model.model}`;

        await chatService.sendChatMessage(
          {
            ...conversation!,
            provider_name: model.providerName,
            api_format: model.apiFormat,
            model: model.model,
            messages: messages,
          },
          userMessage,
          (chunk, thinking) => {
            if (chunk) {
              streamingMessages = {
                ...streamingMessages,
                [modelKey]: (streamingMessages[modelKey] || "") + chunk
              };
              // Scroll immediately when new chunk arrives for smooth streaming experience
              if (!userScrolledUp && isAtBottom) {
                scrollToBottom();
              }
            }
            if (thinking !== undefined) {
              streamingThinkings = {
                ...streamingThinkings,
                [modelKey]: thinking
              };
              // Scroll immediately when thinking content updates
              if (!userScrolledUp && isAtBottom) {
                scrollToBottom();
              }
            }
          },
          async (usage) => {
            // On complete for this model
            const assistantMessage = streamingMessages[modelKey] || "";
            const thinkingContent = streamingThinkings[modelKey];

            if (assistantMessage) {
              // Add to database (with thinking content and usage)
              try {
                await chatService.addMessage(
                  conversation!.id,
                  "assistant",
                  assistantMessage,
                  model.model,
                  thinkingContent || undefined,
                  usage?.input_tokens,
                  usage?.output_tokens,
                  model.providerName || undefined,
                  model.apiFormat || undefined,
                );
              } catch (err) {
                console.error("Failed to save assistant message:", err);
              }
              // Don't add to messages array - let loadMessages handle it
            }

            // Mark this stream as completed
            streamingCompleted = {
              ...streamingCompleted,
              [modelKey]: true
            };

            // Check if all models are done
            let allCompleted = true;
            for (const key in streamingCompleted) {
              if (!streamingCompleted[key]) {
                allCompleted = false;
                break;
              }
            }

            if (allCompleted) {
              // All streams completed - merge streaming messages into messages array and cleanup
              isLoading = false;

              // Convert streaming messages to Message objects and add to messages array
              const completedMessages: Message[] = [];
              for (const [modelKey, content] of Object.entries(streamingMessages)) {
                if (content) {
                  const [providerName, apiFormat, model] = modelKey.split('-');
                  const assistantMessage: Message = {
                    id: Date.now() + Math.random(), // Unique ID for streaming messages
                    role: "assistant",
                    content: content,
                    thinking: streamingThinkings[modelKey] || undefined,
                    model: model,
                    input_tokens: null, // Will be updated when usage data is available
                    output_tokens: null,
                    created_at: new Date().toISOString(),
                    provider_name: providerName,
                    api_format: apiFormat,
                  };
                  completedMessages.push(assistantMessage);
                }
              }

              // Add completed messages to the messages array
              if (completedMessages.length > 0) {
                messages = [...messages, ...completedMessages];
              }

              // Clear streaming state
              streamingMessages = {};
              streamingThinkings = {};
              streamingCompleted = {};

              // Scroll to bottom after adding completed messages
              await tick();
              scrollToBottom();
            }
          },
          (err) => {
            // Type assert to ExtendedError to access additional properties
            const extendedErr = err as ExtendedError;

            // Store detailed error information
            error = extendedErr.message;
            errorDetails = {
              message: extendedErr.message,
              status: extendedErr.status,
              statusText: extendedErr.statusText,
              details: extendedErr.details,
              timestamp: new Date().toISOString()
            };

            console.error("Chat message error for model", model.model, ":", err);

            // Mark this stream as completed (even though it errored)
            streamingCompleted = {
              ...streamingCompleted,
              [modelKey]: true
            };

            // Check if all models are done
            let allCompleted = true;
            for (const key in streamingCompleted) {
              if (!streamingCompleted[key]) {
                allCompleted = false;
                break;
              }
            }

            if (allCompleted) {
              // All streams completed (with or without errors) - cleanup
              isLoading = false;
              // Clear streaming state
              streamingMessages = {};
              streamingThinkings = {};
              streamingCompleted = {};
            }

            dispatch("error", { message: extendedErr.message });
          },
        );
      });

      await Promise.all(promises);
    } catch (err) {
      error = err instanceof Error ? err.message : t('common.error');
      streamingMessages = {};
      streamingThinkings = {};
      isLoading = false;
      dispatch("error", { message: error });
    }
  }

  function handleRetry(event: { message: any }) {
    handleSendMessage({ message: event.message.content });
  }

  async function handleEditMessage(event: { message: any; newContent: string }) {
    if (!conversation) return;

    const { message, newContent } = event;

    try {
      // Update the message in the local state
      messages = messages.map((msg) =>
        msg.id === message.id ? { ...msg, content: newContent } : msg
      );

      // Update conversation state
      if (conversation) {
        const updatedConversation = {
          ...conversation,
          messages: messages,
        };
        conversation = updatedConversation;
        dispatch("conversationUpdate", { conversation: updatedConversation });
      }

      // Retry the message (send it again with the new content)
      // Remove the old assistant message if it exists
      const messageIndex = messages.findIndex((msg) => msg.id === message.id);
      if (messageIndex !== -1 && messageIndex < messages.length - 1) {
        // Check if next message is an assistant message that was a response to this message
        const nextMessage = messages[messageIndex + 1];
        if (nextMessage && nextMessage.role === "assistant") {
          // Remove the assistant message that followed this user message
          messages = messages.filter((msg) => msg.id !== nextMessage.id);
        }
      }

      // Now resend with new content
      await handleSendMessage({ message: newContent });
    } catch (err) {
      error = err instanceof Error ? err.message : t('common.error');
      console.error("Failed to edit message:", err);
      dispatch("error", { message: error });
    }
  }
</script>

<div class="chat-area">
  <!-- Model Selector - Top Left Corner -->
  <div class="model-selector-container">
    <!-- Expand Sidebar Button - Only show when sidebar is collapsed -->
    {#if sidebarCollapsed}
      <button class="expand-sidebar-btn" onclick={() => dispatch("toggleSidebar")} title={t('chat.expandSidebar')}>
        <span class="hamburger-icon">
          <span class="line line-1"></span>
          <span class="line line-2"></span>
          <span class="line line-3"></span>
        </span>
      </button>
    {/if}

    <ModelSelector
      bind:selectedModels={selectedModels}
      bind:selectedProviderName={selectedProviderName}
      bind:selectedApiFormat={selectedApiFormat}
      bind:selectedModelName={selectedModelName}
      bind:selectedCategory={selectedCategory}
      on:modelSelected={handleModelSelected}
    />
  </div>

  <div
    class="messages-container"
    bind:this={messagesContainer}
    onscroll={handleScroll}
  >
    {#if !conversation}
      <div class="welcome">
        <h2>{t('chatArea.welcomeTitle')}</h2>
        <p>{t('chatArea.welcomeDescription')}</p>
      </div>
    {:else if isLoading && messages.length === 0}
      <div class="loading">
        <div class="spinner"></div>
        <p>{t('common.loading')}</p>
      </div>
    {:else if error}
      <div class="error-container">
        <div class="error-icon">⚠</div>
        <div class="error-content">
          <h3>{t('common.error')}</h3>
          <p class="error-message">{error}</p>

          <!-- Show error details in development or when available -->
          {#if errorDetails}
            <button
              class="toggle-details-btn"
              onclick={() => showErrorDetails = !showErrorDetails}
            >
              {showErrorDetails ? 'Hide' : 'Show'} Details
            </button>

            {#if showErrorDetails}
              <div class="error-details">
                {#if errorDetails.status}
                  <div class="error-detail-item">
                    <strong>Status:</strong>
                    <span>{errorDetails.status} {errorDetails.statusText}</span>
                  </div>
                {/if}

                <!-- New structured error fields from backend -->
                {#if errorDetails.type}
                  <div class="error-detail-item">
                    <strong>Error Type:</strong>
                    <span>{errorDetails.type}</span>
                  </div>
                {/if}

                {#if errorDetails.provider}
                  <div class="error-detail-item">
                    <strong>Provider:</strong>
                    <span>{errorDetails.provider}</span>
                  </div>
                {/if}

                {#if errorDetails.model}
                  <div class="error-detail-item">
                    <strong>Model:</strong>
                    <span>{errorDetails.model}</span>
                  </div>
                {/if}

                {#if errorDetails.request_id}
                  <div class="error-detail-item">
                    <strong>Request ID:</strong>
                    <span>{errorDetails.request_id}</span>
                  </div>
                {/if}

                {#if errorDetails.provider_status_code}
                  <div class="error-detail-item">
                    <strong>Provider Status:</strong>
                    <span>{errorDetails.provider_status_code}</span>
                  </div>
                {/if}

                {#if errorDetails.provider_url}
                  <div class="error-detail-item">
                    <strong>Provider URL:</strong>
                    <span class="error-url">{errorDetails.provider_url}</span>
                  </div>
                {/if}

                {#if errorDetails.status_code}
                  <div class="error-detail-item">
                    <strong>Backend Status:</strong>
                    <span>{errorDetails.status_code}</span>
                  </div>
                {/if}

                <!-- Network error category (ssl_error, dns_error, timeout_error, etc.) -->
                {#if errorDetails.category}
                  <div class="error-detail-item">
                    <strong>Error Category:</strong>
                    <span class="error-category {errorDetails.category}">{errorDetails.category}</span>
                  </div>
                {/if}

                <!-- User-friendly hint for network errors -->
                {#if errorDetails.hint}
                  <div class="error-detail-item">
                    <strong>Hint:</strong>
                    <span class="error-hint">{errorDetails.hint}</span>
                  </div>
                {/if}

                {#if errorDetails.details}
                  <div class="error-detail-item">
                    <strong>Full Details:</strong>
                    <pre>{JSON.stringify(errorDetails.details, null, 2)}</pre>
                  </div>
                {/if}

                {#if errorDetails.timestamp}
                  <div class="error-detail-item">
                    <strong>Time:</strong>
                    <span>{new Date(errorDetails.timestamp).toLocaleString()}</span>
                  </div>
                {/if}
              </div>
            {/if}
          {/if}
        </div>

        <div class="error-actions">
          <button class="retry-btn" onclick={loadMessages}>
            {t('messageBubble.retry')}
          </button>
        </div>
      </div>
    {:else if messages.length === 0}
      <div class="empty">
        <p>{t('chatArea.startConversation')}</p>
      </div>
    {:else}
      {@const messageGroups = getMessageGroups()}
      {@const lastGroupIndex = messageGroups.length - 1}
      {#each messageGroups as group, index}
        {@const isLastGroup = index === lastGroupIndex}
        {#if group.userMessage}
          <MessageBubble
            message={group.userMessage}
            showModel={false}
            showTokens={true}
            providerName={group.userMessage.provider_name ?? selectedProviderName ?? (conversation?.provider_name ?? null)}
            apiFormat={group.userMessage.api_format ?? selectedApiFormat ?? (conversation?.api_format ?? null)}
            onretry={handleRetry}
            onedit={handleEditMessage}
          />
        {/if}

        <!-- Streaming messages for the last group only (if user message exists and streaming is active) -->
        {#if isLastGroup && group.userMessage && Object.keys(streamingMessages).length > 0}
          <div class="assistant-messages-grid">
            {#each Object.entries(streamingMessages) as [modelKey, content]}
              {@const [providerName, apiFormat, model] = modelKey.split('-')}
              <div class="assistant-message-column">
                <MessageBubble
                  message={{
                    id: Date.now(),
                    role: "assistant",
                    content: content,
                    thinking: streamingThinkings[modelKey] || undefined,
                    model: model,
                    input_tokens: null,
                    output_tokens: null,
                    created_at: new Date().toISOString(),
                    provider_name: providerName,
                    api_format: apiFormat,
                  } as any}
                  isStreaming={true}
                  showModel={true}
                  showTokens={false}
                  providerName={providerName}
                  apiFormat={apiFormat}
                />
              </div>
            {/each}
          </div>
        {/if}

        {#if group.assistantMessages.length > 0}
          <div class="assistant-messages-grid">
            {#each group.assistantMessages as assistantMessage}
              {@const isStreaming = `${assistantMessage.provider_name}-${assistantMessage.api_format}-${assistantMessage.model}` in streamingMessages}
              {#if !isStreaming}
                <div class="assistant-message-column">
                  <MessageBubble
                    message={assistantMessage}
                    showModel={true}
                    showTokens={true}
                    providerName={assistantMessage.provider_name ?? selectedProviderName ?? (conversation?.provider_name ?? null)}
                    apiFormat={assistantMessage.api_format ?? selectedApiFormat ?? (conversation?.api_format ?? null)}
                    onretry={handleRetry}
                    onedit={handleEditMessage}
                  />
                </div>
              {/if}
            {/each}
          </div>
        {/if}
      {/each}
    {/if}
  </div>

  <!-- Scroll to bottom button -->
  {#if userScrolledUp && !isAtBottom}
    <button
      class="scroll-to-bottom"
      onclick={scrollToBottom}
      title={t('chatArea.scrollToBottom')}
    >
      ↓
    </button>
  {/if}

  <div class="input-container">
    {#if conversation}
      <MessageInput
        disabled={isLoading}
        placeholder={t('messageInput.placeholder')}
        hasMessages={messages.length > 0}
        onsend={handleSendMessage}
      />
    {:else}
      <div class="no-conversation-prompt">
        <p>{t('chatArea.startConversation')}</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    height: 100%;
    position: relative;
  }

  .model-selector-container {
    flex-shrink: 0;
    background: transparent;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    padding-left: 1rem;
  }

  .expand-sidebar-btn {
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

  .expand-sidebar-btn:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
    transform: scale(1.05);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .expand-sidebar-btn:active {
    transform: scale(0.98);
  }

  .expand-sidebar-btn .hamburger-icon {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 18px;
    height: 14px;
  }

  .expand-sidebar-btn .hamburger-icon .line {
    display: block;
    height: 2px;
    background: currentColor;
    border-radius: 1px;
    transition: all 0.2s ease;
  }

  .expand-sidebar-btn .hamburger-icon .line-1 {
    width: 100%;
  }

  .expand-sidebar-btn .hamburger-icon .line-2 {
    width: 65%;
    align-self: flex-end;
  }

  .expand-sidebar-btn .hamburger-icon .line-3 {
    width: 100%;
  }

  .expand-sidebar-btn:hover .hamburger-icon .line {
    background: var(--text-primary);
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 2rem;
    padding-bottom: 2rem;
    background: linear-gradient(
      to bottom,
      var(--bg-secondary) 0%,
      var(--bg-primary) 100%
    );
    min-height: 0;
    scroll-behavior: smooth;
  }

  .input-container {
    flex-shrink: 0;
    background: var(--bg-primary);
    border-top: 1px solid var(--border-color);
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  }

  /* Custom scrollbar */
  .messages-container::-webkit-scrollbar {
    width: 8px;
  }

  .messages-container::-webkit-scrollbar-track {
    background: transparent;
  }

  .messages-container::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
    transition: background 0.2s;
  }

  .messages-container::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
  }

  /* Empty states */
  .welcome,
  .loading,
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    color: var(--text-secondary);
    padding: 2rem;
  }

  .welcome h2 {
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.75rem;
    background: linear-gradient(135deg, var(--primary-color), #6ba5ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .welcome p {
    font-size: 1rem;
    opacity: 0.8;
  }

  .empty {
    opacity: 0.7;
  }

  .empty p {
    font-size: 1rem;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--border-color);
    border-top: 3px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  /* Enhanced error display */
  .error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 2rem;
    text-align: center;
    color: var(--text-secondary);
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 1rem;
    margin: 2rem;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
  }

  .error-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    color: #ef4444;
  }

  .error-content {
    width: 100%;
  }

  .error-content h3 {
    color: #ef4444;
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  .error-message {
    color: var(--text-primary);
    font-size: 1rem;
    margin-bottom: 1rem;
    word-break: break-word;
  }

  .toggle-details-btn {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.875rem;
    margin-bottom: 1rem;
    transition: all 0.2s;
  }

  .toggle-details-btn:hover {
    background: rgba(239, 68, 68, 0.2);
    transform: translateY(-1px);
  }

  .error-details {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    padding: 1rem;
    margin-top: 1rem;
    text-align: left;
    max-height: 300px;
    overflow-y: auto;
  }

  .error-detail-item {
    margin-bottom: 0.75rem;
    font-size: 0.875rem;
  }

  .error-detail-item:last-child {
    margin-bottom: 0;
  }

  .error-detail-item strong {
    color: var(--text-primary);
    display: block;
    margin-bottom: 0.25rem;
  }

  .error-detail-item span,
  .error-detail-item pre {
    color: var(--text-secondary);
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.8125rem;
    word-break: break-word;
    white-space: pre-wrap;
  }

  .error-url {
    color: var(--primary-color);
    text-decoration: none;
    word-break: break-all;
  }

  .error-url:hover {
    text-decoration: underline;
    color: var(--primary-hover);
  }

  .error-category {
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
  }

  .error-category.ssl_error,
  .error-category.tls_error {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  .error-category.dns_error,
  .error-category.hostname_error {
    background: rgba(245, 158, 11, 0.1);
    color: #f59e0b;
  }

  .error-category.timeout_error {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
  }

  .error-category.connection_error {
    background: rgba(156, 163, 175, 0.1);
    color: #6b7280;
  }

  .error-hint {
    color: var(--primary-color);
    font-style: italic;
    padding: 0.25rem;
    background: rgba(79, 70, 229, 0.05);
    border-radius: 0.25rem;
    border-left: 3px solid var(--primary-color);
    display: block;
    margin-top: 0.25rem;
  }

  .error-actions {
    margin-top: 1.5rem;
  }

  .error-actions .retry-btn {
    padding: 0.625rem 1.5rem;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .error-actions .retry-btn:hover {
    background: var(--primary-hover);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
  }

  /* Legacy error styles (deprecated - kept for compatibility) */

  .scroll-to-bottom {
    position: absolute;
    bottom: 7rem;
    left: 50%;
    width: 36px;
    height: 36px;
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.25rem;
    font-weight: bold;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transition: all 0.3s ease;
    z-index: 10;
    animation: fadeInUp 0.3s ease-out;
  }

  .scroll-to-bottom:hover {
    background: var(--bg-tertiary);
    color: var(--primary-color);
    border-color: var(--primary-color);
    transform: translateY(-2px) scale(1.05);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
  }

  .scroll-to-bottom:active {
    transform: translateY(0) scale(0.98);
    background: var(--bg-tertiary);
    color: var(--primary-color);
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .no-conversation-prompt {
    padding: 2rem;
    text-align: center;
    color: var(--text-secondary);
    font-size: 1rem;
    opacity: 0.7;
  }

  /* Multi-model cards layout */
  .assistant-messages-grid {
    display: flex;
    gap: 1rem;
    overflow-x: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border-color) transparent;
    padding-bottom: 0.5rem;
    margin-bottom: 2rem;
  }

  .assistant-messages-grid::-webkit-scrollbar {
    height: 6px;
  }

  .assistant-messages-grid::-webkit-scrollbar-track {
    background: transparent;
  }

  .assistant-messages-grid::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;
  }

  .assistant-messages-grid::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
  }

  .assistant-message-column {
    flex: 0 0 calc(50% - 0.5rem);
    min-width: 300px;
    display: flex;
    flex-direction: column;
  }

  /* Tablet styles */
  @media (max-width: 1024px) {
    .messages-container {
      padding: 1.5rem;
    }
  }

  /* Mobile styles */
  @media (max-width: 768px) {
    .messages-container {
      padding: 1rem;
      background: var(--bg-secondary);
    }

    .welcome h2 {
      font-size: 1.5rem;
    }

    .welcome p {
      font-size: 0.9rem;
    }

    .messages-container::-webkit-scrollbar {
      width: 4px;
    }

    .model-selector-container {
      padding: 0.75rem;
      gap: 0.5rem;
    }

    .expand-sidebar-btn {
      width: 36px;
      height: 36px;
    }

    .scroll-to-bottom {
      width: 32px;
      height: 32px;
      font-size: 1.125rem;
    }
  }

  /* Small mobile styles */
  @media (max-width: 480px) {
    .messages-container {
      padding: 0.75rem;
    }

    .welcome h2 {
      font-size: 1.25rem;
    }

    .scroll-to-bottom {
      width: 30px;
      height: 30px;
      font-size: 1rem;
    }
  }
</style>
