<script lang="ts">
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
  }

  let {
    options = [],
    value = $bindable(""),
    placeholder = "请选择",
    onChange
  }: Props = $props();

  let isOpen = $state(false);
  let listElement: HTMLDivElement;

  // Find selected option
  let selectedOption = $derived(
    options.find(opt => opt.value === value)
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
    onChange?.(optionValue);
    // Prevent event bubbling to parent components
    if (event) {
      event.stopPropagation();
    }
  }

  function handleClickOutside(event: MouseEvent) {
    if (isOpen && listElement && !listElement.contains(event.target as Node)) {
      isOpen = false;
    }
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
    <div class="options-container">
      <div
        class="options-list"
        class:with-scroll={options.length > 5}
        role="listbox"
      >
        {#each options as option}
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
          <div class="no-options">暂无选项</div>
        {/each}
      </div>
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
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
  }

  .trigger-label .option-description {
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
    max-width: 600px;
    z-index: 1000;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15), 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 0.5rem 0;
  }

  .options-list {
    max-height: 280px;
    overflow-y: auto;
    overflow-x: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--text-tertiary) transparent;
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
  }

  .option-label,
  .option-description {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
      padding: 0.5rem 0.75rem;
      font-size: 0.85rem;
    }

    .options-list {
      max-height: 240px;
    }

    .option {
      padding: 0.625rem 0.875rem;
      font-size: 0.85rem;
    }
  }
</style>
