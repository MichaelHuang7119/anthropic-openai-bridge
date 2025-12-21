<script lang="ts">
  import { toast } from '$stores/toast';
  import type { Toast } from '$stores/toast';
  import ErrorMessageModal from '../ErrorMessageModal.svelte';
  import { tStore } from '$stores/language';

  let toasts = $state<Toast[]>([]);

  // 获取翻译函数
  const t = $derived($tStore);

  // 订阅toast变化
  $effect(() => {
    const unsubscribe = toast.subscribe((value) => {
      toasts = value;
    });
    return unsubscribe;
  });

  function handleClose(id: string) {
    toast.remove(id);
  }

  // 错误信息模态框相关
  let showErrorModal = $state(false);
  let selectedError: string = $state('');
  let selectedErrorTitle: string = $state('');

  function showFullErrorMessage(message: string, title: string = '错误信息') {
    selectedError = message;
    selectedErrorTitle = title || t('common.errorMessageTitle');
    showErrorModal = true;
  }

  function closeErrorModal() {
    showErrorModal = false;
    selectedError = '';
    selectedErrorTitle = '';
  }

  // 判断错误信息是否过长（超过100字符）
  function isLongMessage(message: string): boolean {
    return message.length > 100;
  }

  // 截断消息用于显示
  function truncateMessage(message: string, maxLength: number = 100): string {
    if (message.length <= maxLength) return message;
    return message.substring(0, maxLength) + '...';
  }
</script>

<div class="toast-container">
  {#each toasts as toastItem (toastItem.id)}
    {@const isLong = isLongMessage(toastItem.message)}
    {@const displayMessage = isLong ? truncateMessage(toastItem.message) : toastItem.message}
    <div class="toast toast-{toastItem.type}" role="alert">
      <div class="toast-content">
        {#if isLong && toastItem.type === 'error'}
          <span
            class="toast-message clickable"
            role="button"
            tabindex="0"
            onclick={() => showFullErrorMessage(toastItem.message, t('common.errorMessageTitle'))}
            onkeydown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                showFullErrorMessage(toastItem.message, t('common.errorMessageTitle'));
              }
            }}
            title={t('common.clickToViewFullError')}
          >
            {displayMessage}
          </span>
        {:else}
          <span class="toast-message">{displayMessage}</span>
        {/if}
      </div>
      <button class="toast-close" onclick={() => handleClose(toastItem.id)} aria-label={t('common.close')}>
        ×
      </button>
    </div>
  {/each}
</div>

<!-- Error Message Modal for long error messages -->
<ErrorMessageModal
  show={showErrorModal}
  errorMessage={selectedError}
  title={selectedErrorTitle}
  on:close={closeErrorModal}
/>

<style>
  .toast-container {
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 10000;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    pointer-events: none;
  }

  .toast {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-width: auto;
    max-width: 350px;
    width: fit-content;
    padding: 0.875rem 1rem;
    background: white;
    border-radius: 0.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    pointer-events: auto;
    animation: slideIn 0.3s ease-out;
    border-left: 4px solid;
  }

  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  .toast-success {
    border-left-color: #28a745;
  }

  .toast-error {
    border-left-color: #dc3545;
  }

  .toast-info {
    border-left-color: #17a2b8;
  }

  .toast-warning {
    border-left-color: #ffc107;
  }

  .toast-content {
    flex: 0 1 auto;
    min-width: 0;
  }

  .toast-message {
    display: block;
    color: #1a1a1a;
    font-size: 0.875rem;
    line-height: 1.5;
    white-space: pre-line;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  .toast-message.clickable {
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
    text-underline-offset: 2px;
  }

  .toast-message.clickable:hover {
    opacity: 0.8;
  }

  .toast-message.clickable:focus {
    outline: 2px solid var(--primary-color, #007bff);
    outline-offset: 2px;
    border-radius: 0.25rem;
  }

  .toast-close {
    margin-left: 1rem;
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #666;
    cursor: pointer;
    padding: 0;
    width: 1.5rem;
    height: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.25rem;
    transition: all 0.2s;
    flex-shrink: 0;
  }

  .toast-close:hover {
    background: rgba(0, 0, 0, 0.05);
    color: #1a1a1a;
  }

  .toast-close:active {
    background: rgba(0, 0, 0, 0.1);
  }
</style>

