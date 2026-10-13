"""Package a public data snapshot of the archive for a GitHub Release.

Makes tmp/snapshot/nederland-archive-YYYY-MM-DD.zip with:
  archive.db      the search database (SQLite, full-text index), Town documents only
  documents.csv   one row per document: id, title, date, body, kind, format, pages, source URL
  README.txt      what it is, what it covers, what it leaves out, and how to search it

Left out on purpose: records released to residents through public records requests (IDs 910001 and up). Their
text in the archive comes from the files as received, some with email addresses, phone numbers, or bank-account
details, and some not posted at all. The ones that were posted are on eldorarecord.org/records/ as redacted copies.

  python3 scripts/make_data_snapshot.py
"""
import csv, datetime as dt, os, shutil, sqlite3, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST_PRIVATE = 910000

today = dt.date.today().isoformat()
out_dir = os.path.join(ROOT, 'tmp', 'snapshot')
os.makedirs(out_dir, exist_ok=True)
db = os.path.join(out_dir, 'archive.db')
if os.path.exists(db):
    os.replace(db, db + '.old')
shutil.copyfile(os.path.join(ROOT, 'archive.db'), db)

c = sqlite3.connect(db)
c.execute('DELETE FROM pages WHERE CAST(doc_id AS INTEGER) >= ?', (FIRST_PRIVATE,))
c.execute('DELETE FROM docs WHERE id >= ?', (FIRST_PRIVATE,))
c.commit()
assert c.execute('SELECT COUNT(*) FROM docs WHERE id >= ?', (FIRST_PRIVATE,)).fetchone()[0] == 0
assert c.execute('SELECT COUNT(*) FROM pages WHERE CAST(doc_id AS INTEGER) >= ?', (FIRST_PRIVATE,)).fetchone()[0] == 0
c.execute("INSERT INTO pages(pages) VALUES('optimize')")
c.commit()
c.execute('VACUUM')
rows = c.execute('SELECT id, title, date, body, kind, fmt, pages, url FROM docs ORDER BY date, id').fetchall()
n_pages = c.execute('SELECT COUNT(*) FROM pages').fetchone()[0]
first = c.execute("SELECT MIN(date) FROM docs WHERE date != ''").fetchone()[0]
limit = (dt.date.today() + dt.timedelta(days=31)).isoformat()   # upcoming meeting packets, not folder-name years
last = c.execute("SELECT MAX(date) FROM docs WHERE date != '' AND date <= ?", (limit,)).fetchone()[0]
recent = c.execute("SELECT COUNT(*) FROM docs WHERE date >= '2023'").fetchone()[0]
c.close()

with open(os.path.join(out_dir, 'documents.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['id', 'title', 'date', 'body', 'kind', 'format', 'pages', 'source_url'])
    w.writerows(rows)

readme = f"""Nederland Town records archive: data snapshot of {today}

What this is
A searchable copy of {len(rows):,} public documents of the Town of Nederland, Colorado ({n_pages:,} pages of
text), filed {first[:4]} to {last}, {recent:,} of them from 2023 on: Board of Trustees and
advisory-board agendas, packets, minutes, resolutions, and ordinances from the Town's CivicWeb portal, and Eldora-related posts and audits from the Town website. It is the
archive behind eldorarecord.org. Every document is a public Town record; documents.csv gives each one's source.

What it leaves out
Records released to residents through public records requests (the site's IDs 910001 and up). Some were received
with email addresses, phone numbers, or bank-account details, and some were never posted. The ones that were
posted are at https://eldorarecord.org/records/ as redacted copies. The original PDFs are not included either;
each document's source_url links to the Town's copy.

Dates
Each document's date comes from CivicWeb (the meeting date for agendas and packets) or, for older files, from the
folder it is filed in, so some are only a year, and a few are wrong: files in an "Envision 2030" folder carry 2030.

Text quality
Text comes from each PDF's text layer, or from OCR (tesseract) where a page had none; the "ocr" column of the
pages table marks those pages. OCR text can contain errors, so check the original before quoting.

Files
  archive.db      SQLite database
                    docs   one row per document: id, title, path, body, date, kind, fmt, url, pages, ocr_pages
                    pages  full-text index (FTS5): doc_id, page, ocr, text
  documents.csv   the docs table as a spreadsheet

Searching it
  sqlite3 archive.db "SELECT d.date, d.title, p.page FROM pages p JOIN docs d ON d.id = p.doc_id
                      WHERE pages MATCH 'eldora AND appropriation' ORDER BY d.date LIMIT 20;"
DB Browser for SQLite (sqlitebrowser.org) and Datasette (datasette.io) also open it.

Rebuilding it yourself
The code is at https://github.com/dallasmasters/nederland-eldora-record. Run ./update.sh to download the
documents from CivicWeb and rebuild the archive; it needs Python 3 and tesseract, and takes hours the first time.

This is not a Town product. Corrections: see eldorarecord.org.
"""
open(os.path.join(out_dir, 'README.txt'), 'w').write(readme)

zpath = os.path.join(out_dir, f'nederland-archive-{today}.zip')
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in ('README.txt', 'documents.csv', 'archive.db'):
        z.write(os.path.join(out_dir, name), name)
if os.path.exists(db + '.old'):
    os.replace(db + '.old', os.path.join(ROOT, 'tmp', 'claude', 'archive-snapshot-previous.db'))
print(f'{zpath}: {os.path.getsize(zpath) / 1e6:.0f} MB; {len(rows):,} documents, {n_pages:,} pages, {first} to {last}')
