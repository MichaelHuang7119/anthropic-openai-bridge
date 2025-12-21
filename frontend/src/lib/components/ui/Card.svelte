<script lang="ts">
  interface Props {
    title?: string;
    subtitle?: string;
    variant?: 'default' | 'elevated' | 'outlined' | 'filled';
    padding?: 'none' | 'sm' | 'md' | 'lg';
    hoverable?: boolean;
    icon?: string;
    gradient?: boolean;
    class?: string;
    'aria-labelledby'?: string;
    role?: string;
    id?: string;
    overflow?: 'hidden' | 'visible' | 'auto';
    titleSlot?: () => any;
    titleActionsSlot?: () => any;
    footerSlot?: () => any;
    children?: () => any;
  }

  let {
    title = '',
    subtitle = '',
    variant = 'default',
    padding = 'md',
    hoverable = false,
    icon = '',
    gradient = false,
    class: className = '',
    'aria-labelledby': ariaLabelledby,
    role,
    id,
    overflow = 'hidden',
    titleSlot,
    titleActionsSlot,
    footerSlot,
    children
  }: Props = $props();

  // Get default slot content - use $derived to ensure reactivity
  const defaultSlot = $derived(children);

  // Compute padding value
  const paddingValue = $derived(() => {
    switch (padding) {
      case 'none': return '0';
      case 'sm': return 'var(--space-4)';
      case 'md': return 'var(--space-6)';
      case 'lg': return 'var(--space-8)';
      default: return 'var(--space-6)';
    }
  });
</script>

<div
  class="card card-{variant} {hoverable ? 'hoverable' : ''} {gradient ? 'gradient' : ''} {className}"
  style="overflow: {overflow}; padding: {paddingValue};"
  {...(role ? { role } : {})} {...(ariaLabelledby ? { 'aria-labelledby': ariaLabelledby } : {})} {...(id ? { id } : {})}
>
  {#if icon}
    <div class="card-icon">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        {#if icon === 'server'}
          <rect width="20" height="8" x="2" y="6" rx="2"/>
          <rect width="20" height="8" x="2" y="14" rx="2"/>
          <line x1="6" x2="6.01" y1="10" y2="10"/>
        {:else if icon === 'chat'}
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        {:else if icon === 'heart'}
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
        {:else if icon === 'activity'}
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        {:else if icon === 'user'}
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        {:else if icon === 'settings'}
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        {:else}
          <circle cx="12" cy="12" r="10"/>
        {/if}
      </svg>
    </div>
  {/if}

  {#if title || titleSlot || titleActionsSlot}
    <div class="card-header">
      <div class="title-section">
        {#if title}
          <h3 class="card-title">{title}</h3>
        {/if}
        {#if subtitle}
          <p class="card-subtitle">{subtitle}</p>
        {/if}
        {@render titleSlot?.()}
      </div>
      {#if titleActionsSlot}
        <div class="title-actions">
          {@render titleActionsSlot()}
        </div>
      {/if}
    </div>
  {/if}
  <div class="card-body">
    {@render defaultSlot?.()}
  </div>
  {#if footerSlot}
    <div class="card-footer">
      {@render footerSlot()}
    </div>
  {/if}
</div>

<style>
  .card {
    background: var(--card-bg, white);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: var(--radius-xl, 1rem);
    box-shadow: var(--shadow-sm, 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06));
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }

  /* 变体样式 */
  .card-default {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-sm);
  }

  .card-elevated {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-lg);
  }

  .card-outlined {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    box-shadow: none;
  }

  .card-filled {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    box-shadow: none;
  }

  /* 渐变样式 */
  .card-gradient {
    background: linear-gradient(135deg, var(--primary-500), var(--primary-600));
    border: none;
    color: white;
  }

  .card-gradient .card-title,
  .card-gradient .card-subtitle {
    color: white;
  }

  /* 图标样式 */
  .card-icon {
    position: absolute;
    top: var(--space-4);
    right: var(--space-4);
    width: 3rem;
    height: 3rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-lg);
    background: var(--primary-100);
    color: var(--primary-600);
    opacity: 0.8;
    transition: all 0.3s ease;
  }

  [data-theme="dark"] .card-icon {
    background: rgba(96, 165, 250, 0.2);
    color: var(--primary-400);
  }

  /* 悬停效果 */
  .card.hoverable {
    cursor: pointer;
  }

  .card.hoverable:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-xl);
  }

  .card.hoverable:hover .card-icon {
    opacity: 1;
    transform: scale(1.1);
  }

  .card-gradient.hoverable:hover {
    box-shadow: var(--shadow-2xl);
  }

  .card-gradient.hoverable:hover .card-icon {
    background: rgba(255, 255, 255, 0.2);
    color: white;
  }

  /* 头部样式 */
  .card-header {
    padding: var(--space-4) var(--space-6);
    background: var(--bg-tertiary, #f8f9fa);
    border-bottom: 1px solid var(--border-color, #e0e0e0);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .card-gradient .card-header {
    background: rgba(255, 255, 255, 0.1);
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  }

  .title-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    flex: 1;
  }

  .title-actions {
    display: flex;
    align-items: center;
    margin-left: var(--space-4);
  }

  .card-title {
    margin: 0;
    font-size: var(--font-size-lg, 1.125rem);
    font-weight: var(--font-weight-semibold, 600);
    color: var(--text-primary, #1a1a1a);
  }

  .card-subtitle {
    margin: 0;
    font-size: var(--font-size-sm, 0.875rem);
    color: var(--text-secondary, #666);
  }

  /* 内容区域 */
  .card-body {
    padding: var(--space-4);
  }

  /* 底部区域 */
  .card-footer {
    padding: var(--space-4) var(--space-6);
    background: var(--bg-tertiary, #f8f9fa);
    border-top: 1px solid var(--border-color, #e0e0e0);
  }

  .card-gradient .card-footer {
    background: rgba(255, 255, 255, 0.1);
    border-top: 1px solid rgba(255, 255, 255, 0.2);
  }

  /* 响应式设计 */
  @media (max-width: 768px) {
    .card-icon {
      width: 2.5rem;
      height: 2.5rem;
    }

    .card-header {
      padding: var(--space-3) var(--space-4);
    }

    .card-body {
      padding: var(--space-3);
    }

    .card-footer {
      padding: var(--space-3) var(--space-4);
    }
  }
</style>
