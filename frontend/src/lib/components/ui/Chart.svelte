<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    Chart as ChartJS,
    type ChartConfiguration,
    type ChartType,
    registerables
  } from 'chart.js';
  import 'chartjs-adapter-date-fns';

  ChartJS.register(...registerables);

  let { type = 'bar', data, options = {}, height = 300, width = undefined, class: className = '' }: {
    type?: ChartType;
    data: ChartConfiguration['data'];
    options?: ChartConfiguration['options'];
    height?: number;
    width?: number | undefined;
    class?: string;
  } = $props();

  let canvas: HTMLCanvasElement;
  let chart: ChartJS | null = null;

  // 递归合并配置的工具函数
  function deepMerge(target: any, source: any): any {
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        target[key] = deepMerge(target[key] || {}, source[key]);
      } else {
        target[key] = source[key];
      }
    }
    return target;
  }

  // 默认配置
  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 15,
          font: {
            size: 12,
            family: 'system-ui, -apple-system, sans-serif'
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleFont: {
          size: 14,
          weight: 'bold' as const
        },
        bodyFont: {
          size: 13
        },
        cornerRadius: 8
      }
    },
    scales: {
      x: {
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          font: {
            size: 11
          },
          color: 'var(--text-secondary, #6b7280)'
        }
      },
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          font: {
            size: 11
          },
          color: 'var(--text-secondary, #6b7280)'
        }
      }
    }
  };

  onMount(() => {
    if (canvas) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        // 深拷贝默认配置，避免引用问题
        const mergedOptions = JSON.parse(JSON.stringify(defaultOptions));

        // 递归合并用户自定义选项
        const finalOptions = deepMerge(mergedOptions, options);

        chart = new ChartJS(ctx, {
          type,
          data,
          options: finalOptions
        });
      }
    }
  });

  onDestroy(() => {
    if (chart) {
      chart.destroy();
      chart = null;
    }
  });

  // 更新图表数据
  export function updateChart(newData: ChartConfiguration['data']) {
    if (chart) {
      chart.data = newData;
      chart.update();
    }
  }

  // 更新图表选项
  export function updateOptions(newOptions: ChartConfiguration['options']) {
    if (chart) {
      chart.options = { ...chart.options, ...newOptions };
      chart.update();
    }
  }

  // 重新渲染图表
  export function render() {
    if (chart) {
      chart.update();
    }
  }

  // 获取图表实例
  export function getChart(): ChartJS | null {
    return chart;
  }

  // 下载图表为图片
  export function downloadImage(filename: string = 'chart.png') {
    if (chart) {
      const url = chart.toBase64Image();
      const link = document.createElement('a');
      link.download = filename;
      link.href = url;
      link.click();
    }
  }
</script>

<div
  class="chart-container {className}"
  style="height: {height}px; width: {width ? width + 'px' : '100%'}; position: relative;"
>
  <canvas bind:this={canvas}></canvas>
  {#if !data || (data.datasets && data.datasets.length === 0)}
    <div class="chart-empty">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
      </svg>
      <p>No data available</p>
    </div>
  {/if}
</div>

<style>
  .chart-container {
    position: relative;
    width: 100%;
    background: var(--card-bg, white);
    border-radius: var(--radius-lg, 0.5rem);
    padding: var(--space-4);
    box-shadow: var(--shadow-sm, 0 1px 3px 0 rgba(0, 0, 0, 0.1));
  }

  canvas {
    max-width: 100%;
    height: auto !important;
  }

  .chart-empty {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    color: var(--text-secondary, #9ca3af);
    pointer-events: none;
  }

  .chart-empty svg {
    opacity: 0.5;
  }

  .chart-empty p {
    margin: 0;
    font-size: var(--font-size-sm, 0.875rem);
    font-weight: 500;
  }

  /* 暗黑主题 */
  :global([data-theme="dark"]) .chart-container {
    background: var(--card-bg, #1f2937);
    box-shadow: var(--shadow-sm, 0 1px 3px 0 rgba(0, 0, 0, 0.3));
  }

  :global([data-theme="dark"]) .chart-empty {
    color: var(--text-secondary, #6b7280);
  }

  /* 响应式调整 */
  @media (max-width: 768px) {
    .chart-container {
      padding: var(--space-3);
    }

    :global(.chart-container .chartjs-legend) {
      font-size: 0.75rem;
    }

    :global(.chart-container canvas) {
      max-height: 250px !important;
    }
  }
</style>
