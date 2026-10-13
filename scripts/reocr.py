"""Re-OCR the signed "Minutes - Adopted" scans for the Board of Trustees with tesseract.

The text layer CivicWeb ships with these scans is unreliable (it has scrambled names in vote tallies), so
every page is rendered at 300 dpi and read by tesseract, ignoring the embedded layer. Output replaces
text/<id>.json / .txt, with every page marked ocr=true. Already re-OCR'd documents are skipped.
"""
import csv
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import ROOT, TEXT, TMP, ocr_page, page_count  # noqa: E402


def reocr(doc_id):
    path = os.path.join(ROOT, 'pdf', f'{doc_id}.pdf')
    out_json = os.path.join(TEXT, f'{doc_id}.json')
    if os.path.exists(out_json) and json.load(open(out_json)).get('reocr'):
        return doc_id, None
    pages = [{'n': n, 'text': ocr_page(path, n), 'ocr': True} for n in range(1, page_count(path) + 1)]
    with open(out_json, 'w') as f:
        json.dump({'pages': pages, 'reocr': True}, f)
    with open(os.path.join(TEXT, f'{doc_id}.txt'), 'w') as f:
        for p in pages:
            f.write(f"\n=== Page {p['n']} (OCR) ===\n{p['text']}\n")
    return doc_id, len(pages)


if __name__ == '__main__':
    os.makedirs(TEXT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    with open(os.path.join(ROOT, 'catalog', 'catalog.csv')) as f:
        ids = [r['id'] for r in csv.DictReader(f)
               if r['selected'] == '1' and r['kind'] == 'Minutes' and r['fmt'] == 'Adopted'
               and 'TRUSTEES' in r['body'].upper()]
    print(f'{len(ids)} adopted BOT minutes', file=sys.stderr)
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as ex:
        for n, (doc_id, pages) in enumerate(ex.map(reocr, ids), 1):
            if pages:
                print(f'{n}/{len(ids)} {doc_id} pages={pages}', file=sys.stderr, flush=True)
