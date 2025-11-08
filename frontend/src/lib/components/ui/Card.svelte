<script lang="ts">
  export let title: string = '';
  export let subtitle: string = '';
</script>

<div class="card">
  {#if title || $$slots.title}
    <div class="card-header">
      {#if title || $$slots.title}
        <div class="title-section">
          {#if title}
            <h3 class="card-title">{title}</h3>
          {/if}
          {#if subtitle}
            <p class="card-subtitle">{subtitle}</p>
          {/if}
          <slot name="title" />
        </div>
      {/if}
    </div>
  {/if}
  <div class="card-body">
    <slot />
  </div>
  {#if $$slots.footer}
    <div class="card-footer">
      <slot name="footer" />
    </div>
  {/if}
</div>

<style>
  .card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 0.5rem;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .card-header {
    padding: 1rem 1.5rem;
    background: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
  }

  .title-section {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .card-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #1a1a1a;
  }

  .card-subtitle {
    margin: 0;
    font-size: 0.875rem;
    color: #666;
  }

  .card-body {
    padding: 1.5rem;
  }

  .card-footer {
    padding: 1rem 1.5rem;
    background: #f8f9fa;
    border-top: 1px solid #e0e0e0;
  }
</style>
