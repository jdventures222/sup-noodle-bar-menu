"""Small, semantic English fallback generated from the same approved menu data."""
from html import escape as esc
from build_common import LANGS

LABELS = ['English','Español','Tiếng Việt','한국어','简体中文','繁體中文','Tagalog','فارسی','العربية','日本語','Русский','हिन्दी','اردو']

def markup(structure, s):
    def t(key): return esc(s.get(key, ''))
    def price(p):
        n=p['p']; value=str(int(n)) if n==int(n) else format(n,'.2f')
        return '<bdi dir="ltr">'+('+' if p.get('plus') else '')+'$'+value+'</bdi>'
    def contains(entry):
        # The Contains line leaves off what a dish is itself, as a fried egg is egg (the owner, 2026-09-23).
        values=set(entry.get('contains',[])+entry.get('likely',[]))-set(entry.get('containsOmit',[]))
        return ('<p><b>'+t('ui.contains')+':</b> '+', '.join(t('allergen.'+a) for a in structure['allergens'] if a in values)+'</p>') if values else ''
    def item(it,kind='item'):
        key=kind+'.'+it['id']; out='<article><h3>'+t(key+'.name')+'</h3>'
        for suffix in ('tagline','desc','note'):
            if key+'.'+suffix in s: out+='<p>'+t(key+'.'+suffix)+'</p>'
        for p in it['prices']:
            out+='<p>'+(t(key+'.price.'+p['k'])+' · ' if 'k' in p else '')+price(p)+'</p>'+contains(p)
        out+=contains(it)
        if it.get('addons'): out+='<h4>'+t('ui.sides')+'</h4>'+''.join(item(a,'addon') for a in it['addons'])
        return out+'</article>'
    out='<noscript><style>.masthead,.bar,footer.end,.skip{display:none} #sup-nojs{padding-block:20px} #sup-nojs article{border-bottom:1px solid var(--line);padding:8px 0} #sup-nojs p{margin:6px 0} #sup-nojs a{overflow-wrap:anywhere}</style><div id="sup-nojs" lang="en" dir="ltr"><h1>'+t('ui.title')+'</h1><p>'+t('ui.tagline')+'</p>'
    out+='<p>'+t('ui.legendTitle')+': '+t('ui.printKey')+' '+t('ui.noLineNote')+'</p>'
    for sp in structure['specials']:
        k='lunch' if sp['id']=='lunch' else 'kimchi'
        out+='<h2>'+t('ui.'+k+'Title')+'</h2>'
        if k=='lunch':out+='<p>'+price({'p':sp['offer']})+' <s>'+price({'p':sp['regular']})+'</s></p>'
        for suffix in ('Eyebrow','When','Terms','Sub'):
            if 'ui.'+k+suffix in s:out+='<p>'+t('ui.'+k+suffix)+'</p>'
    for sec in structure['sections']:
        out+='<section><h2>'+t('sec.'+sec['id']+'.title')+'</h2>'
        for suffix in ('intro','brothNote'):
            if 'sec.'+sec['id']+'.'+suffix in s:out+='<p>'+t('sec.'+sec['id']+'.'+suffix)+'</p>'
        if sec['id']=='drinks':out+='<p>'+t('ui.refillsNote')+'</p>'
        out+=''.join(item(it) for it in sec['items'])
        if sec.get('addons'):out+='<h3>'+t('ui.addons')+'</h3>'+''.join(item(a,'addon') for a in sec['addons'])
        out+='</section>'
    out+='<p><b>'+t('ui.allergyTitle')+'</b> '+t('ui.allergyNotice')+'</p><p><b>'+t('ui.rawTitle')+'</b> '+t('ui.rawNotice')+'</p>'
    out+='<p>'+t('ui.pdfMenu')+': '+' · '.join('<a href="pdf/SUP-Menu-'+lang+'.pdf"><bdi lang="'+lang+'">'+label+'</bdi></a>' for lang,label in zip(LANGS,LABELS))+'</p>'
    out+='<p>Buena Park · 5141 Beach Blvd Unit B · 714-521-2444<br>Irvine · 14370 Culver Dr Unit 2H · 657-300-8420</p><p>@supnoodlebar<br><a href="https://www.keiconcepts.info/brands/sup">keiconcepts.info/brands/sup</a><br><a href="mailto:hello@keiconcepts.info">hello@keiconcepts.info</a></p></div></noscript>'
    return out
