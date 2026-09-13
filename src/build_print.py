import json, base64, html, pathlib, subprocess, sys
root = pathlib.Path(__file__).parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LANGS = [("en","English"),("es","Español"),("vi","Tiếng Việt"),("ko","한국어"),("zh","简体中文"),("zh-Hant","繁體中文"),("tl","Tagalog")]
structure = json.load(open(root/"structure.json"))
S = {l: json.load(open(root/f"strings.{l}.json")) for l,_ in LANGS}
ORDER = structure["allergens"]
esc = html.escape
def uri(p, mime=None):
    p = pathlib.Path(p); mime = mime or ("image/png" if p.suffix==".png" else "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
IMG = {"logo": uri(root/"assets"/"logo.png")}
def money(n, plus=False):
    v = round(n*100)/100; s = str(int(v)) if v == int(v) else f"{v:.2f}"
    return ("+" if plus else "") + "$" + s
def merged(e):
    st = set(e.get("contains", [])) | set(e.get("likely", [])); return [a for a in ORDER if a in st]
def photo_of(id):
    for ext in (".png", ".jpg"):
        p = root/"assets"/"items"/f"{id}{ext}"
        if p.exists(): return p
    return None

def build(lang):
    s = S[lang]; en = S["en"]
    t = lambda k: s.get(k, en.get(k, ""))
    has = lambda k: k in en
    names = lambda lst: ", ".join(esc(t("allergen."+a)) for a in lst)
    price = lambda p: f'<span class="price">{money(p["p"], p.get("plus"))}</span>'
    def al_line(e):
        lst = merged(e)
        if not lst: return ""
        return f'<p class="al"><b>{esc(t("ui.contains"))}:</b> {names(lst)}</p>'
    def name_block(k):
        e, l = en[k+".name"], t(k+".name")
        if lang=="en" or l==e: return esc(e), ""
        return esc(l), f'<div class="en-name" lang="en">{esc(e)}</div>'
    def badges(it):
        b=[]
        if it.get("badge"): b.append(f'<span class="badge caps">{esc(t("ui."+it["badge"]))}</span>')
        if it.get("refill"): b.append(f'<span class="badge refill caps">{esc(t("ui.freeRefill"))}</span>')
        return f'<div class="badges">{"".join(b)}</div>' if b else ""
    def variants(k, it):
        rows=[]
        for p in it["prices"]:
            extra = f' <span class="vplus">(+ {names(p["contains"])})</span>' if p.get("contains") else ""
            rows.append(f'<li><span>{esc(t(k+".price."+p["k"]))}{extra}</span><span class="dots"></span>{price(p)}</li>')
        return '<ul class="variants">' + "".join(rows) + '</ul>'
    def item(it, kind):
        k = f"{kind}.{it['id']}"
        keyed = bool(it["prices"]) and "k" in it["prices"][0]
        single = price(it["prices"][0]) if (not keyed and len(it["prices"])==1) else ""
        h3, sub = name_block(k)
        tagline = f'<div class="tagline">{esc(t(k+".tagline"))}</div>' if has(k+".tagline") else ""
        desc = f'<p class="desc">{esc(t(k+".desc"))}</p>' if has(k+".desc") else ""
        note = f'<p class="note">{esc(t(k+".note"))}</p>' if has(k+".note") else ""
        var = variants(k, it) if keyed else ""
        sides = ""
        if it.get("addons"):
            rows = ""
            for a in it["addons"]:
                extra = (' <span class="vplus">(+ ' + names(merged(a)) + ')</span>') if merged(a) else ""
                rows += f'<li><span>{esc(t("addon."+a["id"]+".name"))}{extra}</span><span class="dots"></span>{price(a["prices"][0])}</li>'
            sides = f'<div class="sides"><span class="lab caps">{esc(t("ui.sides"))}</span><ul class="variants">{rows}</ul></div>'
        ph = photo_of(it["id"]) if kind=="item" else None
        thumb = f'<img class="thumb{" cutout" if ph.suffix==".png" else ""}" src="{uri(ph)}" alt="">' if ph else ("<span></span>" if kind=="item" else "")
        return f'<div class="item"><div class="item-body"><div class="head"><h3 class="caps">{h3}</h3>{single}</div>{sub}{badges(it)}{tagline}{desc}{var}{note}{sides}{al_line(it)}</div>{thumb}</div>'
    def section(sec):
        sid = sec["id"]
        hp = " has-photos" if any(photo_of(i["id"]) for i in sec["items"]) else ""
        intro = f'<p class="intro">{esc(t(f"sec.{sid}.intro"))}</p>' if has(f"sec.{sid}.intro") else ""
        broth = f'<p class="intro small">{esc(t(f"sec.{sid}.brothNote"))}</p>' if has(f"sec.{sid}.brothNote") else ""
        refills = f'<p class="intro small">{esc(t("ui.refillsNote"))}</p>' if sid=="drinks" else ""
        items = "".join(item(it,"item") for it in sec["items"])
        addons = (f'<div class="addons"><h3 class="t caps">{esc(t("ui.addons"))}</h3>' + "".join(item(a,"addon") for a in sec["addons"]) + '</div>') if sec.get("addons") else ""
        return f'<section class="{hp.strip()}" id="sec-{sid}"><header><h2 class="caps">{esc(t(f"sec.{sid}.title"))}</h2></header>{intro}{broth}{refills}{items}{addons}</section>'
    def specials():
        out=[]
        for sp in structure["specials"]:
            ph = photo_of(sp["item"]); img = f'<img src="{uri(ph)}" alt="">' if ph else "<span></span>"
            if sp["id"]=="lunch":
                out.append(f'<div class="special">{img}<div><div class="eyebrow caps">{esc(t("ui.lunchEyebrow"))}</div><h2 class="caps">{esc(t("ui.lunchTitle"))}</h2><div class="price">{money(sp["offer"])}<s>{money(sp["regular"])}</s></div><p class="when">{esc(t("ui.lunchWhen"))}</p><p class="terms">{esc(t("ui.lunchTerms"))}</p></div></div>')
            else:
                out.append(f'<div class="special">{img}<div><div class="eyebrow caps">{esc(t("ui.kimchiEyebrow"))}</div><h2 class="caps">{esc(t("ui.kimchiTitle"))}</h2><p class="when">{esc(t("ui.kimchiSub"))}</p></div></div>')
        return '<div class="specials">' + "".join(out) + '</div>'
    body = f'''
<div class="masthead">
  <div class="brand"><img src="{IMG["logo"]}" alt=""><div><h1 class="caps">{esc(t("ui.brand"))}</h1><p>{esc(t("ui.tagline"))}</p></div></div>
  <div class="key"><b class="caps">{esc(t("ui.legendTitle"))}</b>{esc(t("ui.printKey"))} {esc(t("ui.noLineNote"))}</div>
</div>
{specials()}
<div class="flow">
{"".join(section(sec) for sec in structure["sections"])}
<div class="end">
  <div class="loc"><h3 class="caps">{esc(t("ui.buenaPark"))}</h3><address>5141 Beach Blvd Unit B, Buena Park, CA 90621 · 714-521-2444</address></div>
  <div class="loc"><h3 class="caps">{esc(t("ui.irvine"))}</h3><address>14370 Culver Dr Unit 2H, Irvine, CA 92604 · 657-300-8420</address></div>
  <div class="loc"><h3 class="caps">SUP Noodle Bar</h3><div class="web">supnoodlebar.com · @supnoodlebar · info@supnoodlebar.com</div></div>
  <p class="notice"><b class="caps">{esc(t("ui.allergyTitle"))}</b>{esc(t("ui.allergyNotice"))}</p>
  <p class="notice"><b class="caps">{esc(t("ui.rawTitle"))}</b>{esc(t("ui.rawNotice"))}</p>
</div>
</div>'''
    tpl = (root/"print_template.html").read_text()
    label = dict(LANGS)[lang]
    page = tpl.replace("__LANG__", "zh-Hans" if lang=="zh" else lang).replace("__TITLE__", f"SUP Noodle Bar Menu ({label})").replace("__BODY__", body)
    out = root/f"print-{lang}.html"; out.write_text(page); return out

def to_pdf(src, dst):
    if dst.exists(): dst.unlink()
    prof = root/"chrome-profile"
    subprocess.run(["rm","-rf",str(prof)])
    cmd = ["perl","-e","alarm 50; exec @ARGV","--",CHROME,"--headless=new","--disable-gpu","--no-first-run",f"--user-data-dir={prof}","--no-pdf-header-footer","--virtual-time-budget=10000",f"--print-to-pdf={dst}",f"file://{src}"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill","-f",f"user-data-dir={prof}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dst.exists() and dst.read_bytes()[:4] == b"%PDF"

if __name__ == "__main__":
    langs = sys.argv[1:] or [l for l,_ in LANGS]
    outdir = root/"pdf"; outdir.mkdir(exist_ok=True)
    for l in langs:
        src = build(l); dst = outdir/f"SUP-Menu-{l}.pdf"
        ok = to_pdf(src, dst)
        print(l, "OK" if ok else "FAILED", dst.stat().st_size//1024 if ok else "", "KB")
