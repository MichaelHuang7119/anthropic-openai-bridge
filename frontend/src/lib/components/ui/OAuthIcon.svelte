<script lang="ts">
  import github from '$lib/assets/oauth/github.svg?raw';
  import google from '$lib/assets/oauth/google.svg?raw';
  import feishu from '$lib/assets/oauth/feishu.svg?raw';
  import microsoft from '$lib/assets/oauth/microsoft.svg?raw';
  import oidc from '$lib/assets/oauth/oidc.svg?raw';

  const icons: Record<string, string> = {
    github,
    google,
    feishu,
    microsoft,
    oidc
  };

  interface Props {
    provider: string;
    size?: number;
  }

  let { provider, size = 20 }: Props = $props();

  const iconSvg = $derived(icons[provider] || '');
</script>

{#if iconSvg}
  <span class="oauth-icon" style="width: {size}px; height: {size}px;">
    {@html iconSvg}
  </span>
{:else}
  <span class="oauth-icon-fallback" style="width: {size}px; height: {size}px;">
    {provider[0]?.toUpperCase()}
  </span>
{/if}

<style>
  .oauth-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .oauth-icon :global(svg) {
    width: 100%;
    height: 100%;
  }

  .oauth-icon-fallback {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #6b7280;
    color: white;
    font-size: 10px;
    font-weight: 600;
    border-radius: 4px;
  }
</style>
