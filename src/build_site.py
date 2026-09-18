"""Package public assets only; release.py is the verified publishing entry point."""
import json
import pathlib
import shutil
import subprocess
import tempfile
from build_common import LANGS, read_strings, revision
from sup_seo import manifest
from sup_sw import generate

root = pathlib.Path(__file__).parent
site = root / 'site'
if site.exists():
    shutil.rmtree(site)
(site / 'img' / 'full').mkdir(parents=True)
(site / 'img' / 'var').mkdir()
(site / 'pdf').mkdir()
(site / 'index.html').write_text((root / 'sup-menu.html').read_text())
for source, target in [('items', 'img'), ('full', 'img/full'), ('variants', 'img/var')]:
    for path in (root / 'assets' / source).iterdir():
        if path.suffix in ('.jpg', '.png', '.avif', '.webp'):
            shutil.copy2(path, site / target / path.name)
for lang in LANGS:
    shutil.copy2(root / 'pdf' / f'SUP-Menu-{lang}.pdf', site / 'pdf')
shutil.copy2(root / 'assets' / 'logo.png', site / 'img' / 'logo.png')
for path in sorted(list(root.glob('assets/logo.l*.*')) + list(root.glob('assets/mark.*'))):
    if path.suffix in ('.png', '.avif', '.webp'):
        shutil.copy2(path, site / 'img' / path.name)
shutil.copy2(root / 'assets' / 'logo.png', site / 'img' / 'social-logo.png')
shutil.copy2(root / 'assets' / 'icon.png', site / 'img' / 'icon.png')
for name in ('doodle.jpg', 'doodle.avif', 'doodle.webp'):
    shutil.copy2(root / 'assets' / name, site / 'img' / name)

# Compile and run by exact executable path; all tools/intermediate files stay in tests/.
(root / 'tests').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='qr-build-', dir=root / 'tests') as work:
    work = pathlib.Path(work)
    for name in ('qr', 'qrread'):
        subprocess.run(['swiftc', '-O', '-module-cache-path', str(work / 'modules'), '-o', str(work / name), str(root / f'{name}.swift')], check=True)
    qr = root / 'assets' / 'qr-menu.png'
    url = 'https://menu.fyt.life/r/sup'  # the printed address forwards to the menu; the root is the directory
    subprocess.run([str(work / 'qr'), url, str(qr), '2048', str(root / 'assets' / 'logo.png')], check=True)
    decoded = subprocess.check_output([str(work / 'qrread'), str(qr)], text=True).strip()
    if not decoded.endswith(f'1 code(s) -> ["{url}"]'):
        raise ValueError(f'QR decode mismatch: {decoded}')
    print(decoded, flush=True)
    shutil.copy2(qr, site / 'img' / 'qr-menu.png')
card = (root / 'qrcard.html').read_text().replace('assets/logo.png', 'img/logo.png').replace('assets/qr-menu.png', 'img/qr-menu.png')
(site / 'qrcard.html').write_text(card)
(site / 'revision.json').write_text(json.dumps(revision(root), indent=2) + '\n')
(site / 'manifest.webmanifest').write_text(manifest(read_strings(root)['en']))
(site / '.nojekyll').write_text('')
shutil.copytree(root / 'assets/sup-fonts', site / 'sup-fonts')
generate(root, site, revision(root))
print(f'site built: {sum(p.is_file() for p in site.rglob("*"))} public files', flush=True)
