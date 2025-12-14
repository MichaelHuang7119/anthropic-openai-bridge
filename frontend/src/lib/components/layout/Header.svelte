<script lang="ts">
  import { tStore } from '$stores/language';
  import { authService } from '$services/auth';
  import SettingsModal from '$components/SettingsModal.svelte';
  import { onMount } from 'svelte';

  let { title = 'Anthropic OpenAI Bridge', subtitle = '', nav } = $props<{
    title?: string;
    subtitle?: string;
    nav?: () => any;
  }>();

  // 设置弹窗状态
  let showSettingsModal = $state(false);

  // 用户菜单状态
  let showUserMenu = $state(false);
  let userMenuRef = $state<HTMLDivElement | null>(null);

  // 移动端导航菜单状态
  let showMobileNav = $state(false);

  // 获取翻译函数（响应式）
  const t = $derived($tStore);

  function handleLogout() {
    const message = t('common.logoutConfirm');
    if (confirm(message)) {
      authService.logout();
    }
  }

  function openSettings() {
    showSettingsModal = true;
    showUserMenu = false;
  }

  // 点击外部关闭用户菜单和移动端导航
  function handleClickOutside(event: MouseEvent) {
    if (showUserMenu && userMenuRef && !userMenuRef.contains(event.target as Node)) {
      showUserMenu = false;
    }

    // 点击导航项后关闭移动端导航
    if (showMobileNav) {
      const target = event.target as HTMLElement;
      if (target.closest('.mobile-nav a')) {
        showMobileNav = false;
      }
    }
  }

  // 添加和移除文档级点击监听器
  onMount(() => {
    document.addEventListener('click', handleClickOutside);

    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  });
</script>

