<script lang="ts">
  interface Column<T> {
    key: keyof T;
    title: string;
    sortable?: boolean;
    filterable?: boolean;
    width?: string;
    align?: 'left' | 'center' | 'right';
    render?: (value: any, row: T) => any;
  }

  interface Props<T> {
    data?: () => T[];
    columns?: () => Column<T>[];
    keyField?: keyof T;
    sortable?: boolean;
    filterable?: boolean;
    expandable?: boolean;
    pageSize?: number;
    class?: string;
    loading?: boolean;
    emptyMessage?: string;
    onRowClick?: (row: T, index: number) => void;
    onExpand?: (row: T, index: number) => any;
  }

  let {
    data = () => [],
    columns = () => [],
    keyField,
    sortable = true,
    filterable = false,
    expandable = false,
    pageSize = 10,
    class: className = '',
    loading = false,
    emptyMessage = 'No data available',
    onRowClick,
    onExpand
  }: Props<any> = $props();

  // 状态管理
  let sortColumn = $state<string>('');
  let sortDirection = $state<'asc' | 'desc'>('asc');
  let filterText = $state<string>('');
  let expandedRows = $state<Set<any>>(new Set());
  let currentPage = $state<number>(1);

  // 计算排序后的数据
  const sortedData = $derived(() => {
    if (!sortable || !sortColumn) return data();

    const dataArray = data();
    return [...dataArray].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (aVal === bVal) return 0;

      let comparison = 0;
      if (aVal < bVal) comparison = -1;
      if (aVal > bVal) comparison = 1;

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  });

  // 计算筛选后的数据
  const filteredData = $derived(() => {
    if (!filterable || !filterText.trim()) return sortedData();

    const lowerFilter = filterText.toLowerCase();
    const sortedArray = sortedData();
    const columnsArray = columns();
    return sortedArray.filter((row) => {
      return columnsArray.some((col) => {
        const value = row[col.key];
        return value && value.toString().toLowerCase().includes(lowerFilter);
      });
    });
  });

  // 计算分页数据
  const paginatedData = $derived(() => {
    const dataArray = filteredData();
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return dataArray.slice(start, end);
  });

  // 计算总页数
  const totalPages = $derived(() => {
    return Math.ceil(filteredData().length / pageSize);
  });

  // 排序处理
  function handleSort(column: Column<any>) {
    if (!sortable || !column.sortable) return;

    if (sortColumn === column.key) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      sortColumn = column.key as string;
      sortDirection = 'asc';
    }
  }

  // 切换行展开
  function _toggleExpand(row: any) {
    const keyValue = keyField ? row[keyField] : JSON.stringify(row);
    if (expandedRows.has(keyValue)) {
      expandedRows.delete(keyValue);
    } else {
      expandedRows.add(keyValue);
    }
    expandedRows = new Set(expandedRows);
  }

  // 检查行是否展开
  function isExpanded(row: any): boolean {
    const keyValue = keyField ? row[keyField] : JSON.stringify(row);
    return expandedRows.has(keyValue);
  }

  // 分页处理
  function goToPage(page: number) {
    if (page >= 1 && page <= totalPages()) {
      currentPage = page;
    }
  }

  // 获取排序图标
  function getSortIcon(column: Column<any>): string {
    if (!sortable || !column.sortable || sortColumn !== column.key) {
      return '↕';
    }
    return sortDirection === 'asc' ? '↑' : '↓';
  }

  // 获取对齐样式
  function getAlignClass(align?: string): string {
    return align ? `text-${align}` : 'text-left';
  }
</script>

