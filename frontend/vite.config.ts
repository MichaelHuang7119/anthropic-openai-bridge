/// <reference types="@sveltejs/kit" />
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      // Proxy API requests to the backend
      // Keep /api prefix when proxying since backend routes use /api prefix
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Don't remove /api prefix - backend routes need it
      },
      // Also proxy the original /v1 endpoints
      '/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
