<script lang="ts">
  import { marked } from 'marked';
  import { createEventDispatcher } from 'svelte';
  import { theme } from '$stores/theme';

  interface Message {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    model?: string | null;
    input_tokens?: number | null;
    output_tokens?: number | null;
    created_at?: string;
  }

  export let message: Message;
  export let isStreaming = false;
  export let showModel = false;
  export let showTokens = false;

  const dispatch = createEventDispatcher<{
    retry: { message: Message };
  }>();

  // Render markdown content
  $: renderedContent = message.content ? marked.parse(message.content) : '';

  // Format timestamp
  function formatTime(timestamp?: string): string {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '';
    }
  }

  // Format tokens
  function formatTokens(tokens: number | null | undefined): string | null {
    if (!tokens && tokens !== 0) return null;
    return tokens.toLocaleString();
  }

  function handleRetry() {
    dispatch('retry', { message });
  }
</script>

<div class="message-bubble {message.role}">
  <div class="message-header">
    <span class="role-label">
      {message.role === 'user' ? '你' : '助手'}
    </span>
    {#if showModel && message.model}
      <span class="model-info">
        {message.model}
      </span>
    {/if}
    {#if showTokens && message.input_tokens !== undefined && message.output_tokens !== undefined}
      <span class="token-info">
        输入: {formatTokens(message.input_tokens)} |
        输出: {formatTokens(message.output_tokens)} |
        总计: {formatTokens((message.input_tokens || 0) + (message.output_tokens || 0))}
      </span>
    {/if}
    {#if message.created_at}
      <span class="timestamp">
        {formatTime(message.created_at)}
      </span>
    {/if}
  </div>

  <div class="message-content">
    <div class="content-text">
      {#if isStreaming}
        <div class="typing-animation">{message.content}</div>
        <span class="cursor"></span>
      {:else}
        {@html renderedContent}
      {/if}
    </div>

    {#if message.role === 'user'}
      <div class="message-actions">
        <button class="retry-btn" on:click={handleRetry} title="重新发送">
        </button>
      </div>
    {/if}
  </div>

  {#if message.role === 'assistant' && message.content}
    <div class="message-actions">
      <button class="copy-btn" on:click={() => navigator.clipboard.writeText(message.content)} title="复制">
      </button>
    </div>
  {/if}
</div>

<style>
  .message-bubble {
    margin-bottom: 1.5rem;
    display: flex;
    flex-direction: column;
    animation: slideIn 0.3s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(0.5rem);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .message-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
    font-size: 0.75rem;
  }

  .role-label {
    font-weight: 600;
    color: var(--primary-color);
  }

  .model-info {
    color: var(--text-secondary);
    font-family: 'Courier New', monospace;
  }

  .token-info {
    color: var(--text-tertiary);
    font-size: 0.7rem;
  }

  .timestamp {
    color: var(--text-tertiary);
    font-size: 0.7rem;
    margin-left: auto;
  }

  .message-content {
    display: flex;
    gap: 0.75rem;
    position: relative;
  }

  .content-text {
    flex: 1;
    padding: 1rem;
    border-radius: 0.75rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    font-size: 0.95rem;
    line-height: 1.6;
  }

  .message-bubble.user .content-text {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
  }

  .message-bubble.user .role-label {
    color: var(--primary-color);
  }

  .message-bubble.user .content-text :global(*) {
    color: white !important;
  }

  .content-text :global(h1), .content-text :global(h2), .content-text :global(h3) {
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    color: var(--text-primary);
  }

  .content-text :global(code) {
    background: rgba(99, 102, 241, 0.1);
    color: #6366f1;
    padding: 0.125rem 0.25rem;
    border-radius: 0.25rem;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
  }

  .content-text :global(pre) {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    padding: 1rem;
    overflow-x: auto;
    margin: 0.75rem 0;
  }

  .content-text :global(pre code) {
    background: none;
    color: inherit;
    padding: 0;
  }

  .content-text :global(blockquote) {
    border-left: 3px solid var(--primary-color);
    padding-left: 1rem;
    margin: 0.75rem 0;
    color: var(--text-secondary);
    font-style: italic;
  }

  .content-text :global(ul), .content-text :global(ol) {
    margin: 0.75rem 0;
    padding-left: 1.5rem;
  }

  .content-text :global(li) {
    margin: 0.25rem 0;
  }

  .typing-animation {
    white-space: pre-wrap;
  }

  .cursor {
    display: inline-block;
    width: 2px;
    height: 1em;
    background: var(--primary-color);
    animation: blink 1s infinite;
    vertical-align: text-bottom;
    margin-left: 2px;
  }

  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }

  .message-actions {
    opacity: 0;
    transition: opacity 0.3s;
  }

  .message-bubble:hover .message-actions {
    opacity: 1;
  }

  .retry-btn, .copy-btn {
    padding: 0.25rem;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    transition: color 0.2s;
    font-size: 0.75rem;
  }

  .retry-btn:hover, .copy-btn:hover {
    color: var(--primary-color);
  }

  .retry-btn::before {
    content: '↻';
    font-size: 1rem;
  }

  .copy-btn::before {
    content: '复制';
  }

  .copy-btn.copied::before {
    content: '已复制';
  }

  @media (max-width: 768px) {
    .message-header {
      flex-wrap: wrap;
    }

    .model-info, .token-info {
      display: none;
    }

    .message-content {
      flex-direction: column;
    }

    .message-actions {
      opacity: 1;
      align-self: flex-end;
      margin-top: 0.5rem;
    }
  }
</style>
