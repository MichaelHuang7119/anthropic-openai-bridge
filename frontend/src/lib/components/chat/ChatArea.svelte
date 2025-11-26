<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { tick } from 'svelte';
  import MessageBubble from './MessageBubble.svelte';
  import MessageInput from './MessageInput.svelte';
  import { chatService, type ConversationDetail, type Message } from '$services/chatService';
  import { theme } from '$stores/theme';
  import { authService } from '$services/auth';

  export let conversation: ConversationDetail | null = null;
  export let selectedModel: any = null;

  const dispatch = createEventDispatcher<{
    conversationUpdate: { conversation: ConversationDetail };
    error: { message: string };
  }>();

  let messages: Message[] = [];
  let isLoading = false;
  let streamingMessage: string | null = null;
  let error: string | null = null;
  let messagesContainer: HTMLDivElement;

  // Load messages when conversation changes
  $: if (conversation) {
    loadMessages();
  } else {
    messages = [];
  }

  async function loadMessages() {
    if (!conversation) return;

    try {
      isLoading = true;
      const detail = await chatService.getConversation(conversation.id);
      messages = detail.messages || [];
    } catch (err) {
      error = err instanceof Error ? err.message : '加载消息失败';
      console.error('Failed to load messages:', err);
    } finally {
      isLoading = false;
      // Scroll to bottom after loading
      await tick();
      scrollToBottom();
    }
  }

  // Auto-scroll to bottom when new messages arrive
  $: if (messages.length > 0 || streamingMessage) {
    tick().then(() => scrollToBottom());
  }

  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  async function handleSendMessage(event: { message: string }) {
    if (!conversation || !authService.getApiKey()) {
      error = '请选择对话并配置API Key';
      return;
    }

    if (!selectedModel) {
      error = '请选择模型';
      return;
    }

    const userMessage = event.message;
    error = null;

    try {
      // Add user message to UI
      const userMsg: Message = {
        id: Date.now(),
        role: 'user',
        content: userMessage,
        model: conversation.model || null
      };
      messages = [...messages, userMsg];

      // Add to database
      await chatService.addMessage(
        conversation.id,
        'user',
        userMessage,
        conversation.model || null
      );

      // Send to AI
      streamingMessage = '';
      isLoading = true;

      await chatService.sendChatMessage(
        {
          ...conversation,
          messages: messages
        },
        userMessage,
        (chunk) => {
          streamingMessage += chunk;
        },
        async () => {
          // On complete
          const assistantMessage = streamingMessage;
          streamingMessage = null;
          isLoading = false;

          if (assistantMessage) {
            // Add assistant message to UI
            const assistantMsg: Message = {
              id: Date.now() + 1,
              role: 'assistant',
              content: assistantMessage,
              model: conversation.model || null
            };
            messages = [...messages, assistantMsg];

            // Add to database
            await chatService.addMessage(
              conversation.id,
              'assistant',
              assistantMessage,
              conversation.model || null
            );

            // Update conversation
            const updatedConversation = await chatService.getConversation(conversation.id);
            conversation = updatedConversation;
            dispatch('conversationUpdate', { conversation });
          }
        },
        (err) => {
          error = err.message;
          streamingMessage = null;
          isLoading = false;
          dispatch('error', { message: err.message });
        }
      );
    } catch (err) {
      error = err instanceof Error ? err.message : '发送消息失败';
      streamingMessage = null;
      isLoading = false;
      dispatch('error', { message: error });
    }
  }

  function handleRetry(event: { message: any }) {
    handleSendMessage({ message: event.message.content });
  }

  // Expose sendMessage for parent component
  export { handleSendMessage as sendMessage };
</script>

<div class="chat-area">
  <div class="messages-container" bind:this={messagesContainer}>
    {#if !conversation}
      <div class="welcome">
        <h2>欢迎使用 AI 聊天</h2>
        <p>选择左侧的对话开始聊天，或创建新对话</p>
      </div>
    {:else if isLoading && messages.length === 0}
      <div class="loading">
        <div class="spinner" />
        <p>加载消息中...</p>
      </div>
    {:else if error}
      <div class="error">
        <p>{error}</p>
        <button on:click={loadMessages}>重试</button>
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
          on:retry={handleRetry}
        />
      {/each}

      {#if streamingMessage !== null}
        <MessageBubble
          message={{
            id: Date.now(),
            role: 'assistant',
            content: streamingMessage,
            model: conversation.model || null
          }}
          isStreaming={true}
          showModel={true}
          showTokens={false}
        />
      {/if}
    {/if}
  </div>

  <div class="input-container">
    {#if conversation}
      <MessageInput
        disabled={isLoading}
        placeholder="输入消息..."
        on:send={handleSendMessage}
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
    height: 100%;
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    background: var(--bg-secondary);
  }

  .messages-container::-webkit-scrollbar {
    width: 6px;
  }

  .messages-container::-webkit-scrollbar-track {
    background: transparent;
  }

  .messages-container::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;
  }

  .welcome, .loading, .empty, .error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    color: var(--text-secondary);
  }

  .welcome h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border-color);
    border-top: 3px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .error button {
    margin-top: 1rem;
  }

  .input-container {
    background: var(--bg-primary);
    border-top: 1px solid var(--border-color);
  }

  .no-conversation-prompt {
    padding: 2rem;
    text-align: center;
    color: var(--text-secondary);
    font-size: 0.95rem;
  }

  @media (max-width: 768px) {
    .messages-container {
      padding: 1rem;
    }

    .welcome h2 {
      font-size: 1.25rem;
    }
  }
</style>
