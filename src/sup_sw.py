"""Generate an exact allowlist from the finished public tree, including its own files."""
import json
import os

BASE='/sup/'  # the menu's directory on menu.fyt.life; the directory of every menu is the root

def manifest(site, rev):
    paths=sorted({BASE+p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()} |
                 {BASE+'sup-worker.js',BASE+'sup-manifest.json'})
    return {'revision':rev,'enabled':os.environ.get('SUP_SW_DISABLED')!='1','base':BASE,'files':paths,
            'aliases':{BASE:BASE+'index.html'},'precache':[BASE+'index.html',BASE+'img/logo.png']}

def generate(root, site, rev):
    data=manifest(site,rev)
    (site/'sup-manifest.json').write_text(json.dumps(data,indent=2)+'\n')
    (site/'sup-worker.js').write_text((root/'sup-worker.js').read_text().replace('__SUP_MANIFEST__',json.dumps(data,separators=(',',':'))))
