<script lang="ts">
  import { marked } from "marked";
  import { theme } from "$stores/theme";

  interface Message {
    id: number;
    role: "user" | "assistant";
    content: string;
    thinking?: string;
    model?: string | null;
    input_tokens?: number | null;
    output_tokens?: number | null;
    created_at?: string;
  }

  let {
    message,
    isStreaming = false,
    showModel = false,
    showTokens = false,
    providerName = null,
    apiFormat = null,
    onretry,
  }: {
    message: Message;
    isStreaming?: boolean;
    showModel?: boolean;
    showTokens?: boolean;
    providerName?: string | null;
    apiFormat?: string | null;
    onretry?: (event: { message: Message }) => void;
  } = $props();

  // State for thinking collapse/expand
  let thinkingExpanded = $state(false);

  // Render markdown content
  let renderedContent = $derived(
    message.content ? marked.parse(message.content) : "",
  );
  let renderedThinking = $derived(
    message.thinking ? marked.parse(message.thinking) : "",
  );

  // Format timestamp - 直接解析本地时间
  function formatTime(timestamp?: string): string {
    if (!timestamp) return "";
    try {
      // 直接当作本地时间解析
      const date = new Date(timestamp + ' GMT+0800');
      return date.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Asia/Shanghai",
      });
    } catch {
      return timestamp || "";
    }
  }

  // Format tokens
  function formatTokens(tokens: number | null | undefined): string | null {
    if (!tokens && tokens !== 0) return null;
    return tokens.toLocaleString();
  }

  function handleRetry() {
    onretry?.({ message });
  }
</script>