<header class="header">
  <div class="container">
    <div class="brand">
      <img src="/favicon.svg" alt="Anthropic OpenAI Bridge Logo" class="brand-icon" />
      <div class="brand-text">
        <h1>{title}</h1>
        {#if subtitle}
          <p class="subtitle">{subtitle}</p>
        {/if}
      </div>
    </div>

    <div class="header-actions">
      {#if nav}
        <nav class="nav desktop-nav">
          {@render nav()}
        </nav>
      {/if}

      <!-- 移动端汉堡菜单按钮 -->
      <button
        class="mobile-menu-button"
        onclick={(e) => {
          e.stopPropagation();
          showMobileNav = !showMobileNav;
        }}
        aria-label={t('header.toggleMenu')}
        aria-expanded={showMobileNav}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" class="line-1"></line>
          <line x1="3" y1="12" x2="21" y2="12" class="line-2"></line>
          <line x1="3" y1="18" x2="21" y2="18" class="line-3"></line>
        </svg>
      </button>

      <div class="user-menu" bind:this={userMenuRef}>
        <button
          class="user-menu-button"
          onclick={() => showUserMenu = !showUserMenu}
          aria-label={t('header.userCenter')}
          aria-expanded={showUserMenu}
          aria-haspopup="true"
        >
          <span class="user-avatar">👤</span>
          <span class="user-name">{t('header.userCenter')}</span>
          <span class="dropdown-arrow" class:rotated={showUserMenu}>▼</span>
        </button>

        {#if showUserMenu}
          <div class="user-menu-dropdown" role="menu">
            <button
              class="menu-item"
              onclick={openSettings}
              role="menuitem"
            >
              <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              <span>{t('header.settings')}</span>
            </button>
            <div class="menu-separator"></div>
            <button
              class="menu-item logout-item"
              onclick={handleLogout}
              role="menuitem"
            >
              <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
              <span>{t('header.logout')}</span>
            </button>
          </div>
        {/if}
      </div>
    </div>
  </div>
</header>

<!-- 移动端导航菜单 -->
{#if showMobileNav && nav}
  <nav class="mobile-nav">
    {@render nav()}
  </nav>
{/if}

<!-- 设置弹窗 -->
<SettingsModal show={showSettingsModal} onClose={() => showSettingsModal = false} />

<style>
  .header {
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
    padding: 1rem 0;
    box-shadow: 0 2px 4px var(--card-shadow);
    /* 确保Header始终可见 */
    position: sticky;
    top: 0;
    z-index: 100;
  }

  /* 聊天页面的Header需要更高的z-index */
  :global(.chat-layout) .header {
    z-index: 50;
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

  .brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .brand-icon {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .brand-text h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 350px;
  }

  @media (max-width: 1200px) {
    .brand-text h1 {
      max-width: 250px;
      font-size: 1.25rem;
    }
  }

  @media (max-width: 768px) {
    .brand-text h1 {
      max-width: 180px;
      font-size: 1.1rem;
    }
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
    gap: 0.5rem;
    align-items: center;
    flex-wrap: wrap;
    max-width: 600px;
  }

  /* 响应式调整 - 在较小屏幕上缩小间距 */
  @media (max-width: 1200px) {
    .nav {
      gap: 0.375rem;
      max-width: 500px;
    }
  }

  @media (max-width: 1024px) {
    .nav {
      gap: 0.25rem;
      max-width: 400px;
    }
  }

  .user-menu {
    position: relative;
  }

  .user-menu-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    background: var(--bg-primary);
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .user-menu-button:hover {
    background: var(--bg-secondary);
    border-color: var(--primary-color);
  }

  .user-avatar {
    font-size: 1.125rem;
    line-height: 1;
  }

  .user-name {
    font-weight: 500;
  }

  .dropdown-arrow {
    font-size: 0.625rem;
    transition: transform 0.2s;
  }

  .dropdown-arrow.rotated {
    transform: rotate(180deg);
  }

  .user-menu-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 0.5rem;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    box-shadow: 0 4px 12px var(--card-shadow);
    min-width: 12rem;
    z-index: 1000;
    overflow: hidden;
  }

  .menu-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.75rem 1rem;
    background: none;
    border: none;
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.875rem;
    transition: background 0.15s;
    text-align: left;
  }

  .menu-item:hover {
    background: var(--bg-secondary);
  }

  .menu-item.logout-item {
    color: var(--danger-color);
  }

  .menu-item.logout-item:hover {
    background: var(--bg-secondary);
  }

  .menu-icon {
    flex-shrink: 0;
    color: var(--text-secondary);
  }

  .menu-item.logout-item .menu-icon {
    color: var(--danger-color);
  }

  .menu-separator {
    height: 1px;
    background: var(--border-color);
    margin: 0.25rem 0;
  }

  /* 移动端汉堡菜单按钮 */
  .mobile-menu-button {
    display: none;
    padding: 0.5rem;
    background: transparent;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.2s;
  }

  .mobile-menu-button:hover {
    background: var(--bg-secondary);
    border-color: var(--primary-color);
  }

  .mobile-menu-button svg {
    display: block;
  }

  .mobile-menu-button .line-1,
  .mobile-menu-button .line-2,
  .mobile-menu-button .line-3 {
    transition: all 0.3s;
  }

  /* 移动端导航菜单 */
  .mobile-nav {
    position: fixed;
    top: 4.5rem; /* Header高度约4.5rem */
    left: 0;
    right: 0;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
    box-shadow: 0 4px 12px var(--card-shadow);
    padding: 1rem;
    z-index: 9999;
    animation: slideDown 0.3s ease-out;
  }

  .mobile-nav a {
    display: block;
    padding: 0.875rem 1rem;
    color: var(--text-primary);
    text-decoration: none;
    border-radius: 0.375rem;
    transition: all 0.2s;
    margin-bottom: 0.25rem;
    border-bottom: 2px solid transparent;
    background: var(--bg-secondary); /* 添加背景色以便调试 */
  }

  .mobile-nav a:hover {
    background: var(--bg-tertiary);
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }

  .mobile-nav a.active {
    background: var(--bg-tertiary);
    color: var(--primary-color);
    font-weight: 600;
    border-bottom-color: var(--primary-color);
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 768px) {
    .container {
      padding: 0 1rem;
      flex-wrap: nowrap; /* 不换行，保持品牌和按钮在一行 */
    }

    .mobile-menu-button {
      display: inline-flex;
    }

    .desktop-nav {
      display: none;
    }

    .brand-icon {
      width: 32px;
      height: 32px;
    }

    .brand-text h1 {
      font-size: 1.125rem;
      max-width: 160px;
    }

    .subtitle {
      font-size: 0.8125rem;
    }

    .header-actions {
      order: 2;
      margin-left: auto;
      gap: 0.5rem; /* 按钮之间的间距 */
    }

    .user-name {
      display: none;
    }

    .user-menu-button {
      padding: 0.5rem;
      min-width: 2.5rem;
    }
  }

  @media (max-width: 480px) {
    .brand-icon {
      width: 28px;
      height: 28px;
    }

    .brand-text h1 {
      font-size: 1rem;
      max-width: 140px;
    }

    .mobile-menu-button svg {
      width: 20px;
      height: 20px;
    }

    .mobile-nav {
      padding: 0.75rem;
    }

    .mobile-nav a {
      padding: 0.75rem 0.875rem;
      font-size: 0.9375rem;
    }
  }
</style>