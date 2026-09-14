import json, base64, sys, pathlib, html as html_lib
from build_common import LANGS, read_strings, revision
from sup_nojs import markup
from sup_fonts import glyph_hash
root = pathlib.Path(__file__).parent
langs = sys.argv[1:] or LANGS
all_strings = read_strings(root)
if 'en' not in langs or any(l not in LANGS for l in langs):
    raise ValueError('Language arguments must include en and use supported language codes')
strings = {l: all_strings[l] for l in langs}
rev = revision(root)
font_manifest = json.loads((root / 'assets/sup-fonts/sup-manifest.json').read_text())
for lang in langs:
    if font_manifest['languages'][lang]['glyph_hash'] != glyph_hash(all_strings, lang):
        raise ValueError('Font subset is stale for ' + lang + '; run python3 sup_fonts.py')
structure = json.load(open(root / "structure.json"))
photos = {p.stem: p.name for p in sorted((root / "assets" / "items").glob("*")) if p.suffix in (".jpg", ".png")}
import subprocess
def dims(p):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(p)], capture_output=True, text=True).stdout
    w, h = [int(l.split()[-1]) for l in out.splitlines() if "pixel" in l]
    return w, h
full = {}
for p in sorted((root / "assets" / "full").glob("*")):
    if p.suffix in (".jpg", ".png") and p.stem in photos:
        w, h = dims(p); full[p.stem] = {"f": p.name, "w": w, "h": h}
variants = {}
vdir = root / "assets" / "variants"
if vdir.exists():
    vmap = json.load(open(vdir / "map.json"))
    for item, keys in vmap.items():
        rows = []
        for k in keys:
            f = vdir / f"{item}-{k}.jpg"; t = vdir / f"{item}-{k}-thumb.jpg"
            if not (f.exists() and t.exists()): continue
            w, h = dims(f)
            rows.append({"k": k, "t": t.name, "f": f.name, "w": w, "h": h})
        if len(rows) > 1: variants[item] = rows
data = json.dumps({"structure": structure, "strings": strings, "photos": photos, "full": full, "variants": variants, "revision": rev}, ensure_ascii=False, separators=(",", ":"))
def uri(name, mime):
    return f"data:{mime};base64," + base64.b64encode((root / "assets" / name).read_bytes()).decode()
html = (root / "template.html").read_text()
html = html.replace("__DESCRIPTION__", html_lib.escape(all_strings['en']['ui.tagline'], quote=True)).replace("__PREVIEW_TITLE__", html_lib.escape(all_strings['en']['ui.title'], quote=True)).replace("__REVISION__", rev['stamp'])
html = html.replace("__DATA__", data.replace("</", "<\\/"))
fallback = markup(structure, all_strings['en'])
html = html.replace('__NOJS__', fallback)
print('No-JS markup:', len(fallback.encode()), 'bytes')
# Referenced as files, not inlined: base64 of these three was 62% of the gzipped
# document, and every byte of the document blocks first paint.
html = html.replace("__ICON__", "img/icon.png").replace("__LOGO__", "img/logo.png").replace("__DOODLE__", "img/doodle.jpg")
html = html.replace("__BOWL__", uri("bowl.jpg", "image/jpeg")).replace("__KIMCHI__", uri("kimchi.jpg", "image/jpeg"))
out = root / "sup-menu.html"
out.write_text(html)
print("wrote", out, round(out.stat().st_size / 1024), "KB; langs:", ",".join(langs))
