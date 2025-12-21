<script lang="ts">
  import { tStore } from '$stores/language';

  interface Option {
    value: string;
    label: string;
    description?: string;
    coloredPart?: {
      text: string;
      color?: string;
      opacity?: number;
    };
  }

  interface Props {
    options: Option[];
    value?: string;
    placeholder?: string;
    onChange?: (value: string) => void;
    searchable?: boolean;
    searchPlaceholder?: string;
    maxHeight?: string;
    isInBottomSheet?: boolean;
  }

  let {
    options = [],
    value = $bindable(""),
    placeholder = "请选择",
    onChange,
    searchable = false,
    searchPlaceholder = "搜索...",
    maxHeight,
    isInBottomSheet = false
  }: Props = $props();

  // 获取翻译函数
  const t = $derived($tStore);

  interface FloatingStyles {
    top?: string;
    bottom?: string;
    left?: string;
    right?: string;
    width?: string;
    maxWidth?: string;
    minWidth?: string;
    maxHeight?: string;
  }

  let isOpen = $state(false);
  let listElement: HTMLDivElement;
  let searchQuery = $state("");
  let floatingPosition = $state<'below' | 'above'>('below');
  let floatingStyles = $state<FloatingStyles>({});

  // 计算悬浮位置
  $effect(() => {
    if (isOpen && isInBottomSheet && listElement) {
      const calculatePosition = () => {
        const triggerRect = listElement.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;
        const triggerBottom = triggerRect.bottom;
        const triggerTop = triggerRect.top;

        // 估算下拉菜单高度（根据选项数量，最大 60vh）
        const estimatedHeight = Math.min(
          400,
          Math.max(200, (filteredOptions.length || 5) * 48 + 80)
        );

        // 计算最大可用宽度（基于触发器宽度，限制在屏幕内）
        const maxLeft = 8;
        const maxRight = 8;
        const availableWidth = viewportWidth - maxLeft - maxRight;

        // 下拉菜单宽度：与触发器一致，但不超过可用宽度
        const dropdownWidth = Math.min(triggerRect.width, availableWidth);

        // 查找 messages-container
        const messagesContainer = document.querySelector('[data-messages-container], .messages-container, #messages-container');
        let messagesBottom = viewportHeight; // 默认使用屏幕底部
        let messagesTop = 0;

        if (messagesContainer) {
          const messagesRect = messagesContainer.getBoundingClientRect();
          messagesBottom = messagesRect.bottom;
          messagesTop = messagesRect.top;
        }

        // 计算相对于 messages-container 的可用空间
        const spaceBelowInMessages = messagesBottom - triggerBottom;
        const spaceAboveInMessages = triggerTop - messagesTop;

        // 计算下拉菜单在messages-container内的边界限制
        const menuTopLimit = messagesTop + 8; // 距离顶部最小距离
        const menuBottomLimit = messagesBottom - 8; // 距离底部最小距离

        // 检查在触发器下方是否有足够空间（在 messages-container 内）
        if (spaceBelowInMessages > estimatedHeight) {
          // 在下方展开
          floatingPosition = 'below';
          const maxHeight = Math.min(
            messagesBottom - triggerBottom - 16,
            menuBottomLimit - triggerBottom - 8
          );
          floatingStyles = {
            top: `${triggerBottom + 8}px`,
            left: `${Math.max(maxLeft, triggerRect.left)}px`,
            width: `${dropdownWidth}px`,
            bottom: 'auto',
            maxWidth: `${dropdownWidth}px`,
            minWidth: `${dropdownWidth}px`,
            maxHeight: `${Math.max(150, maxHeight)}px`
          };
        } else if (spaceAboveInMessages > estimatedHeight) {
          // 在上方展开（在 messages-container 内）
          floatingPosition = 'above';
          const maxHeight = Math.min(
            triggerTop - messagesTop - 16,
            triggerTop - menuTopLimit - 8
          );
          floatingStyles = {
            bottom: `${viewportHeight - triggerTop + 8}px`,
            left: `${Math.max(maxLeft, triggerRect.left)}px`,
            width: `${dropdownWidth}px`,
            top: 'auto',
            maxWidth: `${dropdownWidth}px`,
            minWidth: `${dropdownWidth}px`,
            maxHeight: `${Math.max(150, maxHeight)}px`
          };
        } else {
          // 在 messages-container 内空间都不够，选择空间较大的位置并限制高度
          if (spaceBelowInMessages > spaceAboveInMessages) {
            // 下方空间更大
            floatingPosition = 'below';
            const maxHeight = Math.max(150, Math.min(spaceBelowInMessages - 16, menuBottomLimit - triggerBottom - 8));
            floatingStyles = {
              top: `${triggerBottom + 8}px`,
              left: `${Math.max(maxLeft, triggerRect.left)}px`,
              width: `${dropdownWidth}px`,
              bottom: 'auto',
              maxWidth: `${dropdownWidth}px`,
              minWidth: `${dropdownWidth}px`,
              maxHeight: `${maxHeight}px`
            };
          } else {
            // 上方空间更大
            floatingPosition = 'above';
            const maxHeight = Math.max(150, Math.min(spaceAboveInMessages - 16, triggerTop - menuTopLimit - 8));
            floatingStyles = {
              bottom: `${viewportHeight - triggerTop + 8}px`,
              left: `${Math.max(maxLeft, triggerRect.left)}px`,
              width: `${dropdownWidth}px`,
              top: 'auto',
              maxWidth: `${dropdownWidth}px`,
              minWidth: `${dropdownWidth}px`,
              maxHeight: `${maxHeight}px`
            };
          }
        }
      };

      // 延迟计算，等待渲染完成
      const timer = setTimeout(calculatePosition, 0);
      window.addEventListener('resize', calculatePosition);
      window.addEventListener('scroll', calculatePosition, true);

      return () => {
        clearTimeout(timer);
        window.removeEventListener('resize', calculatePosition);
        window.removeEventListener('scroll', calculatePosition, true);
      };
    }
  });

  // Find selected option
  let selectedOption = $derived(
    options.find(opt => opt.value === value)
  );

  // Filter options based on search query
  let filteredOptions = $derived(
    searchable && searchQuery.trim()
      ? options.filter(opt => {
          const query = searchQuery.toLowerCase();
          // Search in label
          if (opt.label.toLowerCase().includes(query)) return true;
          // Search in description
          if (opt.description && opt.description.toLowerCase().includes(query)) return true;
          // Search in coloredPart (for provider name + api format mixed search)
          if (opt.coloredPart && opt.coloredPart.text && opt.coloredPart.text.toLowerCase().includes(query)) return true;
          return false;
        })
      : options
  );

  function handleToggle(event?: MouseEvent) {
    isOpen = !isOpen;
    if (event) {
      event.stopPropagation();
    }
  }

  function handleSelect(optionValue: string, event?: MouseEvent) {
    value = optionValue;
    isOpen = false;
    searchQuery = "";
    onChange?.(optionValue);
    // Prevent event bubbling to parent components
    if (event) {
      event.stopPropagation();
    }
  }

  function handleClickOutside(event: MouseEvent) {
    if (isOpen && listElement && !listElement.contains(event.target as Node)) {
      isOpen = false;
      searchQuery = "";
      event.stopPropagation(); // 阻止事件传播，避免干扰父组件
    }
  }

  function handleSearchChange(event: Event) {
    searchQuery = (event.target as HTMLInputElement).value;
  }

  $effect(() => {
    if (isOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => {
        document.removeEventListener('click', handleClickOutside);
      };
    }
  });
