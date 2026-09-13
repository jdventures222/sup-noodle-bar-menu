import json, subprocess, pathlib, re, sys
root = pathlib.Path(__file__).parent
structure = json.load(open(root/"structure.json"))
en = json.load(open(root/"strings.en.json"))
names = []
for sec in structure["sections"]:
    for it in sec["items"]: names.append((it["id"], en[f"item.{it['id']}.name"]))
prices = set()
for sec in structure["sections"]:
    for it in sec["items"] + sec.get("addons", []):
        for p in it["prices"]:
            v = round(p["p"]*100)/100; prices.add(str(int(v)) if v == int(v) else f"{v:.2f}")
ok_all = True
for lang in sys.argv[1:]:
    pdf = root/"pdf"/f"SUP-Menu-{lang}.pdf"
    out = root/"pdf"/f"{lang}-check"; subprocess.run(["rm","-rf",str(out)]); out.mkdir()
    r = subprocess.run([str(root/"render"), str(pdf), str(out)], capture_output=True, text=True).stdout
    pages = int(re.search(r"pages: (\d+)", r).group(1))
    sizes = set(re.findall(r"size: ([\d.]+) x ([\d.]+)", r))
    text = "".join(open(p, encoding="utf-8").read() for p in sorted(out.glob("*.txt")))
    norm = re.sub(r"\s+", " ", text)
    missing = [n for _, n in names if n.lower() not in norm.lower()]
    missing_prices = [p for p in prices if ("$"+p) not in norm]
    photo_note = "placeholders" in norm
    status = "OK" if not missing and not missing_prices and sizes == {("612.0","792.0")} else "CHECK"
    if status != "OK": ok_all = False
    print(f"{lang}: pages={pages} size={sizes} missingNames={missing} missingPrices={missing_prices} photoNote={photo_note} -> {status}")
    subprocess.run(["rm","-rf",str(out)])
sys.exit(0 if ok_all else 1)
