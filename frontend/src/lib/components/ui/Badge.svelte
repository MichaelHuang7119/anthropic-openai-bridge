<script lang="ts">
  export let type: 'success' | 'danger' | 'warning' | 'info' | 'secondary' = 'secondary';
</script>

<span class="badge badge-{type}">
  <slot />
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

  .badge-danger {
    background: #f8d7da;
    color: #721c24;
  }

  .badge-warning {
    background: #fff3cd;
    color: #856404;
  }

  .badge-info {
    background: #d1ecf1;
    color: #0c5460;
  }

  .badge-secondary {
    background: #e2e3e5;
    color: #383d41;
  }
</style>
