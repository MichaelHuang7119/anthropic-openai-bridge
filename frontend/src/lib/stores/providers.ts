import { writable, derived } from "svelte/store";
import type { Provider } from "$types/provider";

export const providers = writable<Provider[]>([]);
export const enabledProviders = derived(providers, ($providers) =>
  $providers.filter((p) => p.enabled),
);

export const providerStats = derived(providers, ($providers) => {
  return {
    total: $providers.length,
    enabled: $providers.filter((p) => p.enabled).length,
    disabled: $providers.filter((p) => !p.enabled).length,
  };
});
