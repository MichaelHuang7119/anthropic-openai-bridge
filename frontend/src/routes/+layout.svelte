<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import Header from '$components/layout/Header.svelte';
  import Toast from '$components/ui/Toast.svelte';
  import { theme } from '$stores/theme';
  import { authService } from '$services/auth';
  import '../lib/styles/global.css';

  // 导航项配置
  const navItems = [
    { href: '/', label: '首页' },
    { href: '/chat', label: '聊天' },
    { href: '/providers', label: '供应商' },
    { href: '/health', label: '健康监控' },
    { href: '/config', label: '配置' },
    { href: '/stats', label: '性能监控' },
    { href: '/api-keys', label: 'API Key 管理' }
  ];

  // 检查链接是否激活
  function isActive(href: string): boolean {
    if (href === '/') {
      return $page.url.pathname === '/';
    }
    return $page.url.pathname.startsWith(href);
  }

  // 初始化主题和认证检查
  onMount(() => {
    theme.init();
    
    // 注册 Service Worker for PWA
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js')
        .then((registration) => {
          console.log('Service Worker registered:', registration);
        })
        .catch((error) => {
          console.error('Service Worker registration failed:', error);
        });
    }
    
    // 检查认证状态（排除登录页）
    if ($page.url.pathname !== '/login' && !authService.isAuthenticated()) {
      goto('/login');
    }
  });

  function _handleLogout() {
    authService.logout();
  }
</script>

<div class="app" class:chat-layout={$page.url.pathname === '/chat'}>
  {#if $page.url.pathname !== '/login'}
    <Header title="Anthropic OpenAI Bridge">
      <nav slot="nav">
        {#each navItems as item}
          <a
            href={item.href}
            class="nav-link"
            class:active={isActive(item.href)}
          >
            {item.label}
          </a>
        {/each}
      </nav>
    </Header>
  {/if}
  <main class="main">
    <slot />
  </main>
  {#if $page.url.pathname !== '/login'}
    <footer class="footer">
      <p>© 2025 Anthropic OpenAI Bridge.</p>
    </footer>
  {/if}
  <Toast />
</div>

<style>
  .app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .main {
    flex: 1;
    background: var(--bg-secondary);
    padding: 2rem 0;
    min-height: 0;
  }

  :global(.chat-layout) .main {
    padding: 0;
  }

  :global(.chat-layout) {
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  @media (max-width: 768px) {
    .main {
      padding: 1rem 0;
    }
  }

  .footer {
    background: var(--bg-tertiary);
    border: none;
    padding: 0.5rem 0;
    text-align: center;
    color: var(--text-secondary);
  }

  .footer p {
    margin: 0;
    font-size: 0.875rem;
    color: rgba(66, 153, 225, 0.6);
  }

  .nav-link {
    color: var(--text-secondary);
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    transition: all 0.2s;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
  }

  .nav-link:hover {
    background: var(--bg-tertiary);
    color: var(--primary-color);
  }

  .nav-link.active {
    color: var(--primary-color);
    font-weight: 600;
    background: var(--bg-tertiary);
    border-bottom-color: var(--primary-color);
  }

  @media (max-width: 768px) {
    .nav-link {
      padding: 0.5rem 0.75rem;
      font-size: 0.875rem;
    }
  }

  @media (max-width: 480px) {
    .nav-link {
      padding: 0.5rem 0.5rem;
      font-size: 0.8125rem;
    }
  }
</style>