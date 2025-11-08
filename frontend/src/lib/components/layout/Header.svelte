<script lang="ts">
  export let title: string = 'Anthropic OpenAI Bridge';
  export let subtitle: string = '';
</script>

<header class="header">
  <div class="container">
    <div class="brand">
      <h1>{title}</h1>
      {#if subtitle}
        <p class="subtitle">{subtitle}</p>
      {/if}
    </div>
    <nav class="nav">
      <slot name="nav" />
    </nav>
  </div>
</header>

<style>
  .header {
    background: #fff;
    border-bottom: 1px solid #e0e0e0;
    padding: 1rem 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .brand h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #1a1a1a;
  }

  .subtitle {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: #666;
  }

  .nav {
    display: flex;
    gap: 1rem;
    align-items: center;
  }
</style>
