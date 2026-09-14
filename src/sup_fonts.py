"""Refresh bundled Google Fonts text subsets. Not run during an ordinary release."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode
from build_common import LANGS, read_strings

ROOT = Path(__file__).resolve().parent
FAMILIES = {'ko':'Noto Sans KR','zh':'Noto Sans SC','zh-Hant':'Noto Sans TC',
            'fa':'Noto Sans Arabic','ar':'Noto Sans Arabic','ur':'Noto Nastaliq Urdu',
            'ja':'Noto Sans JP','hi':'Noto Sans Devanagari','ru':'Noto Sans'}
UA = 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'

def glyphs(strings, lang):
    return ''.join(sorted(set(''.join(strings[lang].values()) + ''.join(strings['en'].values()) +
        '0123456789+$.,:;!?@/()-–— ·، hello@keiconcepts.info keiconcepts.info/brands/sup SUP Noodle Bar')))

def glyph_hash(strings, lang):
    return hashlib.sha256(glyphs(strings, lang).encode()).hexdigest()

def fetch(url):
    return subprocess.check_output(['curl','--fail','--silent','--show-error','--retry','3','-A',UA,url])

def refresh():
    strings=read_strings(ROOT); folder=ROOT/'assets/sup-fonts'; folder.mkdir(exist_ok=True)
    manifest={'languages':{},'fonts':{},'licenses':[]}
    for lang in LANGS:
        families=[FAMILIES[lang]] if lang in FAMILIES else ['Barlow Condensed','Noto Sans']
        css=''
        for family in families:
            weights='700;800' if family=='Barlow Condensed' else '400..800'
            if family=='Noto Nastaliq Urdu': weights='400..700'
            url='https://fonts.googleapis.com/css2?'+urlencode({'family':family+':wght@'+weights,'display':'swap','text':glyphs(strings,lang)})
            chunk=fetch(url).decode()
            for fonturl in set(re.findall(r'url\((https://[^)]+)\)',chunk)):
                data=fetch(fonturl); assert data[:4]==b'wOF2', family
                name='sup-'+hashlib.sha256(data).hexdigest()[:16]+'.woff2'; (folder/name).write_bytes(data)
                manifest['fonts'][name]={'family':family,'url':fonturl,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
                chunk=chunk.replace(fonturl,name)
            css+=chunk
        (folder/('sup-'+lang+'.css')).write_text(css)
        manifest['languages'][lang]={'glyph_hash':glyph_hash(strings,lang),'families':families}
        print(lang,len(css),'CSS bytes',flush=True)
    for family in sorted(set(['barlowcondensed','notosans','notosanskr','notosanssc','notosanstc','notosansarabic','notonastaliqurdu','notosansjp','notosansdevanagari'])):
        name='sup-'+family+'-OFL.txt';(folder/name).write_bytes(fetch('https://raw.githubusercontent.com/google/fonts/main/ofl/'+family+'/OFL.txt'));manifest['licenses'].append(name)
    keep=set(manifest['fonts'])|set(manifest['licenses'])|{'sup-'+l+'.css' for l in LANGS}|{'sup-manifest.json'}
    for p in folder.iterdir():
        if p.name not in keep:p.unlink()
    (folder/'sup-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__': refresh()
