<script lang="ts">
  // import { theme } from "$stores/theme";

  let { disabled = false, placeholder = "输入消息...", onsend }: {
    disabled?: boolean;
    placeholder?: string;
    onsend?: (event: { message: string }) => void;
  } = $props();

  let message = $state("");
  let textarea: HTMLTextAreaElement | undefined = $state(undefined);
  let showPrompts = $state(true);

  // Preset prompts
  const presetPrompts = [
    { icon: "💡", text: "解释这个概念", prompt: "请详细解释一下" },
    { icon: "📝", text: "写一段代码", prompt: "请帮我写一段代码来实现" },
    { icon: "🔍", text: "分析问题", prompt: "请帮我分析一下这个问题：" },
    { icon: "✨", text: "优化建议", prompt: "请给出优化建议：" },
    { icon: "📚", text: "总结要点", prompt: "请总结以下内容的要点：" },
    { icon: "🤔", text: "头脑风暴", prompt: "让我们一起头脑风暴，关于" },
  ];

  // Auto-resize textarea
  $effect(() => {
    if (textarea && message) {
      autoResize();
    }
  });

  function autoResize() {
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px";
  }

  function handleKeydown(event: KeyboardEvent) {
    // Enter to send, Shift+Enter for new line
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  function handleSend() {
    const trimmed = message.trim();
    if (!trimmed || disabled) return;

    console.log("MessageInput: Sending message:", trimmed);
    onsend?.({ message: trimmed });
    message = "";

    // Reset textarea height
    if (textarea) {
      textarea.style.height = "auto";
    }
  }

  function handleInput(event: Event) {
    message = (event.target as HTMLTextAreaElement).value;
  }

  function handlePromptClick(prompt: string) {
    message = prompt;
    // Hide prompts after selection
    showPrompts = false;
    // Focus textarea
    textarea?.focus();
    // Auto-resize
    setTimeout(() => autoResize(), 0);
  }

  // Show prompts when input is empty
  $effect(() => {
    if (message.trim() === "") {
      showPrompts = true;
    }
  });
</script>

<div class="input-container">
  {#if showPrompts && !message.trim()}
    <div class="preset-prompts">
      <div class="prompts-header">
        <span class="prompts-title">💬 快速开始</span>
      </div>
      <div class="prompts-scroll-container">
        <div class="prompts-scroll">
          <div class="prompts-grid">
            {#each presetPrompts as preset}
              <button
                class="prompt-button"
                onclick={() => handlePromptClick(preset.prompt)}
                {disabled}
              >
                <span class="prompt-icon">{preset.icon}</span>
                <span class="prompt-text">{preset.text}</span>
              </button>
            {/each}
          </div>
        </div>
      </div>
    </div>
  {/if}

  <div class="message-input">
    <textarea
      bind:this={textarea}
      class="input-textarea"
      {placeholder}
      bind:value={message}
      onkeydown={handleKeydown}
      oninput={handleInput}
      rows="1"
      {disabled}
    ></textarea>
    <button
      class="send-button"
      class:disabled={!message.trim() || disabled}
      onclick={handleSend}
      disabled={!message.trim() || disabled}
      title="发送 (Enter)"
    >
      ➤
    </button>
  </div>

  <div class="input-hints">
    <span class="hint">Enter 发送，Shift + Enter 换行</span>
  </div>
</div>

<style>
  .input-container {
    background: var(--bg-primary);
  }

  .preset-prompts {
    padding: 1rem 1rem 0.5rem;
    border-top: 1px solid var(--border-color);
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .prompts-header {
    margin-bottom: 0.5rem;
  }

  .prompts-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .prompts-scroll-container {
    position: relative;
    margin: 0 -0.5rem;
  }

  .prompts-scroll {
    display: flex;
    gap: 0.5rem;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 0.25rem 0.5rem;
    scroll-behavior: smooth;
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE/Edge */
  }

  .prompts-scroll::-webkit-scrollbar {
    display: none; /* Chrome/Safari */
  }

  .prompts-grid {
    display: flex;
    gap: 0.5rem;
    min-width: 100%;
  }

  .prompt-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 0.875rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .prompt-button:hover:not(:disabled) {
    background: var(--bg-tertiary);
    border-color: var(--primary-color);
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .prompt-button:active:not(:disabled) {
    transform: translateY(0);
  }

  .prompt-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .prompt-icon {
    font-size: 1.125rem;
    flex-shrink: 0;
  }

  .prompt-text {
    flex: 1;
  }

  .message-input {
    display: flex;
    gap: 0.75rem;
    align-items: flex-end;
    padding: 1rem;
    background: var(--bg-primary);
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
    border: 2px solid var(--primary-color);
    border-radius: 0.75rem;
    cursor: pointer;
    transition: all 0.2s;
    min-width: 44px;
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    transform: rotate(90deg);
  }

  .send-button:hover:not(.disabled) {
    background: white;
    color: var(--primary-color);
    border-color: var(--primary-color);
  }

  .send-button:active:not(.disabled) {
    transform: rotate(90deg) scale(0.95);
  }

  .send-button.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .input-hints {
    padding: 0 1rem 0.75rem;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    text-align: center;
    background: var(--bg-primary);
  }

  .hint {
    opacity: 0.7;
  }

  @media (max-width: 768px) {
    .preset-prompts {
      padding: 0.75rem 0.75rem 0.5rem;
    }

    .prompt-button {
      padding: 0.5rem 0.75rem;
      font-size: 0.8rem;
    }

    .prompt-icon {
      font-size: 1rem;
    }

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
