/// <reference types="@sveltejs/kit" />
import { build, files, version } from '$service-worker';

const CACHE_NAME = `cache-${version}`;
const ASSETS = [
  ...build, // the app itself
  ...files  // everything in `static`
];

self.addEventListener('install', (event) => {
  // Create a new cache and add all files to it
  async function addFilesToCache() {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(ASSETS);
  }

  event.waitUntil(addFilesToCache());
});

self.addEventListener('activate', (event) => {
  // Remove previous cached data from disk
  async function deleteOldCaches() {
    for (const key of await caches.keys()) {
      if (key !== CACHE_NAME) await caches.delete(key);
    }
  }

  event.waitUntil(deleteOldCaches());
});

self.addEventListener('fetch', (event) => {
  // Ignore non-GET requests
  if (event.request.method !== 'GET') return;

  // Ignore API requests - always fetch from network
  if (event.request.url.includes('/api/') || event.request.url.includes('/v1/')) {
    return;
  }

  async function respond() {
    const url = new URL(event.request.url);
    const cache = await caches.open(CACHE_NAME);

    // `build`/`files` can always be served from the cache
    if (ASSETS.includes(url.pathname)) {
      const cachedResponse = await cache.match(event.request);
      if (cachedResponse) {
        return cachedResponse;
      }
    }

    // For everything else, try the network first, but fall back to cache
    try {
      const response = await fetch(event.request);
      
      // Cache successful responses
      if (response.status === 200) {
        cache.put(event.request, response.clone());
      }
      
      return response;
    } catch (error) {
      // If network fails, try cache
      const cachedResponse = await cache.match(event.request);
      if (cachedResponse) {
        return cachedResponse;
      }
      
      throw error;
    }
  }

  event.respondWith(respond());
});

// Handle background sync (optional)
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  // Implement background sync logic here
  console.log('Background sync triggered');
}


