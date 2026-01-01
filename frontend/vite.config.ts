/// <reference types="@sveltejs/kit" />
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

// Get backend port from environment or use default
const backendPort = process.env.BACKEND_PORT || "8001";

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    // Enable HMR (Hot Module Replacement)
    // HMR is enabled by default, but we can configure it explicitly
    hmr: {
      protocol: "ws",
      host: "localhost",
      // Port will be automatically set based on the dev server port
      // When using custom port, HMR will use the same port or a nearby port
      clientPort: undefined, // Let Vite auto-detect the port
    },
    // Watch for file changes (enables hot reload)
    watch: {
      // Use polling mode if native file watching doesn't work
      // Set to true if hot reload doesn't work on your system
      usePolling: process.env.VITE_USE_POLLING === "true",
      // Increase polling interval for better performance
      interval: 1000,
      // Ignore node_modules to improve performance
      ignored: ["**/node_modules/**", "**/.git/**", "**/.svelte-kit/**"],
    },
    // Enable file system watching for hot reload
    fs: {
      // Allow serving files from one level up to the project root
      allow: [".."],
    },
    // Enable strict port checking
    strictPort: false,
    proxy: {
      // Proxy API requests to the backend
      // Only proxy paths that start with /api/ (not /api-keys which is a frontend route)
      "^/api/": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
        // Don't remove /api prefix - backend routes need it
      },
      // Also proxy the original /v1 endpoints
      "^/v1/": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
      // Proxy OAuth endpoints
      "^/oauth/providers": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
      "^/oauth/([^/]+)/login": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
      "^/oauth/([^/]+)/callback": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    // Enable code splitting and optimization
    rollupOptions: {
      output: {
        // Manual chunk splitting for better caching
        manualChunks: (id) => {
          // Vendor chunks
          if (id.includes("node_modules")) {
            // Split large dependencies
            if (id.includes("date-fns")) {
              return "vendor-date-fns";
            }
            // All other node_modules go to vendor chunk
            return "vendor";
          }
          // Route-based code splitting is handled by SvelteKit automatically
        },
        // Optimize chunk file names for better caching
        chunkFileNames: "chunks/[name]-[hash].js",
        entryFileNames: "entries/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash].[ext]",
      },
    },
    // Enable minification
    minify: "esbuild",
    // Source maps for production debugging (optional)
    sourcemap: false,
    // Chunk size warning limit (500kb)
    chunkSizeWarningLimit: 500,
    // Target modern browsers for smaller bundle
    target: "esnext",
    // CSS code splitting
    cssCodeSplit: true,
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ["date-fns"],
  },
});
