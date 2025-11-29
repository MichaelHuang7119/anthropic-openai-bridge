<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import Header from '$components/layout/Header.svelte';
  import Toast from '$components/ui/Toast.svelte';
  import { theme } from '$stores/theme';
  import { language, tStore } from '$stores/language';
  import { authService } from '$services/auth';
  import '../lib/styles/global.css';

  // 获取翻译函数（响应式）
  const t = $derived($tStore);

  // 导航项配置
  const navItems = [
    { href: '/', label: 'nav.home' },
    { href: '/chat', label: 'nav.chat' },
    { href: '/providers', label: 'nav.providers' },
    { href: '/config', label: 'nav.config' },
    { href: '/health', label: 'nav.health' },
    { href: '/stats', label: 'nav.stats' },
    { href: '/api-keys', label: 'nav.apiKeys' }
  ];

  // 检查链接是否激活
  function isActive(href: string): boolean {
    if (href === '/') {
      return $page.url.pathname === '/';
    }
    return $page.url.pathname.startsWith(href);
  }

  // 初始化主题和语言，以及认证检查
  onMount(async () => {
    theme.init();

    // 初始化语言设置（会尝试从后端获取，如果已登录的话）
    await language.init();

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

  let { children } = $props();
</script>

<div class="app" class:chat-layout={$page.url.pathname === '/chat'}>
  {#if $page.url.pathname !== '/login'}
    <Header title="Anthropic OpenAI Bridge">
      {#snippet nav()}
        <nav>
          {#each navItems as item}
            <a
              href={item.href}
              class="nav-link"
              class:active={isActive(item.href)}
            >
              {t(item.label)}
            </a>
          {/each}
        </nav>
      {/snippet}
    </Header>
  {/if}
  <main class="main">
    {@render children()}
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
    padding: 0.5rem 0.375rem;
    border-radius: 0.25rem;
    transition: all 0.2s;
    border-bottom: 2px solid transparent;
    font-size: 0.875rem;
    white-space: nowrap;
    max-width: 110px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  @media (max-width: 1200px) {
    .nav-link {
      padding: 0.5rem 0.25rem;
      font-size: 0.8125rem;
      max-width: 95px;
    }
  }

  @media (max-width: 1024px) {
    .nav-link {
      padding: 0.5rem 0.1875rem;
      font-size: 0.78125rem;
      max-width: 85px;
    }
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
      padding: 0.5rem 0.375rem;
      font-size: 0.8125rem;
      max-width: 100px;
    }
  }

  @media (max-width: 480px) {
    .nav-link {
      padding: 0.5rem 0.25rem;
      font-size: 0.78125rem;
      max-width: 90px;
    }
  }
</style>