<script lang="ts">
  let {
    type = 'secondary',
    children
  }: {
    type?: 'success' | 'danger' | 'warning' | 'info' | 'secondary';
    children?: () => any;
  } = $props();
</script>

<span class="badge badge-{type}">
  {@render children?.()}
</span>

<style>
  .badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
    line-height: 1.2;
    white-space: nowrap;
    box-sizing: border-box;
    vertical-align: middle;
    width: fit-content;
    max-width: 100%;
  }

  .badge-success {
    background: #d4edda;
    color: #155724;
  }

  :global([data-theme="dark"]) .badge-success {
    background: rgba(35, 134, 54, 0.2);
    color: #238636;
    border: 1px solid rgba(35, 134, 54, 0.4);
  }

  .badge-danger {
    background: #f8d7da;
    color: #721c24;
  }

  :global([data-theme="dark"]) .badge-danger {
    background: rgba(248, 81, 73, 0.2);
    color: #f85149;
    border: 1px solid rgba(248, 81, 73, 0.4);
  }

  .badge-warning {
    background: #fff3cd;
    color: #856404;
  }

  :global([data-theme="dark"]) .badge-warning {
    background: rgba(210, 153, 34, 0.2);
    color: #d29922;
    border: 1px solid rgba(210, 153, 34, 0.4);
  }

  .badge-info {
    background: #d1ecf1;
    color: #0c5460;
  }

  :global([data-theme="dark"]) .badge-info {
    background: rgba(88, 166, 255, 0.2);
    color: #58a6ff;
    border: 1px solid rgba(88, 166, 255, 0.4);
  }

  .badge-secondary {
    background: #e2e3e5;
    color: #383d41;
  }

  :global([data-theme="dark"]) .badge-secondary {
    background: rgba(139, 148, 158, 0.2);
    color: #8b949e;
    border: 1px solid rgba(139, 148, 158, 0.4);
  }
</style>
