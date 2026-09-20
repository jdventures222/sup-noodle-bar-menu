import json, base64, html, pathlib, subprocess, sys, re, tempfile, os, signal, select, time
from build_common import read_strings, revision
root = pathlib.Path(__file__).parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LANGS = [("en","English"),("es","Español"),("vi","Tiếng Việt"),("ko","한국어"),("zh","简体中文"),("zh-Hant","繁體中文"),("tl","Tagalog"),("fa","فارسی"),("ar","العربية"),("ja","日本語"),("ru","Русский"),("hi","हिन्दी"),("ur","اردو")]
structure = json.load(open(root/"structure.json"))
S = read_strings(root)
REVISION = revision(root)
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
    rtl = lang in ("fa", "ar", "ur")
    def ltr(value): return f'<bdi dir="ltr">{esc(value)}</bdi>'
    def prose(value):
        if not rtl: return esc(value)
        parts = re.split(r"(\+?\$[0-9]+(?:\.[0-9]+)?|[A-Za-zÀ-ž0-9]+(?:[ .,:/@+&’'–−-]+[A-Za-zÀ-ž0-9]+)*)", value)
        return "".join(ltr(part) if i % 2 else esc(part) for i, part in enumerate(parts))
    t = lambda k: s.get(k, en.get(k, ""))
    has = lambda k: k in en
    names = lambda lst: ("، " if rtl else ", ").join(prose(t("allergen."+a)) for a in lst)
    price = lambda p: f'<span class="price">{ltr(money(p["p"], p.get("plus")))}</span>'
    def al_line(e):
        lst = merged(e)
        if not lst: return ""
        return f'<p class="al"><b>{prose(t("ui.contains"))}:</b> {names(lst)}</p>'
    def name_block(k):
        e, l = en[k+".name"], t(k+".name")
        if lang=="en" or l==e: return prose(e), ""
        return prose(l), f'<div class="en-name" lang="en" dir="ltr">{esc(e)}</div>'
    def badges(it):
        b=[]
        if it.get("badge"): b.append(f'<span class="badge caps">{prose(t("ui."+it["badge"]))}</span>')
        if it.get("refill"): b.append(f'<span class="badge refill caps">{prose(t("ui.freeRefill"))}</span>')
        return f'<div class="badges">{"".join(b)}</div>' if b else ""
    def variants(k, it):
        rows=[]
        for p in it["prices"]:
            extra = f' <span class="vplus">({prose(t("ui.contains"))}: {names(p["contains"])})</span>' if p.get("contains") else ""
            rows.append(f'<li><span>{prose(t(k+".price."+p["k"]))}{extra}</span><span class="dots"></span>{price(p)}</li>')
        return '<ul class="variants">' + "".join(rows) + '</ul>'
    def item(it, kind):
        k = f"{kind}.{it['id']}"
        keyed = bool(it["prices"]) and "k" in it["prices"][0]
        single = price(it["prices"][0]) if (not keyed and len(it["prices"])==1) else ""
        h3, sub = name_block(k)
        tagline = f'<div class="tagline">{prose(t(k+".tagline"))}</div>' if has(k+".tagline") else ""
        desc = f'<p class="desc">{prose(t(k+".desc"))}</p>' if has(k+".desc") else ""
        note = f'<p class="note">{prose(t(k+".note"))}</p>' if has(k+".note") else ""
        var = variants(k, it) if keyed else ""
        sides = ""
        if it.get("addons"):
            rows = ""
            for a in it["addons"]:
                extra = (' <span class="vplus">(' + prose(t("ui.contains")) + ': ' + names(merged(a)) + ')</span>') if merged(a) else ""
                rows += f'<li><span>{prose(t("addon."+a["id"]+".name"))}{extra}</span><span class="dots"></span>{price(a["prices"][0])}</li>'
            sides = f'<div class="sides"><span class="lab caps">{prose(t("ui.sides"))}</span><ul class="variants">{rows}</ul></div>'
        ph = photo_of(it["id"]) if kind=="item" else None
        thumb = f'<img class="thumb{" cutout" if ph.suffix==".png" else ""}" src="{uri(ph)}" alt="">' if ph else ("<span></span>" if kind=="item" else "")
        return f'<div class="item"><div class="item-body"><div class="head"><h3 class="caps">{h3}</h3>{single}</div>{sub}{badges(it)}{tagline}{desc}{var}{note}{sides}{al_line(it)}</div>{thumb}</div>'
    def section(sec):
        sid = sec["id"]
        hp = " has-photos" if any(photo_of(i["id"]) for i in sec["items"]) else ""
        intro = f'<p class="intro">{prose(t(f"sec.{sid}.intro"))}</p>' if has(f"sec.{sid}.intro") else ""
        broth = f'<p class="intro small">{prose(t(f"sec.{sid}.brothNote"))}</p>' if has(f"sec.{sid}.brothNote") else ""
        refills = f'<p class="intro small">{prose(t("ui.refillsNote"))}</p>' if sid=="drinks" else ""
        items = "".join(item(it,"item") for it in sec["items"])
        addons = (f'<div class="addons"><h3 class="t caps">{prose(t("ui.addons"))}</h3>' + "".join(item(a,"addon") for a in sec["addons"]) + '</div>') if sec.get("addons") else ""
        return f'<section class="{hp.strip()}" id="sec-{sid}"><header><h2 class="caps">{prose(t(f"sec.{sid}.title"))}</h2></header>{intro}{broth}{refills}{items}{addons}</section>'
    def specials():
        out=[]
        for sp in structure["specials"]:
            ph = photo_of(sp["item"]); img = f'<img src="{uri(ph)}" alt="">' if ph else "<span></span>"
            if sp["id"]=="lunch":
                out.append(f'<div class="special">{img}<div><div class="eyebrow caps">{prose(t("ui.lunchEyebrow"))}</div><h2 class="caps">{prose(t("ui.lunchTitle"))}</h2><div class="price">{ltr(money(sp["offer"]))}<s>{ltr(money(sp["regular"]))}</s></div><p class="when">{prose(t("ui.lunchWhen"))}</p><p class="terms">{prose(t("ui.lunchTerms"))}</p></div></div>')
            else:
                out.append(f'<div class="special">{img}<div><div class="eyebrow caps">{prose(t("ui.kimchiEyebrow"))}</div><h2 class="caps">{prose(t("ui.kimchiTitle"))}</h2><p class="when">{prose(t("ui.kimchiSub"))}</p></div></div>')
        return '<div class="specials">' + "".join(out) + '</div>'
    body = f'''
<div class="masthead">
  <div class="brand"><img src="{IMG["logo"]}" alt=""><div><h1 class="caps">{prose(t("ui.brand"))}</h1><p>{prose(t("ui.tagline"))}</p></div></div>
  <div class="key"><b class="caps">{prose(t("ui.legendTitle"))}</b>{prose(t("ui.printKey"))} {prose(t("ui.noLineNote"))}</div>
</div>
{specials()}
<div class="flow">
{"".join(section(sec) for sec in structure["sections"])}
<div class="end">
  <div class="loc"><h3 class="caps">{prose(t("ui.buenaPark"))}</h3><address dir="ltr">5141 Beach Blvd Unit B, Buena Park, CA 90621 · 714-521-2444</address></div>
  <div class="loc"><h3 class="caps">{prose(t("ui.irvine"))}</h3><address dir="ltr">14370 Culver Dr Unit 2H, Irvine, CA 92604 · 657-300-8420</address></div>
  <div class="loc"><h3 class="caps"><bdi dir="ltr">SUP Noodle Bar</bdi></h3><div class="web" dir="ltr"><bdi dir="ltr"><a href="https://www.keiconcepts.info/brands/sup">keiconcepts.info/brands/sup</a></bdi><br><bdi dir="ltr">@supnoodlebar</bdi> · <bdi dir="ltr"><a href="mailto:hello@keiconcepts.info">hello@keiconcepts.info</a></bdi></div></div>
  <div class="closing-notices">
  <p class="notice"><b class="caps">{prose(t("ui.allergyTitle"))}</b>{prose(t("ui.allergyNotice"))}</p>
  {f'<p class="notice halal-note">{prose(t("ui.halalNote"))}</p>' if lang in ("ar", "fa", "ur") else ""}
  <p class="notice"><b class="caps">{prose(t("ui.rawTitle"))}</b>{prose(t("ui.rawNotice"))}</p>
  </div>
</div>
</div>'''
    tpl = (root/"print_template.html").read_text()
    label = dict(LANGS)[lang]
    page = tpl.replace("__LANG__", "zh-Hans" if lang=="zh" else lang).replace("__DIR__", "rtl" if rtl else "ltr").replace("__TITLE__", f"SUP Noodle Bar Menu ({label})").replace("__BODY__", body)
    # CSS page counters use the document fonts and preserve localized word order.
    footer = t("ui.pdfPage") + " · " + t("ui.revision").replace("{date}", "\u2066" + REVISION["date"] + "\u2069")
    parts = re.split(r"(\{page\}|\{pages\})", footer)
    content = " ".join("counter(page)" if part == "{page}" else "counter(pages)" if part == "{pages}" else json.dumps(part, ensure_ascii=False) for part in parts)
    page = page.replace("__PAGE_FOOTER__", content).replace("__REVISION__", REVISION["stamp"])
    out = root/f"print-{lang}.html"; out.write_text(page); return out

