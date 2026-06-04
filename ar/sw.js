// Service Worker for Sahih al-Bukhari Arabic edition (scope: /buxoriy/ar/)
// CACHE name embeds a version that build_ar.py bumps when data.json changes.

const CACHE = 'buxoriy-ar-v1780608082';

const ASSETS = [
  './',
  './index.html',
  './index.json',
  './data.json',
  './manifest.json',
  '../icon-192.png',
  '../icon-512.png',
  '../apple-touch-icon.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS).catch(() => {}))
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE && k.startsWith('buxoriy-ar-')).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (e.request.headers.get('range')) return;
  if (url.pathname.endsWith('/sw.js')) return;
  // Only handle requests inside /buxoriy/ar/ scope or shared icons
  e.respondWith(staleWhileRevalidate(e.request));
});

async function staleWhileRevalidate(request){
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request).then(response => {
    if (response && response.ok && response.status === 200){
      cache.put(request, response.clone()).catch(() => {});
    }
    return response;
  }).catch(() => cached);
  return cached || fetchPromise;
}

self.addEventListener('message', e => {
  if (e.data && e.data.type === 'skip-waiting') self.skipWaiting();
});

