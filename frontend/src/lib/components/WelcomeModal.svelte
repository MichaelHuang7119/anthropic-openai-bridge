<script lang="ts">
  import Card from '$components/ui/Card.svelte';
  import Button from '$components/ui/Button.svelte';
  import { tStore } from '$stores/language';
  import { browser } from '$app/environment';

  interface Props {
    show: boolean;
    onClose?: () => void;
  }

  let { show, onClose }: Props = $props();

  // Debug: log when show prop changes
  $effect(() => {
    console.log('[WelcomeModal] Component initialized with show:', show);
    console.log('[WelcomeModal] Will render:', show);
  });

  // 获取翻译函数
  const t = $derived($tStore);

  // 模态框元素引用
  let modalElement: HTMLDivElement | null = $state(null);

  // 记录是否已经显示过欢迎弹窗
  $effect(() => {
    console.log('[WelcomeModal] Effect running, show:', show);
    if (show && browser) {
      console.log('[WelcomeModal] Setting welcome_shown in localStorage');
      localStorage.setItem('welcome_shown', 'true');
      console.log('[WelcomeModal] Set welcome_shown to true');
    }
  });

  // 焦点管理
  $effect(() => {
    if (show && modalElement) {
      setTimeout(() => {
        const firstFocusable = modalElement?.querySelector<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        firstFocusable?.focus();
      }, 0);
    }
  });

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      show = false;
    }
  }

  function handleBackdropClick() {
    show = false;
  }

  function handleModalClick(event: MouseEvent) {
    event.stopPropagation();
  }

  function closeModal() {
    show = false;
    onClose?.();
  }
</script>

