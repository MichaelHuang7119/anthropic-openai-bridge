<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { theme } from '$stores/theme';

  export let disabled = false;
  export let placeholder = '输入消息...';

  const dispatch = createEventDispatcher<{
    send: { message: string };
  }>();

  let message = '';
  let textarea: HTMLTextAreaElement;

  // Auto-resize textarea
  $: if (textarea && message) {
    autoResize();
  }

  function autoResize() {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  }

  function handleKeydown(event: KeyboardEvent) {
    // Enter to send, Shift+Enter for new line
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  function handleSend() {
    const trimmed = message.trim();
    if (!trimmed || disabled) return;

    dispatch('send', { message: trimmed });
    message = '';

    // Reset textarea height
    if (textarea) {
      textarea.style.height = 'auto';
    }
  }

  function handleInput(event: Event) {
    message = (event.target as HTMLTextAreaElement).value;
  }
</script>

<div class="message-input">
  <textarea
    bind:this={textarea}
    class="input-textarea"
    {placeholder}
    bind:value={message}
    on:keydown={handleKeydown}
    on:input={handleInput}
    rows="1"
    {disabled}
  />
  <button
    class="send-button"
    class:disabled={!message.trim() || disabled}
    on:click={handleSend}
    disabled={!message.trim() || disabled}
    title="发送 (Enter)"
  >
  </button>
</div>

<div class="input-hints">
  <span class="hint">Enter 发送，Shift + Enter 换行</span>
</div>

<style>
  .message-input {
    display: flex;
    gap: 0.75rem;
    align-items: flex-end;
    padding: 1rem;
    background: var(--bg-primary);
    border-top: 1px solid var(--border-color);
  }

  .input-textarea {
    flex: 1;
    padding: 0.75rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    background: var(--bg-secondary);
    color: var(--text-primary);
    font-size: 0.95rem;
    line-height: 1.5;
    resize: none;
    max-height: 200px;
    transition: all 0.2s;
  }

  .input-textarea:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
  }

  .input-textarea:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .send-button {
    padding: 0.75rem;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 0.75rem;
    cursor: pointer;
    transition: all 0.2s;
    min-width: 44px;
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
  }

  .send-button:hover:not(.disabled) {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }

  .send-button:active:not(.disabled) {
    transform: translateY(0);
  }

  .send-button.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .send-button::before {
    content: '➤';
    transform: rotate(90deg);
    display: inline-block;
  }

  .input-hints {
    padding: 0 1rem 1rem;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    text-align: center;
  }

  .hint {
    opacity: 0.7;
  }

  @media (max-width: 768px) {
    .message-input {
      padding: 0.75rem;
      gap: 0.5rem;
    }

    .input-textarea {
      padding: 0.625rem 0.875rem;
      font-size: 0.9rem;
    }

    .send-button {
      min-width: 40px;
      min-height: 40px;
      padding: 0.625rem;
    }
  }
</style>