<div class="message-bubble {message.role}">
  <div class="message-header">
    <span class="role-label">
      {message.role === "user" ? "你" : "助手"}
    </span>
    {#if showModel && (providerName || message.model)}
      <span class="model-info">
        {#if providerName}
          <span class="provider-name">{providerName}</span>
          {#if apiFormat}
            <span class="api-format">({apiFormat})</span>
          {/if}
          {#if message.model}
            <span class="model-separator">/</span>
          {/if}
        {/if}
        {#if message.model}
          <span class="model-name">{message.model}</span>
        {/if}
      </span>
    {/if}
    {#if showTokens && message.input_tokens !== undefined && message.output_tokens !== undefined}
      <span class="token-info">
        输入: {formatTokens(message.input_tokens)} | 输出: {formatTokens(
          message.output_tokens,
        )} | 总计: {formatTokens(
          (message.input_tokens || 0) + (message.output_tokens || 0),
        )}
      </span>
    {/if}
    {#if message.created_at}
      <span class="timestamp">
        {formatTime(message.created_at)}
      </span>
    {/if}
  </div>

  {#if message.thinking}
    <div class="thinking-section">
      <button
        class="thinking-toggle"
        onclick={() => (thinkingExpanded = !thinkingExpanded)}
        title={thinkingExpanded ? "收起思考过程" : "展开思考过程"}
      >
        <span class="toggle-icon {thinkingExpanded ? 'expanded' : ''}">▶</span>
        <span class="thinking-label">思考过程</span>
        <span class="thinking-preview">
          {thinkingExpanded
            ? ""
            : message.thinking.slice(0, 50) +
              (message.thinking.length > 50 ? "..." : "")}
        </span>
      </button>

      {#if thinkingExpanded}
        <div class="thinking-content">
          {#if isStreaming}
            <div class="typing-animation">{message.thinking}</div>
            <span class="cursor"></span>
          {:else}
            {@html renderedThinking}
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <div class="message-content">
    <div class="content-text">
      {#if isStreaming}
        <div class="typing-animation">{message.content}</div>
        <span class="cursor"></span>
      {:else}
        {@html renderedContent}
      {/if}
    </div>

    {#if message.role === "user"}
      <div class="message-actions">
        <button class="retry-btn" onclick={handleRetry} title="重新发送">
        </button>
      </div>
    {/if}
  </div>

  {#if message.role === "assistant" && message.content}
    <div class="message-actions">
      <button
        class="copy-btn"
        onclick={() => navigator.clipboard.writeText(message.content)}
        title="复制"
      >
      </button>
    </div>
  {/if}
</div>

<style>
  .message-bubble {
    margin-bottom: 2rem;
    display: flex;
    flex-direction: column;
    animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    max-width: 100%;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(1rem);
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
    margin-bottom: 0.625rem;
    font-size: 0.8rem;
    flex-wrap: wrap;
  }

  .role-label {
    font-weight: 600;
    color: var(--primary-color);
    font-size: 0.85rem;
  }

  .model-info {
    color: var(--text-secondary);
    font-family: "Courier New", monospace;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .provider-name {
    color: var(--primary-color);
    font-weight: 600;
  }

  .api-format {
    color: var(--text-tertiary);
    font-size: 0.65rem;
    font-style: italic;
  }

  .model-separator {
    color: var(--text-tertiary);
    margin: 0 0.15rem;
  }

  .model-name {
    color: var(--text-secondary);
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

  .thinking-section {
    margin-bottom: 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    background: var(--bg-tertiary);
    overflow: hidden;
  }

  .thinking-toggle {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 0.875rem;
    color: var(--text-primary);
    transition: background 0.2s;
    text-align: left;
  }

  .thinking-toggle:hover {
    background: rgba(99, 102, 241, 0.05);
  }

  .toggle-icon {
    display: inline-block;
    transition: transform 0.2s;
    color: var(--primary-color);
    font-size: 0.75rem;
  }

  .toggle-icon.expanded {
    transform: rotate(90deg);
  }

  .thinking-label {
    font-weight: 600;
    color: var(--primary-color);
  }

  .thinking-preview {
    flex: 1;
    color: var(--text-tertiary);
    font-size: 0.8rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .thinking-content {
    padding: 1rem;
    border-top: 1px solid var(--border-color);
    background: var(--bg-secondary);
    font-size: 0.875rem;
    line-height: 1.6;
    color: var(--text-secondary);
    animation: slideDown 0.2s ease-out;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      max-height: 0;
    }
    to {
      opacity: 1;
      max-height: 1000px;
    }
  }

  .thinking-content :global(p) {
    margin: 0.5rem 0;
  }

  .thinking-content :global(code) {
    background: rgba(99, 102, 241, 0.1);
    color: #6366f1;
    padding: 0.125rem 0.25rem;
    border-radius: 0.25rem;
    font-family: "Courier New", monospace;
    font-size: 0.8rem;
  }

  .message-content {
    display: flex;
    gap: 0.75rem;
    position: relative;
  }

  .content-text {
    flex: 1;
    padding: 1.25rem;
    border-radius: 1rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    font-size: 0.95rem;
    line-height: 1.7;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    transition: all 0.2s;
  }

  .content-text:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  }

  .message-bubble.user .content-text {
    background: linear-gradient(135deg, var(--primary-color), #8b5cf6);
    color: white;
    border-color: transparent;
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
  }

  .message-bubble.user .content-text:hover {
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
  }

  .message-bubble.user .role-label {
    color: var(--primary-color);
  }

  .message-bubble.user .content-text :global(*) {
    color: white !important;
  }

  .content-text :global(h1),
  .content-text :global(h2),
  .content-text :global(h3) {
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    color: var(--text-primary);
  }

  .content-text :global(code) {
    background: rgba(99, 102, 241, 0.1);
    color: #6366f1;
    padding: 0.125rem 0.25rem;
    border-radius: 0.25rem;
    font-family: "Courier New", monospace;
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

  .content-text :global(ul),
  .content-text :global(ol) {
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
    0%,
    50% {
      opacity: 1;
    }
    51%,
    100% {
      opacity: 0;
    }
  }

  .message-actions {
    opacity: 0;
    transition: opacity 0.3s;
  }

  .message-bubble:hover .message-actions {
    opacity: 1;
  }

  .retry-btn,
  .copy-btn {
    padding: 0.25rem;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    transition: color 0.2s;
    font-size: 0.75rem;
  }

  .retry-btn:hover,
  .copy-btn:hover {
    color: var(--primary-color);
  }

  .retry-btn::before {
    content: "↻";
    font-size: 1rem;
  }

  .copy-btn::before {
    content: "复制";
  }

  .copy-btn.copied::before {
    content: "已复制";
  }

  @media (max-width: 768px) {
    .message-header {
      flex-wrap: wrap;
    }

    .model-info,
    .token-info {
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