<div class="data-table-container {className}">
  {#if filterable}
    <div class="table-controls">
      <div class="filter-input">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46"></polygon>
        </svg>
        <input
          type="text"
          placeholder="Filter data..."
          bind:value={filterText}
          class="filter-field"
        />
      </div>
    </div>
  {/if}

  <div class="table-wrapper">
    <table class="data-table">
      <thead>
        <tr>
          {#each columns() as column (column.key)}
            <th
              class="table-header {getAlignClass(column.align)} {sortable && column.sortable ? 'sortable' : ''}"
              style={column.width ? `width: ${column.width}` : ''}
              onclick={() => handleSort(column)}
            >
              <div class="header-content">
                <span class="column-title">{column.title}</span>
                {#if sortable && column.sortable}
                  <span class="sort-icon">{getSortIcon(column)}</span>
                {/if}
              </div>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#if loading}
          {@const cols = columns()}
          <tr>
            <td colspan={cols.length} class="loading-cell">
              <div class="loading-spinner"></div>
              <span>Loading...</span>
            </td>
          </tr>
        {:else if paginatedData().length === 0}
          {@const cols = columns()}
          <tr>
            <td colspan={cols.length} class="empty-cell">
              {emptyMessage}
            </td>
          </tr>
        {:else}
          {@const cols = columns()}
          {@const data = paginatedData()}
          {#each data as row, i}
            {@const originalIndex = (currentPage - 1) * pageSize + i}
            <tr
              class="table-row {onRowClick ? 'clickable' : ''}"
              onclick={() => onRowClick?.(row, originalIndex)}
            >
              {#each cols as column (column.key)}
                <td class="table-cell {getAlignClass(column.align)}">
                  {#if column.render}
                    {@render column.render(row[column.key], row)}
                  {:else}
                    {row[column.key]}
                  {/if}
                </td>
              {/each}
            </tr>
            {#if expandable && isExpanded(row)}
              <tr class="expandable-row">
                <td colspan={cols.length} class="expanded-content">
                  {@render onExpand?.(row, originalIndex)}
                </td>
              </tr>
            {/if}
          {/each}
        {/if}
      </tbody>
    </table>
  </div>

  {#if totalPages() > 1}
    <div class="table-pagination">
      <button
        class="page-btn"
        disabled={currentPage === 1}
        onclick={() => goToPage(currentPage - 1)}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        Previous
      </button>

      <div class="page-numbers">
        {#each Array.from({ length: totalPages() }, (_, i) => i + 1) as page}
          {#if page === 1 || page === totalPages() || (page >= currentPage - 1 && page <= currentPage + 1)}
            <button
              class="page-number {currentPage === page ? 'active' : ''}"
              onclick={() => goToPage(page)}
            >
              {page}
            </button>
          {:else if page === currentPage - 2 || page === currentPage + 2}
            <span class="page-ellipsis">...</span>
          {/if}
        {/each}
      </div>

      <button
        class="page-btn"
        disabled={currentPage === totalPages()}
        onclick={() => goToPage(currentPage + 1)}
      >
        Next
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
    </div>
  {/if}
</div>

<style>
  .data-table-container {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .table-controls {
    display: flex;
    justify-content: flex-end;
  }

  .filter-input {
    position: relative;
    display: flex;
    align-items: center;
  }

  .filter-input svg {
    position: absolute;
    left: var(--space-3);
    color: var(--text-secondary, #6b7280);
    pointer-events: none;
  }

  .filter-field {
    padding: var(--space-2) var(--space-3) var(--space-2) var(--space-10);
    border: 1px solid var(--border-color, #e5e7eb);
    border-radius: var(--radius-md, 0.375rem);
    background: var(--card-bg, white);
    color: var(--text-primary, #1f2937);
    font-size: var(--font-size-sm, 0.875rem);
    transition: all 0.2s;
    width: 250px;
  }

  .filter-field:focus {
    outline: none;
    border-color: var(--primary-500, #3b82f6);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .table-wrapper {
    overflow-x: auto;
    border: 1px solid var(--border-color, #e5e7eb);
    border-radius: var(--radius-lg, 0.5rem);
    background: var(--card-bg, white);
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm, 0.875rem);
  }

  .table-header {
    padding: var(--space-3) var(--space-4);
    background: var(--bg-tertiary, #f9fafb);
    color: var(--text-primary, #374151);
    font-weight: 600;
    text-align: left;
    border-bottom: 2px solid var(--border-color, #e5e7eb);
    white-space: nowrap;
    user-select: none;
  }

  .table-header.sortable {
    cursor: pointer;
    transition: background 0.2s;
  }

  .table-header.sortable:hover {
    background: var(--bg-tertiary, #f3f4f6);
  }

  .header-content {
    display: flex;
    align-items: center;
    gap: var(--space-1);
  }

  .sort-icon {
    font-size: 0.75rem;
    color: var(--text-secondary, #9ca3af);
  }

  .table-row {
    border-bottom: 1px solid var(--border-color, #e5e7eb);
    transition: background 0.2s;
  }

  .table-row.clickable {
    cursor: pointer;
  }

  .table-row.clickable:hover {
    background: var(--bg-tertiary, #f9fafb);
  }

  .table-cell {
    padding: var(--space-3) var(--space-4);
    color: var(--text-secondary, #6b7280);
    vertical-align: middle;
  }

  .text-left {
    text-align: left;
  }

  .text-center {
    text-align: center;
  }

  .text-right {
    text-align: right;
  }

  .expandable-row {
    background: var(--bg-tertiary, #f9fafb);
  }

  .expanded-content {
    padding: var(--space-4);
    border-bottom: 1px solid var(--border-color, #e5e7eb);
  }

  .loading-cell,
  .empty-cell {
    padding: var(--space-8);
    text-align: center;
    color: var(--text-secondary, #9ca3af);
  }

  .loading-spinner {
    display: inline-block;
    width: 24px;
    height: 24px;
    border: 3px solid var(--border-color, #e5e7eb);
    border-top-color: var(--primary-500, #3b82f6);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-right: var(--space-2);
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .table-pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2);
  }

  .page-btn {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--border-color, #e5e7eb);
    background: var(--card-bg, white);
    color: var(--text-primary, #374151);
    border-radius: var(--radius-md, 0.375rem);
    font-size: var(--font-size-sm, 0.875rem);
    cursor: pointer;
    transition: all 0.2s;
  }

  .page-btn:hover:not(:disabled) {
    background: var(--bg-tertiary, #f9fafb);
  }

  .page-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-numbers {
    display: flex;
    gap: var(--space-1);
  }

  .page-number {
    min-width: 2rem;
    height: 2rem;
    padding: 0 var(--space-2);
    border: 1px solid var(--border-color, #e5e7eb);
    background: var(--card-bg, white);
    color: var(--text-primary, #374151);
    border-radius: var(--radius-md, 0.375rem);
    font-size: var(--font-size-sm, 0.875rem);
    cursor: pointer;
    transition: all 0.2s;
  }

  .page-number:hover {
    background: var(--bg-tertiary, #f9fafb);
  }

  .page-number.active {
    background: var(--primary-500, #3b82f6);
    color: white;
    border-color: var(--primary-500, #3b82f6);
  }

  .page-ellipsis {
    display: flex;
    align-items: center;
    padding: 0 var(--space-1);
    color: var(--text-secondary, #9ca3af);
  }

  /* 暗黑主题 */
  :global([data-theme="dark"]) .filter-field {
    background: var(--card-bg, #1f2937);
    border-color: var(--border-color, #374151);
    color: var(--text-primary, #f9fafb);
  }

  :global([data-theme="dark"]) .filter-field:focus {
    border-color: var(--primary-500, #3b82f6);
  }

  :global([data-theme="dark"]) .table-wrapper {
    background: var(--card-bg, #1f2937);
    border-color: var(--border-color, #374151);
  }

  :global([data-theme="dark"]) .table-header {
    background: var(--bg-tertiary, #111827);
    color: var(--text-primary, #f9fafb);
    border-bottom-color: var(--border-color, #374151);
  }

  :global([data-theme="dark"]) .table-header.sortable:hover {
    background: var(--bg-tertiary, #1f2937);
  }

  :global([data-theme="dark"]) .table-row {
    border-bottom-color: var(--border-color, #374151);
  }

  :global([data-theme="dark"]) .table-row.clickable:hover {
    background: var(--bg-tertiary, #1f2937);
  }

  :global([data-theme="dark"]) .table-cell {
    color: var(--text-secondary, #d1d5db);
  }

  :global([data-theme="dark"]) .expandable-row {
    background: var(--bg-tertiary, #111827);
  }

  :global([data-theme="dark"]) .loading-spinner {
    border-color: var(--border-color, #374151);
  }

  :global([data-theme="dark"]) .page-btn {
    background: var(--card-bg, #1f2937);
    border-color: var(--border-color, #374151);
    color: var(--text-primary, #f9fafb);
  }

  :global([data-theme="dark"]) .page-btn:hover:not(:disabled) {
    background: var(--bg-tertiary, #111827);
  }

  :global([data-theme="dark"]) .page-number {
    background: var(--card-bg, #1f2937);
    border-color: var(--border-color, #374151);
    color: var(--text-primary, #f9fafb);
  }

  :global([data-theme="dark"]) .page-number:hover {
    background: var(--bg-tertiary, #111827);
  }

  /* 响应式设计 */
  @media (max-width: 768px) {
    .filter-field {
      width: 100%;
    }

    .table-header,
    .table-cell {
      padding: var(--space-2) var(--space-3);
      font-size: var(--font-size-xs, 0.75rem);
    }

    .table-pagination {
      flex-wrap: wrap;
    }

    .page-numbers {
      order: -1;
      width: 100%;
      justify-content: center;
    }
  }
</style>
