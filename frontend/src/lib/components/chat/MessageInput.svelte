<script lang="ts">
  import { tStore } from "$stores/language";

  let { disabled = false, placeholder, hasMessages = false, onsend }: {
    disabled?: boolean;
    placeholder?: string;
    hasMessages?: boolean;
    onsend?: (event: { message: string }) => void;
  } = $props();

  // 获取翻译函数
  const t = $derived($tStore);

  let message = $state("");
  let textarea: HTMLTextAreaElement | undefined = $state(undefined);
  let showPrompts = $state(!hasMessages);
  let selectedPromptIndex = $state<number | null>(null);

  let promptsScrollContainer: HTMLDivElement | undefined = $state(undefined);

  // Preset prompts - 使用翻译函数生成
  const presetPrompts = $derived([
    { icon: "💡", text: t('messageInput.prompts.explain'), prompt: t('messageInput.prompts.explainPrompt') },
    { icon: "📝", text: t('messageInput.prompts.code'), prompt: t('messageInput.prompts.codePrompt') },
    { icon: "🔍", text: t('messageInput.prompts.analyze'), prompt: t('messageInput.prompts.analyzePrompt') },
    { icon: "✨", text: t('messageInput.prompts.suggest'), prompt: t('messageInput.prompts.suggestPrompt') },
    { icon: "📚", text: t('messageInput.prompts.summarize'), prompt: t('messageInput.prompts.summarizePrompt') },
    { icon: "🤔", text: t('messageInput.prompts.brainstorm'), prompt: t('messageInput.prompts.brainstormPrompt') },
  ]);

  // Auto-resize textarea
  $effect(() => {
    if (textarea && message) {
      autoResize();
    }
  });

  // 设置默认占位符
  $effect(() => {
    if (!placeholder) {
      placeholder = t('messageInput.placeholder');
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

  function handlePromptClick(prompt: string, index: number) {
    // Only allow selection if this prompt is the center-selected one
    // OR if nothing is selected yet (allows first selection)
    if (selectedPromptIndex === null || index === selectedPromptIndex) {
      message = prompt;
      selectedPromptIndex = index;
      // Hide prompts after selection
      showPrompts = false;
      // Focus textarea
      textarea?.focus();
      // Auto-resize
      setTimeout(() => autoResize(), 0);
    }
  }

  // Scroll to center the selected prompt
  function scrollToPrompt(index: number) {
    if (!promptsScrollContainer) return;

    const promptElements = promptsScrollContainer.querySelectorAll('.prompt-button');
    const targetElement = promptElements[index] as HTMLElement;

    if (targetElement) {
      const containerHeight = promptsScrollContainer.clientHeight;
      const elementHeight = targetElement.clientHeight;
      const targetPosition = targetElement.offsetTop - (containerHeight / 2 - elementHeight / 2);

      promptsScrollContainer.scrollTo({
        top: targetPosition,
        behavior: 'smooth'
      });
    }
  }

  // Handle scroll and auto-select the centered prompt
  function handleScroll() {
    if (!promptsScrollContainer) return;

    const containerHeight = promptsScrollContainer.clientHeight;
    const scrollTop = promptsScrollContainer.scrollTop;
    const scrollCenter = scrollTop + containerHeight / 2;

    const promptElements = promptsScrollContainer.querySelectorAll('.prompt-button');

    let closestIndex = -1;
    let closestDistance = Infinity;

    for (let i = 0; i < promptElements.length; i++) {
      const element = promptElements[i] as HTMLElement;
      const elementTop = element.offsetTop;
      const elementCenter = elementTop + element.clientHeight / 2;
      const distance = Math.abs(scrollCenter - elementCenter);

      if (distance < closestDistance) {
        closestDistance = distance;
        closestIndex = i;
      }
    }

    // Only update if the selected index actually changed
    if (closestIndex !== -1 && closestIndex !== selectedPromptIndex) {
      selectedPromptIndex = closestIndex;
    }
  }

  // Show prompts when input is empty and reset selection
  $effect(() => {
    // Only show prompts if no messages exist and input is empty
    if (message.trim() === "" && !hasMessages) {
      showPrompts = true;
      selectedPromptIndex = null;
    } else if (hasMessages) {
      // Hide prompts if there are messages
      showPrompts = false;
    }
  });

  // Auto-scroll to selected prompt when selection changes
  $effect(() => {
    if (selectedPromptIndex !== null && promptsScrollContainer) {
      scrollToPrompt(selectedPromptIndex);
    }
  });

  // Handle scroll end to snap to the nearest prompt
  let scrollTimeout: number | null = null;

  function handleScrollEnd() {
    if (scrollTimeout !== null) {
      window.clearTimeout(scrollTimeout);
    }

    scrollTimeout = window.setTimeout(() => {
      if (selectedPromptIndex !== null) {
        scrollToPrompt(selectedPromptIndex);
      }
    }, 100);
  }
</script>

<div class="input-container">
  {#if showPrompts && !message.trim()}
    <div class="preset-prompts">
      <div class="prompts-header">
        <span class="prompts-title">💬 {t('messageInput.quickStart')}</span>
      </div>
      <div class="prompts-scroll-container">
        <div
          class="prompts-scroll"
          bind:this={promptsScrollContainer}
          onscroll={() => { handleScroll(); handleScrollEnd(); }}
        >
          <div class="prompts-grid">
            {#each presetPrompts as preset, index}
              <button
                class="prompt-button"
                class:selected={selectedPromptIndex === index}
                class:centered={selectedPromptIndex === index}
                onclick={() => handlePromptClick(preset.prompt, index)}
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
      title={t('messageInput.send')}
    >
      ➤
    </button>
  </div>

  <div class="input-hints">
    <span class="hint">{t('messageInput.disclaimer')}</span>
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
    height: 144px;
    overflow-y: auto;
    overflow-x: hidden;
    scroll-behavior: smooth;
    scrollbar-width: none;
    -ms-overflow-style: none;
    position: relative;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    /* Enable scroll snap with proximity for smoother control */
    scroll-snap-type: y proximity;
  }

  .prompts-scroll::-webkit-scrollbar {
    display: none;
  }

  .prompts-grid {
    display: flex;
    flex-direction: column;
    padding: 0;
  }

  /* Fade mask effect on scroll container */
  .prompts-scroll {
    /* Padding ensures first/last items can snap to center */
    padding: 48px 0;
    /* Gradient mask for fading edges */
    -webkit-mask-image: linear-gradient(to bottom,
      transparent 0%,
      black 48px,
      black calc(100% - 48px),
      transparent 100%);
    mask-image: linear-gradient(to bottom,
      transparent 0%,
      black 48px,
      black calc(100% - 48px),
      transparent 100%);
    /* Fallback for browsers without mask support */
    background: linear-gradient(to bottom,
      transparent 0%,
      var(--bg-primary) 48px,
      var(--bg-primary) calc(100% - 48px),
      transparent 100%);
  }

  .prompt-button {
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 1.5rem;
    background: transparent;
    border: none;
    border-radius: 0;
    color: var(--text-tertiary);
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.15s ease-out;
    transform: scale(0.9);
    /* No margin to reduce scroll jump distance */
    /* Enable scroll snap */
    scroll-snap-align: center;
  }

  .prompt-button.centered {
    background: var(--primary-color);
    color: white;
    opacity: 1;
    transform: scale(1);
    box-shadow: 0 2px 12px rgba(90, 156, 255, 0.4);
    font-weight: 600;
    border-radius: 0.5rem;
    margin: 4px 0;
  }

  .prompt-button:disabled {
    cursor: not-allowed;
  }

  .prompt-icon {
    font-size: 1.25rem;
    flex-shrink: 0;
    transition: transform 0.3s;
  }

  .prompt-button.selected .prompt-icon,
  .prompt-button.centered .prompt-icon {
    transform: scale(1.1);
  }

  .prompt-text {
    flex: 1;
    font-weight: 500;
  }

  .message-input {
    display: flex;
    gap: 0.75rem;
    align-items: flex-end;
    padding: 0.5rem;
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
    background: var(--bg-secondary);
    color: var(--text-primary);
    transform: rotate(90deg) scale(1.1);
  }

  .send-button:active:not(.disabled) {
    transform: rotate(90deg) scale(0.95);
  }

  .send-button.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .input-hints {
    padding: 0 1rem 0.5rem;
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

    .prompts-scroll {
      height: 120px;
    }

    .prompt-button {
      height: 40px;
      font-size: 0.85rem;
    }

    .prompt-icon {
      font-size: 1.125rem;
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
