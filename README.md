# SUP Noodle Bar menu

Static, thirteen-language QR menu for SUP Noodle Bar (Buena Park and Irvine) with dish photos, one "Contains" allergen line per dish, an allergen avoid filter, and printable PDFs.

- `index.html` — the menu. `?lang=en|es|vi|ko|zh|zh-Hant|tl|fa|ar|ja|ru|hi|ur` preselects a language.
- `img/` — dish thumbnails; `img/full/` — the larger versions shown in the full-screen photo viewer. Community photos from Yelp are placeholders; see `src/assets/items/manifest.json` for each source and replace them with restaurant-owned photography before wide release.
- `pdf/` — printable US Letter menus, one per language.
- `src/` — data and templates. Rebuild with `python3 build.py en es vi ko zh zh-Hant tl fa ar ja ru hi ur` (web), `python3 build_print.py` (PDFs, needs Google Chrome), then `python3 build_site.py`.
- `docs/` — design research, translation audits, and SUP's published Toast allergen statements used for the allergen data.
- `src/qr.swift` — QR generator for the menu link (`swiftc -O -o qr qr.swift && ./qr <url> out.png 2048 assets/logo.png`); `src/qrread.swift` decodes a PNG to check it scans; `src/qrcard.html` is the printable table card.

Languages: English, Spanish, Vietnamese, Korean, Simplified Chinese, Traditional Chinese, Tagalog, Persian (Farsi), Arabic, Japanese, Russian, Hindi, and Urdu. Persian, Arabic, and Urdu use right-to-left layouts.

Allergen lines combine SUP's published statements (ingredients and possible cross-contact) with the menu descriptions and are marked pending kitchen review.
