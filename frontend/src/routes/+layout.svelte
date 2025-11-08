<script lang="ts">
  import Header from '$components/layout/Header.svelte';
  import Toast from '$components/ui/Toast.svelte';
  import { page } from '$app/stores';
  import '../lib/styles/global.css';

  // 导航项配置
  const navItems = [
    { href: '/', label: '首页' },
    { href: '/providers', label: '供应商' },
    { href: '/health', label: '健康监控' },
    { href: '/config', label: '配置' }
  ];

  // 检查链接是否激活
  function isActive(href: string): boolean {
    if (href === '/') {
      return $page.url.pathname === '/';
    }
    return $page.url.pathname.startsWith(href);
  }
</script>

<div class="app">
  <Header title="Anthropic OpenAI Bridge 管理界面" subtitle="供应商管理与监控系统">
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
  <main class="main">
    <slot />
  </main>
  <footer class="footer">
    <p>© 2025 Anthropic OpenAI Bridge.</p>
  </footer>
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
    background: #f5f5f5;
    padding: 2rem 0;
  }

  .footer {
    background: #fff;
    border-top: 1px solid #e0e0e0;
    padding: 1.5rem 0;
    text-align: center;
    color: #666;
  }

  .footer p {
    margin: 0;
    font-size: 0.875rem;
  }

  .nav-link {
    color: #495057;
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    transition: all 0.2s;
    border-bottom: 2px solid transparent;
  }

  .nav-link:hover {
    background: #e9ecef;
    color: #007bff;
  }

  .nav-link.active {
    color: #007bff;
    font-weight: 600;
    background: #e7f3ff;
    border-bottom-color: #007bff;
  }
</style>
