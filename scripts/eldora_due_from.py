"""Extract every payment to General Fund account 10-00-1150 "Due From" (Eldora acquisition costs), and from Nov. 9,
2026, to account 10-10-7000 "Eldora Expense," from the Board warrant lists, and check the "Due From" running balance
against the listed invoices.

Writes analysis/eldora_due_from.csv and prints any balance jump the listed invoices don't explain.
"""
import csv
import json
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMT = r'\(?\$?-?[\d,]+\.\d\d\)?'
LINE = re.compile(rf'^\s*(\S+)\s+(\d\d/\d\d/\d\d)\s+(.*?)\s+(\d\d/\d\d/\d\d)\s+({AMT})\s+({AMT})\s+'
                  rf'(\d\d-\d\d-\d{{4}})\s+(.*?)\s+({AMT})\s+({AMT})\s*$')
VENDOR = re.compile(r'^\s*(?:\d{1,5}\s+)?([A-Z][^$]*?,.*)$')
ACCOUNT = '10-00-1150'
# From the Nov. 9, 2026, warrant list on, Eldora invoices are charged to a new General Fund expense account. Its
# running balance on the lists is a year-to-date figure that doesn't match the "Due From" payments (see the record's
# #eldora-expense), so its payments are counted by amount and left out of the balance check.
ACCOUNTS = (ACCOUNT, '10-10-7000')
# Balance jumps between warrant lists that are already accounted for: amounts the Town's ledger (public records
# response, Sept. 25, 2026) shows were added between lists (OFF_LIST in eldora_spending_page.py). A new unexplained
# jump is reported for review.
KNOWN_GAPS = {'2025-11-05': 55890.50, '2026-03-03': 50000.00, '2026-06-16': 852.50}


def amount(s):
    return float(s.replace('$', '').replace(',', '').replace('(', '-').replace(')', ''))


def extract():
    db = sqlite3.connect(os.path.join(ROOT, 'archive.db'))
    rows = []
    for doc, date, _ in db.execute("SELECT id, date, title FROM docs WHERE title LIKE '%Warrant%' "
                                   "AND date >= '2025-06-01' ORDER BY date, id"):
        path = os.path.join(ROOT, 'text', f'{doc}.json')
        if not os.path.exists(path):
            continue
        vendor = None
        for page in json.load(open(path))['pages']:
            for line in page['text'].splitlines():
                m = LINE.match(line)
                if m:
                    if m.group(7) in ACCOUNTS:
                        rows.append({'warrant_meeting': date, 'vendor': vendor, 'invoice': m.group(1),
                                     'invoice_date': m.group(2), 'amount': f'{amount(m.group(6)):.2f}',
                                     'account': m.group(7), 'account_balance_after': m.group(10),
                                     'warrant_page': page['n'],
                                     'source': f'https://nederlandco.civicweb.net/document/{doc}/'})
                    continue
                v = VENDOR.match(line)
                if v and not re.search(r'Council Approval|Town of Nederland|InvoiceNumber|Total ', line) and \
                        re.search(r'\b(LLC|Inc|PLLC|LLP|P\.C\.|Corp|Group|dba|Company|,\s*[A-Z]{2},)', line):
                    vendor = ' '.join(v.group(1).split()).split(',')[0]
    return rows


def reconcile(rows):
    """Return (meeting, unexplained amount) for every balance jump not covered by listed invoices or KNOWN_GAPS."""
    rows = [r for r in rows if r['account'] == ACCOUNT]
    problems, prev, i = [], 0.0, 0
    while i < len(rows):
        bal = -amount(rows[i]['account_balance_after'])
        j, listed = i, 0.0
        while j < len(rows) and rows[j]['account_balance_after'] == rows[i]['account_balance_after']:
            listed += float(rows[j]['amount'])
            j += 1
        gap = round(bal - prev - listed, 2)
        if abs(gap) > 0.01 and abs(gap - KNOWN_GAPS.get(rows[i]['warrant_meeting'], 0)) > 0.01:
            problems.append((rows[i]['warrant_meeting'], gap))
        prev, i = bal, j
    return problems


if __name__ == '__main__':
    rows = extract()
    with open(os.path.join(ROOT, 'analysis', 'eldora_due_from.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    due = [r for r in rows if r['account'] == ACCOUNT]
    print(f'{len(rows)} payments; "Due From" balance {due[-1]["account_balance_after"]}; '
          f'{len(rows) - len(due)} charged to 10-10-7000')
    for meeting, gap in reconcile(rows):
        print(f'REVIEW: balance on the {meeting} warrant list rose ${gap:,.2f} more than its listed invoices')
