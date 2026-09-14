/* Only exact SUP paths reach respondWith. The root scope also covers future restaurants. */
const SUP = __SUP_MANIFEST__;
const SUP_CACHE = 'sup-menu-' + SUP.revision.stamp;
const SUP_STATE = 'sup-cache-state';
const SUP_FILES = new Set(SUP.files);
const supPath = url => SUP.aliases[url.pathname] || url.pathname;
const supFull = path => path.startsWith('/img/full/') || (path.startsWith('/img/var/') && !path.endsWith('-thumb.jpg'));
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    // No cache:'reload': the page downloaded these seconds ago and they are still fresh,
    // so reloading re-fetched the whole document while the diner was scrolling.
    if (SUP.enabled) await (await caches.open(SUP_CACHE)).addAll(SUP.precache);
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    await (await caches.open(SUP_STATE)).put('/sup-active', new Response(SUP.enabled ? SUP_CACHE : 'disabled'));
    await Promise.all((await caches.keys()).filter(k => k.startsWith('sup-') && k !== SUP_STATE && (!SUP.enabled || k !== SUP_CACHE)).map(k => caches.delete(k)));
    if (!SUP.enabled) { await self.registration.unregister(); return; }
    await self.clients.claim();
  })());
});
async function supCache() {
  const state=await caches.open(SUP_STATE);
  const current=async()=>{const value=await state.match('/sup-active');return value && await value.text()};
  if (await current() !== SUP_CACHE) return null;
  const cache=await caches.open(SUP_CACHE);
  // An old worker can finish requests after a new worker activates. Never resurrect its cache.
  if (await current() !== SUP_CACHE) { await caches.delete(SUP_CACHE); return null; }
  return cache;
}
async function supHTML(request, path) {
  const cache=await supCache(), abort=new AbortController();
  if (!cache) return fetch(request);
  const timeout=setTimeout(()=>abort.abort(), 4000);
  try {
    const response=await fetch(request, {cache:'no-store',signal:abort.signal});
    if (!response.ok || response.redirected) throw new Error('Menu unavailable');
    await cache.put(path,response.clone()).catch(()=>{}); return response;
  } catch (error) {
    const saved=await cache.match(path); if (!saved) throw error;
    const text=await saved.text();
    // Read the saved document's revision, even during a build transition.
    const date=(text.match(/name="menu-revision" content="([0-9-]+)/)||[])[1] || SUP.revision.date;
    const headers=new Headers(saved.headers);headers.delete('content-length');headers.delete('content-encoding');headers.set('X-SUP-Offline',date);
    return new Response(text.replace('</head>', '<meta name="sup-offline" content="'+date+'"></head>'),{status:200,headers});
  } finally { clearTimeout(timeout); }
}
self.addEventListener('fetch', event => {
  const url=new URL(event.request.url), path=supPath(url);
  if (!SUP.enabled || event.request.method!=='GET' || url.origin!==self.location.origin || !SUP_FILES.has(path)) return;
  if (event.request.mode==='navigate' && path.endsWith('.html')) { event.respondWith(supHTML(event.request,path)); return; }
  event.respondWith((async()=>{
    const cache=await supCache(); if (!cache) return fetch(event.request);
    const saved=await cache.match(path);
    if (saved) return saved;
    // PDF viewers may request a byte range. Save/return a complete 200 response so
    // a later offline open is usable; Cache.put cannot store partial 206 responses.
    let request=event.request;
    if (path.startsWith('/pdf/') && request.headers.has('range')) {
      const headers=new Headers(request.headers);headers.delete('range');
      request=new Request(request,{headers});
    }
    const response=await fetch(request);
    if (response.status===200 && !response.redirected && !supFull(path)) await cache.put(path,response.clone()).catch(()=>{});
    return response;
  })());
});
self.addEventListener('message', event => {
  if (!SUP.enabled || !event.source?.url) return;
  const sender=new URL(event.source.url);
  if (sender.origin!==self.location.origin || supPath(sender)!=='/index.html') return;
  // The viewer preloads adjacent photos. Cache the displayed photo only.
  const path=event.data?.supOpened;
  if (typeof path!=='string' || !SUP_FILES.has(path) || !supFull(path)) return;
  event.waitUntil((async()=>{const cache=await supCache();if (cache && !await cache.match(path)) {const r=await fetch(path);if(r.ok&&!r.redirected)await cache.put(path,r)}})().catch(()=>{}));
});
