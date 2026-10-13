"""Turn catalog/tree.json into catalog/catalog.csv, parsing meeting body/date/type and marking what to download.

Selection rules (selected=1):
  * Board of Trustees agendas/packets, minutes and attachments (PDF variants) dated on or after MEETING_START,
    including Trustee work sessions and the Eldora acquisition town hall
  * every document in the non-meeting folders listed in TOPICAL_FOLDERS, any date
  * other boards' agendas, packets, minutes and attachments (PDF variants: Planning Commission, DDA, SAB, PROSAB,
    Board of Zoning Adjustment, Town Talks, ...) dated on or after OTHER_BODIES_START, to search them for the acquisition
"""
import csv
import json
import os
import re
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEETING_START = '2023-01-01'
OTHER_BODIES_START = '2024-01-01'
MEETING_ROOTS = ('Agendas/Packets', 'Minutes')
TOPICAL_FOLDERS = ('Resolutions', 'Ordinances', 'Board of Trustees', 'Finance',
                   'From the Desk of the Town Administrator', 'Documents and Information',
                   'Staff Reports', 'Tourism Management')

TITLE_RE = re.compile(r'^(?P<body>.+?) - (?P<date>\d{1,2} [A-Z][a-z]{2} \d{4})(?: - (?P<kind>Agenda|Minutes)'
                      r'(?: - (?P<fmt>[A-Za-z]+))?)?')


def parse(doc):
    m = TITLE_RE.match(doc['title'])
    body = date = kind = fmt = ''
    if m:
        body, kind, fmt = m.group('body').strip(), m.group('kind') or '', m.group('fmt') or ''
        date = datetime.strptime(m.group('date'), '%d %b %Y').strftime('%Y-%m-%d')
    elif (m := TITLE_RE.match(doc['path'].split('/')[-1])):
        # Agenda attachments live in a folder named after their meeting, e.g. "BOARD OF TRUSTEES - 07 Jan 2025"
        body, kind = m.group('body').strip(), 'Attachment'
        date = datetime.strptime(m.group('date'), '%d %b %Y').strftime('%Y-%m-%d')
    else:
        y = re.search(r'\b(20\d\d)\b', doc['path'] + ' ' + doc['title'])
        date = y.group(1) if y else ''
    return body, date, kind, fmt


def is_trustees(body, title):
    """Board of Trustees meetings, its work sessions, and the Eldora acquisition town hall."""
    b = body.upper()
    return ('TRUSTEES' in b or b.startswith('BOT') or b == 'WORK SESSION'
            or 'Eldora' in title)


def selected(doc, date, fmt, body):
    if doc['path'].startswith(MEETING_ROOTS):
        if fmt.lower() == 'html':
            return False
        return date >= MEETING_START if is_trustees(body, doc['title']) else date >= OTHER_BODIES_START
    return doc['path'].split('/')[0] in TOPICAL_FOLDERS


if __name__ == '__main__':
    docs = json.load(open(os.path.join(ROOT, 'catalog', 'tree.json')))
    with open(os.path.join(ROOT, 'catalog', 'catalog.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'title', 'path', 'body', 'date', 'kind', 'fmt', 'selected', 'url'])
        for d in docs:
            body, date, kind, fmt = parse(d)
            w.writerow([d['id'], d['title'], d['path'], body, date, kind, fmt,
                        int(selected(d, date, fmt, body)), f"https://nederlandco.civicweb.net/document/{d['id']}/"])
