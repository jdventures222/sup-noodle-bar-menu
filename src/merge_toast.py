import json, re
a=json.load(open("research/toast-out.json")); st=json.load(open("structure.json"))
WORDS={"dairy":"milk","milk":"milk","egg":"egg","eggs":"egg","fish":"fish","shellfish":"shellfish","peanut":"peanut","peanuts":"peanut","tree nuts":"treenut","tree nut":"treenut","wheat":"gluten","soy":"soy","sesame":"sesame"}
ORDER=st["allergens"]
def norm(s): return re.sub(r'[^a-z0-9 ]','',s.lower().replace("&","and")).replace("noodles","noodle").strip()
def parse(stmt):
    s=stmt.lower(); return {c for w,c in WORDS.items() if re.search(r'\b'+re.escape(w)+r'\b', s)}
toast={}
for it in a["items"]:
    toast.setdefault(norm(it["name"]),set()).update(parse(it["allergenStatement"]))
def T(*names):
    out=set()
    for n in names:
        k=norm(n); hits=[x for x in toast if x==k] or [x for x in toast if x.startswith(k) or k.startswith(x)]
        if not hits: print("  !! no Toast match for", n); continue
        for h in hits: out|=toast[h]
    return out
MAP={
 "bao":{None:["Three Golden Baos","Single Golden Bao"]}, "springroll":{None:["Shrimp Spring Rolls"]}, "eggrolls":{None:["Egg Rolls"]},
 "shakenfries":{None:["Shaken House Fries"]}, "trufflefries":{None:["Truffle Fries"]}, "parmfries":{None:["Parmesan Fries"]},
 "wings":{"garlic":["Garlic Chicken Wings"],"parmesan":["Parmesan Chicken Wings"]}, "nuggets":{None:["Chicken Nugget Basket"]},
 "phoshortrib":{None:["Short Rib Pho"]}, "phoribbones":{None:["Rib Bone Pho"]}, "phobeefbelly":{None:["Beef Belly Pho"]}, "phofilet":{None:["Filet Mignon Pho"]},
 "phocombo":{None:["Combination Pho"]}, "phoveggie":{None:["Veggie & Tofu Pho"]}, "phobrisket":{None:["Brisket Pho"]}, "phoshrimp":{None:["Shrimp Pho"]},
 "phomeatballs":{None:["Meatball Pho","Meatball Only Pho"]}, "phobourdain":{None:["Anthony Bourdain Pho"]}, "drynoodle":{None:["Beef Belly Dry Noodle"]},
 "lomo":{"filet":["Filet Mignon Lomo Saltado"],"shrimp":["Shrimp Lomo Saltado"],"tofu":["Vegan Tofu Lomo Saltado"]},
 "cajun":{"shrimpsausage":["Shrimp And Sausage Cajun Garlic Noodle","Cajun Garlic Noodles with Shrimp/Sausage"],"filet":["Filet Mignon Cajun Garlic Noodles"]},
 "friedrice":{"shrimp":["Shrimp Fried Rice"],"spam":["Spam Fried Rice"],"wings":["Chicken Wing Fried Rice"],"filet":["Filet Mignon Fried Rice"],"softtofu":["Soft Tofu Fried Rice"],"friedtofu":["Fried Tofu Fried Rice"]},
 "kimchi":{"spam":["Spam Kimchi Fried Rice"],"softtofu":["Soft Tofu Kimchi Fried Rice"],"filet":["Filet Mignon Kimchi Fried Rice"]},
 "soybutter":{None:["Soy And Butter Noodle","Soy Butter Noodles"]}, "strawberrysoda":{None:["Strawberry Cream Soda"]}, "kidsbox":{None:["Kids Meal Box"]},
}
items={it["id"]:it for sec in st["sections"] for it in sec["items"]}
for id,vm in MAP.items():
    it=items[id]; before=set(it["contains"])|set(it["likely"])
    vsets={k:T(*names) for k,names in vm.items()}
    nonempty=[v for v in vsets.values() if v]
    common=set.intersection(*nonempty) if nonempty else set()
    base=before|common
    it["contains"]=[x for x in ORDER if x in base]; it["likely"]=[]
    it["source"]="SUP Toast allergen statements (Irvine + Buena Park) merged with menu descriptions"
    for p in it["prices"]:
        if "k" in p:
            extra=vsets.get(p["k"],set())-base
            if extra: p["contains"]=[x for x in ORDER if x in extra]
            elif "contains" in p: del p["contains"]
    variants=", ".join("%s:%s" % (p["k"], p["contains"]) for p in it["prices"] if p.get("contains"))
    print("%-14s base=%s added=%s variants={%s}" % (id, it["contains"], sorted(set(it["contains"])-before), variants))
items["sidebroth"]["contains"]=["fish","shellfish"]; items["sidebroth"]["likely"]=[]
json.dump(st, open("structure.json","w"), ensure_ascii=False, indent=1)
print("structure.json written")
