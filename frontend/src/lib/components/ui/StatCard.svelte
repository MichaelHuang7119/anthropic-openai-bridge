<script lang="ts">
  interface Props {
    title: string;
    value: string | number | (() => string | number);
    subtitle?: string;
    icon?: string;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
    type?: 'default' | 'success' | 'danger' | 'warning' | 'info';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
    children?: () => any;
  }

  let {
    title,
    value,
    subtitle = '',
    icon = '',
    trend = 'neutral',
    trendValue = '',
    type = 'default',
    size = 'md',
    loading = false,
    children
  }: Props = $props();

  // 响应式样式类
  const typeClass = $derived(`stat-card-${type}`);
  const sizeClass = $derived(`stat-card-${size}`);

  // 获取趋势图标
  function getTrendIcon() {
    switch (trend) {
      case 'up':
        return '↑';
      case 'down':
        return '↓';
      default:
        return '';
    }
  }

  // 获取趋势颜色类
  function getTrendClass() {
    switch (trend) {
      case 'up':
        return 'trend-up';
      case 'down':
        return 'trend-down';
      default:
        return 'trend-neutral';
    }
  }

  // 获取图标SVG
  const iconSvg = $derived(() => {
    if (!icon) return null;

    const icons: Record<string, string> = {
      server: `<path d="M4 10h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2zM4 14h16a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2zM4 18h16"></path>`,
      'check-circle': `<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>`,
      'x-circle': `<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>`,
      'power': `<path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line>`,
      cpu: `<rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><line x1="9" y1="9" x2="15" y2="9"></line><line x1="9" y1="15" x2="15" y2="15"></line><line x1="15" y1="9" x2="15" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>`
    };

    return icons[icon] || '';
  });
</script>

