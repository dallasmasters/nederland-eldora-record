"""Crawl the Nederland CivicWeb Document Center folder tree.

Writes catalog/tree.json: one record per document with its id, title and folder path.
"""
import html
import json
import os
import re
import subprocess
import sys
import time

BASE = 'https://nederlandco.civicweb.net'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get(path):
    for _ in range(3):
        r = subprocess.run(['curl', '-sL', '-m', '60', '-A', 'Mozilla/5.0', BASE + path],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout
        time.sleep(2)
    print(f'FAILED {path}', file=sys.stderr)
    return ''


def ls(fid):
    """Return [(kind, id, title)] for the children of a folder (fid=None for the root)."""
    h = get('/filepro/documents' + (f'/{fid}' if fid else ''))
    out, seen = [], set()
    for m in re.finditer(r'href="/(filepro/documents|document)/(\d+)[^"]*"[^>]*>(.{0,600}?)</a>', h, re.S):
        title = html.unescape(html.unescape(' '.join(re.sub(r'<[^>]+>', ' ', m.group(3)).split())))
        i = int(m.group(2))
        if not title or i in seen or i == fid:
            continue
        seen.add(i)
        out.append(('folder' if m.group(1).startswith('filepro') else 'doc', i, title))
    return out


def walk(fid, path, docs, visited):
    for kind, i, title in ls(fid):
        if kind == 'folder':
            if i in visited:
                continue
            visited.add(i)
            print('  ' * len(path) + f'[{i}] {title}', file=sys.stderr, flush=True)
            walk(i, path + [title], docs, visited)
        else:
            docs.append({'id': i, 'title': title, 'folder_id': fid, 'path': '/'.join(path)})


if __name__ == '__main__':
    docs = []
    walk(None, [], docs, set())
    os.makedirs(os.path.join(ROOT, 'catalog'), exist_ok=True)
    with open(os.path.join(ROOT, 'catalog', 'tree.json'), 'w') as f:
        json.dump(docs, f, indent=1)
    print(f'{len(docs)} documents', file=sys.stderr)
