const CACHE_PREFIX = "oxomiai-local-";
const CACHE_NAME = `${CACHE_PREFIX}v1`;
const PRECACHE_URLS = ["/data/destinations.json", "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        // Only prune our own caches: WebLLM keeps the downloaded model weights in
        // separate caches, and deleting those would force a ~1 GB re-download.
        Promise.all(
          keys
            .filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
  );
  self.clients.claim();
});

// Network-first: always prefer a fresh response so a new deploy is visible
// immediately. Cache is only a fallback for when the network is unavailable.
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  // Model weights/wasm come from Hugging Face and GitHub and are cached by
  // WebLLM itself; caching them here too would double the storage used.
  if (new URL(event.request.url).origin !== self.location.origin) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
