<script lang="ts">
  import { marked } from "marked";
  import { tStore, language } from "$stores/language";

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
    onedit,
  }: {
    message: Message;
    isStreaming?: boolean;
    showModel?: boolean;
    showTokens?: boolean;
    providerName?: string | null;
    apiFormat?: string | null;
    onretry?: (event: { message: Message }) => void;
    onedit?: (event: { message: Message; newContent: string }) => void;
  } = $props();

  // State for thinking collapse/expand
  let thinkingExpanded = $state(false);
  let copied = $state(false);
  let contentContainer: HTMLDivElement;

  // State for editing
  let isEditing = $state(false);
  let editContent = $state('');
  let editTextarea: HTMLTextAreaElement | undefined = $state();

  // 获取翻译函数和当前语言
  const t = $derived($tStore);
  let currentLang = $state('en-US');

  // 订阅语言变化
  $effect(() => {
    const unsubscribe = language.subscribe((lang) => {
      currentLang = lang;
    });
    return unsubscribe;
  });

  // Track which code blocks are copied
  let copiedCodeBlocks = $state<Set<string>>(new Set());

  // Rendered markdown content
  let renderedContent = $state('');
  let renderedThinking = $state('');

  // Escape HTML to prevent inline HTML rendering
  function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Create custom renderer for code blocks with copy buttons
  function createRenderer() {
    const renderer = new marked.Renderer();

    renderer.code = ({ text, lang }: { text: string; lang?: string }) => {
      const language = lang || 'text';
      const id = `code-${Math.random().toString(36).substr(2, 9)}`;
      const escapedCode = text;

      return `
        <div class="code-block-container">
          <div class="code-block-header" style="display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 1rem; background: var(--bg-secondary); border-bottom: 1px solid var(--border-color);">
            <span class="code-language" style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-right: auto; flex-shrink: 0;">${language}</span>
            <button class="copy-code-btn" data-code-id="${id}" data-code="${encodeURIComponent(escapedCode)}" title="${t('messageBubble.copy')}" onclick="handleCodeCopy(event)" style="display: flex; align-items: center; gap: 0.375rem; padding: 0.375rem 0.625rem; background: rgba(79, 70, 229, 0.1); border: 1px solid rgba(79, 70, 229, 0.3); border-radius: 0.375rem; color: var(--primary-color); cursor: pointer; font-size: 0.75rem; transition: all 0.2s ease; line-height: 1; opacity: 0.95; font-weight: 500; flex-shrink: 0;">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span class="copy-text">${t('messageBubble.copy')}</span>
              <span class="copied-text" style="display: none;">${t('messageBubble.copied')}</span>
            </button>
          </div>
          <pre><code class="language-${language}" id="${id}">${escapedCode}</code></pre>
        </div>
      `;
    };

    return renderer;
  }

  // Render markdown content with custom renderer
  $effect(() => {
    // Expose handleCodeCopy to window for inline event handlers
    (window as any).handleCodeCopy = handleCodeCopy;

    const renderMarkdown = async () => {
      if (message.content) {
        const renderer = createRenderer();
        // Escape HTML to prevent inline HTML rendering
        // This prevents CSS styles and HTML structures from being rendered as actual DOM elements
        const safeContent = escapeHtml(message.content);
        renderedContent = await marked.parse(safeContent, {
          renderer,
          breaks: false,
          gfm: true
        });
      } else {
        renderedContent = "";
      }
    };
    renderMarkdown();
  });

  $effect(() => {
    const renderThinking = async () => {
      if (message.thinking) {
        const renderer = createRenderer();
        // Escape HTML to prevent inline HTML rendering for thinking content as well
        const safeThinking = escapeHtml(message.thinking);
        renderedThinking = await marked.parse(safeThinking, {
          renderer,
          breaks: false,
          gfm: true
        });
      } else {
        renderedThinking = "";
      }
    };
    renderThinking();
  });

  // Store previous values
  let previousContent = $state('');
  let previousThinking = $state<string | undefined>('');

  // Reset copied state when content changes
  $effect(() => {
    if (message.content !== previousContent) {
      copiedCodeBlocks = new Set();
      previousContent = message.content;
    }
    if ((message.thinking || '') !== (previousThinking || '')) {
      copiedCodeBlocks = new Set();
      previousThinking = message.thinking;
    }
  });

  // Format timestamp to short time (HH:MM)
  function formatTime(timestamp?: string): string {
    if (!timestamp) return "";
    try {
      const date = parseDate(timestamp);
      if (isNaN(date.getTime())) return "";

      return date.toLocaleTimeString(currentLang, {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  }

  // Format timestamp to full detailed time
  function formatFullTime(timestamp?: string): string {
    if (!timestamp) return "";
    try {
      const date = parseDate(timestamp);
      if (isNaN(date.getTime())) return "";

      return date.toLocaleString(currentLang, {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        weekday: "long",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return "";
    }
  }

  // Helper function to parse date
  function parseDate(timestamp: string): Date {
    // 如果已经是 ISO 格式或包含 T，直接解析
    if (timestamp.includes("T")) {
      return new Date(timestamp);
    }
    // 如果格式是 "YYYY-MM-DD HH:MM:SS"，转换为 ISO 格式
    else if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(timestamp)) {
      return new Date(timestamp.replace(" ", "T") + "Z");
    }
    // 其他格式尝试直接解析
    else {
      return new Date(timestamp);
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

  function handleEdit() {
    isEditing = true;
    editContent = message.content;
  }

  function handleSendEdit() {
    if (editContent.trim() && editContent !== message.content) {
      onedit?.({ message, newContent: editContent });
      isEditing = false;
    }
  }

  function handleCancelEdit() {
    isEditing = false;
    editContent = message.content;
  }

  function handleCopy() {
    navigator.clipboard.writeText(message.content);
    copied = true;
    setTimeout(() => copied = false, 2000);
  }

  function handleCodeCopy(event: MouseEvent) {
    const button = event.target as HTMLElement;
    const copyBtn = button.closest('.copy-code-btn') as HTMLButtonElement;
    if (!copyBtn) return;

    const codeData = copyBtn.getAttribute('data-code');
    if (!codeData) return;

    try {
      const code = decodeURIComponent(codeData);
      navigator.clipboard.writeText(code);

      // Update button UI immediately
      const originalText = copyBtn.querySelector('.copy-text') as HTMLElement;
      const copiedText = copyBtn.querySelector('.copied-text') as HTMLElement;
      if (originalText && copiedText) {
        originalText.style.display = 'none';
        copiedText.style.display = 'inline';
        copyBtn.classList.add('copied');
      }

      // Mark this specific code block as copied
      const codeId = copyBtn.getAttribute('data-code-id');
      if (codeId) {
        copiedCodeBlocks = new Set(copiedCodeBlocks).add(codeId);
        setTimeout(() => {
          copiedCodeBlocks = new Set(
            Array.from(copiedCodeBlocks).filter(id => id !== codeId)
          );
          // Reset button UI
          if (originalText && copiedText) {
            originalText.style.display = 'inline';
            copiedText.style.display = 'none';
            copyBtn.classList.remove('copied');
          }
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  }
</script>

<div class="message-bubble {message.role}">
  <div class="message-header">
    <span class="role-label">
      {message.role === "user" ? t('messageBubble.user') : t('messageBubble.assistant')}
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
        {t('messageBubble.inputTokens')}: {formatTokens(message.input_tokens)} | {t('messageBubble.outputTokens')}: {formatTokens(
          message.output_tokens,
        )} | {t('messageBubble.totalTokens')}: {formatTokens(
          (message.input_tokens || 0) + (message.output_tokens || 0),
        )}
      </span>
    {/if}
    {#if message.created_at}
      <span class="timestamp" title={formatFullTime(message.created_at)}>
        {formatTime(message.created_at)}
      </span>
    {/if}
  </div>

  {#if message.thinking}
    <div class="thinking-section">
      <button
        class="thinking-toggle"
        onclick={() => (thinkingExpanded = !thinkingExpanded)}
        title={thinkingExpanded ? t('messageBubble.hideThinking') : t('messageBubble.showThinking')}
      >
        <span class="toggle-icon {thinkingExpanded ? 'expanded' : ''}">▶</span>
        <span class="thinking-label">{t('messageBubble.thinking')}</span>
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
            <!-- Marked.parse() sanitizes the markdown content -->
            <!-- eslint-disable-next-line svelte/no-at-html-tags -->
            {@html renderedThinking}
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <div class="message-content">
    <div class="content-text" bind:this={contentContainer}>
      {#if isEditing}
        <div class="edit-mode">
          <textarea
            bind:this={editTextarea}
            bind:value={editContent}
            class="edit-textarea"
            rows="3"
            placeholder={t('messageInput.placeholder')}
            onkeydown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendEdit();
              }
              if (e.key === 'Escape') {
                handleCancelEdit();
              }
            }}
          ></textarea>
          <div class="edit-actions">
            <button class="edit-send-btn" onclick={handleSendEdit}>
              {t('messageInput.send')}
            </button>
            <button class="edit-cancel-btn" onclick={handleCancelEdit}>
              {t('messageBubble.cancel')}
            </button>
          </div>
        </div>
      {:else if isStreaming}
        <div class="typing-animation">{message.content}</div>
        <span class="cursor"></span>
      {:else}
        <!-- Marked.parse() sanitizes the markdown content -->
        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
        {@html renderedContent}
      {/if}
    </div>

    {#if message.role === "user"}
      <div class="message-actions">
        {#if isEditing}
          <button class="edit-btn sending" disabled>
            {t('messageInput.send')}
          </button>
        {:else}
          <button class="edit-btn" onclick={handleEdit} title={t('messageBubble.edit')}>
          </button>
          <button class="retry-btn" onclick={handleRetry} title={t('messageBubble.retry')}>
          </button>
        {/if}
      </div>
    {/if}
  </div>

  {#if message.role === "assistant" && message.content}
    <div class="message-actions">
      <button
        class="copy-btn"
        class:copied
        onclick={handleCopy}
        title={t('messageBubble.copy')}
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

  .message-bubble.user {
    align-items: flex-end;
  }

  .message-bubble.assistant {
    align-items: flex-start;
  }

  .message-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.625rem;
    font-size: 0.8rem;
    flex-wrap: wrap;
    max-width: 100%;
  }

  .message-bubble.user .message-header {
    justify-content: flex-end;
    flex-direction: row-reverse;
  }

  .role-label {
    font-weight: 600;
    font-size: 0.85rem;
  }

  .message-bubble.user .role-label {
    color: var(--primary-color);
  }

  .message-bubble.assistant .role-label {
    color: var(--success-color, #28a745);
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

  .message-bubble.user .timestamp {
    margin-left: 0;
    margin-right: auto;
  }

  .code-block-container {
    position: relative;
    margin: 0.75rem 0;
    border-radius: 0.5rem;
    overflow: hidden;
    border: 1px solid var(--border-color);
    background: var(--bg-tertiary);
    width: 100%;
    box-sizing: border-box;
  }

  .code-block-header {
    position: relative;
    padding: 0.5rem 4rem;  /* 增加左右内边距，为两端元素留出空间 */
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
  }

  .code-language {
    position: absolute;
    left: 1rem;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: var(--bg-secondary);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
  }

  .copy-code-btn {
    position: absolute;
    right: 1rem;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.625rem;
    background: rgba(79, 70, 229, 0.1);
    border: 1px solid rgba(79, 70, 229, 0.3);
    border-radius: 0.375rem;
    color: var(--primary-color);
    cursor: pointer;
    font-size: 0.75rem;
    transition: all 0.2s ease;
    line-height: 1;
    opacity: 0.95;
    font-weight: 500;
  }

  .copy-code-btn:hover {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    opacity: 1;
  }

  .copy-code-btn:active {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25);
  }

  .copy-text,
  .copied-text {
    font-size: 0.75rem;
  }

  .copy-code-btn.copied {
    background: var(--success-color, #10b981);
    color: white;
    border-color: var(--success-color, #10b981);
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    transform: translateY(-2px);
    font-weight: 600;
  }

  .copy-code-btn.copied:hover {
    background: var(--success-color, #0ea371);
    border-color: var(--success-color, #0ea371);
  }

  :global([data-theme="dark"]) .copy-code-btn {
    background: rgba(79, 70, 229, 0.2);
    border: 1px solid rgba(79, 70, 229, 0.4);
    color: #a5b4fc;
  }

  :global([data-theme="dark"]) .copy-code-btn.copied {
    background: #059669;
    border-color: #059669;
    box-shadow: 0 4px 16px rgba(5, 150, 105, 0.4);
  }

  :global([data-theme="dark"]) .copy-code-btn.copied:hover {
    background: #047857;
    border-color: #047857;
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
    max-width: 100%;
    overflow-wrap: break-word;
    word-wrap: break-word;
  }

  .thinking-content :global(code) {
    background: rgba(90, 156, 255, 0.15);
    color: #5a9cff;
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

  .message-bubble.user .message-content {
    justify-content: flex-end;
  }

  .message-bubble.assistant .message-content {
    justify-content: flex-start;
  }

  .content-text {
    padding: 1.25rem;
    border-radius: 1rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    font-size: 0.95rem;
    line-height: 1.7;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    transition: all 0.2s;
    /* Ensure text wraps properly within container */
    word-wrap: break-word;
    overflow-wrap: anywhere;
    /* Prevent horizontal overflow */
    max-width: 100%;
    /* Ensure content is properly contained */
    box-sizing: border-box;
  }

  .message-bubble.assistant .content-text {
    flex: 1;
  }

  .message-bubble.assistant .content-text {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
  }

  .message-bubble.user .content-text {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    flex: 1;
    max-width: 85%;
    margin-left: auto;
    text-align: left;
    transition: all 0.2s ease;
  }

  .message-bubble.user .content-text:hover {
    border: 1px solid var(--primary-color);
    box-shadow: 0 4px 12px rgba(90, 156, 255, 0.4);
  }

  .message-bubble.assistant .content-text:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  }

  .message-bubble.user .content-text :global(*) {
    color: inherit;
  }

  .content-text :global(h1),
  .content-text :global(h2),
  .content-text :global(h3) {
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    color: var(--text-primary);
    /* Prevent headings from overflowing */
    max-width: 100%;
    overflow-wrap: break-word;
  }

  .content-text :global(code) {
    background: rgba(90, 156, 255, 0.15);
    color: #5a9cff;
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
    margin: 0;
    /* Ensure pre tags also respect container boundaries */
    max-width: 100%;
    /* Remove top padding since header covers that area */
    padding-top: 3rem;
  }

  .content-text :global(pre code) {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
    font-size: 0.875rem;
    line-height: 1.6;
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
    max-width: 100%;
    overflow-wrap: break-word;
  }

  .content-text :global(ul),
  .content-text :global(ol) {
    margin: 0.75rem 0;
    padding-left: 1.5rem;
    max-width: 100%;
  }

  .content-text :global(li) {
    margin: 0.25rem 0;
    max-width: 100%;
    overflow-wrap: break-word;
  }

  .content-text :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
    font-size: 0.875rem;
    overflow-x: auto;
    display: block;
    max-width: 100%;
  }

  .content-text :global(table thead) {
    background: var(--bg-tertiary);
    border-bottom: 2px solid var(--border-color);
  }

  .content-text :global(table th) {
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-color);
  }

  .content-text :global(table td) {
    padding: 0.625rem 1rem;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-primary);
  }

  .content-text :global(table tbody tr) {
    transition: background-color 0.2s;
  }

  .content-text :global(table tbody tr:hover) {
    background: var(--bg-tertiary);
  }

  .content-text :global(table tbody tr:last-child td) {
    border-bottom: none;
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
    align-self: flex-end;
    margin-top: 0.5rem;
  }

  .message-bubble.assistant .message-actions {
    align-self: flex-start;
  }

  .message-bubble:hover .message-actions {
    opacity: 1;
  }

  .retry-btn,
  .copy-btn,
  .edit-btn {
    padding: 0.25rem;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    transition: color 0.2s;
    font-size: 0.75rem;
  }

  .retry-btn:hover,
  .copy-btn:hover,
  .edit-btn:hover {
    color: var(--primary-color);
  }

  .retry-btn::before {
    content: "↻";
    font-size: 1rem;
  }

  .copy-btn::before {
    content: t('messageBubble.copy');
  }

  .copy-btn.copied::before {
    content: t('messageBubble.copied');
  }

  .edit-btn::before {
    content: "✎";
    font-size: 0.9rem;
  }

  .edit-btn.sending {
    opacity: 0.5;
    cursor: default;
  }

  .edit-btn.sending::before {
    content: "✓";
    font-size: 1rem;
  }

  /* Edit mode styles */
  .edit-mode {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .edit-textarea {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 0.95rem;
    font-family: inherit;
    line-height: 1.6;
    resize: vertical;
    min-height: 80px;
    transition: border-color 0.2s;
  }

  .edit-textarea:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(90, 156, 255, 0.1);
  }

  .edit-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .edit-send-btn,
  .edit-cancel-btn {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
    font-weight: 500;
  }

  .edit-send-btn {
    background: var(--primary-color);
    color: white;
  }

  .edit-send-btn:hover {
    background: var(--primary-color-dark, #3b82f6);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(90, 156, 255, 0.3);
  }

  .edit-cancel-btn {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
  }

  .edit-cancel-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
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
    }

    .content-text :global(table) {
      font-size: 0.8125rem;
    }

    .content-text :global(table th),
    .content-text :global(table td) {
      padding: 0.5rem 0.625rem;
    }

    .code-language {
      left: 0.75rem;
      font-size: 0.7rem;
    }

    .copy-code-btn {
      right: 0.75rem;
      padding: 0.25rem 0.5rem;
      font-size: 0.6875rem;
      opacity: 1; /* 在移动端始终显示复制按钮 */
    }

    .content-text :global(pre) {
      padding: 1rem;
    }

    .edit-actions {
      gap: 0.375rem;
    }

    .edit-send-btn,
    .edit-cancel-btn {
      padding: 0.375rem 0.75rem;
      font-size: 0.8125rem;
    }
  }
</style>
