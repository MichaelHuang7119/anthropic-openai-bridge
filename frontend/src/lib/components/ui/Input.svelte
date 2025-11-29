<script lang="ts">
  interface Props {
    type?: string;
    placeholder?: string;
    disabled?: boolean;
    required?: boolean;
    id?: string;
    class?: string;
    name?: string;
    readonly?: boolean;
    autocomplete?: string | undefined;
    maxlength?: number;
    minlength?: number;
    min?: string | number;
    max?: string | number;
    step?: string | number;
    pattern?: string;
    title?: string;
    'aria-label'?: string;
    'aria-describedby'?: string;
    'aria-labelledby'?: string;
    oninput?: (e: Event) => void;
    onblur?: (e: FocusEvent) => void;
    onfocus?: (e: FocusEvent) => void;
    onchange?: (e: Event) => void;
    onclick?: (e: MouseEvent) => void;
    onkeydown?: (e: KeyboardEvent) => void;
    onkeyup?: (e: KeyboardEvent) => void;
    onkeypress?: (e: KeyboardEvent) => void;
    value?: string;
  }

  let {
    type = 'text',
    placeholder = '',
    disabled = false,
    required = false,
    id,
    class: className = '',
    name,
    readonly = false,
    autocomplete = undefined as any,
    maxlength,
    minlength,
    min,
    max,
    step,
    pattern,
    title,
    'aria-label': ariaLabel,
    'aria-describedby': ariaDescribedby,
    'aria-labelledby': ariaLabelledby,
    oninput,
    onblur,
    onfocus,
    onchange,
    onclick,
    onkeydown,
    onkeyup,
    onkeypress,
    value = $bindable('')
  }: Props = $props();
</script>

<input
  {...({
    id,
    type,
    placeholder,
    disabled,
    required,
    name,
    readonly,
    ...(autocomplete ? { autocomplete } : {}),
    maxlength,
    minlength,
    min,
    max,
    step,
    pattern,
    title,
    ...(ariaLabel ? { 'aria-label': ariaLabel } : {}),
    ...(ariaDescribedby ? { 'aria-describedby': ariaDescribedby } : {}),
    ...(ariaLabelledby ? { 'aria-labelledby': ariaLabelledby } : {})
  } as any)}
  bind:value
  class="input {className}"
  {oninput}
  {onblur}
  {onfocus}
  {onchange}
  {onclick}
  {onkeydown}
  {onkeyup}
  {onkeypress}
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
