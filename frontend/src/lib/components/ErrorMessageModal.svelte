<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Button from './ui/Button.svelte';
  import { toast } from '$stores/toast';

  export let show: boolean = false;
  export let errorMessage: string = '';
  export let title: string = '错误信息';

  const dispatch = createEventDispatcher<{
    close: void;
  }>();

  function handleClose() {
    dispatch('close');
  }

  function handleOverlayClick(event: MouseEvent) {
    // Only close if clicking directly on the overlay (not on modal content)
    if (event.target === event.currentTarget) {
      handleClose();
    }
  }

  async function copyToClipboard() {
    if (typeof window === 'undefined' || !errorMessage) return;
    
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(errorMessage);
        toast.success('已复制到剪贴板');
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = errorMessage;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        toast.success('已复制到剪贴板');
      }
    } catch (error) {
      console.error('Failed to copy:', error);
      toast.error('复制失败，请手动复制');
    }
  }
</script>

{#if show && errorMessage}
  <div class="modal-overlay" on:click={handleOverlayClick}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h2>{title}</h2>
        <div class="header-actions">
          <Button variant="secondary" size="sm" on:click={copyToClipboard} title="复制错误信息" class="icon-button">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
          </Button>
          <Button variant="secondary" size="sm" on:click={handleClose} title="关闭" class="icon-button">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </Button>
        </div>
      </div>
      
      <div class="error-content">
        <pre class="error-text">{errorMessage}</pre>
      </div>

      <div class="modal-actions">
        <Button variant="primary" on:click={copyToClipboard}>复制错误信息</Button>
        <Button variant="secondary" on:click={handleClose}>关闭</Button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    max-width: 800px;
    width: 90%;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem;
    border-bottom: 1px solid var(--border-color, #dee2e6);
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.25rem;
    color: var(--text-primary, #1a1a1a);
  }

  .header-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .error-content {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    min-height: 200px;
  }

  .error-text {
    margin: 0;
    padding: 1rem;
    background: var(--bg-tertiary, #f8f9fa);
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 0.375rem;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
    font-size: 0.875rem;
    line-height: 1.6;
    color: var(--text-primary, #1a1a1a);
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    padding: 1.5rem;
    border-top: 1px solid var(--border-color, #dee2e6);
  }

  :global([data-theme="dark"]) .error-text {
    background: #1a1a1a;
    border-color: #30363d;
    color: #c9d1d9;
  }
</style>

