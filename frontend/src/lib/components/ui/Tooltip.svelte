<script lang="ts">
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';

  let {
    content = '',
    placement = 'top',
    maxWidth = '500px',
    children
  }: {
    content?: string;
    placement?: 'top' | 'bottom' | 'left' | 'right';
    maxWidth?: string;
    children?: () => any;
  } = $props();

  let tooltipElement: HTMLElement;
  let tooltipBox = $state<HTMLElement>();
  let showTooltip = $state(false);
  let tooltipStyle = $state('');
  
  function updateTooltipPosition() {
    if (!tooltipElement || !tooltipBox || !showTooltip) return;
    
    const rect = tooltipElement.getBoundingClientRect();
    const tooltipRect = tooltipBox.getBoundingClientRect();
    
    let top = 0;
    let left = 0;
    
    switch (placement) {
      case 'top':
        top = rect.top - tooltipRect.height - 8;
        left = rect.left + rect.width / 2 - tooltipRect.width / 2;
        break;
      case 'bottom':
        top = rect.bottom + 8;
        left = rect.left + rect.width / 2 - tooltipRect.width / 2;
        break;
      case 'left':
        top = rect.top + rect.height / 2 - tooltipRect.height / 2;
        left = rect.left - tooltipRect.width - 8;
        break;
      case 'right':
        top = rect.top + rect.height / 2 - tooltipRect.height / 2;
        left = rect.right + 8;
        break;
    }
    
    // 确保 tooltip 不会超出视口
    const padding = 8;
    if (left < padding) left = padding;
    if (left + tooltipRect.width > window.innerWidth - padding) {
      left = window.innerWidth - tooltipRect.width - padding;
    }
    if (top < padding) top = padding;
    if (top + tooltipRect.height > window.innerHeight - padding) {
      top = window.innerHeight - tooltipRect.height - padding;
    }
    
    tooltipStyle = `position: fixed; top: ${top}px; left: ${left}px; max-width: ${maxWidth};`;
  }
  
  function handleMouseEnter() {
    showTooltip = true;
    // 使用双重 requestAnimationFrame 确保 DOM 已更新并渲染
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        updateTooltipPosition();
      });
    });
  }
  
  function handleMouseLeave() {
    showTooltip = false;
  }
  
  function handleScroll() {
    if (showTooltip) {
      updateTooltipPosition();
    }
  }
  
  function handleResize() {
    if (showTooltip) {
      updateTooltipPosition();
    }
  }
  
  onMount(() => {
    window.addEventListener('scroll', handleScroll, true);
    window.addEventListener('resize', handleResize);
  });
  
  onDestroy(() => {
    window.removeEventListener('scroll', handleScroll, true);
    window.removeEventListener('resize', handleResize);
  });

  // 当 tooltip 显示且元素已绑定后，更新位置
  $effect(() => {
    if (showTooltip && tooltipBox) {
      // 使用 setTimeout 确保 tooltip 已经渲染并有了尺寸
      setTimeout(() => {
        updateTooltipPosition();
      }, 0);
    }
  });
</script>

<div
  class="tooltip-wrapper"
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  bind:this={tooltipElement}
  role="presentation"
>
  {@render children?.()}
</div>

{#if showTooltip && content}
  <div 
    class="tooltip" 
    style={tooltipStyle}
    bind:this={tooltipBox}
  >
    {content}
  </div>
{/if}

<style>
  .tooltip-wrapper {
    position: relative;
    display: inline-block;
  }
  
  .tooltip {
    position: fixed;
    z-index: 10000;
    padding: 0.5rem 0.75rem;
    background: var(--bg-tooltip, #1a1a1a);
    color: var(--text-tooltip, #ffffff);
    border-radius: 0.375rem;
    font-size: 0.8125rem;
    line-height: 1.5;
    white-space: pre-wrap;
    word-wrap: break-word;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    pointer-events: none;
    animation: fadeIn 0.15s ease-in-out;
  }
  
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
</style>

