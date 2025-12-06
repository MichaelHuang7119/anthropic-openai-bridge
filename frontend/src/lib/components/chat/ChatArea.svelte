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
    selectedModel = $bindable(null),
    selectedProvider = $bindable(""),
    selectedApiFormat = $bindable(""),
    selectedModelName = $bindable(""),
    selectedCategory = $bindable("middle"),
    sidebarCollapsed = $bindable(false),
  }: {
    conversation: ConversationDetail | null;
    selectedModel: any;
    selectedProvider: string;
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

  let messages: Message[] = $state([]);
  let isLoading = $state(false);
  let streamingMessage: string | null = $state(null);
  let streamingThinking: string | null = $state(null);
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
    if (messages.length > 0 || streamingMessage || streamingThinking) {
      // For streaming messages, use requestAnimationFrame for smoother scrolling
      // For regular messages, use a small delay to ensure DOM is ready
      const scrollAction = () => {
        // Only auto-scroll if user is at bottom or hasn't manually scrolled up
        if (!userScrolledUp && isAtBottom) {
          scrollToBottom();
        }
      };

      // Use requestAnimationFrame for streaming messages, setTimeout for others
      if (streamingMessage || streamingThinking) {
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

    if (!selectedModelName && !conversation.model) {
      error = t('common.error');
      return;
    }

    // Use currently selected model configuration instead of conversation's saved config
    const useProvider = selectedProvider || conversation.provider_name || null;
    const useApiFormat = selectedApiFormat || conversation.api_format || null;
    const useModel = selectedModelName || conversation.model || null;

    if (!useModel) {
      error = t('common.error');
      return;
    }

    const userMessage = event.message;
    error = null;

    // Reset scroll state when sending new message
    userScrolledUp = false;
    isAtBottom = true;

    console.log("ChatArea: Sending message with config:", {
      provider: useProvider,
      apiFormat: useApiFormat,
      model: useModel,
    });

    try {
      // Add user message to UI
      const userMsg: Message = {
        id: Date.now(),
        role: "user",
        content: userMessage,
        provider_name: useProvider,
        api_format: useApiFormat,
        model: useModel,
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
        model: useModel,
        provider_name: useProvider,
        api_format: useApiFormat,
      });
      await chatService.addMessage(
        conversation.id,
        "user",
        userMessage,
        useModel,
        undefined, // thinking
        undefined, // inputTokens
        undefined, // outputTokens
        useProvider || undefined,
        useApiFormat || undefined,
      );

      // Send to AI with current selected configuration
      streamingMessage = "";
      streamingThinking = "";
      isLoading = true;

      await chatService.sendChatMessage(
        {
          ...conversation,
          provider_name: useProvider,
          api_format: useApiFormat,
          model: useModel,
          messages: messages,
        },
        userMessage,
        (chunk, thinking) => {
          if (chunk) {
            streamingMessage += chunk;
            // Scroll immediately when new chunk arrives for smooth streaming experience
            if (!userScrolledUp && isAtBottom) {
              scrollToBottom();
            }
          }
          if (thinking !== undefined) {
            streamingThinking = thinking;
            // Scroll immediately when thinking content updates
            if (!userScrolledUp && isAtBottom) {
              scrollToBottom();
            }
          }
        },
        async (usage) => {
          // On complete
          const assistantMessage = streamingMessage;
          const thinkingContent = streamingThinking;
          streamingMessage = null;
          streamingThinking = null;
          isLoading = false;

          if (assistantMessage) {
            // Add assistant message to UI (with thinking content and usage)
            const assistantMsg: Message = {
              id: Date.now() + 1,
              role: "assistant",
              content: assistantMessage,
              thinking: thinkingContent || undefined,
              provider_name: useProvider,
              api_format: useApiFormat,
              model: useModel,
              input_tokens: usage?.input_tokens || null,
              output_tokens: usage?.output_tokens || null,
              created_at: new Date().toISOString(),
            };
            messages = [...messages, assistantMsg];

            // Add to database (with thinking content and usage)
            const savedMessage = await chatService.addMessage(
              conversation!.id,
              "assistant",
              assistantMessage,
              useModel,
              thinkingContent || undefined,
              usage?.input_tokens,
              usage?.output_tokens,
              useProvider || undefined,
              useApiFormat || undefined,
            );

            // Update the temporary message with the actual saved message data - preserve frontend config
            if (savedMessage && conversation) {
              console.log("=== DEBUG CONFIG TRACKING ===");
              console.log("Frontend sent to database:", {
                provider: useProvider,
                apiFormat: useApiFormat,
                model: useModel
              });
              console.log("Database returned savedMessage:", savedMessage);
              console.log("Original temporary assistantMsg:", assistantMsg);

              // Create updated message with explicit typing
              const updatedMessage: Message = {
                id: savedMessage.id,
                role: 'assistant',
                content: assistantMsg.content,
                model: assistantMsg.model || useModel || savedMessage.model || null,
                thinking: assistantMsg.thinking || savedMessage.thinking || undefined,
                input_tokens: savedMessage.input_tokens !== undefined ? savedMessage.input_tokens : null,
                output_tokens: savedMessage.output_tokens !== undefined ? savedMessage.output_tokens : null,
                created_at: savedMessage.created_at || new Date().toISOString(),
                // Explicitly preserve frontend configuration
                provider_name: assistantMsg.provider_name || useProvider || null,
                api_format: assistantMsg.api_format || useApiFormat || null,
              };

              messages = messages.map((msg) =>
                msg.id === assistantMsg.id ? updatedMessage : msg
              );

              // Verify the final configuration
              const finalUpdatedMsg = messages.find(m => m.id === assistantMsg.id);
              console.log("Final message after update:", {
                provider_name: finalUpdatedMsg?.provider_name,
                api_format: finalUpdatedMsg?.api_format,
                model: finalUpdatedMsg?.model,
                id: finalUpdatedMsg?.id,
                created_at: finalUpdatedMsg?.created_at
              });
              console.log("========================");

              // Update conversation messages - with type safety
              const updatedConversation: ConversationDetail = {
                ...conversation,
                messages: messages,
                // Ensure conversation config matches current selection if changed
                provider_name: useProvider || conversation.provider_name || null,
                api_format: useApiFormat || conversation.api_format || null,
                model: useModel || conversation.model || null,
              };

              conversation = updatedConversation;
              dispatch("conversationUpdate", { conversation: updatedConversation });
            }
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

          console.error("Chat message error:", err);

          streamingMessage = null;
          streamingThinking = null;
          isLoading = false;
          dispatch("error", { message: extendedErr.message });
        },
      );
    } catch (err) {
      error = err instanceof Error ? err.message : t('common.error');
      streamingMessage = null;
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
      bind:selectedModel={selectedModel}
      bind:selectedProvider={selectedProvider}
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
      {#each messages as message}
        <MessageBubble
          {message}
          showModel={true}
          showTokens={true}
          providerName={message.provider_name ?? selectedProvider ?? (conversation?.provider_name ?? null)}
          apiFormat={message.api_format ?? selectedApiFormat ?? (conversation?.api_format ?? null)}
          onretry={handleRetry}
          onedit={handleEditMessage}
        />
      {/each}

      {#if streamingMessage !== null || streamingThinking !== null}
        <MessageBubble
          message={{
            id: Date.now(),
            role: "assistant",
            content: streamingMessage || "",
            thinking: streamingThinking || undefined,
            model: (selectedModel?.model || selectedModelName) || conversation?.model || null,
            input_tokens: null,
            output_tokens: null,
            created_at: new Date().toISOString(),
          } as any}
          isStreaming={true}
          showModel={true}
          showTokens={false}
          providerName={selectedProvider}
          apiFormat={selectedApiFormat}
        />
      {/if}
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
