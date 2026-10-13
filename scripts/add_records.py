"""Add Town records that arrive outside CivicWeb and the Town website (public records [CORA] responses and the
like) to the archive.

catalog/records.csv lists each record: an ID from 910001 up (so it never collides with CivicWeb or Town website
IDs), its title, date, kind and source, the original file under private/records/ (git-ignored; kept exactly as
received) and that file's SHA-256 checksum. This script checks each original against its checksum, then writes its
text to text/<id>.json in the same format as CivicWeb documents, so build_index.py puts it in archive.db.

  PDF    text extracted like CivicWeb PDFs (OCR for scanned pages); a copy goes to pdf/<id>.pdf
  .xls   one page per worksheet, one line per row; Excel date serials in a "Date" column become YYYY-MM-DD and
         "...Amt" columns show cents
  .txt   one page (used for an email that came as quoted text)

Records released to a requester are Town records. The `url` column is the public copy posted with the site, if
any; it is empty until a copy is published. When it is under the site's base_url, the original is copied unchanged
to that path under docs/ (only for records that need no redaction; bank statements are not posted).
"""
import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import extract as pdf_extract  # noqa: E402
import xls_biff  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = json.load(open(os.path.join(ROOT, 'site_config.json'))).get('base_url', 'https://eldorarecord.org/')
CATALOG = os.path.join(ROOT, 'catalog', 'records.csv')
PRIVATE = os.path.join(ROOT, 'private', 'records')
TEXT = os.path.join(ROOT, 'text')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def cell(v, kind):
    if isinstance(v, float):
        if kind == 'date' and v > 20000:
            return (dt.date(1899, 12, 30) + dt.timedelta(days=int(v))).isoformat()
        if kind == 'amount' or not v.is_integer():
            return f'{v:,.2f}'
        return str(int(v))
    return str(v).strip()


def xls_pages(path):
    pages = []
    for n, (sheet, cells) in enumerate(xls_biff.read(path).items(), 1):
        lines, kinds = [f'Worksheet: {sheet}'], {}
        for _, row in xls_biff.rows(cells):
            if 'Date' in row:   # header row: note which columns hold dates and amounts
                kinds = {i: 'date' if v == 'Date' else 'amount' for i, v in enumerate(row)
                         if v == 'Date' or str(v).endswith('Amt')}
            lines.append(' | '.join(cell(v, kinds.get(i)) for i, v in enumerate(row) if v != ''))
        pages.append({'n': n, 'text': '\n'.join(lines), 'ocr': False})
    return pages


def write(doc_id, pages):
    json.dump({'pages': pages}, open(os.path.join(TEXT, f'{doc_id}.json'), 'w'))
    with open(os.path.join(TEXT, f'{doc_id}.txt'), 'w') as f:
        for p in pages:
            f.write(f"=== Page {p['n']} ===\n{p['text']}\n")


def main():
    if not os.path.exists(CATALOG):
        return
    problems = 0
    for r in csv.DictReader(open(CATALOG)):
        src = os.path.join(PRIVATE, r['file'])
        if not os.path.exists(src):
            print(f"MISSING: {r['id']} {r['file']} (originals are kept in private/records/, not in git)")
            problems += 1
            continue
        if sha256(src) != r['sha256']:
            print(f"CHANGED: {r['id']} {r['file']} no longer matches its recorded checksum; not indexed")
            problems += 1
            continue
        ext = os.path.splitext(src)[1].lower()
        if ext == '.pdf':
            dest = os.path.join(ROOT, 'pdf', f"{r['id']}.pdf")
            if not os.path.exists(dest) or sha256(dest) != r['sha256']:
                shutil.copy(src, dest)
            pdf_extract(dest)
        elif ext == '.xls':
            write(r['id'], xls_pages(src))
        elif ext == '.txt':
            write(r['id'], [{'n': 1, 'text': open(src).read(), 'ocr': False}])
        else:
            print(f"SKIPPED: {r['id']} {r['file']}: no text extraction for {ext}")
            continue
        if r['url'].startswith(SITE):   # public copy posted with the site
            dest = os.path.join(ROOT, 'docs', r['url'][len(SITE):])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not os.path.exists(dest) or sha256(dest) != r['sha256']:
                shutil.copy(src, dest)
        n = len(json.load(open(os.path.join(TEXT, f"{r['id']}.json")))['pages'])
        print(f"{r['id']} {r['date']} {r['title']}: {n} page(s)")
    if problems:
        sys.exit(1)


if __name__ == '__main__':
    main()
