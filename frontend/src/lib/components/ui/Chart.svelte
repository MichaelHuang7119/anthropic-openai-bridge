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

  export let type: ChartType = 'bar';
  export let data: ChartConfiguration['data'];
  export let options: ChartConfiguration['options'] = {};
  export let height: number = 300;
  export let width: number | undefined = undefined;

  let canvas: HTMLCanvasElement;
  let chart: ChartJS | null = null;

  onMount(() => {
    if (canvas) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        chart = new ChartJS(ctx, {
          type,
          data,
          options: {
            responsive: true,
            maintainAspectRatio: false,
            ...options
          }
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

  // 获取图表实例
  export function getChart(): ChartJS | null {
    return chart;
  }
</script>

<div class="chart-container" style="height: {height}px; width: {width ? width + 'px' : '100%'};">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .chart-container {
    position: relative;
    width: 100%;
  }

  canvas {
    max-width: 100%;
  }
</style>
