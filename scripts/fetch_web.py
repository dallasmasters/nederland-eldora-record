"""Add the Town of Nederland's own website posts about the Eldora acquisition, and Town documents posted only on its
website (the 2025 audit), to the archive.

The Town's FAQs and announcements are not in CivicWeb. Current posts come from www.nederlandco.gov; earlier FAQ
versions were posted on the Town's previous site (townofnederland.colorado.gov), which no longer serves them, so
those come from the Internet Archive's Wayback Machine.

Raw pages are kept in web/raw/ (downloaded once, then reused). Each post's text is written to text/<id>.json in the
same format as CivicWeb documents, and catalog/web.csv lists them for build_index.py. IDs start at 900001 so they
never collide with CivicWeb document IDs.

FAQ 5.0 is referenced by the Town but no copy was found online or in the Internet Archive (October 2026).
"""
import csv
import gzip
import html
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import extract as pdf_extract  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'web', 'raw')
OLD = 'https://townofnederland.colorado.gov/press-release/'
NEW = 'https://www.nederlandco.gov/m/newsflash/home/detail/'
# id, key, title, date posted, live URL, Wayback timestamp (None = fetch live)
SOURCES = [
    (900001, 'faq-1-engage', 'Eldora Mountain Acquisition FAQ on Engage Nederland', '2024-11-14',
     OLD + 'eldora-mountain-acquisition-faq-on-engage-nederland', '20250815043449'),
    (900002, 'faq-2-round2', 'Eldora Mountain Acquisition FAQ Round 2', '2025-01-07',
     OLD + 'eldora-mountain-acquisition-faq-round-2', '20251008154122'),
    (900003, 'faq-3', 'Eldora Mountain Acquisition FAQs 3.0', '2025-07-08',
     OLD + 'eldora-mountain-acquisition-faqs-30', '20250709224556'),
    (900004, 'faq-4', 'Eldora Mountain Acquisition FAQs 4.0', '2025-08-28',
     OLD + 'eldora-mountain-acquisition-faqs-40', '20251112014324'),
    (900006, 'faq-6', 'Eldora FAQ 6.0', '2026-04-02', NEW + '22', None),   # online by Apr 2, 2026 (Internet Archive); reposted Oct 5, 2026
    (900007, 'faq-7', 'Eldora FAQ 7.0', '2026-07-23', NEW + '17', None),
    (900020, 'auditor-rfp', 'Request for Proposals for Town Auditor Services', '2026-09-17', NEW + '20', None),
    (900025, 'audit-2025', '2025 Nederland Financials Audit (John Cutler & Associates)', '2026-06-30',
     'https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit', None),   # scanned PDF, OCR'd
    # Earlier audits not in CivicWeb (Town website, Finance > Audits - Previous Years); dated by fiscal year like the
    # CivicWeb audits, since the posting date isn't shown
    (900026, 'audit-2023', '2023 Nederland Audit', '2023', 'https://www.nederlandco.gov/DocumentCenter/View/593/2023-Audit', None),
    (900027, 'audit-2022', '2022 Nederland Audit', '2022', 'https://www.nederlandco.gov/DocumentCenter/View/591/2022-Audit', None),
    (900021, 'update-2026-09-30', 'Update on Eldora Transaction from Mayor Sterling & the Board of Trustees',
     '2026-09-30', NEW + '21', None),
]
BOILERPLATE = re.compile(r'^(Submitted by \[user:.*|Hide Featured Image|true|Skip to main content)$')


def fetch(src):
    data = subprocess.run(['curl', '-sL', '--compressed', '-m', '120', '-A', 'Mozilla/5.0', src],
                          capture_output=True).stdout
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    if b'Internet Archive: Temporarily Offline' in data or b'Custom404' in data or len(data) < 5000:
        return None
    return data


def download(key, url, ts):
    """Live posts are re-downloaded each run (they get edited); archived copies are downloaded once."""
    path = os.path.join(RAW, f'{key}.html')
    if ts is None or not os.path.exists(path):
        src = f'https://web.archive.org/web/{ts}id_/{url}' if ts else url
        data = fetch(src)
        if data:
            open(path, 'wb').write(data)
        elif os.path.exists(path):
            print(f'  {key}: could not download {src}; using the saved copy')
        else:
            raise RuntimeError(f'{key}: download failed from {src}; try again later')
    return open(path, encoding='utf-8', errors='replace').read()


