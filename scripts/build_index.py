"""Build archive.db: a SQLite database with document metadata and a full-text index of every page.

Sources: catalog/catalog.csv (CivicWeb), catalog/web.csv (Town website posts, see fetch_web.py) and
catalog/records.csv (records from public records responses, see add_records.py).

Tables:
  docs(id, title, path, body, date, kind, fmt, url, pages, ocr_pages)
  pages(doc_id, page, ocr, text)              -- FTS5, porter stemming
"""
import csv
import json
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    db_path = os.path.join(ROOT, 'archive.db')
    if os.path.exists(db_path):
        os.remove(db_path)
    db = sqlite3.connect(db_path)
    db.executescript('''
        CREATE TABLE docs(id INTEGER PRIMARY KEY, title TEXT, path TEXT, body TEXT, date TEXT,
                          kind TEXT, fmt TEXT, url TEXT, pages INTEGER, ocr_pages INTEGER);
        CREATE VIRTUAL TABLE pages USING fts5(doc_id UNINDEXED, page UNINDEXED, ocr UNINDEXED, text,
                                              tokenize='porter unicode61');
    ''')
    catalogs = [os.path.join(ROOT, 'catalog', 'catalog.csv'),
                os.path.join(ROOT, 'catalog', 'web.csv'),       # CivicWeb documents, Town website posts,
                os.path.join(ROOT, 'catalog', 'records.csv')]   # then records from public records responses
    for cat in catalogs:
        if not os.path.exists(cat):
            continue
        for r in csv.DictReader(open(cat)):
            tj = os.path.join(ROOT, 'text', f"{r['id']}.json")
            if not os.path.exists(tj):
                continue
            pages = json.load(open(tj))['pages']
            db.execute('INSERT OR REPLACE INTO docs VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (int(r['id']), r['title'], r['path'], r['body'], r['date'], r['kind'], r['fmt'],
                        r['url'], len(pages), sum(p['ocr'] for p in pages)))
            db.executemany('INSERT INTO pages VALUES (?,?,?,?)',
                           [(int(r['id']), p['n'], int(p['ocr']), p['text']) for p in pages])
    db.commit()
    n_docs, n_pages = db.execute('SELECT count(*), sum(pages) FROM docs').fetchone()
    print(f'{n_docs} documents, {n_pages} pages indexed -> {db_path}')
