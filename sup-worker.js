/* SUP's menu moved to /sup/ and registers its own worker there. This file replaces the old root-scope
   worker at /sup-worker.js: when a phone that still holds that registration checks for an update, this
   one installs, drops the old caches and unregisters itself. It never answers a fetch. */
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil((async () => {
  await Promise.all((await caches.keys()).filter(key => key.startsWith('sup-')).map(key => caches.delete(key)));
  await self.registration.unregister();
})()));
