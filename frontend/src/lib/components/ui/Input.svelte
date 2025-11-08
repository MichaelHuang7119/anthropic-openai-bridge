<script lang="ts">
  export let type: string = 'text';
  export let value: string = '';
  export let placeholder: string = '';
  export let disabled: boolean = false;
  export let required: boolean = false;
  export let id: string | undefined = undefined;
</script>

<input
  {id}
  {type}
  bind:value
  {placeholder}
  {disabled}
  {required}
  class="input"
  on:input
  on:blur
  on:focus
/>

<style>
  .input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    font-size: 1rem;
    font-family: inherit;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .input:focus {
    outline: none;
    border-color: #007bff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
  }

  .input:disabled {
    background-color: #e9ecef;
    opacity: 1;
    cursor: not-allowed;
  }
</style>
