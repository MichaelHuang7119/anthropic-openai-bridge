<script lang="ts">
  interface Props {
    status?: 'online' | 'offline' | 'warning';
    text?: string;
    size?: 'sm' | 'md' | 'lg';
    animated?: boolean;
    class?: string;
  }

  let {
    status = 'online',
    text = '',
    size = 'md',
    animated = true,
    class: className = ''
  }: Props = $props();

  // 计算状态样式类
  let statusClass = $derived(`indicator-${status}`);

  // 计算尺寸样式类
  let sizeClass = $derived(`indicator-${size}`);

  // 获取默认文本
  let displayText = $derived(
    text || (status === 'online' ? 'Online' : status === 'offline' ? 'Offline' : status === 'warning' ? 'Warning' : '')
  );
</script>

<div
  class="realtime-indicator {statusClass} {sizeClass} {animated ? 'animated' : ''} {className}"
  role="status"
  aria-live="polite"
  aria-label={displayText}
>
  <div class="indicator-dot">
    <div class="pulse-ring"></div>
    <div class="pulse-ring-delayed"></div>
    <div class="indicator-core"></div>
  </div>
  <div class="indicator-content">
    <span class="indicator-text">{displayText}</span>
    {#if status === 'online'}
      <span class="indicator-time">Last updated: {new Date().toLocaleTimeString()}</span>
    {/if}
  </div>
</div>

<style>
  .realtime-indicator {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-lg, 0.5rem);
    background: var(--card-bg, white);
    border: 1px solid var(--border-color, #e5e7eb);
    transition: all 0.3s ease;
  }

  .indicator-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-0-5);
  }

  .indicator-text {
    font-size: var(--font-size-sm, 0.875rem);
    font-weight: 600;
    color: var(--text-primary, #1f2937);
    line-height: 1;
  }

  .indicator-time {
    font-size: var(--font-size-xs, 0.75rem);
    color: var(--text-secondary, #6b7280);
    line-height: 1;
  }

  /* 状态点样式 */
  .indicator-dot {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .indicator-core {
    position: relative;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    z-index: 2;
  }

  .pulse-ring {
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    z-index: 1;
  }

  .pulse-ring-delayed {
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    z-index: 0;
  }

  /* 尺寸变体 */
  .indicator-sm .indicator-dot {
    width: 0.5rem;
    height: 0.5rem;
  }

  .indicator-sm .indicator-core {
    width: 0.5rem;
    height: 0.5rem;
  }

  .indicator-sm .pulse-ring {
    width: 0.5rem;
    height: 0.5rem;
  }

  .indicator-sm .pulse-ring-delayed {
    width: 0.5rem;
    height: 0.5rem;
  }

  .indicator-md .indicator-dot {
    width: 0.75rem;
    height: 0.75rem;
  }

  .indicator-md .indicator-core {
    width: 0.75rem;
    height: 0.75rem;
  }

  .indicator-md .pulse-ring {
    width: 0.75rem;
    height: 0.75rem;
  }

  .indicator-md .pulse-ring-delayed {
    width: 0.75rem;
    height: 0.75rem;
  }

  .indicator-lg .indicator-dot {
    width: 1rem;
    height: 1rem;
  }

  .indicator-lg .indicator-core {
    width: 1rem;
    height: 1rem;
  }

  .indicator-lg .pulse-ring {
    width: 1rem;
    height: 1rem;
  }

  .indicator-lg .pulse-ring-delayed {
    width: 1rem;
    height: 1rem;
  }

  /* Online 状态 */
  .indicator-online .indicator-core {
    background: var(--success-500, #10b981);
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.3);
  }

  .indicator-online .pulse-ring {
    background: rgba(16, 185, 129, 0.4);
    animation: pulse 2s infinite;
  }

  .indicator-online .pulse-ring-delayed {
    background: rgba(16, 185, 129, 0.2);
    animation: pulse 2s infinite 0.5s;
  }

  /* Offline 状态 */
  .indicator-offline .indicator-core {
    background: var(--danger-500, #ef4444);
    box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.3);
  }

  .indicator-offline .pulse-ring,
  .indicator-offline .pulse-ring-delayed {
    display: none;
  }

  /* Warning 状态 */
  .indicator-warning .indicator-core {
    background: var(--warning-500, #f59e0b);
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.3);
    animation: warningPulse 1.5s infinite;
  }

  .indicator-warning .pulse-ring {
    background: rgba(245, 158, 11, 0.4);
    animation: pulse 2s infinite;
  }

  .indicator-warning .pulse-ring-delayed {
    background: rgba(245, 158, 11, 0.2);
    animation: pulse 2s infinite 0.5s;
  }

  /* 动画效果 */
  .realtime-indicator.animated .pulse-ring,
  .realtime-indicator.animated .pulse-ring-delayed {
    opacity: 1;
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
      opacity: 0.8;
    }
    70% {
      transform: scale(2);
      opacity: 0;
    }
    100% {
      transform: scale(2);
      opacity: 0;
    }
  }

  @keyframes warningPulse {
    0%, 100% {
      box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.3);
    }
    50% {
      box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.5);
    }
  }

  /* 暗黑主题 */
  :global([data-theme="dark"]) .realtime-indicator {
    background: var(--card-bg, #1f2937);
    border-color: var(--border-color, #374151);
  }

  :global([data-theme="dark"]) .indicator-text {
    color: var(--text-primary, #f9fafb);
  }

  :global([data-theme="dark"]) .indicator-time {
    color: var(--text-secondary, #9ca3af);
  }

  :global([data-theme="dark"]) .indicator-online .indicator-core {
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.4);
  }

  :global([data-theme="dark"]) .indicator-offline .indicator-core {
    box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.4);
  }

  :global([data-theme="dark"]) .indicator-warning .indicator-core {
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.4);
  }

  /* 响应式设计 */
  @media (max-width: 640px) {
    .realtime-indicator {
      padding: var(--space-1-5) var(--space-2);
    }

    .indicator-text {
      font-size: var(--font-size-xs, 0.75rem);
    }

    .indicator-time {
      font-size: 0.625rem;
    }
  }
</style>
