"""Generate an exact allowlist from the finished public tree, including its own files."""
import json
import os

def manifest(site, rev):
    paths=sorted({'/'+p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()} |
                 {'/sup-worker.js','/sup-manifest.json'})
    return {'revision':rev,'enabled':os.environ.get('SUP_SW_DISABLED')!='1','files':paths,
            'aliases':{'/':'/index.html'},'precache':['/index.html','/img/logo.png']}

def generate(root, site, rev):
    data=manifest(site,rev)
    (site/'sup-manifest.json').write_text(json.dumps(data,indent=2)+'\n')
    (site/'sup-worker.js').write_text((root/'sup-worker.js').read_text().replace('__SUP_MANIFEST__',json.dumps(data,separators=(',',':'))))
