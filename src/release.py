#!/usr/bin/env python3
"""Build, verify, then replace site/. See BUILD.md for prerequisites and guarantees."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from build_common import LANGS, SOURCES, PHASE2_KEYS, read_strings, source_hash, poppler_tool
from sup_sw import BASE, manifest
from sup_nojs import markup
from sup_seo import LOCATIONS

ROOT = Path(__file__).resolve().parent

class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.urls, self.prices, self.price_depth = [], [], 0
        self.price_text = ''
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('src', 'href', 'poster'):
            if key in attrs:
                self.urls.append(attrs[key])
        if tag == 'meta' and attrs.get('property', attrs.get('name')) in ('og:image', 'twitter:image'):
            self.urls.append(attrs['content'])
        if self.price_depth:
            self.price_depth += 1
        elif 'price' in attrs.get('class', '').split():
            self.price_depth, self.price_text = 1, ''
    def handle_endtag(self, tag):
        if self.price_depth:
            self.price_depth -= 1
            if not self.price_depth:
                self.prices.append(self.price_text)
    def handle_data(self, data):
        if self.price_depth:
            self.price_text += data


LOCATION_BLOCKS = set('address article aside blockquote br dd div dl dt fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section table tbody td th thead tr ul'.split())


class LocationText(HTMLParser):
    """Decode HTML5 entities; inline elements preserve adjoining text nodes."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag in ('head', 'script', 'style'):
            self.hidden.append(tag)
        if not self.hidden and tag in LOCATION_BLOCKS:
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        if not self.hidden and tag in LOCATION_BLOCKS:
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def normalize_location(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    return re.sub(r'[\s\u00b7\u30fb\u00ad\u034f\u180e\u200b-\u200f\u2060-\u2064\ufeff\u202a-\u202e\u2066-\u2069\-\u2010-\u2015\u2212]+', '', text)


def verify_menu_contacts(fallback):
    """Only SUP's final no-JS contacts (city · street · phone) and its tagline under the heading may name a place,
    each exactly as restored on the owner's word (2026-09-29)."""
    expected = '<p>' + '<br>'.join(loc['city'] + ' · ' + loc['street'] + ' · ' + loc['phone'] for loc in LOCATIONS) + '</p>'
    pattern = r'<p>[^<>]*<br>[^<>]*</p>(?=<p>@supnoodlebar<br>[\s\S]*?</p></div></noscript>\s*$)'
    contacts = re.findall(pattern, fallback)
    if 'id="sup-nojs"' not in fallback or contacts != [expected]:
        raise ValueError('SUP phone labels: missing footer, street address or incorrect city/phone pairing')
    # Standalone serving copy of brand/scripts/location_terms.json; checked for parity.
    contract = json.loads((ROOT / 'location_terms.json').read_text())
    tagline = r'(?<=</h1>)<p>([^<>]*)</p>'
    if re.findall(r'<h1>[^<>]*</h1><p>([^<>]*)</p>', fallback) != [contract['supTaglines']['en']]:
        raise ValueError('SUP tagline: the fallback does not carry the tagline with its cities')
    # Remove exactly the validated footer contacts and tagline, not every city occurrence.
    remaining = re.sub(pattern, '<p>' + '<br>'.join(loc['phone'] for loc in LOCATIONS) + '</p>', fallback)
    remaining = re.sub(tagline, '<p></p>', remaining, count=1)
    visible = normalize_location(''.join(LocationText(remaining).parts))
    terms = set(contract['forbidden'])
    terms.update(loc[key] for loc in LOCATIONS for key in ('city', 'street'))
    terms.update(words[key] for words in read_strings(ROOT).values() for key in ('ui.buenaPark', 'ui.irvine'))
    for term in terms:
        if normalize_location(term) in visible:
            raise ValueError('Visible menu location: ' + term)


def verify_location_controls(fallback):
    # Inside the menu, BEFORE contacts: the end-anchored footer remains valid.
    def insert(html):
        mutant = fallback.replace('<h1>', html + '<h1>', 1)
        assert mutant != fallback, 'Missing menu body for location control'
        return mutant

    verify_menu_contacts(insert('<p>Welcome</p>'))
    contract = json.loads((ROOT / 'location_terms.json').read_text())
    controls = contract['regressionControls'] + [
        {'class': 'verified alias', 'html': '<p>' + term + '</p>'} for term in contract['forbidden']]
    controls += [{'class': 'SUP source contact', 'html': '<p>' + loc[key] + '</p>'}
                 for loc in LOCATIONS for key in ('city', 'street')]
    for test in controls:
        try:
            verify_menu_contacts(insert(test['html']))
        except ValueError as exc:
            if not str(exc).startswith('Visible menu location: '):
                raise AssertionError('Wrong failure for ' + test['class']) from exc
        else:
            raise ValueError('Menu location control accepted: ' + test['class'])
    tagline = '<p>' + contract['supTaglines']['en'] + '</p>'
    for name, mutant, reason in [
            ('swapped city/phone', fallback.replace('Buena Park · 5141', 'Irvine · 5141'), 'SUP phone labels: '),
            ('footer without a street address', fallback.replace(' · 5141 Beach Blvd Unit B · ', ' · '), 'SUP phone labels: '),
            ('tagline without its cities', fallback.replace(tagline, '<p>Vietnamese noodle bar</p>'), 'SUP tagline: '),
            ('another city in the tagline', fallback.replace(tagline, tagline[:-4] + ' and Fountain Valley</p>'), 'SUP tagline: ')]:
        assert mutant != fallback, 'Vacuous control: ' + name
        try:
            verify_menu_contacts(mutant)
        except ValueError as exc:
            if not str(exc).startswith(reason):
                raise AssertionError('Wrong failure for ' + name) from exc
        else:
            raise ValueError('SUP control accepted: ' + name)
    print(f'PASS SUP location controls: {len(controls)} location-specific failures; swapped phone, bare footer and tagline controls rejected; harmless body text passes')


def verify_restored_locations(work, site, text, strings):
    """James, 2026-09-29: SUP shows both street addresses and the tagline's cities again, on screen in every language,
    in the no-JS menu (verify_menu_contacts) and in all 13 print pages and PDFs."""
    contract = json.loads((work / 'location_terms.json').read_text())
    contacts = contract['supFooterPhones']
    if [(c['street'], c['locality'], c['phone']) for c in contacts] != [(loc['street'], loc['city'] + ', CA ' + loc['zip'], loc['phone']) for loc in LOCATIONS]:
        raise ValueError('Location contract differs from the JSON-LD locations')
    for c in contacts:
        # The screen footer is one template for every language; only its city heading is translated.
        if text.count(f'{c["street"]}<br>{c["locality"]}<br><a href="{c["href"]}"><bdi dir="ltr">{c["phone"]}</bdi></a>') != 1:
            raise ValueError('Screen footer lacks the street address: ' + c['street'])
    for lang in LANGS:
        if strings[lang]['ui.tagline'] != contract['supTaglines'][lang]:
            raise ValueError(f'{lang}: tagline is not the tagline with its cities')
        page = (work / f'print-{lang}.html').read_text()
        brand = re.findall(r'<h1 class="caps">[\s\S]*?</h1><p>([\s\S]*?)</p></div></div>', page)
        if len(brand) != 1 or re.sub(r'<[^>]+>', '', brand[0]) != contract['supTaglines'][lang]:
            raise ValueError(f'{lang}: print tagline is not the tagline with its cities')
        pdf_text = re.sub(r'\s+', '', subprocess.check_output([poppler_tool('pdftotext'), '-enc', 'UTF-8', str(site / 'pdf' / f'SUP-Menu-{lang}.pdf'), '-'], text=True))
        for c in contacts:
            address = f'{c["street"]}, {c["locality"]} · {c["phone"]}'
            if page.count(f'<address dir="ltr">{address}</address>') != 1 or re.sub(r'\s+', '', address) not in pdf_text:
                raise ValueError(f'{lang}: print page or PDF lacks the street address: {c["street"]}')
    print('PASS SUP locations shown: both street addresses on screen, in print and in 13 PDFs; the tagline with its cities in 13 languages')


def verify(work):
    site = work / 'site'
    strings = read_strings(work)
    if not PHASE2_KEYS <= set(strings['en']):
        raise ValueError('Missing phase 2 UI keys: ' + str(PHASE2_KEYS - set(strings['en'])))
    text = (site / 'index.html').read_text()
    data = json.loads(re.search(r'const DATA = (.*?);\nconst LANGS', text, re.S).group(1))
    if set(data['strings']) != set(LANGS) or data['strings'] != strings:
        raise ValueError('Built language bundle differs from complete source translations')
    if data['structure'] != json.loads((work / 'structure.json').read_text()):
        raise ValueError('Built structure/prices differ from source')
    expected = {'index.html', 'qrcard.html', 'revision.json', '.nojekyll', 'manifest.webmanifest',
                'img/logo.png', 'img/social-logo.png', 'img/qr-menu.png',
                'img/icon.png', 'img/doodle.jpg', 'img/doodle.avif', 'img/doodle.webp'}
    for source, target in [('items', 'img'), ('full', 'img/full'), ('variants', 'img/var')]:
        expected.update(f'{target}/{p.name}' for p in (work / 'assets' / source).iterdir() if p.suffix in ('.jpg', '.png', '.avif', '.webp'))
    expected.update(f'img/{p.name}' for p in (work / 'assets').glob('logo.l*.*') if p.suffix in ('.avif', '.webp'))
    expected.update(f'img/{p.name}' for p in (work / 'assets').glob('mark.*') if p.suffix in ('.png', '.avif', '.webp'))
    expected.update(f'pdf/SUP-Menu-{lang}.pdf' for lang in LANGS)
    expected.update('sup-fonts/' + p.name for p in (work / 'assets/sup-fonts').iterdir() if p.is_file())
    expected.update({'sup-worker.js', 'sup-manifest.json'})
    actual = {str(p.relative_to(site)) for p in site.rglob('*') if p.is_file()}
    if actual != expected:
        raise ValueError(f'Public output mismatch: missing={expected-actual}; stray/private={actual-expected}')
    sw_manifest = json.loads((site / 'sup-manifest.json').read_text())
    if sw_manifest != manifest(site, data['revision']) or set(sw_manifest['files']) != {BASE + p for p in actual}:
        raise ValueError('SUP worker allowlist does not exactly match published files')
    worker = (site / 'sup-worker.js').read_text()
    if worker != (work / 'sup-worker.js').read_text().replace('__SUP_MANIFEST__', json.dumps(sw_manifest, separators=(',', ':'))):
        raise ValueError('Worker differs from approved template / allowlist')
    fallback = markup(data['structure'], strings['en'])
    if fallback not in text or '<div id="sup-nojs"' not in fallback:
        raise ValueError('Missing generated no-JS menu')
    places = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S).group(1))
    dishes = sum(len(sec['items']) for sec in data['structure']['sections'])
    if [p['address']['streetAddress'] for p in places] != [loc['street'] for loc in LOCATIONS] or any(
            sum(len(s['hasMenuItem']) for s in p['hasMenu']['hasMenuSection']) != dishes for p in places):
        raise ValueError('JSON-LD places or dish count differ from the data')
    verify_menu_contacts(fallback)
    verify_location_controls(fallback)
    verify_restored_locations(work, site, text, strings)
    if '<link rel="manifest" href="manifest.webmanifest">' not in text:
        raise ValueError('Missing web app manifest link')
    # The menu lives under BASE: its canonical, alternates and worker scope must all say so.
    if f'<link rel="canonical" href="https://menu.fyt.life{BASE}">' not in text or f'href="https://menu.fyt.life{BASE}?lang=ur"' not in text:
        raise ValueError('Canonical or alternates do not point at ' + BASE)
    if f"register('{BASE}sup-worker.js',{{scope:'{BASE}'" not in text or f"['{BASE}', '{BASE}index.html'].includes(location.pathname)" not in text:
        raise ValueError('Service worker is not registered at ' + BASE)
    contact = ('https://www.keiconcepts.info/brands/sup', 'keiconcepts.info/brands/sup', 'hello@keiconcepts.info')
    for filename in [site / 'index.html', site / 'qrcard.html'] + [work / f'print-{lang}.html' for lang in LANGS]:
        content = filename.read_text()
        if not all(part in content for part in contact) or 'info@supnoodlebar.com' in content:
            raise ValueError('Contact mismatch in ' + str(filename))
    # Every generated photo URL, including full-size and option images used only by JS.
    variant_map = json.loads((work / 'assets/variants/map.json').read_text())
    for item, keys in variant_map.items():
        for key in keys:
            for suffix in ('.jpg', '-thumb.jpg'):
                filename = f'{item}-{key}{suffix}'
                if not (site / 'img/var' / filename).is_file():
                    raise ValueError(f'Missing referenced option photo: {filename}')
    urls = ['img/' + filename for filename in data['photos'].values()]
    urls += ['img/full/' + row['f'] for row in data['full'].values()]
    urls += ['img/var/' + row[key] for rows in data['variants'].values() for row in rows for key in ('f', 't')]
    urls += [row[0] for formats in data['alt'].values() for fmt in ('avif', 'webp') for row in formats[fmt]]
    urls += [f'pdf/SUP-Menu-{lang}.pdf' for lang in LANGS]
    for file in site.glob('*.html'):
        urls += Document(file.read_text()).urls
        css = '\n'.join(re.findall(r'<style>(.*?)</style>', file.read_text(), re.S))
        urls += re.findall(r'url\([\'"]?([^\)\'"\s]+)', css)
    for url in urls:
        parsed = urlsplit(url)
        if parsed.scheme and not (parsed.scheme in ('http', 'https') and parsed.netloc == 'menu.fyt.life'):
            continue
        if not parsed.path:
            continue
        path = unquote(parsed.path)
        if parsed.netloc == 'menu.fyt.life':
            if not path.startswith(BASE):
                raise ValueError(f'Absolute URL outside {BASE}: {url}')
            path = path[len(BASE):]
        target = (site / path.lstrip('/')).resolve()
        if not target.is_relative_to(site.resolve()) or not target.exists():
            raise ValueError(f'Missing/invalid referenced asset: {url}')
    base_prices = None
    counts = {}
    for lang in LANGS:
        prices = Document((work / f'print-{lang}.html').read_text()).prices
        if base_prices is None:
            base_prices = prices
        if not prices or prices != base_prices or any(not re.fullmatch(r'[+$0-9.]+', p) for p in prices):
            raise ValueError(f'{lang}: price sequence differs or is not ASCII')
        pdf = site / 'pdf' / f'SUP-Menu-{lang}.pdf'
        info = subprocess.check_output([poppler_tool('pdfinfo'), str(pdf)], text=True)
        count = int(re.search(r'^Pages:\s+(\d+)', info, re.M).group(1))
        pages = subprocess.check_output([poppler_tool('pdfinfo'), '-f', '1', '-l', str(count), str(pdf)], text=True)
        sizes = re.findall(r'(?:Page\s+\d+ size|Page size):\s+([\d.]+) x ([\d.]+) pts', pages)
        if len(sizes) != count or any((float(w), float(h)) != (612, 792) for w, h in sizes):
            raise ValueError(f'{lang}: PDF is not US Letter on every page: {sizes}')
        counts[lang] = count
        pdf_text = subprocess.check_output([poppler_tool('pdftotext'), '-enc', 'UTF-8', str(pdf), '-'], text=True)
        if not all(part in pdf_text for part in contact[1:]) or 'info@supnoodlebar.com' in pdf_text:
            raise ValueError('PDF contact mismatch: ' + lang)
    rev = json.loads((site / 'revision.json').read_text())
    if rev != data['revision'] or f'content="{rev["stamp"]}"' not in text:
        raise ValueError('Revision stamp mismatch')
    print(json.dumps({'verified': True, 'languages': LANGS, 'keys_per_language': len(strings['en']),
                      'price_runs_per_language': len(base_prices), 'pdf_pages': counts,
                      'public_files': len(actual), 'revision': rev, 'worker_allowlist': len(sw_manifest['files']),
                      'nojs_bytes': len(fallback.encode()), 'contacts_verified': True}, ensure_ascii=False), flush=True)


