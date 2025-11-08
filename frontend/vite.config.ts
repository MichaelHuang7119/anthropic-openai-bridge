/// <reference types="@sveltejs/kit" />
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      // Proxy API requests to the backend
      // Only proxy paths that start with /api/ (not /api-keys which is a frontend route)
      '^/api/': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Don't remove /api prefix - backend routes need it
      },
      // Also proxy the original /v1 endpoints
      '^/v1/': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
