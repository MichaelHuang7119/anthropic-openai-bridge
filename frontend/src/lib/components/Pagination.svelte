<script lang="ts">
  import { tStore } from "$stores/language";

  const t = $derived($tStore);

  let {
    currentPage = 1,
    totalPages = 1,
    total = 0,
    pageSize = 10,
    onPageChange,
  } = $props<{
    currentPage?: number;
    totalPages?: number;
    total?: number;
    pageSize?: number;
    onPageChange?: (page: number) => void;
  }>();

  let pageInput = $state(currentPage);

  $effect(() => {
    pageInput = currentPage;
  });

  function goToPage(page: number) {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
      onPageChange?.(page);
    }
  }

  function handlePageInput() {
    if (pageInput >= 1 && pageInput <= totalPages) {
      goToPage(pageInput);
    }
  }

  function getPageNumbers(): (number | string)[] {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible + 2) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);

      const start = Math.max(2, currentPage - Math.floor(maxVisible / 2));
      const end = Math.min(totalPages - 1, currentPage + Math.floor(maxVisible / 2));

      if (start > 2) {
        pages.push("...");
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      if (end < totalPages - 1) {
        pages.push("...");
      }

      pages.push(totalPages);
    }

    return pages;
  }

  function getStartIndex(): number {
    return total > 0 ? (currentPage - 1) * pageSize + 1 : 0;
  }

  function getEndIndex(): number {
    return Math.min(currentPage * pageSize, total);
  }
</script>

{#if total > 0}
  <div class="pagination-container">
    <div class="pagination-info">
      <span>
        {getStartIndex()} - {getEndIndex()} / {total}
      </span>
    </div>

    <div class="pagination-controls">
      <button
        class="pagination-btn"
        onclick={() => goToPage(1)}
        disabled={currentPage === 1}
        title={t("pagination.firstPage")}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="11 17 6 12 11 7"></polyline>
          <polyline points="18 17 13 12 18 7"></polyline>
        </svg>
      </button>

      <button
        class="pagination-btn"
        onclick={() => goToPage(currentPage - 1)}
        disabled={currentPage === 1}
        title={t("pagination.previousPage")}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>

      <div class="page-numbers">
        {#each getPageNumbers() as page}
          {#if page === "..."}
            <span class="page-ellipsis">...</span>
          {:else}
            <button
              class="page-number"
              class:active={page === currentPage}
              onclick={() => goToPage(page as number)}
            >
              {page}
            </button>
          {/if}
        {/each}
      </div>

      <button
        class="pagination-btn"
        onclick={() => goToPage(currentPage + 1)}
        disabled={currentPage === totalPages}
        title={t("pagination.nextPage")}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>

      <button
        class="pagination-btn"
        onclick={() => goToPage(totalPages)}
        disabled={currentPage === totalPages}
        title={t("pagination.lastPage")}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="13 17 18 12 13 7"></polyline>
          <polyline points="6 17 11 12 6 7"></polyline>
        </svg>
      </button>

      <div class="page-jump">
        <span>{t("pagination.jumpTo")}</span>
        <input
          type="number"
          min="1"
          max={totalPages}
          bind:value={pageInput}
          onchange={handlePageInput}
          class="page-input"
        />
        <span>{t("pagination.page")}</span>
      </div>
    </div>
  </div>
{/if}

<style>
  .pagination-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: var(--bg-primary, white);
    border-top: 1px solid var(--border-color, #e0e0e0);
    flex-wrap: wrap;
    gap: 1rem;
  }

  .pagination-info {
    color: var(--text-secondary, #666);
    font-size: 0.875rem;
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .pagination-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.375rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #333);
    cursor: pointer;
    transition: all 0.2s;
  }

  .pagination-btn:hover:not(:disabled) {
    background: var(--bg-hover, #f5f5f5);
    border-color: var(--primary-color, #007bff);
    color: var(--primary-color, #007bff);
  }

  .pagination-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-numbers {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .page-number {
    min-width: 32px;
    height: 32px;
    padding: 0 0.5rem;
    border: 1px solid transparent;
    border-radius: 0.375rem;
    background: transparent;
    color: var(--text-primary, #333);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .page-number:hover {
    background: var(--bg-hover, #f5f5f5);
  }

  .page-number.active {
    background: var(--primary-color, #007bff);
    color: white;
    border-color: var(--primary-color, #007bff);
  }

  .page-ellipsis {
    padding: 0 0.5rem;
    color: var(--text-secondary, #666);
  }

  .page-jump {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--text-secondary, #666);
    font-size: 0.875rem;
  }

  .page-input {
    width: 50px;
    height: 28px;
    padding: 0 0.5rem;
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.375rem;
    text-align: center;
    font-size: 0.875rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #333);
  }

  .page-input:focus {
    outline: none;
    border-color: var(--primary-color, #007bff);
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
  }

  /* Hide number input spinners */
  .page-input::-webkit-inner-spin-button,
  .page-input::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  .page-input[type="number"] {
    -moz-appearance: textfield;
    appearance: textfield;
  }
</style>
