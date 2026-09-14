# Build and verify

Run **`python3 release.py`** from this workspace. Required: macOS, Python 3.9+, Google Chrome at its standard Applications path, Swift command-line tools, and Poppler (`pdfinfo`). Google Fonts must be reachable for PDF rendering.

The command snapshots the explicit product inputs into a temporary directory under `tests/`, builds all 13 languages and PDFs, generates and independently decodes the QR, and validates strict translation key parity, identical ASCII price sequences, every PDF page's US Letter size, all photo/PDF references and a strict public-file allowlist. Any error exits nonzero before replacing `site/`. A source change during the build also rejects the release, so concurrent edits cannot silently produce stale output. Replacement errors roll back prior outputs.

Only after validation does the command replace `site/`, `pdf/`, `sup-menu.html`, and the 13 print HTML files. `site/` contains public menu/card HTML, images, PDFs, `.nojekyll`, and `revision.json`; sources, research, PRD, tests and logs are excluded. Publication to the live host is separate.

The revision is a UTC ISO date and an eight-character SHA-256 prefix over named source files and assets (excluding the generated QR). Set `SOURCE_DATE_EPOCH` to a fixed Unix timestamp to reproduce the revision date; PDF internal timestamps may still differ. The revision appears in menu metadata, embedded data and `revision.json`; every PDF page has localized page/total and revision date.

`python3 build.py` defaults to every language. The existing three-command sequence remains available for development, but only `release.py` provides the staging/verification guarantee. `site/qrcard.html` is the printable 5×7-inch card; its generated `img/qr-menu.png` encodes exactly `https://menu.fyt.life/`. QR compilation artifacts are temporary under `tests/`.

## Phase 2 build inputs and offline operation

Python 3.9 is supported, including `/Applications/Xcode.app/Contents/Developer/usr/bin/python3`. Chrome's debugging pipes are mapped through `/bin/sh` with positional arguments; the Xcode launcher does not preserve those descriptors when used as the bridge. Chrome processes are stopped and waited by their owned PID. `pdfinfo` and `pdftotext` are resolved before any build from PATH, `/opt/homebrew/bin`, `/usr/local/bin`, or either Homebrew `opt/poppler/bin` directory. Missing Poppler fails immediately with an installation hint.

Run both compatibility checks after changing the build:

```sh
env PATH=/usr/bin:/bin:/usr/sbin:/sbin /Applications/Xcode.app/Contents/Developer/usr/bin/python3 release.py
/opt/homebrew/bin/python3 release.py
```

Web fonts are bundled under `assets/sup-fonts/`, with upstream URLs, SHA-256 checksums, glyph-set hashes and OFL licenses. `python3 sup_fonts.py` refreshes the Google Fonts `text=` subsets when supported glyphs change. It requires curl and network access. Ordinary web builds use those local assets; PDF font loading remains unchanged. The release rejects stale glyph sets. Each language loads its own stylesheet with `font-display: swap`; picker labels use system fonts. No font refresh is needed if a translation edit introduces no new glyphs.

The build generates `sup-manifest.json` and `sup-worker.js` after assembling public files. Release validation requires the manifest to match every published file exactly, plus the explicit `/` → `/index.html` alias. Only same-origin GETs to those exact paths reach `respondWith`. Sibling restaurant paths, other origins, unknown paths and non-GET requests bypass SUP entirely. Do not replace this guard with a catch-all navigation fallback. The root scope necessarily controls sibling pages, but does not serve their requests.

HTML uses network-first with a four-second timeout, then a cached document marked with its own saved revision date. SUP assets use a cache named `sup-menu-<revision stamp>`. Initial installation saves the menu HTML and logo; the active page warms only fonts and thumbnails it already used. Other images/fonts are cached when requested. PDFs are cached when opened; the viewer's displayed full photo is cached via a caption observer, while adjacent preloaded full photos are not cached automatically. Unvisited assets/languages may lack fonts or photos offline; menu text remains embedded and readable with system fallbacks. There is no install prompt.

Activation records the active cache in `sup-cache-state` and deletes obsolete SUP caches, leaving other restaurants' caches alone. The marker prevents an older worker finishing an in-flight request from recreating an obsolete cache. Only `sup-lang` and `sup-avoid` are in localStorage; search queries stay in memory.

**Kill switch:** run `SUP_SW_DISABLED=1 python3 release.py`. The output retains the same worker URL so existing installations receive a self-unregistering worker. It intercepts no requests and deletes SUP menu caches; the tiny `sup-cache-state` disabled marker remains to fence older workers. Existing controlled tabs stop using the worker after reload/close. To restore offline support, rebuild without the flag. The flag changes the revision hash. Publication is a separate owner action; no publication occurs in this workspace.

Release checks additionally cover the five retained search/offline UI keys (221 total keys) in every language, the exact worker manifest/template, the generated no-JavaScript menu, and official website/email text in menu HTML, every PDF and the QR card. The English fallback adds approximately 14 KB of uncompressed HTML and links to all 13 PDFs. The staff view and its dish-share links have been removed. Search results close the sheet and scroll to/focus the dish with a brief static highlight; `?item=` is ignored. Language links continue to use `?lang=<code>`.

Phase 2 test entry points and raw evidence are in [tests/REPORT-phase2.md](tests/REPORT-phase2.md). The browser scripts use the workspace's existing Playwright installation and CDP device metrics, not window resizing. All test servers are local and close with their browsers; the sibling fixture exists only in a temporary test root.

Offline PDF requests with a byte-range header fetch/cache the complete PDF, so partial responses cannot break a later offline open. Cache-write failures leave successful network responses usable.

Current regression entry points and fresh evidence are in [tests/REPORT-removal.md](tests/REPORT-removal.md); phase 1/2 reports and earlier evidence remain historical. The removal retains every font binary, stylesheet and license byte. Four font-manifest glyph hashes were updated for the smaller ko/zh/zh-Hant/ja text sets; the existing subsets already cover every remaining glyph. No font download is required.
