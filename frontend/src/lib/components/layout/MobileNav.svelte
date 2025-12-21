<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  // 导航项配置
  const navItems = [
    {
      id: 'home',
      label: '首页',
      href: '/',
      icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'
    },
    {
      id: 'chat',
      label: '聊天',
      href: '/chat',
      icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z'
    },
    {
      id: 'manage',
      label: '管理',
      href: '/manage',
      icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z'
    },
    {
      id: 'stats',
      label: '统计',
      href: '/stats',
      icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
    }
  ];

  // 当前路径
  let currentPath = $state('/');

  // 订阅页面路径变化
  onMount(() => {
    const unsubscribe = page.subscribe(($page) => {
      currentPath = $page.url.pathname;
    });

    return unsubscribe;
  });

  // 检查是否激活
  function isActive(href: string): boolean {
    if (href === '/') {
      return currentPath === '/';
    }
    return currentPath.startsWith(href);
  }

  // 点击导航项时触发的自定义事件
  let { onNavigate }: { onNavigate?: (href: string) => void } = $props();

  function handleNavigate(href: string, _label: string) {
    // 触发点击动画效果
    const navItem = document.getElementById(`nav-${href}`);
    if (navItem) {
      navItem.classList.add('clicked');
      setTimeout(() => {
        navItem.classList.remove('clicked');
      }, 200);
    }

    // 调用自定义导航处理函数
    if (onNavigate) {
      onNavigate(href);
    }
  }
</script>

<nav class="mobile-nav-container" aria-label="移动端底部导航">
  <div class="mobile-nav-wrapper">
    {#each navItems as item}
      <a
        id="nav-{item.href}"
        href={item.href}
        class="nav-item {isActive(item.href) ? 'active' : ''}"
        aria-label={item.label}
        aria-current={isActive(item.href) ? 'page' : undefined}
        onclick={(e) => {
          e.preventDefault();
          handleNavigate(item.href, item.label);
          // 在实际应用中，这里应该使用路由跳转
          // router.goto(item.href);
        }}
      >
        <svg
          class="nav-icon"
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          {#if item.icon}
            {@html item.icon}
          {/if}
        </svg>
        <span class="nav-label">{item.label}</span>

        {#if isActive(item.href)}
          <div class="active-indicator"></div>
        {/if}
      </a>
    {/each}
  </div>
</nav>

<style>
  .mobile-nav-container {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background: var(--card-bg);
    border-top: 1px solid var(--border-color);
    box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
    padding-bottom: env(safe-area-inset-bottom, 0);
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from {
      transform: translateY(100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .mobile-nav-wrapper {
    display: flex;
    justify-content: space-around;
    align-items: center;
    max-width: 600px;
    margin: 0 auto;
    padding: 0.5rem 1rem;
    padding-bottom: max(0.5rem, env(safe-area-inset-bottom, 0));
  }

  .nav-item {
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 0.75rem;
    text-decoration: none;
    color: var(--text-secondary);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: var(--radius-lg);
    gap: 0.375rem;
    min-height: 60px;
    cursor: pointer;
    user-select: none;
  }

  .nav-item:active {
    transform: scale(0.95);
  }

  :global(.nav-item.clicked) {
    animation: clickRipple 0.2s ease-out;
  }

  @keyframes clickRipple {
    0% {
      transform: scale(1);
    }
    50% {
      transform: scale(0.92);
    }
    100% {
      transform: scale(1);
    }
  }

  .nav-icon {
    width: 24px;
    height: 24px;
    stroke-width: 1.8;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
  }

  .nav-item:hover .nav-icon {
    transform: scale(1.1);
    color: var(--primary-color);
  }

  .nav-label {
    font-size: 0.75rem;
    font-weight: 500;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    white-space: nowrap;
  }

  .nav-item:hover {
    color: var(--primary-color);
    background: var(--bg-tertiary);
  }

  .nav-item.active {
    color: var(--primary-color);
    background: var(--bg-tertiary);
  }

  .nav-item.active .nav-icon {
    color: var(--primary-color);
    transform: scale(1.1);
    filter: drop-shadow(0 2px 4px rgba(90, 156, 255, 0.3));
  }

  .nav-item.active .nav-label {
    font-weight: 600;
    color: var(--primary-color);
  }

  /* 活动状态指示器 */
  .active-indicator {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--primary-color);
    animation: indicatorPulse 2s ease-in-out infinite;
  }

  @keyframes indicatorPulse {
    0%, 100% {
      opacity: 1;
      transform: translateX(-50%) scale(1);
    }
    50% {
      opacity: 0.5;
      transform: translateX(-50%) scale(0.8);
    }
  }

  /* 深色主题适配 */
  :global([data-theme="dark"]) .mobile-nav-container {
    background: rgba(15, 22, 37, 0.95);
    backdrop-filter: blur(10px);
    border-top-color: rgba(36, 48, 71, 0.8);
  }

  /* 响应式调整 */
  @media (max-width: 480px) {
    .nav-item {
      padding: 0.375rem 0.5rem;
      min-height: 56px;
      gap: 0.25rem;
    }

    .nav-icon {
      width: 22px;
      height: 22px;
    }

    .nav-label {
      font-size: 0.6875rem;
    }
  }

  @media (max-width: 360px) {
    .nav-item {
      padding: 0.375rem 0.375rem;
      min-height: 52px;
    }

    .nav-icon {
      width: 20px;
      height: 20px;
    }

    .nav-label {
      font-size: 0.625rem;
    }
  }

  /* 横屏适配 */
  @media (max-width: 768px) and (orientation: landscape) {
    .mobile-nav-container {
      padding-bottom: max(0.375rem, env(safe-area-inset-bottom, 0));
    }

    .nav-item {
      min-height: 52px;
      padding: 0.375rem 0.625rem;
    }
  }

  /* 触摸反馈优化 */
  .nav-item::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(90, 156, 255, 0.2);
    transform: translate(-50%, -50%);
    transition: width 0.3s, height 0.3s;
    pointer-events: none;
  }

  .nav-item:active::after {
    width: 100%;
    height: 100%;
  }

  /* 悬浮效果 */
  .nav-item:not(.active):hover {
    transform: translateY(-2px);
  }

  .nav-item:not(.active):hover .nav-icon {
    transform: scale(1.05);
  }

  /* 图标切换动画 */
  .nav-icon {
    animation: iconFadeIn 0.4s ease-out;
  }

  @keyframes iconFadeIn {
    from {
      opacity: 0;
      transform: scale(0.8);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }
</style>
