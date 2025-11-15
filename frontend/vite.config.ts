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
  },
  build: {
    // Enable code splitting and optimization
    rollupOptions: {
      output: {
        // Manual chunk splitting for better caching
        manualChunks: (id) => {
          // Vendor chunks
          if (id.includes('node_modules')) {
            // Split large dependencies
            if (id.includes('date-fns')) {
              return 'vendor-date-fns';
            }
            // All other node_modules go to vendor chunk
            return 'vendor';
          }
          // Route-based code splitting is handled by SvelteKit automatically
        },
        // Optimize chunk file names for better caching
        chunkFileNames: 'chunks/[name]-[hash].js',
        entryFileNames: 'entries/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    },
    // Enable minification
    minify: 'esbuild',
    // Source maps for production debugging (optional)
    sourcemap: false,
    // Chunk size warning limit (500kb)
    chunkSizeWarningLimit: 500,
    // Target modern browsers for smaller bundle
    target: 'esnext',
    // CSS code splitting
    cssCodeSplit: true
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ['date-fns']
  }
});