def main():
    for name in ('pdfinfo', 'pdftotext'):
        print('Preflight:', name, poppler_tool(name), flush=True)
    read_strings(ROOT)  # Reject invalid inputs before generating anything.
    before = source_hash(ROOT)
    (ROOT / 'tests').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='release-', dir=ROOT / 'tests') as temp:
        work = Path(temp)
        for name in SOURCES:
            shutil.copy2(ROOT / name, work / name)
        shutil.copytree(ROOT / 'assets', work / 'assets')
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'}
        for script in ('build.py', 'build_print.py', 'build_site.py'):
            subprocess.run([sys.executable, str(work / script)], cwd=work, env=env, check=True)
        verify(work)
        if source_hash(ROOT) != before or source_hash(work) != before:
            raise ValueError('Source changed during release; retry to include concurrent edits. site/ untouched.')
        # Validate everything before the first mutation. Roll back all replacements on failure.
        names = ['site', 'pdf', 'sup-menu.html'] + [f'print-{lang}.html' for lang in LANGS]
        backups = work / 'previous'; backups.mkdir()
        installed = []
        try:
            for name in names:
                destination = ROOT / name
                if destination.exists():
                    os.replace(destination, backups / name)
                installed.append(name)
                os.replace(work / name, destination)
        except BaseException:
            for name in reversed(installed):
                destination = ROOT / name
                if destination.is_dir(): shutil.rmtree(destination)
                elif destination.exists(): destination.unlink()
                if (backups / name).exists(): os.replace(backups / name, destination)
            raise
        shutil.copy2(work / 'assets' / 'qr-menu.png', ROOT / 'assets' / 'qr-menu.png')
    print('RELEASE PASSED: site/ and PDF outputs replaced only after verification.', flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'RELEASE FAILED: {error}', file=sys.stderr, flush=True)
        sys.exit(1)
