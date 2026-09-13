import pathlib, shutil, re
root = pathlib.Path(__file__).parent
site = root / "site"
if site.exists(): shutil.rmtree(site)
(site / "img" / "full").mkdir(parents=True); (site / "pdf").mkdir()
html = (root / "sup-menu.html").read_text()
doc = html
(site / "index.html").write_text(doc)
for p in (root / "assets" / "items").glob("*"):
    if p.suffix in (".jpg", ".png"): shutil.copy(p, site / "img" / p.name)
for p in (root / "assets" / "full").glob("*"):
    if p.suffix in (".jpg", ".png"): shutil.copy(p, site / "img" / "full" / p.name)
(site / "img" / "var").mkdir(parents=True, exist_ok=True)
for p in (root / "assets" / "variants").glob("*.jpg"):
    shutil.copy(p, site / "img" / "var" / p.name)
for l in ['en', 'es', 'vi', 'ko', 'zh', 'zh-Hant', 'tl', 'fa', 'ar', 'ja', 'ru', 'hi', 'ur']:
    shutil.copy(root / "pdf" / f"SUP-Menu-{l}.pdf", site / "pdf" / f"SUP-Menu-{l}.pdf")
(site / ".nojekyll").write_text("")
# sources for future edits
src = site / "src"; src.mkdir()
for name in ["structure.json", "template.html", "print_template.html", "build.py", "build_print.py", "verify_pdfs.py", "build_site.py", "merge_toast.py", "qr.swift", "qrread.swift", "qrcard.html"]:
    shutil.copy(root / name, src / name)
for l in ['en', 'es', 'vi', 'ko', 'zh', 'zh-Hant', 'tl', 'fa', 'ar', 'ja', 'ru', 'hi', 'ur']: shutil.copy(root / f"strings.{l}.json", src / f"strings.{l}.json")
(src / "assets").mkdir(); 
for n in ["logo.png", "icon.png", "doodle.jpg", "bowl.jpg", "kimchi.jpg"]: shutil.copy(root / "assets" / n, src / "assets" / n)
shutil.copytree(root / "assets" / "items", src / "assets" / "items")
shutil.copytree(root / "assets" / "full", src / "assets" / "full")
shutil.copytree(root / "assets" / "variants", src / "assets" / "variants")
docs = site / "docs"; docs.mkdir()
for n in ["research-out.json", "toast-out.json", "audit-es-out.json", "audit-vi-out.json", "audit-ko-out.json", "audit-zh-out.json"]:
    shutil.copy(root / "research" / n, docs / n)
(site / "README.md").write_text("""# SUP Noodle Bar menu

Static, thirteen-language QR menu for SUP Noodle Bar (Buena Park and Irvine) with dish photos, one "Contains" allergen line per dish, an allergen avoid filter, and printable PDFs.

- `index.html` — the menu. `?lang=en|es|vi|ko|zh|zh-Hant|tl|fa|ar|ja|ru|hi|ur` preselects a language.
- `img/` — dish thumbnails; `img/full/` — the larger versions shown in the full-screen photo viewer. Community photos from Yelp are placeholders; see `src/assets/items/manifest.json` for each source and replace them with restaurant-owned photography before wide release.
- `pdf/` — printable US Letter menus, one per language.
- `src/` — data and templates. Rebuild with `python3 build.py en es vi ko zh zh-Hant tl fa ar ja ru hi ur` (web), `python3 build_print.py` (PDFs, needs Google Chrome), then `python3 build_site.py`.
- `docs/` — design research, translation audits, and SUP's published Toast allergen statements used for the allergen data.
- `src/qr.swift` — QR generator for the menu link (`swiftc -O -o qr qr.swift && ./qr <url> out.png 2048 assets/logo.png`); `src/qrread.swift` decodes a PNG to check it scans; `src/qrcard.html` is the printable table card.

Languages: English, Spanish, Vietnamese, Korean, Simplified Chinese, Traditional Chinese, Tagalog, Persian (Farsi), Arabic, Japanese, Russian, Hindi, and Urdu. Persian, Arabic, and Urdu use right-to-left layouts.

Allergen lines combine SUP's published statements (ingredients and possible cross-contact) with the menu descriptions and are marked pending kitchen review.
""")
print("site built:", sum(1 for _ in site.rglob("*") if _.is_file()), "files;", round(sum(p.stat().st_size for p in site.rglob("*") if p.is_file())/1e6, 1), "MB")
