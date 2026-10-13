"""Report what changed since the last published update, for the human review before publishing.

  python3 scripts/review_changes.py           # print the report
  python3 scripts/review_changes.py --accept  # record the current state as reviewed (run after publishing)

State is kept in analysis/last_update.json.
"""
import csv
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, 'analysis', 'last_update.json')
ELDORA = re.compile(r'eldora|mountain recreation|ski|resort|powdr|alterra|ikon|bond|purchase of property|'
                    r'recreational activities|enterprise', re.I)
# Statements written into the pages as of a date. Recheck each one at every update.
DATED = [
    ('scripts/eldora_spending_page.py', '<p class="lede">', 'Reread the opening paragraph (lede): does it still summarize the whole page, including this update? '
     'Edit it if the update changed a finding, the deal\'s status, or the totals it describes.'),
    ('scripts/eldora_spending_page.py', 'has expired', 'Is there a new or amended purchase agreement with POWDR (needs Board approval)?'),
    ('scripts/eldora_spending_page.py', 'Lapsed', 'Has the Board passed a new bond ordinance, or have any bonds been sold?'),
    ('scripts/eldora_spending_page.py', '$2.5 million', 'Has the Town updated its estimate of costs owed if the sale fails, or used CSAFE money?'),
    ('scripts/eldora_spending_page.py', 'Butler Snow', 'Do Butler Snow or Brownstein Hyatt Farber Schreck now appear on warrant lists?'),
    ('scripts/eldora_spending_page.py', 'warrant lists (Council Approval Reports) on the Town', 'Update the warrant-list date in the About these figures source line'),
    ('scripts/eldora_spending_page.py', "hasn't itemized", 'Has the Town published a breakdown of what is still owed, or an itemized list of Eldora costs?'),
    ('scripts/eldora_spending_page.py', '$124,000, $10,721, and $50,000', 'Has the purpose of the POWDR invoices been disclosed?'),
    ('scripts/eldora_spending_page.py', 'other receivables', 'Has the 2026 audit been posted (Town website, Finance > Audits)? Update the CSAFE section'),
    ('scripts/eldora_spending_page.py', '$583,730', 'New fund balance figures (2027 budget) or a current CSAFE balance? Update the CSAFE section'),
    ('scripts/eldora_spending_page.py', '$20 million', 'Any progress on the philanthropic fundraising or State of Colorado support?'),
    ('scripts/eldora_spending_page.py', 'sale-leaseback structure', 'Have the sale-leaseback terms, a new purchase agreement, or a lease been made public or approved?'),
    ('scripts/eldora_spending_page.py', 'GF_RESULTS', 'Has the 2026 audit been posted? Add its General Fund result to GF_RESULTS'),
    ('scripts/eldora_spending_page.py', 'HOUSEHOLDS = 685', 'Is there a newer household count?'),
    ('scripts/eldora_spending_page.py', 'April 2028', 'After the April 2028 election, update the election line in Get involved'),
    ('scripts/eldora_spending_page.py', 'BOT@nederlandco.org', 'Is the Board email still current? Have meeting days, times, or comment rules changed?'),
    ('scripts/eldora_spending_page.py', 'home rule', 'Has Nederland adopted a home-rule charter? If so, update the petition rules in Get involved'),
    ('scripts/eldora_spending_page.py', 'Surplus Fund', 'Has a new indenture or lease changed what money could reach the Town?'),
]


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {'through': '2026-10-06', 'due_from_rows': 65,
                                                                  'motions_through': '2026-09-15'}


def current():
    motions = list(csv.DictReader(open(os.path.join(ROOT, 'analysis', 'motions.csv'))))
    due = list(csv.DictReader(open(os.path.join(ROOT, 'analysis', 'eldora_due_from.csv'))))
    import sqlite3
    db = sqlite3.connect(os.path.join(ROOT, 'archive.db'))
    (through,) = db.execute("SELECT max(date) FROM docs WHERE body LIKE '%TRUSTEES%' AND kind IN ('Agenda','Minutes')").fetchone()
    return motions, due, through


def main():
    old = load_state()
    motions, due, through = current()
    motions_through = max(m['date'] for m in motions)
    if '--accept' in sys.argv:
        json.dump({'through': through, 'due_from_rows': len(due), 'motions_through': motions_through},
                  open(STATE, 'w'), indent=2)
        print(f'Recorded as reviewed: records through {through}, {len(due)} payments, motions through {motions_through}')
        return

    print(f'Board records now through {through} (last reviewed: {old["through"]})\n')

    new = [m for m in motions if m['date'] > old['motions_through']]
    print(f'== New motions in adopted minutes: {len(new)}')
    print('   Add Eldora actions to CURATED in scripts/eldora_votes.py. Executive sessions on the purchase are added')
    print('   automatically. Lines marked * mention Eldora-related terms.')
    for m in new:
        flag = '*' if ELDORA.search(m['motion'] + ' ' + m['item']) or m['eldora'] == '1' else ' '
        print(f' {flag} {m["date"]}  {m["item"][:60]:<60}  {m["motion"][:90]}')

    newpay = due[old['due_from_rows']:]
    print(f'\n== New "Due From" payments: {len(newpay)}')
    for r in newpay:
        print(f'   {r["warrant_meeting"]}  {r["vendor"]:<40} ${float(r["amount"]):>12,.2f}  balance {r["account_balance_after"]}')
    if due:
        print(f'   Running balance: {due[-1]["account_balance_after"]}')
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    from eldora_due_from import reconcile
    from eldora_spending_page import PAYEES
    unrated = sorted({r['vendor'] for r in due} - set(PAYEES))
    if unrated:
        print('   NEW PAYEES need an evidence rating in PAYEES (scripts/eldora_spending_page.py): ' + ', '.join(unrated))
    for meeting, gap in reconcile(due):
        print(f'   UNEXPLAINED: the {meeting} list balance rose ${gap:,.2f} more than its invoices. '
              f'Investigate, then add to KNOWN_GAPS (scripts/eldora_due_from.py) and the page.')

    print('\n== Dated statements to recheck before publishing')
    for path, phrase, question in DATED:
        found = phrase in open(os.path.join(ROOT, path)).read()
        print(f'   [{"on page" if found else "not found"}] {question}')

    print('\n== Site files changed')
    out = subprocess.run(['git', 'status', '--short', 'docs'], cwd=ROOT, capture_output=True, text=True).stdout
    print('   ' + (out.strip().replace('\n', '\n   ') or 'none'))
    if 'eldora-record.xlsx' in out:
        print('\n== Spreadsheet changed: upload docs/eldora-record.xlsx as a new version of the Drive copy')
        print('   (Drive: right-click the file > File information > Manage versions > Upload new version)')
    print('\n== Change log')
    print('   Add an entry to analysis/changes.json for this update, and one per correction:')
    print('   {"date": "YYYY-MM-DD", "type": "Update" | "Correction", "text": "..."}')
    print('   For a correction, also put [[corrected:YYYY-MM-DD]] next to the corrected text in the page script.')
    print('\nAfter review: commit and push docs/, then run  python3 scripts/review_changes.py --accept')


if __name__ == '__main__':
    main()
