"""Download selected CivicWeb documents into pdf/.

Usage: python3 scripts/fetch.py            # downloads everything in catalog/catalog.csv with selected=1
Files land at pdf/<id>.pdf (or .<ext> for non-PDF documents). Existing valid files are skipped.
"""
import csv
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

BASE = 'https://nederlandco.civicweb.net'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, 'pdf')


def valid(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    if path.endswith('.pdf'):
        return subprocess.run(['pdfinfo', path], capture_output=True).returncode == 0
    return True


def fetch(row):
    doc_id = row['id']
    existing = [f for f in os.listdir(PDF) if f.split('.')[0] == doc_id]
    if existing and valid(os.path.join(PDF, existing[0])):
        return doc_id, 'skip'
    tmp = os.path.join(PDF, f'{doc_id}.part')
    hdr = os.path.join(PDF, f'{doc_id}.hdr')
    for _ in range(3):
        r = subprocess.run(['curl', '-sL', '-m', '300', '-A', 'Mozilla/5.0', '-D', hdr, '-o', tmp,
                            f'{BASE}/document/{doc_id}/'], capture_output=True)
        if r.returncode == 0 and os.path.getsize(tmp) > 0:
            break
    else:
        return doc_id, 'FAILED'
    ctype = ''
    with open(hdr, errors='replace') as f:
        for line in f:
            if line.lower().startswith('content-type:'):
                ctype = line.split(':', 1)[1].strip().lower()
    os.remove(hdr)
    ext = {'application/pdf': 'pdf', 'text/html': 'html'}.get(ctype.split(';')[0], None)
    if ext is None:
        ext = ctype.split('/')[-1].split(';')[0] or 'bin'
    os.replace(tmp, os.path.join(PDF, f'{doc_id}.{ext}'))
    return doc_id, ext


if __name__ == '__main__':
    os.makedirs(PDF, exist_ok=True)
    with open(os.path.join(ROOT, 'catalog', 'catalog.csv')) as f:
        rows = [r for r in csv.DictReader(f) if r['selected'] == '1']
    print(f'{len(rows)} selected', file=sys.stderr)
    with ThreadPoolExecutor(6) as ex:
        for n, (doc_id, status) in enumerate(ex.map(fetch, rows), 1):
            if status != 'skip':
                print(f'{n}/{len(rows)} {doc_id} {status}', file=sys.stderr, flush=True)
