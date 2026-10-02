/* PainCave ERG · service worker
   L'app funciona sense connexió: es guarda una còpia de cada fitxer propi.
   Sempre prova primer la xarxa (així, quan publiques una versió nova, es fa servir de seguida)
   i només si no n'hi ha fa servir la còpia. Les fonts de Google es guarden en memòria cau. */
const CACHE = 'paincave-v3';
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './icon-maskable-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // fonts: primer la còpia (no canvien mai)
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com'){
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {
      const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); return r;
    })));
    return;
  }
  if (url.origin !== location.origin) return;   // Google Drive, inici de sessió, etc.: directe a la xarxa
  e.respondWith(fetch(req).then(r => {
    if (r.ok){ const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); }
    return r;
  }).catch(() => caches.match(req, { ignoreSearch: true }).then(hit => hit || caches.match('./index.html'))));
});
