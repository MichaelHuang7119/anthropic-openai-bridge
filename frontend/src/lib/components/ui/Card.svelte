<script lang="ts">
  interface Props {
    title?: string;
    subtitle?: string;
    'aria-labelledby'?: string;
    role?: string;
    id?: string;
  }

  let {
    title = '',
    subtitle = '',
    'aria-labelledby': ariaLabelledby,
    role,
    id
  }: Props = $props();
</script>

<div class="card" {...(role ? { role } : {})} {...(ariaLabelledby ? { 'aria-labelledby': ariaLabelledby } : {})} {...(id ? { id } : {})}>
  {#if title || $$slots.title || $$slots.titleActions}
    <div class="card-header">
      <div class="title-section">
        {#if title}
          <h3 class="card-title">{title}</h3>
        {/if}
        {#if subtitle}
          <p class="card-subtitle">{subtitle}</p>
        {/if}
        {#if $$slots.title}
          <slot name="title" />
        {/if}
      </div>
      {#if $$slots.titleActions}
        <div class="title-actions">
          <slot name="titleActions" />
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
    background: var(--card-bg, white);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.5rem;
    overflow: hidden;
    box-shadow: var(--card-shadow, 0 2px 4px rgba(0, 0, 0, 0.1));
  }

  .card-header {
    padding: 1rem 1.5rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-bottom: 1px solid var(--border-color, #e0e0e0);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .title-section {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 1;
  }

  .title-actions {
    display: flex;
    align-items: center;
    margin-left: 1rem;
  }

  .card-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .card-subtitle {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
  }

  .card-body {
    padding: 1rem;
  }

  .card-footer {
    padding: 1rem 1.5rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-top: 1px solid var(--border-color, #e0e0e0);
  }
</style>
