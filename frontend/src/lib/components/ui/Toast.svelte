<script lang="ts">
  import { toast } from '$stores/toast';
  import type { Toast } from '$stores/toast';

  let toasts: Toast[] = [];
  
  toast.subscribe((value) => {
    toasts = value;
  });

  function handleClose(id: string) {
    toast.remove(id);
  }
</script>

<div class="toast-container">
  {#each toasts as toastItem (toastItem.id)}
    <div class="toast toast-{toastItem.type}" role="alert">
      <div class="toast-content">
        <span class="toast-message">{toastItem.message}</span>
      </div>
      <button class="toast-close" on:click={() => handleClose(toastItem.id)} aria-label="关闭">
        ×
      </button>
    </div>
  {/each}
</div>

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

