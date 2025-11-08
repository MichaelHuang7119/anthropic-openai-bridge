<script lang="ts">
  import { theme } from '$stores/theme';
  import { authService } from '$services/auth';
  
  export let title: string = 'Anthropic OpenAI Bridge';
  export let subtitle: string = '';

  function toggleTheme() {
    theme.toggle();
  }

  function handleLogout() {
    if (confirm('确定要退出登录吗？')) {
      authService.logout();
    }
  }
</script>

<header class="header">
  <div class="container">
    <div class="brand">
      <h1>{title}</h1>
      {#if subtitle}
        <p class="subtitle">{subtitle}</p>
      {/if}
    </div>
    <div class="header-actions">
      <nav class="nav">
        <slot name="nav" />
      </nav>
      <button class="theme-toggle" on:click={toggleTheme} aria-label="切换主题">
        {#if $theme === 'dark'}
          <span class="theme-icon">☀️</span>
        {:else}
          <span class="theme-icon">🌙</span>
        {/if}
      </button>
      <button class="logout-button" on:click={handleLogout} aria-label="退出登录">
        退出
      </button>
    </div>
  </div>
</header>

<style>
  .header {
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
    padding: 1rem 0;
    box-shadow: 0 2px 4px var(--card-shadow);
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }

  .brand h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .subtitle {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .nav {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .theme-toggle {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    padding: 0.5rem;
    border-radius: 0.375rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 2.5rem;
    height: 2.5rem;
    transition: all 0.2s;
  }

  .theme-toggle:hover {
    background: var(--bg-secondary);
    transform: scale(1.05);
  }

  .theme-icon {
    font-size: 1.25rem;
    line-height: 1;
  }

  .logout-button {
    background: var(--danger-color);
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .logout-button:hover {
    background: var(--danger-color-dark, #c82333);
    transform: scale(1.05);
  }

  @media (max-width: 768px) {
    .container {
      padding: 0 1rem;
      flex-wrap: wrap;
    }

    .brand h1 {
      font-size: 1.25rem;
    }

    .subtitle {
      font-size: 0.8125rem;
    }

    .nav {
      gap: 0.5rem;
      order: 3;
      width: 100%;
      overflow-x: auto;
      padding: 0.5rem 0;
    }

    .header-actions {
      flex-wrap: wrap;
    }
  }

  @media (max-width: 480px) {
    .brand h1 {
      font-size: 1.125rem;
    }

    .theme-toggle {
      min-width: 2.25rem;
      height: 2.25rem;
      padding: 0.375rem;
    }

    .theme-icon {
      font-size: 1.125rem;
    }
  }
</style>