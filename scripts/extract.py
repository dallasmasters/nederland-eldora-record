"""Extract per-page text from pdf/ into text/, OCRing pages that have no text layer.

text/<id>.json  -> {"pages": [{"n": 1, "text": "...", "ocr": false}, ...]}
text/<id>.txt   -> the same text, readable, with "=== Page N ===" separators
Pages with fewer than MIN_CHARS non-space characters are rendered at 300 dpi and run through tesseract.
"""
import glob
import html
import re
import zipfile
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF, TEXT, TMP = (os.path.join(ROOT, d) for d in ('pdf', 'text', 'tmp'))
MIN_CHARS = 100


def page_count(path):
    out = subprocess.run(['pdfinfo', path], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith('Pages:'):
            return int(line.split()[1])
    return 0


def ocr_page(path, n):
    with tempfile.TemporaryDirectory(dir=TMP) as d:
        img = os.path.join(d, 'p')
        subprocess.run(['pdftoppm', '-r', '300', '-gray', '-png', '-f', str(n), '-l', str(n), '-singlefile', path, img],
                       capture_output=True)
        if not os.path.exists(img + '.png'):
            return ''
        r = subprocess.run(['tesseract', img + '.png', '-', '--psm', '3', '-l', 'eng'],
                           capture_output=True, text=True, env={**os.environ, 'OMP_THREAD_LIMIT': '1'})
        return r.stdout


def extract(path):
    doc_id = os.path.basename(path).split('.')[0]
    out_json = os.path.join(TEXT, f'{doc_id}.json')
    if os.path.exists(out_json) and os.path.getmtime(out_json) >= os.path.getmtime(path):
        return doc_id, None
    if path.endswith('.html'):
        r = subprocess.run(['python3', '-c', 'import sys,html,re;h=sys.stdin.read();'
                            'h=re.sub(r"(?is)<(script|style).*?</\\1>"," ",h);'
                            'print(html.unescape(re.sub(r"<[^>]+>"," ",h)))'],
                           stdin=open(path, errors='replace'), capture_output=True, text=True)
        pages = [{'n': 1, 'text': ' '.join(r.stdout.split()), 'ocr': False}]
    elif path.endswith(('.jpeg', '.jpg', '.png', '.gif', '.tiff')):
        r = subprocess.run(['tesseract', path, '-', '--psm', '3', '-l', 'eng'],
                           capture_output=True, text=True, env={**os.environ, 'OMP_THREAD_LIMIT': '1'})
        pages = [{'n': 1, 'text': r.stdout, 'ocr': True}]
    elif path.endswith('.presentation'):
        # PowerPoint (.pptx): one "page" per slide, text pulled from the slide XML
        with zipfile.ZipFile(path) as z:
            slides = sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                            key=lambda n: int(re.search(r'\d+', n.rsplit('/', 1)[1]).group()))
            pages = [{'n': i, 'text': '\n'.join(html.unescape(t) for t in
                                                re.findall(r'<a:t>([^<]*)</a:t>', z.read(s).decode('utf-8', 'replace'))),
                      'ocr': False} for i, s in enumerate(slides, 1)]
    elif not path.endswith('.pdf'):
        pages = []  # audio/video and other media: cataloged but not transcribed
    else:
        n_pages = page_count(path)
        raw = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True,
                             errors='replace').stdout.split('\f')
        pages = []
        for n in range(1, n_pages + 1):
            text = raw[n - 1] if n - 1 < len(raw) else ''
            ocr = False
            if len(''.join(text.split())) < MIN_CHARS:
                o = ocr_page(path, n)
                if len(''.join(o.split())) > len(''.join(text.split())):
                    text, ocr = o, True
            pages.append({'n': n, 'text': text, 'ocr': ocr})
    with open(out_json, 'w') as f:
        json.dump({'pages': pages}, f)
    with open(os.path.join(TEXT, f'{doc_id}.txt'), 'w') as f:
        for p in pages:
            f.write(f"\n=== Page {p['n']}{' (OCR)' if p['ocr'] else ''} ===\n{p['text']}\n")
    return doc_id, (len(pages), sum(p['ocr'] for p in pages))


if __name__ == '__main__':
    os.makedirs(TEXT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    files = sorted(f for f in glob.glob(os.path.join(PDF, '*')) if not f.endswith(('.part', '.hdr')))
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex:
        done = 0
        for doc_id, res in ex.map(extract, files, chunksize=1):
            done += 1
            if res:
                print(f'{done}/{len(files)} {doc_id} pages={res[0]} ocr={res[1]}', file=sys.stderr, flush=True)
