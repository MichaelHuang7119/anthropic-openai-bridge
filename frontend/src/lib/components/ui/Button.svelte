<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'danger' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let disabled: boolean = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let title: string | undefined = undefined;
  
  // 支持自定义 class
  let className = '';
  export { className as class };
  
  $: classes = `btn btn-${variant} btn-${size} ${className}`.trim();
</script>

<button
  {type}
  class={classes}
  {disabled}
  {title}
  on:click
>
  <slot />
</button>

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: 0.375rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-sm {
    padding: 0.375rem 0.75rem;
    font-size: 0.875rem;
  }

  .btn-md {
    padding: 0.5rem 1rem;
    font-size: 1rem;
  }

  .btn-lg {
    padding: 0.75rem 1.5rem;
    font-size: 1.125rem;
  }

  .btn-primary {
    background: var(--primary-color, #007bff);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--primary-color, #007bff);
    opacity: 0.9;
  }

  :global([data-theme="dark"]) .btn-primary {
    background: #238636;
    color: white;
  }

  :global([data-theme="dark"]) .btn-primary:hover:not(:disabled) {
    background: #2ea043;
  }

  .btn-secondary {
    background: var(--bg-tertiary, #e9ecef);
    color: var(--text-primary, #495057);
    border: 1px solid var(--border-color, #dee2e6);
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--bg-tertiary, #dee2e6);
    border-color: var(--border-color, #adb5bd);
  }

  :global([data-theme="dark"]) .btn-secondary {
    background: #21262d;
    color: var(--text-primary);
    border-color: #30363d;
  }

  :global([data-theme="dark"]) .btn-secondary:hover:not(:disabled) {
    background: #30363d;
    border-color: #484f58;
  }

  .btn-danger {
    background: var(--danger-color, #dc3545);
    color: white;
  }

  .btn-danger:hover:not(:disabled) {
    background: var(--danger-color, #dc3545);
    opacity: 0.9;
  }

  :global([data-theme="dark"]) .btn-danger {
    background: #da3633;
  }

  :global([data-theme="dark"]) .btn-danger:hover:not(:disabled) {
    background: #f85149;
  }
</style>
