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
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from build_common import LANGS, SOURCES, PHASE2_KEYS, read_strings, source_hash, poppler_tool
from sup_sw import manifest
from sup_nojs import markup

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
    expected = {'index.html', 'qrcard.html', 'revision.json', '.nojekyll',
                'img/logo.png', 'img/social-logo.png', 'img/qr-menu.png',
                'img/icon.png', 'img/doodle.jpg', 'img/doodle.avif', 'img/doodle.webp'}
    for source, target in [('items', 'img'), ('full', 'img/full'), ('variants', 'img/var')]:
        expected.update(f'{target}/{p.name}' for p in (work / 'assets' / source).iterdir() if p.suffix in ('.jpg', '.png', '.avif', '.webp'))
    expected.update(f'pdf/SUP-Menu-{lang}.pdf' for lang in LANGS)
    expected.update('sup-fonts/' + p.name for p in (work / 'assets/sup-fonts').iterdir() if p.is_file())
    expected.update({'sup-worker.js', 'sup-manifest.json'})
    actual = {str(p.relative_to(site)) for p in site.rglob('*') if p.is_file()}
    if actual != expected:
        raise ValueError(f'Public output mismatch: missing={expected-actual}; stray/private={actual-expected}')
    sw_manifest = json.loads((site / 'sup-manifest.json').read_text())
    if sw_manifest != manifest(site, data['revision']) or set(sw_manifest['files']) != {'/' + p for p in actual}:
        raise ValueError('SUP worker allowlist does not exactly match published files')
    worker = (site / 'sup-worker.js').read_text()
    if worker != (work / 'sup-worker.js').read_text().replace('__SUP_MANIFEST__', json.dumps(sw_manifest, separators=(',', ':'))):
        raise ValueError('Worker differs from approved template / allowlist')
    fallback = markup(data['structure'], strings['en'])
    if fallback not in text or '<div id="sup-nojs"' not in fallback:
        raise ValueError('Missing generated no-JS menu')
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
        target = (site / unquote(parsed.path).lstrip('/')).resolve()
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
