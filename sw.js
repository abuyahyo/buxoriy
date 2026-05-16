// Service Worker for Buxoriy
// CACHE name embeds a version that build_index.py bumps when data.json changes.
// On version bump the browser sees a new sw.js, installs it, and the page
// shows an "Update available" banner.

const CACHE = 'buxoriy-v1778940828';

const ASSETS = [
  './',
  './index.html',
  './index.json',
  './data.json',
  './apple-touch-icon.png',
  './manifest.json'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS))
  );
  // Don't auto-skipWaiting — let the page trigger it when user clicks the
  // update banner, so we control the reload moment.
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // Only handle same-origin GET requests
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  // Skip Range requests (audio/video seeking) and the SW file itself
  if (e.request.headers.get('range')) return;
  if (url.pathname.endsWith('/sw.js')) return;
  e.respondWith(staleWhileRevalidate(e.request));
});

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request).then(response => {
    if (response && response.ok && response.status === 200) {
      cache.put(request, response.clone()).catch(() => {});
    }
    return response;
  }).catch(() => cached);
  return cached || fetchPromise;
}

// Page can ask the waiting SW to take over immediately.
self.addEventListener('message', e => {
  if (e.data === 'skip-waiting') self.skipWaiting();
});