def new_posts():
    """News Flash posts on the Town site that mention Eldora but are not in SOURCES yet."""
    page = fetch('https://www.nederlandco.gov/m/newsflash/home')
    if not page:
        return ['(could not read the Town News Flash list)']
    known = {url for *_, url, _ in SOURCES}
    out = []
    for n in sorted(set(re.findall(r'/m/newsflash/[Hh]ome/[Dd]etail/(\d+)', page.decode('utf-8', 'replace'))), key=int):
        url = NEW + n
        if url in known:
            continue
        post = fetch(url)
        body = '\n'.join(extract(post.decode('utf-8', 'replace'), True)) if post else ''
        if re.search(r'eldora|mountain recreation', body, re.I):
            title = re.search(rb'<title>(.*?)</title>', post, re.S)
            out.append(f'{url}  {html.unescape(title.group(1).decode("utf-8", "replace")).split(" \u2022")[0].strip() if title else ""}')
    return out


def to_lines(fragment):
    t = re.sub(r'(?is)<(script|style).*?</\1>', '', fragment)
    t = re.sub(r'(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', '', t))
    return [l.strip() for l in t.splitlines() if l.strip() and not BOILERPLATE.match(l.strip())]


def extract(page, live):
    if live:   # www.nederlandco.gov News Flash: from "Posted on" to "Related News"
        lines = to_lines(page)
        start = next(i for i, l in enumerate(lines) if l.startswith('Posted on'))
        end = next((i for i, l in enumerate(lines) if l == 'Related News'), len(lines))
        return lines[start:end]
    main = re.search(r'<main.*?</main>', page, re.S).group(0)  # old Drupal site
    lines = to_lines(main)
    end = next((i for i, l in enumerate(lines) if l == 'Recent'), len(lines))  # drop the "Recent" sidebar
    return lines[:end]


def main():
    os.makedirs(RAW, exist_ok=True)
    rows = []
    for doc_id, key, title, posted, url, ts in SOURCES:
        source = f'https://web.archive.org/web/{ts}/{url}' if ts else url
        if key.startswith('audit-'):   # PDF documents: keep the file, extract text (OCR if scanned) like CivicWeb PDFs
            raw = os.path.join(RAW, f'{key}.pdf')
            if not os.path.exists(raw):
                data = fetch(url)
                if not data or not data.startswith(b'%PDF'):
                    raise RuntimeError(f'{key}: could not download {url}')
                open(raw, 'wb').write(data)
            dest = os.path.join(ROOT, 'pdf', f'{doc_id}.pdf')
            if not os.path.exists(dest):
                shutil.copy(raw, dest)
            pdf_extract(dest)
            n = len(json.load(open(os.path.join(ROOT, 'text', f'{doc_id}.json')))['pages'])
            rows.append({'id': doc_id, 'title': title, 'path': 'Town website', 'body': 'TOWN WEBSITE', 'date': posted,
                         'kind': 'Audit', 'fmt': 'pdf', 'selected': 1, 'url': source})
            print(f'{doc_id} {posted} {title}: {n} pages')
            continue
        lines = extract(download(key, url, ts), ts is None)
        text = '\n'.join(lines)
        json.dump({'pages': [{'n': 1, 'text': text, 'ocr': False}]},
                  open(os.path.join(ROOT, 'text', f'{doc_id}.json'), 'w'))
        open(os.path.join(ROOT, 'text', f'{doc_id}.txt'), 'w').write(f'=== Page 1 ===\n{text}\n')
        rows.append({'id': doc_id, 'title': title, 'path': 'Town website', 'body': 'TOWN WEBSITE', 'date': posted,
                     'kind': 'Web post', 'fmt': 'html', 'selected': 1, 'url': source})
        print(f'{doc_id} {posted} {title}: {len(text):,} characters' + (' (Internet Archive copy)' if ts else ''))
    with open(os.path.join(ROOT, 'catalog', 'web.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for line in new_posts():
        print(f'REVIEW: new Eldora post on the Town website, add it to SOURCES in scripts/fetch_web.py: {line}')


if __name__ == '__main__':
    main()
