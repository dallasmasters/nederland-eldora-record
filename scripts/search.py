"""Search the archive.

  python3 scripts/search.py 'eldora AND (appraisal OR valuation)'
  python3 scripts/search.py '"letter of intent"' --since 2025-01-01 --body "BOARD OF TRUSTEES" -n 50

Query syntax is SQLite FTS5 (AND, OR, NOT, "phrases", prefix*, NEAR(a b, 10)).
Results are ordered by meeting date, with a snippet and the page number to cite.
"""
import argparse
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('query')
    ap.add_argument('--since', default='')
    ap.add_argument('--until', default='9999')
    ap.add_argument('--body', default='', help='substring of the meeting body, e.g. "TRUSTEES"')
    ap.add_argument('-n', type=int, default=30)
    a = ap.parse_args()
    db = sqlite3.connect(os.path.join(ROOT, 'archive.db'))
    rows = db.execute('''
        SELECT d.date, d.title, p.page, p.ocr, d.url, p.snip
        FROM (SELECT doc_id, page, ocr, snippet(pages, 3, '[', ']', ' … ', 24) AS snip
              FROM pages WHERE pages MATCH ?) p
        JOIN docs d ON d.id = p.doc_id
        WHERE d.date >= ? AND d.date <= ? AND d.body LIKE ?
        ORDER BY d.date, d.id, p.page LIMIT ?''',
                      (a.query, a.since, a.until, f'%{a.body}%', a.n)).fetchall()
    for date, title, page, ocr, url, snip in rows:
        print(f"{date}  {title}  p.{page}{' (OCR)' if ocr else ''}\n    {url}\n    {' '.join(snip.split())}\n")
    print(f'{len(rows)} hits shown')
