<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import { tick } from "svelte";
  import MessageBubble from "./MessageBubble.svelte";
  import MessageInput from "./MessageInput.svelte";
  import {
    chatService,
    type ConversationDetail,
    type Message,
  } from "$services/chatService";
  import { theme } from "$stores/theme";
  import { authService } from "$services/auth";

  export let conversation: ConversationDetail | null = null;
  export let selectedModel: any = null;
  export let selectedProvider: string = "";
  export let selectedApiFormat: string = "";

  const dispatch = createEventDispatcher<{
    conversationUpdate: { conversation: ConversationDetail };
    error: { message: string };
  }>();

  let messages: Message[] = [];
  let isLoading = false;
  let streamingMessage: string | null = null;
  let streamingThinking: string | null = null;
  let error: string | null = null;
  let messagesContainer: HTMLDivElement;
  let userScrolledUp = false; // Track if user manually scrolled up
  let isAtBottom = true; // Track if user is at bottom

  // Load messages when conversation changes
  $: if (conversation) {
    console.log("ChatArea: conversation changed:", conversation);
    loadMessages();
  } else {
    // console.log("ChatArea: no conversation");
    messages = [];
  }

  async function loadMessages() {
    if (!conversation) return;

    try {
      isLoading = true;
      const detail = await chatService.getConversation(conversation.id);
      messages = detail.messages || [];
    } catch (err) {
      error = err instanceof Error ? err.message : "加载消息失败";
      console.error("Failed to load messages:", err);
    } finally {
      isLoading = false;
      // Scroll to bottom after loading
      userScrolledUp = false;
      await tick();
      scrollToBottom();
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
  $: if (messages.length > 0 || streamingMessage || streamingThinking) {
    tick().then(() => {
      // Only auto-scroll if user is at bottom or hasn't manually scrolled up
      if (!userScrolledUp && isAtBottom) {
        scrollToBottom();
      }
    });
  }

  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
      userScrolledUp = false;
      isAtBottom = true;
    }
  }

  async function handleSendMessage(event: { message: string }) {
    if (!conversation) {
      error = "请选择对话";
      return;
    }

    if (!authService.isAuthenticated()) {
      error = "请先登录";
      return;
    }

    if (!selectedModel) {
      error = "请选择模型";
      return;
    }

    // Use currently selected model configuration instead of conversation's saved config
    const useProvider = selectedProvider || conversation.provider_name || null;
    const useApiFormat = selectedApiFormat || conversation.api_format || null;
    const useModel = selectedModel || conversation.model || null;

    if (!useModel) {
      error = "请选择模型";
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
      };
      messages = [...messages, userMsg];

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
        useProvider,
        useApiFormat,
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
          }
          if (thinking !== undefined) {
            streamingThinking = thinking;
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
              conversation.id,
              "assistant",
              assistantMessage,
              useModel,
              thinkingContent || undefined,
              usage?.input_tokens,
              usage?.output_tokens,
              useProvider,
              useApiFormat,
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
          error = err.message;
          streamingMessage = null;
          streamingThinking = null;
          isLoading = false;
          dispatch("error", { message: err.message });
        },
      );
    } catch (err) {
      error = err instanceof Error ? err.message : "发送消息失败";
      streamingMessage = null;
      isLoading = false;
      dispatch("error", { message: error });
    }
  }

  function handleRetry(event: { message: any }) {
    handleSendMessage({ message: event.message.content });
  }

  // Expose sendMessage for parent component
  export { handleSendMessage as sendMessage };
</script>

<div class="chat-area">
  <div
    class="messages-container"
    bind:this={messagesContainer}
    onscroll={handleScroll}
  >
    {#if !conversation}
      <div class="welcome">
        <h2>欢迎使用 AI 聊天</h2>
        <p>选择左侧的对话开始聊天，或创建新对话</p>
      </div>
    {:else if isLoading && messages.length === 0}
      <div class="loading">
        <div class="spinner"></div>
        <p>加载消息中...</p>
      </div>
    {:else if error}
      <div class="error">
        <p>{error}</p>
        <button onclick={loadMessages}>重试</button>
      </div>
    {:else if messages.length === 0}
      <div class="empty">
        <p>暂无消息，开始对话吧！</p>
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
        />
      {/each}

      {#if streamingMessage !== null || streamingThinking !== null}
        <MessageBubble
          message={{
            id: Date.now(),
            role: "assistant",
            content: streamingMessage || "",
            thinking: streamingThinking || undefined,
            provider_name: selectedProvider,
            api_format: selectedApiFormat,
            model: selectedModel || conversation.model || null,
          }}
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
      title="滚动到底部"
    >
      ↓
    </button>
  {/if}

  <div class="input-container">
    {#if conversation}
      <MessageInput
        disabled={isLoading}
        placeholder="输入消息..."
        onsend={handleSendMessage}
      />
    {:else}
      <div class="no-conversation-prompt">
        <p>请选择或创建一个对话</p>
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
  .empty,
  .error {
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
    background: linear-gradient(135deg, var(--primary-color), #8b5cf6);
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

  .error {
    color: #ef4444;
  }

  .error button {
    margin-top: 1rem;
    padding: 0.625rem 1.25rem;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.95rem;
    transition: all 0.2s;
  }

  .error button:hover {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }

  .scroll-to-bottom {
    position: absolute;
    bottom: 6rem;
    right: 2rem;
    width: 44px;
    height: 44px;
    background: var(--primary-color);
    color: white;
    border: 2px solid var(--primary-color);
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.5rem;
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
    background: white;
    color: var(--primary-color);
    border-color: var(--primary-color);
    transform: translateY(-2px) scale(1.05);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
  }

  .scroll-to-bottom:active {
    transform: translateY(0) scale(0.98);
    background: white;
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

    .scroll-to-bottom {
      bottom: 5rem;
      right: 1rem;
      width: 40px;
      height: 40px;
      font-size: 1.25rem;
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
      bottom: 4.5rem;
      right: 0.75rem;
      width: 36px;
      height: 36px;
      font-size: 1.125rem;
    }
  }
</style>