def to_pdf(src, dst):
    with tempfile.TemporaryDirectory(prefix=".chrome-print-", dir=root) as prof:
        read_in, write_in = os.pipe(); read_out, write_out = os.pipe()
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={prof}", "--remote-debugging-pipe"]
        # Map inherited pipes in a shell, avoiding Xcode's Python launcher and its FD handling.
        # Positional arguments keep executable/profile paths out of shell source.
        bridge = 'exec 3<&$1 4>&$2; shift 2; exec "$@"'
        errors = tempfile.TemporaryFile()
        proc = subprocess.Popen(['/bin/sh', '-c', bridge, 'sup-chrome-bridge', str(read_in), str(write_out), *cmd], pass_fds=(read_in, write_out), stdout=subprocess.DEVNULL, stderr=errors, start_new_session=True)
        print(f"Chrome PDF PID {proc.pid}: started", flush=True)
        os.close(read_in); os.close(write_out)
        pending = b""; seq = 0; events = []
        def receive():
            nonlocal pending
            deadline = time.monotonic() + 60
            while b"\0" not in pending:
                if not select.select([read_out], [], [], max(0, deadline - time.monotonic()))[0]:
                    raise TimeoutError("Chrome PDF export timed out")
                chunk = os.read(read_out, 65536)
                if not chunk:
                    errors.seek(0)
                    raise RuntimeError("Chrome closed its PDF session: " + errors.read().decode(errors='replace'))
                pending += chunk
            line, pending = pending.split(b"\0", 1)
            return json.loads(line)
        def call(method, params=None, session=None):
            nonlocal seq
            seq += 1; msg = {"id": seq, "method": method, "params": params or {}}
            if session: msg["sessionId"] = session
            payload = json.dumps(msg).encode() + b"\0"
            while payload: payload = payload[os.write(write_in, payload):]
            while True:
                reply = receive()
                if reply.get("id") == seq:
                    if "error" in reply: raise RuntimeError(reply["error"])
                    return reply.get("result", {})
                events.append(reply)
        try:
            target = call("Target.createTarget", {"url": "about:blank"})["targetId"]
            session = call("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
            call("Page.enable", session=session)
            call("Page.navigate", {"url": src.resolve().as_uri()}, session)
            while not any(e.get("method") == "Page.loadEventFired" and e.get("sessionId") == session for e in events):
                events.append(receive())
            ready = call("Runtime.evaluate", {"expression": "document.fonts.ready.then(() => document.fonts.status)", "awaitPromise": True, "returnByValue": True}, session)
            if ready.get("result", {}).get("value") != "loaded": raise RuntimeError("Print fonts did not finish loading")
            pdf = call("Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True, "displayHeaderFooter": False}, session)
            data = base64.b64decode(pdf["data"])
            if not data.startswith(b"%PDF"): raise RuntimeError("Chrome returned an invalid PDF")
            dst.write_bytes(data)
        finally:
            os.close(write_in); os.close(read_out)
            if proc.poll() is None:
                try: proc.terminate()
                except ProcessLookupError: pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Chrome occasionally ignores SIGTERM; target only this owned PID.
                try: proc.kill()
                except ProcessLookupError: pass
                proc.wait(timeout=10)
            print(f"Chrome PDF PID {proc.pid}: stopped ({proc.returncode})", flush=True)
            errors.close()
    return True

if __name__ == "__main__":
    langs = sys.argv[1:] or [l for l,_ in LANGS]
    outdir = root/"pdf"; outdir.mkdir(exist_ok=True)
    for l in langs:
        src = build(l); dst = outdir/f"SUP-Menu-{l}.pdf"
        ok = to_pdf(src, dst)
        print(l, "OK" if ok else "FAILED", dst.stat().st_size//1024 if ok else "", "KB", flush=True)
        if not ok: sys.exit(1)
