import { writable } from 'svelte/store';
import type { GlobalConfig } from '$types/config';

export const globalConfig = writable<GlobalConfig | null>(null);
