<script lang="ts">
  let {
    value = $bindable(''),
    oninput = undefined,
    onblur = undefined,
    onfocus = undefined,
    ...restProps
  } = $props();
</script>

<input
  bind:value
  {...restProps}
  {oninput}
  {onblur}
  {onfocus}
/>

<style>
  .input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--input-border, var(--border-color, #ced4da));
    border-radius: 0.25rem;
    font-size: 1rem;
    font-family: inherit;
    transition: border-color 0.2s, box-shadow 0.2s;
    background: var(--input-bg, var(--bg-primary, white));
    color: var(--text-primary, #333);
  }

  .input:focus {
    outline: none;
    border-color: var(--input-border-focus, var(--primary-color, #007bff));
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
  }

  :global([data-theme="dark"]) .input:focus {
    box-shadow: 0 0 0 0.2rem rgba(31, 111, 235, 0.3);
  }

  .input:disabled {
    background-color: var(--bg-tertiary, #e9ecef);
    opacity: 1;
    cursor: not-allowed;
  }

  :global([data-theme="dark"]) .input:disabled {
    background-color: #161b22;
    opacity: 0.5;
  }
</style>
