"""Build the Eldora acquisition vote table from analysis/motions.csv.

Rows are chosen by hand (CURATED below) after reading each candidate's agenda attachments: keyword and
attachment matching alone pulls in items that only mention Eldora in passing. Every executive session whose
motion cites the purchase of property for recreational activities is included automatically.

Writes analysis/eldora_votes.csv and analysis/eldora_votes.md.
"""
import csv
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (date, regex on motion text, category, description written from the item's AIM / resolution)
CURATED = [
    ('2025-01-07', r'Consent Agenda', 'Consent',
     'Ratified retention of Northland Securities as underwriter for possible revenue-bond financing of an Eldora '
     'purchase (Res. 2025-02); Letter of Interest to Great Outdoors Colorado for a grant to support the acquisition'),
    ('2025-01-07', r'Resolution 2025-03', 'Action',
     'Res. 2025-03: delegated authority to the Town Administrator to engage special legal counsel to evaluate '
     'purchasing Eldora Mountain Resort'),
    ('2025-01-21', r'Ordinance 873', 'Action',
     'Ord. 873 (emergency): established the Mountain Recreation Enterprise Fund "to support the Town\'s strategic '
     'efforts regarding the potential acquisition and operation of the Eldora Ski Area"'),
    ('2025-04-15', r'Consent Agenda', 'Consent',
     'Res. 2025-08: ratified a non-binding Letter of Intent with J.P. Morgan Securities as potential underwriter '
     'of revenue bonds for an Eldora acquisition'),
    ('2025-05-20', r'Consent Agenda', 'Consent',
     'Res. 2025-11: delegated authority to the Town Administrator to retain additional underwriters and financial '
     'advisors for the possible purchase'),
    ('2025-07-15', r'Consent Agenda', 'Consent',
     'Res. 2025-15: due-diligence agreement with SE Group (financial, operational, and infrastructure review of Eldora). '
     'Also approved, as a separate consent item: engagement of Dickinson Wright PLLC for water-rights due diligence on the acquisition'),
    ('2025-08-05', r'Consent Agenda', 'Consent',
     'Res. 2025-16: authorized the Town Manager to engage legal counsel for the acquisition, naming Kline Alvarado Veio as bond counsel (staff memo notes the '
     'Town had entered a non-binding term sheet)'),
    ('2025-08-05', r'Resolution 2025-17', 'Action',
     'Res. 2025-17: declared the Town\'s official intent to reimburse Eldora project expenditures from a future '
     'bond issue'),
    ('2025-09-02', r'Consent Agenda', 'Consent',
     'Res. 2025-19: ratified retention of third-party consultants for due diligence on the Eldora acquisition'),
    ('2025-10-07', r'Consent Agenda', 'Consent',
     'Res. 2025-22: ratified retention of contractors and consultants (HR, finance, and accounting and forecasting) '
     'related to the acquisition'),
    ('2026-01-06', r'Ordinance 882', 'Action',
     'Ord. 882: authorized execution of the Asset Purchase Agreement for the acquisition of Eldora Mountain Resort, '
     'acting through the Mountain Recreation Enterprise'),
    ('2026-01-20', r'Ordinance 885', 'Action',
     'Ord. 885: authorized issuance and sale of Mountain Recreation Enterprise Revenue Bonds, Series 2026, and the '
     'related indenture'),
    ('2026-03-17', r'Consent Agenda', 'Consent',
     'Res. 2026-07: authorized the Town Manager to execute license applications, renewals, and transfers needed to '
     'operate Eldora upon acquisition'),
    ('2026-03-31', r'Consent Agenda', 'Consent',
     'Res. 2026-08 and 2026-09: authorized the Town Manager to execute a U.S. Forest Service Ski Area Term Special Use '
     'Permit, and a Cross Resort Pass Product (IKON) Agreement and a Confidentiality and Disclosure Agreement with '
     'Alterra Mountain Company, at or in connection with closing'),
    ('2026-04-21', r'Consent Agenda', 'Consent',
     'Res. 2026-12: professional services agreement with Plante Moran for operational transition planning and '
     'project management'),
    ('2026-04-21', r'Resolution 2026-13', 'Action',
     'Res. 2026-13: authorized emergency expenditures for the Mountain Recreation Enterprise for the acquisition '
     'and initial operation of Eldora Mountain Resort (C.R.S. § 29-1-111)'),
    ('2026-07-07', r'Stifel', 'Action',
     'Approved a Municipal Advisory Services Agreement with Stifel, Nicolaus & Company through June 30, 2027, '
     'covering Town financing matters including the Eldora acquisition'),
    ('2025-03-18', r'Water Court', 'Related',
     'Executive session on water-court matters, including Eldora\'s Application for Conditional Storage Rights '
     '(Case No. 23CW3176) and Nederland\'s Statement of Opposition'),
]
ES_PROPERTY = re.compile(r'purchase\s*of\s*property|recreational\s*activities', re.I)


def agenda_es_dates():
    """Dates of BOT agendas (Sep 2024 on) that notice an executive session on the property purchase.

    Returns ({date: url}, {date: url} for meetings whose agenda is marked canceled)."""
    dates, canceled = {}, {}
    for c in csv.DictReader(open(os.path.join(ROOT, 'catalog', 'catalog.csv'))):
        if c['kind'] == 'Agenda' and 'TRUSTEES' in c['body'] and c['date'] >= '2024-09-01' and c['selected'] == '1':
            t = subprocess.run(['pdftotext', '-l', '3', os.path.join(ROOT, 'pdf', f"{c['id']}.pdf"), '-'],
                               capture_output=True, text=True, errors='replace').stdout
            if re.search(r'executive\s*session', t, re.I) and ES_PROPERTY.search(t):
                (canceled if re.search(r'\bCANCEL', t) else dates)[c['date']] = c['url']
    return dates, canceled


def es_description(motion):
    subs = ', '.join(dict.fromkeys(re.findall(r'\(4\)\s*\(([a-g])\)', motion)))
    extra = []
    if re.search(r'confidential', motion, re.I):
        extra.append('confidential commercial information')
    if re.search(r'subject to negotiation', motion, re.I):
        extra.append('issues subject to negotiation')
    if re.search(r'personnel|Town (Administrator|Manager) who has consented|evaluation of the Town', motion, re.I):
        extra.append('also: Town Administrator/Manager personnel matter')
    d = 'Executive session: purchase of property and operations for recreational activities'
    return d + (f' (C.R.S. 24-6-402(4) {subs})' if subs else '') + (f'; {"; ".join(extra)}' if extra else '')


def vote_summary(r):
    present = [n for n in r['present'].split('; ') if n]
    absent = f"; absent: {r['absent'].replace('; ', ', ')}" if r['absent'] else ''
    note = f" [roll call: {r['roll_notes']}]" if r['roll_notes'] else ''
    if r['unanimous'] == '1':
        return f"Unanimous of those present ({len(present)}: {', '.join(present)}){absent}{note}"
    parts = []
    for label, field in (('Yes', 'yes'), ('No', 'no'), ('Recused/absent', 'other')):
        if r[field]:
            parts.append(f"{label}: {r[field].replace('; ', ', ')}")
    return ('; '.join(parts) or r['outcome']) + absent + note


if __name__ == '__main__':
    motions = list(csv.DictReader(open(os.path.join(ROOT, 'analysis', 'motions.csv'))))
    out = []
    for r in motions:
        if r['date'] < '2024-09-01':
            continue
        cat = desc = None
        if 'executive session' in r['motion'].lower() and ES_PROPERTY.search(r['motion']):
            cat, desc = 'Executive session', es_description(r['motion'])
        for date, pat, c, d in CURATED:
            if r['date'] == date and re.search(pat, r['motion'], re.I):
                cat, desc = c, d
        if cat:
            out.append({'date': r['date'], 'category': cat, 'description': desc, 'mover': r['mover'],
                        'seconder': r['seconder'], 'outcome': r['outcome'], 'vote': vote_summary(r),
                        'present': r['present'], 'absent': r['absent'], 'roll_notes': r['roll_notes'], 'minutes_page': r['page'], 'source': r['url'],
                        'motion_text': r['motion']})
    missing = [(d, p) for d, p, _, _ in CURATED
               if not any(o['date'] == d and re.search(p, o['motion_text'], re.I) for o in out)]
    assert not missing, f'curated rows not found: {missing}'

    with open(os.path.join(ROOT, 'analysis', 'eldora_votes.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    with open(os.path.join(ROOT, 'analysis', 'eldora_votes.md'), 'w') as f:
        f.write('# Board of Trustees votes on the Eldora Mountain Resort acquisition\n\n'
                'Source: adopted (signed) Board of Trustees minutes on the Town of Nederland CivicWeb portal, '
                're-read with OCR and checked against the page images where names were unclear. Minutes never '
                'posted separately (Oct. 21 and Oct. 30, 2025; the Sept. 15, 2026, special meeting) come from the '
                'drafts in the next meeting\'s packet. '
                'Generated by `scripts/eldora_votes.py`.\n\n')
        for title, cats in (('Actions and consent-agenda approvals', ('Action', 'Consent')),
                            ('Executive sessions on the purchase', ('Executive session',)),
                            ('Related', ('Related',))):
            sel = [o for o in out if o['category'] in cats]
            f.write(f'## {title} ({len(sel)})\n\n| Date | Type | What was approved | Moved / seconded | Vote | Source |\n'
                    '|---|---|---|---|---|---|\n')
            for o in sel:
                f.write(f"| {o['date']} | {o['category']} | {o['description']} | {o['mover']} / {o['seconder']} | "
                        f"{o['vote']} | [minutes p.{o['minutes_page']}]({o['source']}) |\n")
            f.write('\n')
        es_dates = {o['date'] for o in out if o['category'] == 'Executive session'}
        noticed, canceled = agenda_es_dates()
        gaps = {d: u for d, u in noticed.items() if d not in es_dates}
        f.write(f'## Executive sessions noticed on an agenda with no minutes found ({len(gaps)})\n\n'
                'No minutes for these special meetings were found in the archive, either posted on CivicWeb or as a '
                'draft in a later packet, so whether they were held, and who moved, seconded, or attended, is not '
                'in the records searched.\n\n')
        for d, u in sorted(gaps.items()):
            f.write(f'- {d}: [agenda]({u})\n')
        f.write(f'\n## Executive sessions whose agenda is marked canceled ({len(canceled)})\n\n')
        for d, u in sorted(canceled.items()):
            f.write(f'- {d}: canceled ([agenda]({u}))\n')
        f.write('\nThe 2024-09-03 executive session appears only in the minutes: its agenda said '
                '"EXECUTIVE SESSION (approximately 60 minutes)" without a topic.\n')
    print(f"{len(out)} rows; {len(gaps)} agenda-only executive sessions: " + ', '.join(sorted(gaps)))