{#if show}
  <!-- Debug: WelcomeModal is rendering -->
  <div style="display:none">WelcomeModal Render: {show}</div>
  <div
    class="modal-overlay"
    role="dialog"
    aria-modal="true"
    aria-label={t('welcome.title')}
    tabindex="-1"
    bind:this={modalElement}
    onkeydown={handleKeydown}
    onclick={handleBackdropClick}
  >
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
      class="modal-content"
      role="document"
      onclick={handleModalClick}
      onkeydown={(e) => e.stopPropagation()}
    >
      <div class="modal-header">
        <div class="header-icon">
          <img src="/favicon.svg" alt="Logo" />
        </div>
        <h2 class="modal-title">{t('welcome.title')}</h2>
        <button class="close-button" onclick={closeModal} aria-label={t('common.close')}>
          ×
        </button>
      </div>

      <div class="modal-body">
        <Card overflow="auto">
          <!-- 项目描述区域 -->
          <div class="project-description">
            <p class="description-text">{t('welcome.projectDescription')}</p>
            <div class="feature-list">
              <div class="feature-item">
                <svg class="feature-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>{t('welcome.feature1')}</span>
              </div>
              <div class="feature-item">
                <svg class="feature-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>{t('welcome.feature2')}</span>
              </div>
              <div class="feature-item">
                <svg class="feature-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>{t('welcome.feature3')}</span>
              </div>
              <div class="feature-item">
                <svg class="feature-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>{t('welcome.feature4')}</span>
              </div>
            </div>
          </div>

          <!-- 快速开始指南 -->
          <div class="quick-start">
            <h3 class="quick-start-title">{t('welcome.quickStartTitle')}</h3>
            <div class="quick-start-steps">
              <div class="step">
                <div class="step-number">1</div>
                <div class="step-content">
                  <div class="step-title">{t('welcome.step1Title')}</div>
                  <div class="step-desc">{t('welcome.step1Desc')}</div>
                </div>
              </div>
              <div class="step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <div class="step-title">{t('welcome.step2Title')}</div>
                  <div class="step-desc">{t('welcome.step2Desc')}</div>
                </div>
              </div>
              <div class="step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <div class="step-title">{t('welcome.step3Title')}</div>
                  <div class="step-desc">{t('welcome.step3Desc')}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="modal-actions">
            <Button
              variant="primary"
              on:click={closeModal}
            >
              {t('welcome.getStarted')}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 2rem 1rem;
    animation: fadeIn 0.3s ease-out;
    backdrop-filter: blur(2px);
  }

  .modal-content {
    background: var(--bg-primary, white);
    border-radius: 1rem;
    box-shadow:
      0 25px 50px -12px rgba(0, 0, 0, 0.15),
      0 0 0 1px rgba(255, 255, 255, 0.05);
    max-width: 650px;
    width: 100%;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    margin: auto;
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.75rem;
    border-bottom: 1px solid var(--border-color, #e5e7eb);
    background: linear-gradient(180deg, rgba(59, 130, 246, 0.03) 0%, transparent 100%);
  }

  .header-icon {
    flex-shrink: 0;
    width: 3.5rem;
    height: 3.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .header-icon img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .modal-title {
    margin: 0;
    font-size: 1.625rem;
    font-weight: 700;
    color: var(--text-primary, #1a1a1a);
    flex: 1;
    letter-spacing: -0.025em;
  }

  .close-button {
    background: transparent;
    border: none;
    font-size: 2rem;
    line-height: 1;
    cursor: pointer;
    color: var(--text-secondary, #6b7280);
    padding: 0.25rem;
    width: 2.5rem;
    height: 2.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.5rem;
    transition: all 0.2s ease;
  }

  .close-button:hover {
    background: rgba(239, 68, 68, 0.1);
    color: rgb(239, 68, 68);
    transform: rotate(90deg);
  }

  .modal-body {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    max-height: calc(90vh - 5.5rem);
  }

  /* Card滚动条样式 */
  .modal-body :global(.card)::-webkit-scrollbar {
    width: 8px;
  }

  .modal-body :global(.card)::-webkit-scrollbar-track {
    background: var(--bg-tertiary, #f5f5f5);
    border-radius: 4px;
  }

  .modal-body :global(.card)::-webkit-scrollbar-thumb {
    background: var(--text-secondary, #c0c0c0);
    border-radius: 4px;
  }

  .modal-body :global(.card)::-webkit-scrollbar-thumb:hover {
    background: var(--primary-color, #3b82f6);
  }

  .modal-body :global(.card) {
    scrollbar-width: thin;
    scrollbar-color: var(--text-secondary, #c0c0c0) var(--bg-tertiary, #f5f5f5);
  }

  .project-description {
    background: linear-gradient(135deg, var(--primary-color, #3b82f6) 0%, var(--primary-color-dark, #2563eb) 100%);
    color: white;
    padding: 2rem;
    border-radius: 0.75rem;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px -10px rgba(59, 130, 246, 0.4);
    position: relative;
    overflow: hidden;
  }

  .project-description::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
    pointer-events: none;
  }

  .description-text {
    margin: 0 0 1.5rem 0;
    font-size: 1.0625rem;
    line-height: 1.7;
    color: rgba(255, 255, 255, 0.95);
    font-weight: 400;
  }

  .feature-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .feature-item {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    font-size: 1rem;
    color: rgba(255, 255, 255, 0.95);
    font-weight: 500;
  }

  .feature-icon {
    flex-shrink: 0;
    color: white;
    opacity: 1;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  }

  .quick-start {
    margin-bottom: 1.5rem;
  }

  .quick-start-title {
    margin: 0 0 1rem 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .quick-start-steps {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .step {
    display: flex;
    gap: 1.25rem;
    padding: 1.25rem;
    background: var(--bg-secondary, #f9fafb);
    border-radius: 0.75rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: 1px solid rgba(59, 130, 246, 0.08);
    position: relative;
  }

  .step:hover {
    background: var(--bg-tertiary, #f3f4f6);
    transform: translateY(-2px);
    box-shadow: 0 10px 25px -10px rgba(59, 130, 246, 0.3);
    border-color: rgba(59, 130, 246, 0.2);
  }

  .step-number {
    flex-shrink: 0;
    width: 2.5rem;
    height: 2.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--primary-color, #3b82f6), var(--primary-color-dark, #2563eb));
    color: white;
    border-radius: 0.625rem;
    font-weight: 700;
    font-size: 1rem;
    box-shadow: 0 4px 12px -4px rgba(59, 130, 246, 0.5);
  }

  .step-content {
    flex: 1;
  }

  .step-title {
    margin: 0 0 0.5rem 0;
    font-weight: 700;
    color: var(--text-primary, #1a1a1a);
    font-size: 1rem;
  }

  .step-desc {
    margin: 0;
    color: var(--text-secondary, #6b7280);
    font-size: 0.9375rem;
    line-height: 1.6;
  }

  .modal-actions {
    display: flex;
    justify-content: center;
    gap: 1rem;
    padding: 2rem 1rem 1rem;
    margin-top: auto;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 640px) {
    .modal-overlay {
      padding: 0.5rem;
    }

    .modal-content {
      max-height: 90vh;
    }

    .modal-body {
      max-height: calc(90vh - 5.5rem);
    }

    .modal-header {
      padding: 1rem;
    }

    .header-icon {
      width: 2.5rem;
      height: 2.5rem;
    }

    .modal-title {
      font-size: 1.25rem;
    }

    .project-description {
      padding: 1.25rem;
    }

    .description-text {
      font-size: 0.9375rem;
    }

    .feature-item {
      font-size: 0.875rem;
    }

    .step {
      padding: 0.875rem;
    }

    .step-title {
      font-size: 0.875rem;
    }

    .step-desc {
      font-size: 0.8125rem;
    }
  }
</style>
