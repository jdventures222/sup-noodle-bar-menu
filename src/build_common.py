"""Shared release inputs, strict locale coverage and reproducible menu revision."""
import datetime
import hashlib
import json
import os
import shutil
from pathlib import Path

LANGS = ['en', 'es', 'vi', 'ko', 'zh', 'zh-Hant', 'tl', 'fa', 'ar', 'ja', 'ru', 'hi', 'ur']
SOURCES = ['build.py', 'build_print.py', 'build_site.py', 'build_common.py', 'release.py',
           'template.html', 'print_template.html', 'qrcard.html', 'qr.swift', 'qrread.swift',
           'structure.json', 'sup_fonts.py', 'sup_nojs.py', 'sup_seo.py', 'sup_sw.py', 'sup-worker.js'] + [f'strings.{lang}.json' for lang in LANGS]

PHASE2_KEYS = {'ui.' + key for key in ('search', 'searchHint', 'searchCount', 'searchNone',
    'offlineSaved')}

def poppler_tool(name):
    candidates = [shutil.which(name), '/opt/homebrew/bin/' + name, '/usr/local/bin/' + name,
                  '/opt/homebrew/opt/poppler/bin/' + name, '/usr/local/opt/poppler/bin/' + name]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError('Missing Poppler tool ' + name + '. Install Poppler (brew install poppler), '
                       'or add its bin directory to PATH. Build has not started.')

def source_files(root):
    return [root / name for name in SOURCES] + sorted(p for p in (root / 'assets').rglob('*')
        if p.is_file() and p.name != 'qr-menu.png' and not p.name.startswith('.'))

def source_hash(root):
    digest = hashlib.sha256()
    for path in source_files(root):
        digest.update(str(path.relative_to(root)).encode() + b'\0')
        digest.update(path.read_bytes())
    return digest.hexdigest()

def revision(root):
    epoch = os.environ.get('SOURCE_DATE_EPOCH')
    date = (datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc) if epoch
            else datetime.datetime.now(datetime.timezone.utc)).date().isoformat()
    short = hashlib.sha256((source_hash(root) + '|sup-sw-disabled=' + os.environ.get('SUP_SW_DISABLED', '0')).encode()).hexdigest()[:8]
    return {'date': date, 'hash': short, 'stamp': f'{date} {short}'}

def read_strings(root):
    strings = {lang: json.loads((root / f'strings.{lang}.json').read_text()) for lang in LANGS}
    keys = set(strings['en'])
    for lang, values in strings.items():
        missing, extra = keys - set(values), set(values) - keys
        if missing or extra:
            raise ValueError(f'{lang}: missing keys {sorted(missing)}; unknown keys {sorted(extra)}')
        for key, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{lang}: empty/invalid string {key}')
    return strings
