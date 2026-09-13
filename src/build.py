import json, base64, sys, pathlib
root = pathlib.Path(__file__).parent
langs = sys.argv[1:] or ["en"]
strings = {}
for l in langs:
    p = root / f"strings.{l}.json"
    assert p.exists(), f"missing {p}"
    strings[l] = json.load(open(p))
en = set(strings["en"])
for l, s in strings.items():
    extra = set(s) - en
    assert not extra, f"{l}: unknown keys {extra}"
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
data = json.dumps({"structure": structure, "strings": strings, "photos": photos, "full": full}, ensure_ascii=False, separators=(",", ":"))
def uri(name, mime):
    return f"data:{mime};base64," + base64.b64encode((root / "assets" / name).read_bytes()).decode()
html = (root / "template.html").read_text()
html = html.replace("__DATA__", data.replace("</", "<\\/"))
html = html.replace("__ICON__", uri("icon.png", "image/png")).replace("__LOGO__", uri("logo.png", "image/png")).replace("__DOODLE__", uri("doodle.jpg", "image/jpeg"))
html = html.replace("__BOWL__", uri("bowl.jpg", "image/jpeg")).replace("__KIMCHI__", uri("kimchi.jpg", "image/jpeg"))
out = root / "sup-menu.html"
out.write_text(html)
print("wrote", out, round(out.stat().st_size / 1024), "KB; langs:", ",".join(langs))