<div class="stat-card {typeClass} {sizeClass}">
  <div class="stat-card-header">
    <div class="stat-card-title-group">
      <h3 class="stat-card-title">{title}</h3>
      {#if subtitle}
        <p class="stat-card-subtitle">{subtitle}</p>
      {/if}
    </div>
    {#if icon && iconSvg()}
      <div class="stat-card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          {@html iconSvg()}
        </svg>
      </div>
    {/if}
  </div>

  <div class="stat-card-content">
    {#if loading}
      <div class="stat-card-loading">
        <div class="loading-shimmer"></div>
      </div>
    {:else}
      <div class="stat-card-value">
        {#if typeof value === 'function'}
          {value()}
        {:else}
          {value}
        {/if}
      </div>
    {/if}

    {#if trendValue && !loading}
      <div class="stat-card-trend {getTrendClass()}">
        <span class="trend-icon">{getTrendIcon()}</span>
        <span class="trend-value">{trendValue}</span>
      </div>
    {/if}
  </div>

  {#if children}
    <div class="stat-card-footer">
      {@render children?.()}
    </div>
  {/if}
</div>

<style>
  .stat-card {
    background: var(--card-bg, white);
    border-radius: var(--radius-lg, 0.5rem);
    padding: var(--space-4, 1.5rem);
    box-shadow: var(--shadow-sm, 0 1px 3px 0 rgba(0, 0, 0, 0.1));
    border: 1px solid var(--border-color, #e5e7eb);
    transition: all 0.3s ease;
  }

  .stat-card:hover {
    box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
    transform: translateY(-2px);
  }

  .stat-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--space-3, 0.75rem);
  }

  .stat-card-title-group {
    flex: 1;
  }

  .stat-card-title {
    margin: 0;
    font-size: var(--font-size-sm, 0.875rem);
    font-weight: 500;
    color: var(--text-secondary, #6b7280);
    line-height: 1.4;
  }

  .stat-card-subtitle {
    margin: var(--space-1, 0.25rem) 0 0 0;
    font-size: var(--font-size-xs, 0.75rem);
    color: var(--text-tertiary, #9ca3af);
    line-height: 1.3;
  }

  .stat-card-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 0.5rem;
    background: var(--bg-tertiary, #f9fafb);
    color: var(--text-secondary, #6b7280);
    flex-shrink: 0;
  }

  .stat-card-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-2, 0.5rem);
  }

  .stat-card-value {
    font-size: var(--font-size-2xl, 1.875rem);
    font-weight: 700;
    color: var(--text-primary, #111827);
    line-height: 1.2;
  }

  .stat-card-trend {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1, 0.25rem);
    font-size: var(--font-size-xs, 0.75rem);
    font-weight: 500;
    line-height: 1;
  }

  .trend-up {
    color: var(--success-color, #10b981);
  }

  .trend-down {
    color: var(--danger-color, #ef4444);
  }

  .trend-neutral {
    color: var(--text-secondary, #6b7280);
  }

  .trend-icon {
    font-size: var(--font-size-sm, 0.875rem);
  }

  .stat-card-footer {
    margin-top: var(--space-3, 0.75rem);
    padding-top: var(--space-3, 0.75rem);
    border-top: 1px solid var(--border-color, #e5e7eb);
  }

  /* 尺寸变体 */
  .stat-card-sm {
    padding: var(--space-3, 0.75rem);
  }

  .stat-card-sm .stat-card-title {
    font-size: var(--font-size-xs, 0.75rem);
  }

  .stat-card-sm .stat-card-value {
    font-size: var(--font-size-xl, 1.25rem);
  }

  .stat-card-sm .stat-card-icon {
    width: 2rem;
    height: 2rem;
  }

  .stat-card-lg {
    padding: var(--space-6, 2rem);
  }

  .stat-card-lg .stat-card-title {
    font-size: var(--font-size-base, 1rem);
  }

  .stat-card-lg .stat-card-value {
    font-size: var(--font-size-3xl, 2.25rem);
  }

  /* 类型变体 */
  .stat-card-success {
    border-left: 4px solid var(--success-color, #10b981);
  }

  .stat-card-success .stat-card-icon {
    background: rgba(16, 185, 129, 0.1);
    color: var(--success-color, #10b981);
  }

  .stat-card-danger {
    border-left: 4px solid var(--danger-color, #ef4444);
  }

  .stat-card-danger .stat-card-icon {
    background: rgba(239, 68, 68, 0.1);
    color: var(--danger-color, #ef4444);
  }

  .stat-card-warning {
    border-left: 4px solid var(--warning-color, #f59e0b);
  }

  .stat-card-warning .stat-card-icon {
    background: rgba(245, 158, 11, 0.1);
    color: var(--warning-color, #f59e0b);
  }

  .stat-card-info {
    border-left: 4px solid var(--info-color, #3b82f6);
  }

  .stat-card-info .stat-card-icon {
    background: rgba(59, 130, 246, 0.1);
    color: var(--info-color, #3b82f6);
  }

  /* 加载状态 */
  .stat-card-loading {
    width: 100%;
    height: 2.5rem;
    position: relative;
    overflow: hidden;
  }

  .loading-shimmer {
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, var(--bg-tertiary, #f3f4f6) 25%, var(--bg-secondary, #e5e7eb) 50%, var(--bg-tertiary, #f3f4f6) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 0.25rem;
  }

  @keyframes shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  /* 暗黑主题 */
  :global([data-theme="dark"]) .stat-card {
    background: var(--card-bg, #1f2937);
    border-color: var(--border-color, #374151);
  }

  :global([data-theme="dark"]) .stat-card-title {
    color: var(--text-secondary, #9ca3af);
  }

  :global([data-theme="dark"]) .stat-card-subtitle {
    color: var(--text-tertiary, #6b7280);
  }

  :global([data-theme="dark"]) .stat-card-value {
    color: var(--text-primary, #f9fafb);
  }

  :global([data-theme="dark"]) .stat-card-icon {
    background: rgba(55, 65, 81, 0.5);
    color: var(--text-secondary, #9ca3af);
  }

  :global([data-theme="dark"]) .stat-card-footer {
    border-color: var(--border-color, #374151);
  }

  :global([data-theme="dark"]) .loading-shimmer {
    background: linear-gradient(90deg, #374151 25%, #4b5563 50%, #374151 75%);
    background-size: 200% 100%;
  }

  /* 响应式设计 */
  @media (max-width: 640px) {
    .stat-card {
      padding: var(--space-3, 0.75rem);
    }

    .stat-card-title {
      font-size: var(--font-size-xs, 0.75rem);
    }

    .stat-card-value {
      font-size: var(--font-size-xl, 1.25rem);
    }

    .stat-card-icon {
      width: 2rem;
      height: 2rem;
    }
  }
</style>