</script>

<div class="sliding-list" bind:this={listElement}>
  <!-- Trigger Button -->
  <button
    type="button"
    class="trigger"
    onclick={(e) => handleToggle(e)}
    aria-haspopup="listbox"
    aria-expanded={isOpen}
  >
    <span class="trigger-label">
      {#if selectedOption}
        <span class="option-label">
          {selectedOption.label}
          {#if selectedOption.coloredPart}
            <span
              class="option-colored-part"
              style="color: {selectedOption.coloredPart.color || 'var(--text-tertiary)'}; opacity: {selectedOption.coloredPart.opacity || 0.7}"
            >
              {selectedOption.coloredPart.text}
            </span>
          {/if}
        </span>
        {#if selectedOption.description}
          <span class="option-description">{selectedOption.description}</span>
        {/if}
      {:else}
        <span class="placeholder">{placeholder}</span>
      {/if}
    </span>
    <span class="arrow" class:rotated={isOpen}>▼</span>
  </button>

  <!-- Options List -->
  {#if isOpen}
    <div
      class="options-container"
      class:floating={isInBottomSheet}
      class:positioned={isInBottomSheet}
      class:above={floatingPosition === 'above'}
      style:top={isInBottomSheet && floatingStyles.top ? floatingStyles.top : undefined}
      style:bottom={isInBottomSheet && floatingStyles.bottom ? floatingStyles.bottom : undefined}
      style:left={isInBottomSheet && floatingStyles.left ? floatingStyles.left : undefined}
      style:right={isInBottomSheet && floatingStyles.right ? floatingStyles.right : undefined}
      style:width={isInBottomSheet && floatingStyles.width ? floatingStyles.width : undefined}
      style:max-width={isInBottomSheet && floatingStyles.maxWidth ? floatingStyles.maxWidth : undefined}
      style:min-width={isInBottomSheet && floatingStyles.minWidth ? floatingStyles.minWidth : undefined}
      onclick={(e) => e.stopPropagation()}
      role="presentation"
    >
      <!-- Search box -->
      {#if searchable}
        <div class="search-container">
          <input
            type="text"
            class="search-input"
            placeholder={searchPlaceholder}
            value={searchQuery}
            oninput={handleSearchChange}
            autocomplete="off"
          />
        </div>
      {/if}

      <!-- 滚动容器（悬浮模式下） -->
      {#if isInBottomSheet}
        <div
          class="options-wrapper"
          style:max-height={
            floatingStyles.maxHeight
              ? `calc(${floatingStyles.maxHeight} - ${searchable ? '60px' : '0px'})`
              : '300px'
          }
        >
          <div
            class="options-list"
            class:with-scroll={filteredOptions.length > 5}
            role="listbox"
          >
            {#each filteredOptions as option}
              <button
                type="button"
                class="option"
                class:selected={option.value === value}
                onclick={(e) => handleSelect(option.value, e)}
                role="option"
                aria-selected={option.value === value}
              >
                <span class="option-label">
                  {option.label}
                  {#if option.coloredPart}
                    <span
                      class="option-colored-part"
                      style="color: {option.coloredPart.color || 'var(--text-tertiary)'}; opacity: {option.coloredPart.opacity || 0.7}"
                    >
                      {option.coloredPart.text}
                    </span>
                  {/if}
                </span>
                {#if option.description}
                  <span class="option-description">{option.description}</span>
                {/if}
              </button>
            {:else}
              <div class="no-options">{t('common.noOptions')}</div>
            {/each}
          </div>
        </div>
      {:else}
        <!-- 非悬浮模式下的选项列表 -->
        <div
          class="options-list"
          class:with-scroll={filteredOptions.length > 5}
          role="listbox"
          style:max-height={maxHeight ? maxHeight : undefined}
        >
          {#each filteredOptions as option}
            <button
              type="button"
              class="option"
              class:selected={option.value === value}
              onclick={(e) => handleSelect(option.value, e)}
              role="option"
              aria-selected={option.value === value}
            >
              <span class="option-label">
                {option.label}
                {#if option.coloredPart}
                  <span
                    class="option-colored-part"
                    style="color: {option.coloredPart.color || 'var(--text-tertiary)'}; opacity: {option.coloredPart.opacity || 0.7}"
                  >
                    {option.coloredPart.text}
                  </span>
                {/if}
              </span>
              {#if option.description}
                <span class="option-description">{option.description}</span>
              {/if}
            </button>
          {:else}
            <div class="no-options">{t('common.noOptions')}</div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .sliding-list {
    position: relative;
    width: 100%;
  }

  .trigger {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.625rem 0.875rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    color: var(--text-primary);
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .trigger:hover {
    border-color: var(--primary-color);
    background: var(--bg-tertiary);
  }

  .trigger:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  }

  .trigger-label {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
    flex: 1;
    text-align: left;
    overflow: hidden;
  }

  .trigger-label .option-label {
    /* 保持触发器标签的单行显示 */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
  }

  .trigger-label .option-description {
    /* 保持触发器标签的单行显示 */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
  }

  .option-label {
    font-weight: 500;
    color: var(--text-primary);
  }

  .option-description {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .placeholder {
    color: var(--text-tertiary);
    font-style: italic;
  }

  .arrow {
    font-size: 0.7rem;
    color: var(--text-tertiary);
    transition: transform 0.2s ease;
    flex-shrink: 0;
  }

  .arrow.rotated {
    transform: rotate(180deg);
  }

  .options-container {
    position: absolute;
    top: calc(100% + 0.5rem);
    left: 0;
    min-width: 100%;
    width: max-content;
    max-width: min(600px, 90vw); /* 限制最大宽度不超过600px或90%视口宽度 */
    max-height: var(--container-max-height, none);
    z-index: 1000;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15), 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 0;
    /* 非悬浮模式下由 options-list 处理滚动 */
    overflow: visible;
  }

  /* 移动端底部弹窗内悬浮显示 */
  .options-container.floating {
    position: fixed;
    top: auto;
    bottom: auto;
    border-radius: 0.75rem;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3), 0 4px 12px rgba(0, 0, 0, 0.2);
    z-index: 99999;
    /* 确保内容不会溢出容器 */
    overflow: hidden !important;
    -webkit-overflow-scrolling: touch;
    padding: 0;
  }

  /* 悬浮模式下容器内部结构 */
  .options-container.floating .search-container {
    /* 搜索框作为容器的一部分，不使用 sticky */
    padding: 0.5rem;
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-primary);
    border-radius: 0.75rem 0.75rem 0 0;
  }

  /* 悬浮模式下 options-list 独立滚动容器 */
  .options-container.floating .options-wrapper {
    /* 这是真正的滚动容器 - 确保内容不会溢出 */
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
    scrollbar-color: var(--text-tertiary) transparent;
    /* 动态高度在模板中设置 */
    /* 防止内容溢出到容器外部 */
    max-width: 100%;
  }

  .options-container.floating .options-wrapper::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  .options-container.floating .options-wrapper::-webkit-scrollbar-track {
    background: transparent;
  }

  .options-container.floating .options-wrapper::-webkit-scrollbar-thumb {
    background: var(--text-tertiary);
    border-radius: 3px;
  }

  .options-container.floating .options-wrapper::-webkit-scrollbar-thumb:hover {
    background: var(--text-secondary);
  }

  /* options-list 只是内容容器，不处理滚动 */
  .options-container.floating .options-list {
    max-height: none;
    overflow: hidden;
    padding: 0.5rem 0;
    /* 确保选项不会溢出容器 */
    width: 100%;
    box-sizing: border-box;
  }

  /* 超小屏幕悬浮调整 */
  @media (max-width: 480px) {
    .options-container.floating {
      max-height: 40vh;
    }
  }

  .search-container {
    padding: 0.5rem 0.5rem;
    border-bottom: 1px solid var(--border-color);
  }

  .search-input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    outline: none;
    transition: all 0.2s;
  }

  .search-input:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  }

  .search-input::placeholder {
    color: var(--text-tertiary);
    opacity: 0.7;
  }

  .options-list {
    max-height: var(--options-max-height, 280px);
    overflow-y: auto;
    overflow-x: hidden; /* 禁用水平滚动，防止干扰容器滚动 */
    scrollbar-width: thin;
    scrollbar-color: var(--text-tertiary) transparent;
  }

  /* 确保非悬浮模式下容器也不产生滚动条 */
  .options-container:not(.floating) {
    overflow: visible;
  }

  /* 非悬浮模式下 options-list 需要 padding */
  .options-container:not(.floating) .options-list {
    padding: 0.5rem 0;
  }

  .options-list::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  .options-list::-webkit-scrollbar-track {
    background: transparent;
  }

  .options-list::-webkit-scrollbar-thumb {
    background: var(--text-tertiary);
    border-radius: 3px;
  }

  .options-list::-webkit-scrollbar-thumb:hover {
    background: var(--text-secondary);
  }

  .options-list.with-scroll {
    padding-right: 0.25rem;
  }

  .option {
    width: 100%;
    display: flex;
    flex-direction: column;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-size: 0.875rem;
    text-align: left;
    cursor: pointer;
    transition: all 0.15s;
    min-height: 48px;
    position: relative;
    /* 确保选项内容不会溢出 */
    overflow: hidden;
    box-sizing: border-box;
  }

  /* 悬浮模式下选项样式调整 */
  .options-container.floating .option {
    /* 保持一致的宽度约束 */
    max-width: 100%;
  }

  .option-label,
  .option-description {
    display: block;
    /* 移除white-space: nowrap，让长文本换行 */
    overflow-wrap: break-word;
    word-wrap: break-word;
  }

  .option-description {
    margin-top: 0.25rem;
  }

  .option.selected .option-description {
    opacity: 0.8;
  }

  .option:hover {
    background: var(--bg-secondary);
  }

  .option.selected {
    background: rgba(99, 102, 241, 0.1);
    color: var(--primary-color);
    font-weight: 600;
  }

  .option:focus {
    outline: none;
    background: var(--bg-secondary);
  }

  .option-label {
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.4;
  }

  .option.selected .option-label {
    font-weight: 600;
  }

  .option-description {
    font-size: 0.75rem;
    opacity: 0.8;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.4;
  }

  .no-options {
    padding: 1rem;
    text-align: center;
    color: var(--text-tertiary);
    font-style: italic;
  }

  /* Mobile styles */
  @media (max-width: 768px) {
    .trigger {
      padding: 0.375rem 0.625rem;
      font-size: 0.85rem;
      /* 移动端触摸优化，减小最小高度 */
      min-height: 36px;
    }

    /* 移动端选项容器 - 保持常规下拉，避免与ModelSelector的底部弹出冲突 */
    .options-container {
      position: absolute;
      top: calc(100% + 0.5rem);
      left: 0;
      right: 0;
      bottom: auto;
      margin: 0;
      border-radius: 0.75rem;
      width: 100%; /* 继承触发器的宽度 */
      min-width: 100%;
      max-width: 100%; /* 不超出触发器宽度 */
      max-height: var(--container-max-height, 30vh); /* 使用CSS变量，默认为30vh */
      padding: 0.5rem;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
      z-index: 1002; /* 提高z-index，确保在ModelSelector弹窗之上 */
      animation: slideDown 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    @keyframes slideDown {
      from {
        opacity: 0;
        transform: translateY(-8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .options-list {
      max-height: var(--options-max-height, 30vh); /* 使用CSS变量，默认为30vh */
      overflow-y: auto;
    }

    .option {
      padding: 0.625rem 0.875rem;
      font-size: 0.875rem;
      /* 移动端按钮适当减小高度 */
      min-height: 42px;
    }
  }
</style>
