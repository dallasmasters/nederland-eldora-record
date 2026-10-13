"""Render analysis/eldora_due_from.csv as a shareable HTML page on Eldora acquisition spending.

Writes analysis/eldora_spending.html. The commitments and funding sections are written from the cited documents.
"""
import csv
import html
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from page_method import method_html, archive_from, archive_through
from eldora_page import fragment
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = 'https://nederlandco.civicweb.net/document/{}/'
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()

# Evidence that each payee's "Due From" charges are Eldora costs (checked against the whole archive, Oct 2026):
#   named   - a Board document ties this payee to the Eldora acquisition
#   coding  - a regular Town vendor whose other work is billed to normal budget lines; the Eldora link is the account
#   none    - appears nowhere in the archive except the warrant lists
PAYEES = {
    'P&M Holding Group': ('Plante Moran', 'named', 'Eldora transition planning (Res. 2026-12). Since July 2026 it also signs the Town\'s Treasurer '
                          'reports; that work is billed to Professional Services. Two invoices (March and April 2026) were '
                          'split, with $3,429 to Professional Services. $853 of a May 2026 Professional Services invoice '
                          'was later moved into this account (Town ledger)'),
    'POWDR Corp': ('POWDR Corp', 'named', 'The seller (purchase agreement). The $124,000 (Jan 27) and $10,721 (Apr 21) '
                   'invoices are on warrant lists; the Town\'s ledger also records a $50,000 invoice dated Jan 6, 2026, '
                   'that is on no warrant list. None has a stated purpose in the records searched'),
    'Sno.engineering': ('SE Group', 'named', 'Eldora due diligence (Res. 2025-15). Its earlier Comprehensive Plan '
                        'work used other budget lines'),
    'Kline Veio': ('Kline Alvarado Veio', 'named', 'Eldora bond counsel (Res. 2025-16)'),
    'Dickinson Wright PLLC': ('Dickinson Wright', 'named', 'Hired Jul 15, 2025 for Eldora water-rights due diligence. '
                              'Its regular Town water-law work is billed to the Water Fund. Includes an Aug 2025 invoice '
                              '($9,680) first paid from the Legal budget and moved into this account (Town ledger)'),
    'BBA Water Consultants': ('BBA Water Consultants', 'named', "Named in the purchase agreement as Eldora's own "
                              'water consultant, which the seller must keep using until closing'),
    'Widner Juran LLP': ('Widner Juran LLP', 'coding', 'The Town Attorney. Regular legal work is billed separately '
                         'each month. Includes seven January to July 2025 invoices ($46,211) first paid from the Legal '
                         'budget and moved into this account on Sept 30, 2025 (Town ledger)'),
    'JVA': ('JVA', 'coding', "The Town's on-call engineers. Charges August to November 2025, separate from their other "
            'project lines'),
    'DiNatale Water Consultants': ('DiNatale Water Consultants', 'coding', "The Town's water engineers. Charges in "
                                   'August and September 2025 only, during the Eldora water-rights review'),
    'Vadim Municipal Software Inc': ('Vadim Municipal Software', 'coding', "The Town's accounting software. Licenses "
                                     'and fees are billed elsewhere'),
    'Hogan Lovells US LLP': ('Hogan Lovells', 'none', 'Washington, DC law firm. Role not stated in the records searched'),
    'Farnsworth Group': ('Farnsworth Group', 'none', 'Engineering firm. Invoices Oct 2025 to Jan 2026'),
    'Partner Assessment Corporation': ('Partner Engineering and Science', 'none', 'Invoices dated September and December 2025. '
                                       'The Nov 2025 Eldora memo reports a property condition assessment and a Phase I '
                                       'environmental site assessment, but doesn’t name who did them'),
    'Torrent Engineering & Equipment Company LLC': ('Torrent Engineering & Equipment', 'none', 'Engineering firm. One invoice, Dec 2025'),
    'Susan N. Fattor': ('Bolder HR Solutions', 'none', 'HR firm. Res. 2025-22 covers HR support for the acquisition'),
    'Datasite LLC': ('Datasite', 'none', '$200 a month since Feb 2026'),
    'Semple': ('Semple, Farrington, Everall & Case', 'none', 'Law firm. The Res. 2025-16 memo expects "specialized '
               'employment matters"'),
    'Professional Management Systems': ('Professional Management Solutions', 'none', 'Purpose unknown'),
}
# Postings to the account that appear on no warrant list as "Due From" charges. The Town's ledger for the account
# (released in its Sept. 25, 2026, response to a public records request; archive ID 910002) names each one: legal and
# professional-services invoices first paid on earlier warrant lists from other budget lines and later moved into the
# account, and a POWDR invoice that is on no warrant list. warrant_meeting is the list on which the balance first
# includes the amount; `first` is the warrant list (date, CivicWeb document, page) where a moved invoice was first paid.
CORA_LEDGER = 'records/2026-09-25-eldora-reimbursable-expenses.xls'   # posted with the site (relative to base_url)
CORA_REPLY = 'records/2026-09-25-town-cora-response.txt'
_MOVED = 'Moved into this account from {line} by a Town ledger entry dated {when}'
OFF_LIST = [
    {'vendor': 'Widner Juran LLP', 'amt': a, 'warrant_meeting': '2025-11-05', 'invoice': inv, 'invoice_date': idate, 'posted': '2025-09-30',
     'first': first, 'label': _MOVED.format(when='Sept 30, 2025', line='Legal (10-12-5100)')}
    for inv, idate, a, first in [
        ('46.0292', '01/31/25', 6440.00, ('2025-02-18', 119043, 6)),
        ('46.0294', '02/28/25', 1505.00, ('2025-04-15', 120586, 1)),
        ('46.0297', '03/31/25', 1295.00, ('2025-05-06', 120975, 2)),
        ('46.0301', '04/30/25', 2747.50, ('2025-05-20', 121504, 2)),
        ('46.0303', '05/31/25', 9954.00, ('2025-06-17', 122041, 2)),
        ('46.0304', '06/30/25', 5162.50, ('2025-08-05', 123021, 2)),
        ('46.0307', '07/31/25', 19106.50, ('2025-09-02', 123789, 2))]
] + [
    {'vendor': 'Dickinson Wright PLLC', 'amt': 9680.00, 'warrant_meeting': '2025-11-05', 'invoice': '2070334', 'posted': '2025-09-30',
     'invoice_date': '08/20/25', 'first': ('2025-10-07', 124842, 3),
     'label': _MOVED.format(when='Sept 30, 2025', line='Legal (10-12-5100)')},
    {'vendor': 'POWDR Corp', 'amt': 50000.00, 'warrant_meeting': '2026-03-03', 'invoice': '2026-01-06',
     'invoice_date': '01/06/26', 'first': None, 'posted': '2026-01-06',
     'label': 'In the Town ledger (invoice dated Jan 6, 2026); on no warrant list. Purpose not stated'},
    {'vendor': 'P&M Holding Group', 'amt': 852.50, 'warrant_meeting': '2026-06-16', 'invoice': '10693173', 'posted': '2026-05-11',
     'invoice_date': '05/11/26', 'first': ('2026-06-02', 129902, 2),
     'label': 'Part of a $1,550 invoice. ' + _MOVED.format(when='May 11, 2026', line='Professional Services (10-12-5133)')},
]
# Who was paid rows that other sections link to
PAYEE_ANCHORS = {'Hogan Lovells US LLP': 'payee-hogan', 'POWDR Corp': 'payee-powdr', 'unk': 'off-list-postings'}
EVIDENCE = {'named': 'Named in Board documents', 'coding': 'Account coding only', 'none': 'No other record'}


def e(s):
    return html.escape(str(s or ''))


def money(v, cents=False):
    """Whole dollars, rounded half up. The page shows no cents (the CSV keeps them); `cents` is accepted but ignored."""
    return f'${int(Decimal(str(round(v, 2))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)):,}'


def d(s):
    return date.fromisoformat(s)


def fmt(dt):
    return f'{MONTHS[dt.month - 1]} {dt.day}, {dt.year}'


def amt(s):
    return float(s.replace('$', '').replace(',', '').replace('(', '-').replace(')', ''))


def chart(points, narrow=False):
    """Step chart of the account balance after each warrant list, drawn to scale.

    The narrow version is drawn for phones: a smaller canvas so text stays legible, with fewer date labels."""
    W, H, L, R, T, B = (380, 260, 52, 14, 24, 34) if narrow else (760, 300, 64, 16, 24, 36)
    x0, x1 = date(2025, 10, 1), date(2026, 10, 31)
    step = 200_000
    ymax = (int(max(v for _, v in points) * 1.08) // step + 1) * step  # headroom above the last value
    sx = lambda dt: L + (dt - x0).days / (x1 - x0).days * (W - L - R)
    sy = lambda v: T + (1 - v / ymax) * (H - T - B)
    g = []
    for v in range(0, ymax + 1, step):
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/>'
                 f'<text x="{L - 8}" y="{sy(v) + 4:.1f}" class="ylab">{"$0" if v == 0 else f"${v / 1e6:.1f}M"}</text>')
    for y, m in ([(2025, 10), (2026, 4), (2026, 10)] if narrow else [(2025, 10), (2026, 1), (2026, 4), (2026, 7), (2026, 10)]):
        x = sx(date(y, m, 1))
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{H - B}" y2="{H - B + 5}" class="tick"/>'
                 f'<text x="{x:.1f}" y="{H - B + 20}" class="xlab">{MONTHS[m - 1]} {y}</text>')
    path, prev = [f'M{sx(x0):.1f},{sy(0):.1f}'], 0
    for dt, v in points:
        path.append(f'L{sx(dt):.1f},{sy(prev):.1f}L{sx(dt):.1f},{sy(v):.1f}')
        prev = v
    end_x = sx(points[-1][0])
    line = ''.join(path)
    area = line + f'L{end_x:.1f},{sy(0):.1f}Z'
    dots = ''.join(f'<circle cx="{sx(dt):.1f}" cy="{sy(v):.1f}" r="3" class="dot"><title>{fmt(dt)}: {money(v, True)}</title></circle>'
                   for dt, v in points)
    last_dt, last_v = points[-1]
    label = (f'<text x="{sx(last_dt) - 8:.1f}" y="{max(sy(last_v) - 10, T + 12):.1f}" class="endlab">{money(last_v)}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="{'chart-narrow' if narrow else 'chart-wide'}" role="img" aria-label="Running balance of Eldora acquisition costs paid by the General Fund, '
            f'rising from $67,492 in October 2025 to {money(last_v)} in October 2026">{"".join(g)}'
            f'<path d="{area}" class="area"/><path d="{line}" class="line"/>{dots}{label}</svg>')


MONTH = (r'(?:January|February|March|April|May|June|July|August|September|October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)')
DATE_NO_COMMA = re.compile(rf'(\b{MONTH}\.? \d{{1,2}}, \d{{4}})(?=\s+[A-Za-z])')


def american_dates(page):
    """American style puts a comma after the year when a full date sits mid-sentence ("On May 1, 2026, the Board").

    Applied to visible text only (never inside tags), and not to quotations in <q> elements."""
    out, quoted = [], 0
    for part in re.split(r'(<[^>]+>)', page):
        if part.startswith('<'):
            quoted += 1 if part.startswith('<q') else -1 if part.startswith('</q') else 0
            out.append(part)
        else:
            out.append(part if quoted else DATE_NO_COMMA.sub(r'\1,', ap_months(part)))
    return ''.join(out)


AP_MONTHS = {'Jan': 'Jan.', 'Feb': 'Feb.', 'Mar': 'March', 'Apr': 'April', 'Jun': 'June', 'Jul': 'July',
             'Aug': 'Aug.', 'Sep': 'Sept.', 'Sept': 'Sept.', 'Oct': 'Oct.', 'Nov': 'Nov.', 'Dec': 'Dec.'}


def ap_months(text):
    """American (AP) month abbreviations: periods on Jan., Feb., Aug., Sept., Oct., Nov., Dec.; March-July spelled out."""
    full = {'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April', 'Jun': 'June', 'Jul': 'July',
            'Aug': 'August', 'Sep': 'September', 'Sept': 'September', 'Oct': 'October', 'Nov': 'November',
            'Dec': 'December'}
    # a month with only a year is spelled out ("October 2025"); with a day it is abbreviated ("Oct. 6")
    text = re.sub(r'\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b\.?(?=[ \u00a0]\d{4}\b)',
                  lambda m: full[m.group(1)], text)
    return re.sub(r'\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b(?!\.)(?=[ \u00a0]\d)',
                  lambda m: AP_MONTHS[m.group(1)], text)


PUBLISHED = '2026-10-11'


def change_log():
    """Render analysis/changes.json, newest first.

    Each entry: {"date": "YYYY-MM-DD", "type": "Correction" | "Update", "text": "...", optional "headline": "..."}. A correction should also get
    an inline marker next to the corrected text in the page: write [[corrected:YYYY-MM-DD]] there."""
    path = os.path.join(ROOT, 'analysis', 'changes.json')
    # newest first; entries on the same date keep newest-added first
    entries = list(reversed(sorted(json.load(open(path)) if os.path.exists(path) else [], key=lambda c: c['date'])))
    if not entries:
        return f'<p class="prose muted">No corrections or updates since the page was published on {fmt(d(PUBLISHED))}.</p>'
    items = ''.join(
        f'<li id="change-{c["date"]}-{i}"><strong>{fmt(d(c["date"]))} \u2014 {e(c["type"])}.</strong> {c["text"]}</li>'
        for i, c in enumerate(entries))
    n_corr = sum(c['type'] == 'Correction' for c in entries)
    n_upd = len(entries) - n_corr
    counts = f'{n_corr} correction{"s" * (n_corr != 1)}, {n_upd} update{"s" * (n_upd != 1)}'
    return (f'<details class="changes-box"><summary>Show all {len(entries)} entries ({counts}), newest first; '
            f'latest {fmt(d(entries[0]["date"]))}</summary><ul class="changes prose">{items}</ul></details>')


SUBSCRIBE = 'eldora-record-updates+subscribe@googlegroups.com'   # Google Group announcing major updates


def latest_update():
    """One-line notice at the top: the newest change-log entry that has a "headline" (major updates and
    corrections only; routine updates such as a new warrant list leave the previous headline in place)."""
    path = os.path.join(ROOT, 'analysis', 'changes.json')
    entries = json.load(open(path)) if os.path.exists(path) else []
    marked = [c for c in entries if c.get('headline')]
    if not marked:
        return ''
    c = max(reversed(marked), key=lambda c: c['date'])   # latest date; the last-added entry wins a tie
    label = 'Latest major correction' if c['type'] == 'Correction' else 'Latest major update'
    return (f'<p class="latest"><strong>{label}, {fmt(d(c["date"]))}:</strong> {c["headline"]} '
            f'<a href="mailto:{SUBSCRIBE}?subject=Subscribe">Subscribe to page updates</a></p>')


def correction_markers(page):
    """Replace [[corrected:YYYY-MM-DD]] with a small note linking to the change log."""
    return re.sub(r'\[\[corrected:(\d{4}-\d\d-\d\d)\]\]',
                  lambda m: f'<a class="corr-note" href="#changes">Corrected {fmt(d(m.group(1)))}</a>', page)


# "Who's who": every firm in the acquisition records, with its role as the records state it. Roles come only from
# Town documents; "Not stated" where none gives one. (group, firm, vendor key in PAYEES or None, role, how engaged,
# last documented evidence for firms with no Eldora invoices, unused)
WHO = [
    ('Financing', 'Stifel', None, 'Municipal advisor: structures the financing and coordinates the deal team; owes the Town a fiduciary duty', 'Named in the Jan. 2026 draft purchase agreement; extended July 7, 2026', 'July 2026: agreement through June 30, 2027', None),
    ('Financing', 'RBC Capital Markets and BofA Securities', None, 'Underwriters; would buy the bonds "on a best-efforts basis"', 'Engaged by Nov. 2025; approved in Ord. 885', 'April 2026: named in FAQ 6.0', None),
    ('Financing', 'Northland Securities', None, 'Underwriter', 'Res. 2025-02', 'April 2025: last mention', None),
    ('Financing', 'J.P. Morgan Securities', None, 'Underwriter (non-binding letter of intent)', 'Res. 2025-08', 'April 2025: last mention', None),
    ('Lawyers', 'Widner Juran', 'Widner Juran LLP', 'Town Attorney; includes $46,211 in January to July 2025 invoices moved into this account from the Legal budget', 'Standing appointment', None, None),
    ('Lawyers', 'Kline Alvarado Veio', 'Kline Veio', 'Bond counsel', 'Res. 2025-16 (named)', None, None),
    ('Lawyers', 'Butler Snow', None, 'Disclosure counsel', 'Named in FAQ 6.0', 'April 2026: named in FAQ 6.0', None),
    ('Lawyers', 'Brownstein Hyatt Farber Schreck', None, 'Real estate counsel', 'Named in FAQ 6.0', 'April 2026: named in FAQ 6.0', None),
    ('Lawyers', 'Dickinson Wright', 'Dickinson Wright PLLC', 'Water-rights due diligence (its other water-law work is billed to the Water Fund); includes a $9,680 invoice moved into this account from the Legal budget', 'Engagement approved July 15, 2025', None, None),
    ('Lawyers', 'Hogan Lovells', 'Hogan Lovells US LLP', 'Role not stated in the records searched', 'appears in the records searched only on the July 21 and Aug. 18, 2026, warrant lists and in the Town\'s ledger for the account', None, None),
    ('Lawyers', 'Semple, Farrington, Everall & Case', 'Semple', 'Role not stated in the records searched; the Res. 2025-16 memo expects "specialized employment matters"', 'no engagement record in the Board documents searched', None, None),
    ('Due diligence', 'SE Group', 'Sno.engineering', 'Operations, market, and financial review of the resort', 'Res. 2025-15', None, None),
    ('Due diligence', 'Farnsworth Group', 'Farnsworth Group', 'Engineering; work not stated in the records searched', 'no engagement record in the Board documents searched', None, None),
    ('Due diligence', 'Partner Engineering and Science', 'Partner Assessment Corporation', 'Role not stated in the records searched; the Nov. 2025 Eldora memo reports a property condition assessment and an environmental site assessment without naming who did them', 'no engagement record in the Board documents searched', None, None),
    ('Due diligence', 'Torrent Engineering & Equipment', 'Torrent Engineering & Equipment Company LLC', 'Engineering; work not stated in the records searched', 'no engagement record in the Board documents searched', None, None),
    ('Due diligence', 'BBA Water Consultants', 'BBA Water Consultants', "Eldora's own water consultant under the purchase agreement", 'Purchase agreement', None, None),
    ('Due diligence', 'JVA', 'JVA', "The Town's on-call engineers", 'Regular Town vendor', None, None),
    ('Due diligence', 'DiNatale Water Consultants', 'DiNatale Water Consultants', "The Town's water engineers", 'Regular Town vendor', None, None),
    ('Transition and administration', 'Plante Moran', 'P&M Holding Group', 'HR and finance transition planning; since July 2026 also signs the Town\'s Treasurer reports; includes $853 moved into this account from Professional Services', 'Res. 2025-22 covers HR and finance consultants (no firm named); then Res. 2026-12', None, None),
    ('Transition and administration', 'Bolder HR Solutions', 'Susan N. Fattor', 'HR support', 'Res. 2025-22 covers HR and finance consultants (no firm named)', None, None),
    ('Transition and administration', 'Datasite', 'Datasite LLC', 'Role not stated in the records searched ($200 a month)', 'no engagement record in the Board documents searched', None, None),
    ('Transition and administration', 'Vadim Municipal Software', 'Vadim Municipal Software Inc', "The Town's accounting software", 'Regular Town vendor', None, None),
    ('Transition and administration', 'Professional Management Solutions', 'Professional Management Systems', 'Role not stated in the records searched', 'no engagement record in the Board documents searched', None, None),
    ('Seller and partners', 'POWDR', 'POWDR Corp', 'The seller; the records searched don\'t state the purpose of its three invoices, one of which ($50,000) is on no warrant list', 'Purchase agreement', None, None),
    ('Seller and partners', '303 Ski', None, 'Advisory partner in 2025; the Town declined its reimbursement requests', 'Announced in FAQ 3.0', 'April 2026: FAQ 6.0', None),
]
BADGE_SAYS = {'Regular Town vendor', 'no engagement record in the Board documents searched'}
WHO_NOTE = ('Roles are as stated in Town documents. "Last documented" is the latest evidence in the records, not whether a '
            'firm is still engaged: invoices are often paid months late, and the Town has not said which firms are still '
            'working on the deal.')
UNPAID = [
    ('Fees owed only if the sale closes', [
        ('Stifel', 'Municipal advisor: structures the financing and coordinates the deal team, and owes the Town a fiduciary duty "to act in your best interests without regard to our financial or other interests." Named in the Jan. 2026 draft purchase agreement; extended July 7, 2026', '$325,000 at bond sale', 'agreement runs through June 30, 2027', 130472),
        ('Northland Securities', 'Underwriter under a non-binding engagement (Res. 2025-02). "If no bonds are issued, no fees will be incurred"', 'Share of bonds', 'last mentioned April 2025', 118128),
    ]),
    ('Named in Town records; fee terms not in the records searched', [
        ('RBC Capital Markets and BofA Securities', 'Underwriters, engaged by Nov. 2025 and approved in Ord. 885, to buy the bonds "on a best-efforts basis." The Res. 2025-11 memo anticipates pay contingent on a financing', 'Not in records searched', 'last named April 2026 (FAQ 6.0)', 125525),
        ('J.P. Morgan Securities', 'Underwriter under a non-binding letter of intent (Res. 2025-08)', 'None stated', 'last mentioned April 2025', 120603),
        ('Butler Snow', 'Disclosure counsel', 'Not in records searched', 'last named April 2026 (FAQ 6.0)', None),
        ('Brownstein Hyatt Farber Schreck', 'Real estate counsel', 'Not in records searched', 'last named April 2026 (FAQ 6.0)', None),
        ('303 Ski', 'Advisory partner announced in FAQ 3.0; the Town declined its requests for reimbursement', 'None', 'last mentioned April 2026 (FAQ 6.0)', None),
    ]),
]
MONTHS_FULL = 'January February March April May June July August September October November December'.split()



HOUSEHOLDS = 685      # Boulder County recycling agreement, citing the Town's CAA Colorado application (Sept. 15, 2026, packet)
# General Fund net change in fund balance by year, from the audits: (year, reported change, loan proceeds and transfers in)
GF_RESULTS = [(2017, 300_800, 0), (2018, 149_593, 0), (2019, 199_849, 0), (2020, 231_130, 0), (2021, 304_158, 0),
              (2022, 83_265, 43_158), (2023, 124_674, 617_155), (2024, -265_953, 0), (2025, -192_241, 0)]
# Mentions of source documents in the page text, linked automatically (first mention in each section).
# Longer patterns come first so "Res. 2025-16 memo" wins over "Res. 2025-16".
CW_DOC = 'https://nederlandco.civicweb.net/document/{}/'
_WA = 'https://web.archive.org/web/{}/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-'
_NF = 'https://www.nederlandco.gov/m/newsflash/home/detail/{}'
REF_LINKS = [
    (r'FAQ Round 2', CW_DOC.format(118136)),   # also in the Jan. 7, 2025, Board packet
    (r'FAQ 3\.0', _WA.format('20250709224556') + 'faqs-30'),
    (r'FAQ 4\.0', _WA.format('20251112014324') + 'faqs-40'),
    (r'FAQ 6\.0', _NF.format(22)),
    (r'FAQ 7\.0', _NF.format(17)),
    (r'September 30(?:, 2026,)? update', _NF.format(21)),
    (r'Res\. 2025-16 memo', CW_DOC.format(123039)),
    (r'August 2025 legal-counsel memo', CW_DOC.format(123039)),
    (r'November 2025 Eldora memo', CW_DOC.format(125525)),
    (r'July 2025 rate memo', CW_DOC.format(122661)),
    (r'(?<=though )its memo', CW_DOC.format(129045)),
    (r'The engagement letter(?= says an estimate)', CW_DOC.format(122663)),
    (r'Res(?:\.|olution) 2023-16', CW_DOC.format(44652)),
    (r'Res\. 2025-02', CW_DOC.format(118190)),
    (r'Res\. 2025-03', CW_DOC.format(118191)),
    (r'Res\. 2025-08', CW_DOC.format(121523)),
    (r'Res\. 2025-11|(?<=Res\. 2025-03, )2025-11', CW_DOC.format(121635)),
    (r'Res\. 2025-15', CW_DOC.format(124156)),
    (r'Res\. 2025-16', CW_DOC.format(124157)),
    (r'Res\. 2025-17', CW_DOC.format(124158)),
    (r'Res\. 2025-19', CW_DOC.format(125955)),
    (r'Res\. 2025-22|(?<=Res\. 2025-19, )2025-22', CW_DOC.format(125959)),
    (r'Res\. 2026-07', CW_DOC.format(128824)),
    (r'Res\. 2026-12', CW_DOC.format(129077)),
    (r'Res\. 2026-13', CW_DOC.format(129078)),
    (r'Ord(?:\.|inance) 873', CW_DOC.format(119622)),
    (r'Ord(?:\.|inance) 882', CW_DOC.format(127853)),
    (r'Ord(?:\.|inance) 885', CW_DOC.format(127855)),
    (r'Ordinance 859', CW_DOC.format(113049)),
    (r'Ordinance 839', CW_DOC.format(45292)),
    (r'§(?:4\.4\(b\)|7\.2\(a\)\(ii\))', CW_DOC.format(126803)),
    (r'Indenture of Trust', CW_DOC.format(127181)),
    (r'2025 audit', 'https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit'),
    (r'2023 audit', 'https://www.nederlandco.gov/DocumentCenter/View/593/2023-Audit'),
    (r'monthly treasurer reports', CW_DOC.format(131730)),
]
_REF_RE = re.compile('|'.join(f'(?P<r{i}>{pat})' for i, (pat, _) in enumerate(REF_LINKS)))


def link_refs(page):
    """Link the first unlinked mention of each source document in each section. Text inside links, tags, styles,
    scripts, and the method section (which quotes the research requests verbatim) is left alone."""
    out, used, skip, in_raw = [], set(), False, False
    for tok in re.split(r'(<a\b.*?</a>|<[^>]+>)', page, flags=re.S):
        if tok.startswith('<'):
            if tok.startswith(('<section', '<div class="group"', '<footer')):
                used, skip = set(), 'id="method-ai"' in tok
            if tok.startswith(('<style', '<script')):
                in_raw = True
            elif tok.startswith(('</style', '</script')):
                in_raw = False
            out.append(tok)
            continue
        if skip or in_raw or not tok.strip():
            out.append(tok)
            continue

        def repl(m):
            i = int(m.lastgroup[1:])
            if i in used:
                return m.group(0)
            used.add(i)
            return f'<a href="{e(REF_LINKS[i][1])}" target="_blank" rel="noopener">{m.group(0)}</a>'
        out.append(_REF_RE.sub(repl, tok))
    return ''.join(out)



# Recent discretionary projects for the "For scale" chart: (label, total, grant share, source doc id, note)
SCALE_PROJECTS = [
    ('Street equipment lease-purchase, 2023', 511_000, 0, '44830', 'repaid over 5 years [[corrected:2026-10-11]]'),
    ('Comprehensive Plan, 2023–2025', 205_188, 100_000, '119355', 'state grant'),
    ('Crosswalk improvements, 2026', 360_000, 300_000, '129318', 'federal grant'),
    ('Emergency sirens, proposed 2026', 260_000, 195_000, '130735', 'federal grant applied for'),
    ('Shared housing coordinator, 3 years', 200_000, 160_000, '122222', 'state grant'),
]


def scale_chart(paid, estimate):
    """Stacked bars on one scale: the Town's own money vs. grant money."""
    def k(v):
        return f'${v / 1e6:.1f}M' if v >= 1e6 else f'${v / 1e3:,.0f}K'
    rows = [('Eldora, if the sale fails (Town estimate)', estimate, 0, None, 'no grants'),
            ('Eldora, paid so far', paid, 0, None, 'no grants')] + SCALE_PROJECTS
    top = max(r[1] for r in rows) / 0.78   # longest bar uses 78% of the width, leaving room for its label
    out = []
    for label, total, grant, doc, note in rows:
        own = total - grant
        src = f' <a href="https://nederlandco.civicweb.net/document/{doc}/" target="_blank" rel="noopener">source</a>' if doc else ''
        val = f'Town {k(own)}' + (f' + grant {k(grant)}' if grant else '')
        grant_span = f'<span class="sc-grant" style="width:{grant / top * 100:.2f}%"></span>' if grant else ''
        out.append(f'<div class="sc-row{" sc-eldora" if doc is None else ""}"><div class="sc-label">{e(label)}'
                   f'<span class="sc-note"> · {e(note)}{src}</span></div>'
                   f'<div class="sc-bar"><span class="sc-own" style="width:{own / top * 100:.2f}%"></span>'
                   f'{grant_span}'
                   f'<span class="sc-val">{val}</span></div></div>')
    legend = ('<div class="sc-legend"><span><i class="sc-own"></i>Town\'s own money</span>'
              '<span><i class="sc-grant"></i>Grant money</span></div>')
    return f'<figure class="scale-chart" aria-label="Eldora acquisition costs compared with recent discretionary projects">{legend}{"".join(out)}</figure>'


def label_cells(page):
    """Give every cell of each table.commit a data-label naming its column, for the stacked phone layout."""
    def one(m):
        table = m.group(0)
        heads = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<th[^>]*>(.*?)</th>', table.split('</thead>')[0])]
        def row(rm):
            i = iter(heads)
            return re.sub(r'<td(?=[ >])', lambda _: f'<td data-label="{html.escape(next(i, ""), quote=True)}"', rm.group(0))
        head, body = table.split('</thead>', 1)
        return head + '</thead>' + re.sub(r'<tr[^>]*>.*?</tr>', row, body, flags=re.S)
    return re.sub(r'<table class="commit">.*?</table>', one, page, flags=re.S)


def main():
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'analysis', 'eldora_due_from.csv'))))
    for r in rows:
        r['amt'] = float(r['amount'])
        r['bal'] = -amt(r['account_balance_after'])
    balance = max(r['bal'] for r in rows)
    listed = sum(r['amt'] for r in rows)
    points = {}
    for r in rows:
        points[r['warrant_meeting']] = max(points.get(r['warrant_meeting'], 0), r['bal'])
    points = [(d(k), v) for k, v in sorted(points.items())]
    bal_2025 = [v for k, v in points if k.year == 2025][-1]   # account balance after the last 2025 warrant list

    by_vendor = defaultdict(float)
    for r in rows + OFF_LIST:
        by_vendor[r['vendor']] += r['amt']
    unattributed = balance - listed - sum(x['amt'] for x in OFF_LIST)
    moved = sum(x['amt'] for x in OFF_LIST if x['first'])
    top5 = [f'{PAYEES[v][0]} ({money(t)})' for v, t in sorted(by_vendor.items(), key=lambda t: -t[1])[:5]]
    top_payees = ', '.join(top5[:-1]) + ', and ' + top5[-1]
    vendors = sorted(by_vendor.items(), key=lambda t: -t[1])
    top = vendors[0][1]
    missing = [v for v in by_vendor if v not in PAYEES]
    assert not missing, f'payees without an evidence rating: {missing}'
    tier_total = defaultdict(float)
    for v, total in vendors:
        tier_total[PAYEES[v][1]] += total
    # one list, largest first, with each payee's evidence rating as a tag next to the name
    who_by_vendor = {w[2]: w for w in WHO if w[2]}
    last_invoice = {}
    for r in rows + OFF_LIST:
        dd = datetime.strptime(r['invoice_date'], '%m/%d/%y').date()
        last_invoice[r['vendor']] = max(last_invoice.get(r['vendor'], dd), dd)
    entries = [(total, PAYEES[v][0], PAYEES[v][1], v) for v, total in vendors]
    if abs(unattributed) >= 0.5:
        entries.append((unattributed, 'Not on any warrant list', 'unk', None))
    tag_text = dict(EVIDENCE, unk='Payee not in the records searched')
    vrows = []
    for total, name, tier, v in sorted(entries, key=lambda x: -x[0]):
        key = 'unk' if tier == 'unk' else (v if v in PAYEE_ANCHORS else None)
        fid = PAYEE_ANCHORS.get(key) if key else None
        cls = 'unk' if tier == 'unk' else ''
        if v:
            w = who_by_vendor[v]
            li = last_invoice[v]
            # The evidence badge already says these, so the role line leaves them out
            basis = '' if w[4] in BADGE_SAYS else f' · {w[4]}'
            role = (e(f'{w[3]}{basis} · ').replace('&amp;', '&')
                    + f'<span class="lastdoc">last invoice {MONTHS_FULL[li.month - 1]} {li.year}</span>')
        else:
            role = e('Added to the account between warrant lists; payee not in the records searched')
        vrows.append(f'<tr{f" class=\"{cls}\"" if cls else ""}{f" id=\"{fid}\"" if fid else ""}><td class="who">{e(name)} '
                     f'<span class="ev ev-{tier} sm">{tag_text[tier]}</span><div class="role">{role}</div></td>'
                     f'<td class="bar"><span class="b-{tier}" style="width:{total / top * 100:.1f}%"></span></td>'
                     f'<td class="num">{money(total, True)}</td></tr>')
    for heading, firms in UNPAID:
        vrows.append(f'<tr class="who-group"><td colspan="3">{e(heading)}</td></tr>')
        for firm, role, fee, lastdoc, doc in firms:
            src = (f' (<a href="https://nederlandco.civicweb.net/document/{doc}/" target="_blank" rel="noopener">source</a>)'
                   if doc else '')
            vrows.append(f'<tr class="unpaid"><td class="who">{e(firm)}<div class="role">{e(role)}{src} · '
                         f'<span class="lastdoc">{e(lastdoc)}</span></div></td><td class="bar"></td>'
                         f'<td class="num">{e(fee)}</td></tr>')

    site = json.load(open(os.path.join(ROOT, 'site_config.json'))).get('base_url', 'https://eldorarecord.org/')
    rec_ledger, rec_reply = site + CORA_LEDGER, site + CORA_REPLY
    ledger = []
    for r in sorted(rows + OFF_LIST, key=lambda x: (x['warrant_meeting'], 'label' in x)):
        name, tier, _ = PAYEES[r['vendor']]
        if 'label' in r:   # in the Town's ledger, not on a warrant list as a "Due From" charge
            first = r['first']
            note = r['label'] + (f'; first paid on the {fmt(d(first[0]))}, warrant list' if first else '')
            src = f'<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>'
            if first:
                src += (f', <a href="https://nederlandco.civicweb.net/document/{first[1]}/" target="_blank" '
                        f'rel="noopener">p.{first[2]}</a>')
            text = ' '.join([r['warrant_meeting'], name, r['invoice'], r['invoice_date'], f"{r['amt']:.2f}",
                             EVIDENCE[tier], note]).lower()
            ledger.append(f'<tr class="offlist" data-text="{e(text)}"><td class="dt">{fmt(d(r["posted"]))} (ledger)</td>'
                          f'<td>{e(name)} <span class="ev ev-{tier} sm" title="{EVIDENCE[tier]}">{EVIDENCE[tier]}</span>'
                          f'<div class="role">{e(note)}</div></td>'
                          f'<td class="mono opt">{e(r["invoice"])}</td><td class="mono opt">{e(r["invoice_date"])}</td>'
                          f'<td class="num">{money(r["amt"], True)}</td><td class="num muted opt"></td><td>{src}</td></tr>')
            continue
        text = ' '.join([r['warrant_meeting'], name, r['invoice'], r['invoice_date'], r['amount'], EVIDENCE[tier]]).lower()
        ledger.append(f'<tr data-text="{e(text)}"><td class="dt">{fmt(d(r["warrant_meeting"]))}</td>'
                      f'<td>{e(name)} <span class="ev ev-{tier} sm" title="{EVIDENCE[tier]}">{EVIDENCE[tier]}</span></td>'
                      f'<td class="mono opt">{e(r["invoice"])}</td><td class="mono opt">{e(r["invoice_date"])}</td>'
                      f'<td class="num">{money(r["amt"], True)}</td><td class="num muted opt">{money(r["bal"], True)}</td>'
                      f'<td><a href="{e(r["source"])}" target="_blank" rel="noopener">p.{e(r["warrant_page"])}</a></td></tr>')

    votes = fragment()
    from datetime import date as _date
    cov_from, cov_through, cov_updated = fmt(archive_from()), fmt(archive_through()), fmt(_date.today())
    estimate = 2_500_000          # Town's Sept 30, 2026 estimate of costs owed if the sale fails
    unpaid = estimate - balance
    m = lambda v: f'${v / 1e6:.1f} million'
    gf_ops = 3_236_824   # General Fund operating expenditures, adopted 2026 budget
    cfg = json.load(open(os.path.join(ROOT, 'site_config.json')))
    site = cfg.get('base_url', 'https://eldorarecord.org/')
    direct = (f'<a href="{site}eldora-record.xlsx">.xlsx</a>, '
              f'<a href="{site}eldora-payments.csv">payments .csv</a>')
    drive = cfg.get('data_drive_url')
    data_links = (f'Download the data: <a href="{e(drive)}" target="_blank" rel="noopener"><strong>spreadsheet</strong></a> '
                  f'(opens in Google Sheets; no sign-in needed) \u00b7 direct download: {direct}' if drive
                  else f'Download the data: {direct}')
    per_hh = lambda v: money(v / HOUSEHOLDS)   # noqa: E731
    good = [r for r in GF_RESULTS if 2017 <= r[0] <= 2023]
    avg_rep = sum(r[1] for r in good) / len(good)
    avg_op = sum(r[1] - (511_000 if r[0] == 2023 else 0) for r in good) / len(good)   # without the 2023 lease proceeds
    yrs = lambda v, a: f'{v / a:.0f}'   # noqa: E731
    # General Fund if the sale fails in 2026 (this page's calculation; 2025 audit and adopted 2026 budget)
    gf_cash_2025, gf_owed_2025, gf_bal_2025, gf_bud_2026 = -757_482, 1_456_233, 1_030_078, 583_730
    since = round(balance) - round(bal_2025)
    cash_end = gf_cash_2025 + gf_owed_2025 - since - (estimate - balance)
    fb_end = gf_bud_2026 - estimate
    neg = lambda v: '\u2212' + money(-v) if v < 0 else money(v)   # noqa: E731
    page = TEMPLATE.format(
        hh_paid=per_hh(balance), hh_est=per_hh(estimate), hh_alt=per_hh(estimate + balance),
        res_est=money(estimate / 1471), avg_rep=money(round(avg_rep, -3)), avg_op=money(round(avg_op, -3)),
        yrs_est=f'{yrs(estimate, avg_rep)} to {yrs(estimate, avg_op)}', yrs_paid=f'{yrs(balance, avg_rep)} to {yrs(balance, avg_op)}',
        data_links=data_links,
        cash_after=money(gf_cash_2025 + gf_owed_2025), unpaid_x=money(estimate - balance),
        cash_end=neg(cash_end),
        fb_end=neg(fb_end), fb_end_m=f'about ${-fb_end / 1e6:.1f} million', bud_change=neg(gf_bud_2026 - gf_bal_2025),
        yrs_def=f'{yrs(-fb_end, avg_rep)} to {yrs(-fb_end, avg_op)}',
        ufb_2026=f'\u2212{-(fb_end - 147_000 - 10_905) / gf_ops:.2f}',   # unrestricted = balance less restricted and nonspendable (2025 audit)
        scale_chart=scale_chart(balance, estimate),
        pct_paid=f'{balance / gf_ops:.0%}', pct_est=f'{estimate / gf_ops:.0%}', x_comp=f'{balance / 205_188:.0f}',
        changes=change_log(), latest=latest_update(),
        hogan=money(by_vendor['Hogan Lovells US LLP']),
        powdr=money(by_vendor['POWDR Corp']), unpaid=m(unpaid), unpaid_short=f'${unpaid / 1e6:.1f}M',
        alt_total=m(estimate + balance),
        method=method_html('record'), cov_from=cov_from, cov_through=cov_through, cov_updated=cov_updated,
        votes_css=votes['css'], votes_html=votes['html'], votes_js=votes['js'],
        n_actions=votes['n_actions'], n_sessions=votes['n_sessions'], n_es_gaps=votes['n_gaps'], first_es=votes['first'],
        balance=money(balance), balance_c=money(balance, True), since_2025=money(round(balance) - round(bal_2025)), bal_2025=money(bal_2025), listed=money(listed), n=len(rows),
        unlisted=money(balance - listed), unlisted_about=f'about ${round((balance - listed) / 1000):,},000', moved=money(moved), site=site, subscribe=SUBSCRIBE, rec_ledger=rec_ledger, rec_reply=rec_reply, top=e(top_payees), asof=fmt(points[-1][0]), chart=chart(points) + chart(points, narrow=True),
        vendors=''.join(vrows), ledger=''.join(ledger),
        named=money(tier_total['named']), coding=money(tier_total['coding']), none=money(tier_total['none']))
    page = link_refs(american_dates(label_cells(correction_markers(page))))
    with open(os.path.join(ROOT, 'analysis', 'eldora_spending.html'), 'w') as f:
        f.write(page)
    print(f'{len(rows)} payments, balance {money(balance, True)}, listed {money(listed, True)}')


TEMPLATE = '''<title>Nederland Eldora Record</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;800&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a public-finance ledger in the same family as the vote record. Reading column for prose, full-width figures and tables. */
:root {{
  --bg: #f6f8f8; --surface: #ffffff; --fg: #17242a; --muted: #5a6b72; --line: #d7e0e2;
  --accent: #1f6b5c; --accent-soft: #e2f0ec; --warn: #9a4a1c; --warn-soft: #f8e9df;
  --body: "Public Sans", system-ui, sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #11191c; --surface: #172226; --fg: #e3ecee; --muted: #93a6ad; --line: #2b3a40;
  --accent: #6cc7b1; --accent-soft: #1b3832; --warn: #f0a774; --warn-soft: #3d2618; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #11191c; --surface: #172226; --fg: #e3ecee; --muted: #93a6ad; --line: #2b3a40;
  --accent: #6cc7b1; --accent-soft: #1b3832; --warn: #f0a774; --warn-soft: #3d2618; color-scheme: dark }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.55 var(--body); }}
.wrap {{ max-width: 1200px; margin: 0 auto; padding-inline: 20px; padding-block: 40px 64px; display: grid; gap: 44px; }}
.prose {{ max-width: 80ch; }}
header, section {{ display: grid; gap: 14px; min-width: 0; }}
.eyebrow {{ font: 500 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }}
h1 {{ font: 800 clamp(28px, 4.5vw, 42px)/1.1 var(--body); margin: 0; text-wrap: balance; letter-spacing: -.01em; }}
h2 {{ font: 800 22px/1.2 var(--body); margin: 0; text-wrap: balance; }}
h3 {{ font: 600 16px/1.3 var(--body); margin: 0; }}
p {{ margin: 0; }}
.lede {{ font-size: 17px; }}
.disclaimer {{ font-size: 13.5px; color: var(--muted); border-left: 3px solid var(--line); padding-left: 12px; }}
.muted {{ color: var(--muted); }}
a {{ color: var(--accent); }}
a:focus-visible, input:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.steps {{ margin: 0; padding-left: 22px; display: grid; gap: 6px; }}
.changes {{ margin: 0; padding-left: 20px; display: grid; gap: 8px; }}
.changes-box {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px 16px; }}
.changes-box summary {{ cursor: pointer; font-weight: 600; }}
.changes-box[open] summary {{ margin-bottom: 10px; }}
td.vid a {{ white-space: nowrap; font-variant-numeric: tabular-nums; }}
.statement {{ margin: 14px 0 4px; padding: 10px 14px; max-width: 80ch; border: 1px solid var(--line); border-radius: 6px; font-size: 14.5px; }}
.statement b {{ display: block; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); }}
.statement p {{ margin: 6px 0 0; }}
.statement .sig {{ font-style: italic; color: var(--muted); }}
.latest {{ margin: 10px 0 0; padding: 8px 12px; font-size: 14px; background: var(--accent-soft); border-left: 3px solid var(--accent); border-radius: 0 6px 6px 0; max-width: 80ch; }}
.corr-note {{ font: 500 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .04em; color: var(--warn); border: 1px solid var(--warn); border-radius: 4px; padding: 2px 5px; margin-left: 6px; text-decoration: none; white-space: nowrap; }}
.scale-chart {{ margin: 0; display: grid; gap: 12px; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px; }}
.sc-legend {{ display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 13px; color: var(--muted); }}
.sc-legend i {{ display: inline-block; width: 14px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: 0; }}
.sc-row {{ display: grid; gap: 4px; }}
.sc-label {{ font-size: 14px; }}
.sc-eldora .sc-label {{ font-weight: 600; }}
.sc-note {{ color: var(--muted); font-size: 13px; }}
.sc-bar {{ display: flex; align-items: center; gap: 0; min-height: 16px; }}
.sc-bar .sc-own, .sc-bar .sc-grant {{ display: block; height: 14px; min-width: 2px; }}
.sc-own {{ background: var(--warn); }}
.sc-grant {{ background: var(--accent-soft); outline: 1px solid var(--accent); outline-offset: -1px; }}
.sc-val {{ font: 500 13px var(--mono); margin-left: 8px; white-space: nowrap; }}
.findings {{ background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--warn); border-radius: 8px; padding: 18px 22px; display: grid; gap: 10px; }}
.findings h2 {{ font-size: 18px; }}
.findings ol {{ margin: 0; padding-left: 22px; display: grid; gap: 10px; max-width: 80ch; }}
.findings li::marker {{ font: 500 13px var(--mono); color: var(--muted); }}
.findings strong {{ font-weight: 600; }}
.bottom-line {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 18px 22px; }}
.bottom-line .scroll {{ border: 0; }}
.open-q {{ border-left: 4px solid var(--warn); background: var(--warn-soft); border-radius: 0 8px 8px 0; padding: 14px 22px; }}
.open-q ul {{ margin: 8px 0 0; padding-left: 20px; }}
.open-q li {{ margin: 6px 0; }}
table.bl tr.bl-total td {{ background: var(--warn-soft); font-weight: 600; }}
table.bl td.amount {{ white-space: nowrap; font-family: var(--mono); }}
.facts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
.fact {{ background: var(--surface); padding: 16px 18px; display: grid; gap: 6px; align-content: start; }}
.fact b {{ font: 500 28px/1 var(--mono); font-variant-numeric: tabular-nums; }}
.fact.spent b {{ color: var(--warn); }}
.fact span {{ font-size: 13.5px; color: var(--muted); }}
.fact .tag {{ justify-self: start; font: 500 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .06em; padding: 4px 6px; border-radius: 4px; }}
.tag.paid {{ background: var(--warn-soft); color: var(--warn); }}
.tag.auth {{ background: var(--accent-soft); color: var(--accent); }}
.figure {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; overflow-x: auto; }}
.figure svg {{ display: block; width: 100%; min-width: 520px; height: auto; }}
.figure .chart-narrow {{ display: none; }}
.grid {{ stroke: var(--line); stroke-width: 1; }}
.tick {{ stroke: var(--muted); }}
.ylab, .xlab {{ fill: var(--muted); font: 11px var(--mono); }}
.ylab {{ text-anchor: end; }}
.xlab {{ text-anchor: middle; }}
.area {{ fill: var(--warn-soft); stroke: none; }}
.line {{ fill: none; stroke: var(--warn); stroke-width: 2; }}
.dot {{ fill: var(--warn); }}
.endlab {{ fill: var(--fg); font: 600 13px var(--mono); text-anchor: end; }}
.scroll {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
th, td {{ padding: 9px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); }}
tbody tr:last-child td {{ border-bottom: 0; }}
thead th {{ font: 600 12px/1.2 var(--body); color: var(--muted); text-transform: uppercase; letter-spacing: .05em; background: var(--surface); position: sticky; top: 0; }}
.num {{ font-family: var(--mono); font-size: 13.5px; text-align: right; white-space: nowrap; }}
th.num {{ text-align: right; }}
.mono, .dt {{ font-family: var(--mono); font-size: 13px; white-space: nowrap; }}
td.who {{ min-width: 200px; }}
.role {{ font-size: 13px; color: var(--muted); }}
td.bar {{ width: 40%; min-width: 120px; vertical-align: middle; }}
td.bar span {{ display: block; height: 10px; border-radius: 2px; background: var(--warn); opacity: .85; }}
tr.unk td.bar span {{ background: repeating-linear-gradient(45deg, var(--warn) 0 4px, transparent 4px 8px); }}
td.bar span.b-coding {{ opacity: .6; }}
td.bar span.b-none {{ opacity: .35; }}
tr.tier th {{ background: var(--bg); padding: 10px 12px; border-bottom: 1px solid var(--line); text-transform: none; letter-spacing: 0; position: static; }}
.tier-sum {{ float: right; font: 500 13.5px var(--mono); color: var(--fg); }}
.ev {{ display: inline-block; font: 500 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .05em; padding: 4px 6px; border-radius: 4px; white-space: nowrap; }}
.ev.sm {{ font-size: 10px; padding: 3px 5px; margin-left: 4px; vertical-align: 1px; }}
.ev-named {{ background: var(--accent-soft); color: var(--accent); }}
.ev-coding {{ border: 1px solid var(--muted); color: var(--muted); }}
.ev-none {{ border: 1px dashed var(--warn); color: var(--warn); }}
.ev-unk {{ background: var(--warn-soft); color: var(--warn); }}
.evkey {{ display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }}
.evkey li {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: nowrap; }}
.evkey li > .ev {{ flex: none; }}
.evkey li > span:last-child {{ flex: 1; min-width: 0; }}
@media (max-width: 480px) {{ .evkey li {{ flex-wrap: wrap; }} }}
.commit td:first-child {{ min-width: 220px; }}
.commit .amount {{ font: 500 15px var(--mono); white-space: nowrap; }}
.walk .amount {{ font: 500 15px var(--mono); white-space: nowrap; text-align: right; }}
.walk th:nth-child(2) {{ text-align: right; }}
.walk tr.bl-total td {{ border-top: 2px solid var(--line); }}
.status {{ display: inline-block; font: 500 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .05em; padding: 4px 6px; border-radius: 4px; white-space: nowrap; }}
.status.auth {{ background: var(--accent-soft); color: var(--accent); }}
.status.cont {{ border: 1px solid var(--muted); color: var(--muted); }}
.status.none {{ background: var(--warn-soft); color: var(--warn); }}
.flow {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.flow > div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px; display: grid; gap: 8px; align-content: start; min-width: 0; }}
.flow .now {{ border-color: var(--warn); }}
.flow ul, .notes {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; }}
.tools {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
.tools input {{ font: inherit; padding: 8px 12px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--fg); width: min(100%, 340px); }}
tr.hide {{ display: none; }}
.ledger {{ max-height: 560px; overflow: auto; }}
.tp-watch {{ background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--warn); border-radius: 8px; padding: 16px 20px; display: grid; gap: 10px; }}
.tp-watch ul {{ margin: 0; padding-left: 20px; display: grid; gap: 8px; }}
.tp-facts {{ display: grid; grid-template-columns: max-content 1fr; gap: 10px 18px; margin: 0; }}
.tp-facts dt {{ font: 500 12px/1.7 var(--mono); text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }}
.tp-facts dd {{ margin: 0; min-width: 0; }}
.small {{ font-size: 13.5px; }}
@media (max-width: 560px) {{ .tp-facts {{ grid-template-columns: 1fr; gap: 2px; }} .tp-facts dd {{ margin-bottom: 10px; }} }}
footer {{ font-size: 13px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 16px; }}
.sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }}
@media (max-width: 640px) {{
  .wrap {{ padding-inline: 16px; padding-block: 28px 48px; gap: 36px; }}
  .flow {{ grid-template-columns: 1fr; }}
  /* chart: swap to the version drawn for narrow screens */
  .figure {{ padding: 10px; }}
  .figure .chart-wide {{ display: none; }}
  .figure .chart-narrow {{ display: block; min-width: 0; }}
  /* text tables become stacked cards, one per row, each cell labeled with its column name */
  .scroll:has(> table.commit) {{ overflow: visible; border: 0; background: none; }}
  table.commit, table.commit tbody, table.commit tr, table.commit td {{ display: block; width: auto; }}
  table.commit thead {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }}
  table.commit tr {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 6px 14px; margin-bottom: 10px; }}
  table.commit td {{ border-bottom: 1px solid var(--line); padding: 8px 0; min-width: 0 !important; text-align: left; }}
  table.commit td:last-child {{ border-bottom: 0; }}
  .walk td, .walk th {{ padding: 6px 5px; font-size: 13.5px; }}
  .walk .amount {{ font-size: 13.5px; }}
  table.commit td[data-label]::before {{ content: attr(data-label); display: block; font: 600 11px/1.3 var(--body); text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin-bottom: 2px; }}
  /* who was paid: drop the bar column */
  .payees-t .bar {{ display: none; }}
  .payees-t td.who {{ min-width: 0; }}
  /* ledger: keep date, payee, amount, source */
  .ledger .opt {{ display: none; }}
  .ledger table {{ font-size: 13px; }}
  .ledger th, .ledger td {{ padding: 7px 5px; }}
  .ledger td.dt, .ledger .num {{ font-size: 12px; }}
  .ledger td.dt {{ white-space: normal; min-width: 50px; }}
  .ledger .ev.sm {{ display: block; width: fit-content; margin: 3px 0 0; white-space: normal; }}
  .ledger td a {{ overflow-wrap: anywhere; }}
  .ledger thead th {{ white-space: normal; letter-spacing: .02em; }}
}}
.toc {{ display: grid; gap: 6px; font-size: 14px; padding-top: 4px; }}
.toc div {{ display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: baseline; }}
.toc b {{ font: 500 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .08em; color: var(--muted); min-width: 9.5em; }}
tr.who-group td {{ background: var(--accent-soft); font: 500 12px/1.4 var(--mono); text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding-top: 14px; }}
tr.unpaid td.num {{ font-size: 13px; color: var(--muted); white-space: normal; }}
.lastdoc {{ white-space: nowrap; }}
.group {{ border-top: 2px solid var(--fg); padding-top: 10px; margin-bottom: -24px; scroll-margin-top: 16px; }}
.group:empty {{ margin-bottom: -30px; }}
.group span {{ font: 500 12px/1 var(--mono); text-transform: uppercase; letter-spacing: .1em; color: var(--muted); }}
#bottom-line {{ display: grid; gap: 12px; }}
.toc a {{ text-decoration: none; border-bottom: 1px solid var(--line); }}
.toc a:hover {{ border-color: var(--accent); }}
section[id], #board-votes .sub {{ scroll-margin-top: 16px; }}
{votes_css}
</style>

<main class="wrap">
  <header class="prose">
    <div class="eyebrow">Citizen research · compiled from Town of Nederland public records</div>
    <h1>Nederland's Eldora acquisition: summary, costs, and where the money is coming from</h1>
    <p class="lede">As of the {asof} warrant list, the Town had paid <strong>{balance_c}</strong> in Eldora acquisition costs, mostly to <a href="#payees">lawyers and consultants</a>, all charged to its General Fund as money it expects to recover from <a href="#commitments">revenue bonds</a> if the purchase closes. The <a href="#no-sale">purchase agreement expired</a> in April 2026, and no bonds have been sold; the Town says it is pursuing a <a href="#revised-plan">restructured deal</a>. If the sale doesn't close, the Town estimates it would owe <a href="#bottom-line">about $2.5 million in all</a>, paid from its <a href="#csafe">CSAFE investments</a>; it hasn't itemized that estimate, and <a href="#no-limits">no budget or dollar limit</a> covers the costs. By this page's calculation, if the sale fails in 2026, the General Fund would end the year <a href="#gf-tables">{fb_end_m} below zero</a>. This page compares those amounts with the <a href="#afford">Town's finances</a>, lists what the <a href="#open-questions">records searched don't show</a>, and records every <a href="#board-votes">Board vote on the acquisition</a>, each unanimous among the trustees present.</p>
    <p class="disclaimer">This is an independent compilation, not affiliated with, endorsed by, or produced by the Town of Nederland, Eldora Mountain Resort, or POWDR. It is built from the Town's own public records: Board of Trustees meeting records from {cov_from} through {cov_through} on the Town's CivicWeb portal; resolutions, ordinances, finance documents, and staff reports from all years; posts on the Town website; and Town records released in response to a public records request. Statements that something isn't in the records refer only to the records searched (see <a href="#method-ai">How this research was done</a>). Last updated {cov_updated}; the page is updated about once a month, and sooner when there is significant news. Corrections are welcome: <a href="mailto:corrections@eldorarecord.org">corrections@eldorarecord.org</a>.</p>
    <aside class="statement" id="statement" aria-label="Statement from the researcher">
      <b>Why I made this page</b>
      <p>I built this page as a byproduct of researching the Town of Nederland's public records, available on the Town website and its CivicWeb portal of official Town documents. Like many residents, my opinions on the Eldora acquisition have fluctuated and evolved over time. But from day one I have been worried about the cost of the acquisition process itself and the financial risk to the Town if the deal didn't go through, since the due-diligence costs would be repaid from bond proceeds only if the sale closed. So I have tried to do objective research, based only on the Town's records, to explain how much the acquisition process has and will cost and how much financial risk it poses to the Town. I hope this page's careful accounting, and its summary of information scattered across thousands of documents, can help us figure out the best path forward.</p>
      <p><strong>My opinions about what will happen and what the Town should do are on <a href="{site}opinion.html">a separate page</a>, so that they stay apart from the record.</strong></p>
      <p class="sig">— Dallas Masters, Nederland resident · Questions and corrections: <a href="mailto:corrections@eldorarecord.org">corrections@eldorarecord.org</a></p>
    </aside>
    <nav class="toc" aria-label="On this page">
      <div><b>Overview</b><a href="#findings-h">Findings</a><a href="#in-brief">The acquisition in brief</a></div>
      <div><b>The money</b><a href="#costs">Spent</a><a href="#commitments">Committed</a><a href="#no-sale">If the sale fails</a><a href="#afford">Can the Town absorb it?</a></div>
      <div><b>Records and statements</b><a href="#open-questions">Not in the records searched</a><a href="#board-knowledge">Cost information</a><a href="#town-statements">What the Town said</a></div>
      <div><b>Get involved</b><a href="#get-involved">How to get involved</a></div>
      <div><b>Reference</b><a href="#ledger">Payments</a><a href="#board-votes">Votes</a><a href="#changes">Changelog</a><a href="#method-ai">How this was built</a></div>
    </nav>
    {latest}
  </header>

  <div class="facts">
    <div class="fact spent"><span class="tag paid">Already paid</span><b>{balance}</b><span>Charged to the <a href="#funding">General Fund</a> through the <a href="#ledger">{asof} warrant list</a></span></div>
    <div class="fact spent"><span class="tag paid">Not yet paid</span><b>~{unpaid_short}</b><span>The Town's <a href="#bottom-line">$2.5M estimate</a> minus <a href="#costs">what is already paid</a>, if the estimate includes it</span></div>
    <div class="fact"><span class="tag auth">Expired</span><b>$120M</b><span>Purchase price in the <a href="#commitments">agreement approved Jan 6, 2026</a></span></div>
    <div class="fact spent"><span class="tag paid">If the sale fails</span><b>~$2.5M</b><span>The Town's estimate of <a href="#bottom-line">transaction costs it would owe</a>, to be paid from <a href="#csafe">CSAFE investments</a> (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sep 30, 2026</a>)</span></div>
  </div>

  <section class="findings" aria-labeledby="findings-h">
    <h2 id="findings-h">Summary of findings based on records searched</h2>
    <ol>
      <li><strong>The Town has <a href="#costs">paid {balance}</a>, all charged to its <a href="#funding">General Fund</a>.</strong> It is recorded as money owed back to the Town, intended to be repaid from <a href="#commitments">revenue bonds</a> that have not been sold. The <a href="#no-sale">purchase agreement has expired</a>, but the Town says it is still pursuing the deal with a <a href="#revised-plan">restructured plan</a> (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>).</li>
      <li><strong>If the sale fails, the Town estimates it would owe <a href="#bottom-line">about $2.5 million in all</a> (<a href="#per-household">{hh_est} per household</a>), paid from its <a href="#csafe">CSAFE investments</a>.</strong> CSAFE holds pooled cash for all Town funds, most of it restricted to other purposes. By this page's calculation from the 2025 audit, the General Fund's own share was about $0.70 million at the end of 2025, less than it has paid since (<a href="#pay-rest">Could the Town pay the rest?</a>). If that estimate includes what has been paid, about {unpaid} is still to be paid. By this page's calculation, if the sale fails in 2026, the General Fund would end the year about <a href="#gf-tables">{fb_end_m} below zero</a>. This page also calculates that $2.5 million equals <a href="#gf-recovery">{yrs_est} years of the General Fund's average annual gains</a> in 2017–2023. The General Fund's balance fell in 2024 and 2025, and the adopted 2026 budget projects a further decline (<a href="#gf-recovery">audits</a>, <a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>).</li>
      <li><strong>No budget covers the acquisition costs, and every Board vote on the acquisition was unanimous among the trustees present.</strong> <a href="#no-limits">Neither the 2025 nor the 2026 budget includes them</a>. The warrant lists the Board approved <a href="#running-total">showed the listed payments and the account's running balance</a>. The balance also included {unlisted} added between lists (see <a href="#payees">Who was paid</a>). Those were <a href="#board-votes">{n_actions} decisions and {n_sessions} votes to meet in closed session</a> since {first_es}.</li>
      <li><strong>Lawyers and consultants received most of the money.</strong> The <a href="#payees">largest payees</a> are {top}. {named} went to firms whose role in the Eldora acquisition is stated in a Board document (a resolution, staff memo, or the purchase agreement); {coding} to regular Town vendors linked to the acquisition only by the Town's account coding; and {none} to firms that appear in no Board document searched except the warrant lists. The delegation resolutions authorized the Town Manager to engage legal counsel and "additional consultants, as necessary," and <a href="#no-limits">set no dollar limits</a> (Res. 2025-16, 2025-19, 2025-22). The purpose of <a href="#payee-powdr">POWDR's three invoices</a> isn't stated in the records searched.</li>
      <li><strong>The Town hasn't itemized its <a href="#bottom-line">$2.5 million estimate</a>.</strong> The Sept. 30, 2026, update gives that total for the transaction-related costs the Town would owe if the sale doesn't close, but it gives no breakdown and doesn't say whether the total includes the {balance} already paid (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>). If it does, about {unpaid} has not yet appeared on a warrant list, and the records searched don't show which firms or contracts it covers. <a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a> says "some contracts are contingent on successful closing of the transaction, while others will need to be paid regardless of closing," and points readers to the warrant lists for individual payments. Residents <a href="#questions">asked for a breakdown of costs</a> in July 2026. An Oct. 20, 2026, staff memo refers to "outstanding financial obligations," including "certain costs that are contingent upon the successful completion of the transaction," without listing them, and says staff will review Eldora-related expenditures at the Nov. 5, 2026, budget work session (<a href="https://nederlandco.civicweb.net/document/132785/" target="_blank" rel="noopener">Oct. 20 memo</a>).</li>
    </ol>
    <p class="prose muted">Gaps in the records are listed under <a href="#open-questions">Not in the records searched</a>, with the records that could fill them.</p>
  </section>

  <section id="in-brief" class="prose">
    <h2>The acquisition in brief</h2>
    <p>POWDR put Eldora Mountain Resort, the ski area just west of Nederland, up for sale in 2024. The Town plans to buy it through a new Town-owned business, the Mountain Recreation Enterprise, and pay with <a href="#funding">revenue bonds repaid only from the resort's income</a>, not taxes. Its stated reasons are local control and <a href="#profit">long-term revenue</a> (<a href="https://nederlandco.civicweb.net/document/118506/" target="_blank" rel="noopener">Ord. 873</a>, <a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0</a>), including "addressing recurring budget shortfalls through a more stable revenue base" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a>). The plan is being restructured (<a href="#revised-plan">see below</a>).</p>
    <ol class="steps">
      <li><strong>July 2025:</strong> <a href="#town-statements">non-binding term sheet</a> signed with POWDR (<a href="https://web.archive.org/web/20250709224556/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-30" target="_blank" rel="noopener">FAQ 3.0</a>).</li>
      <li><strong>January 2026:</strong> Board approved <a href="#commitments">a $120 million purchase and up to $225 million in bonds</a> (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">Ord. 882</a>, <a href="https://nederlandco.civicweb.net/document/127180/" target="_blank" rel="noopener">Ord. 885</a>).</li>
      <li><strong>April 30, 2026:</strong> the purchase agreement's <a href="#no-sale">closing deadline passed without a closing</a> (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §7.1(d)</a>, <a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a>).</li>
      <li><strong>July 19, 2026:</strong> the Board's <a href="#commitments">authority to sell the bonds ran out</a> with no bonds sold (<a href="https://nederlandco.civicweb.net/document/127180/" target="_blank" rel="noopener">Ord. 885 §5(c)</a>).</li>
      <li><strong>September 30, 2026:</strong> the Town said the agreement had expired but it is still pursuing the purchase with <a href="#revised-plan">restructured financing</a> (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>).</li>
    </ol>
    <p id="revised-plan"><strong>Where things stand.</strong> No purchase agreement is in force. The Town remains bound by its January 2025 confidentiality agreement with POWDR, and a few terms of the expired agreement continue, including that <a href="#no-sale">each side pays its own costs</a> (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §7.2, §8.2</a>). The Town's September 30 update describes a revised plan: a "sale-leaseback structure tied to the asset," less debt, and <a href="#commitments">about $20 million in philanthropy</a> for capital projects, with the State of Colorado the first potential contributor, "at the beginning stages" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>). An overview dated Oct. 16, 2026, in the Oct. 20 Board packet describes the structure. At closing, the Enterprise would transfer legal title to the land and improvements to the bond trustee, which would lease the resort back to the Enterprise to operate. If the bonds defaulted, the trustee could exercise the remedies in the financing documents "without first completing a traditional foreclosure process," and "those remedies could affect who operates or leases the resort." Title would return to the Enterprise once the bonds are paid (<a href="https://nederlandco.civicweb.net/document/132788/" target="_blank" rel="noopener">sale-leaseback overview</a>). An Oct. 20 staff memo says the Town is pursuing the purchase "at the previously negotiated purchase price of $120 million" and exploring "revenue bonds, governmental grants, foundation funding, and private contributions." It says this work "is primarily being performed by the Mayor" and that "the Town is not paying outside consultants to perform this work" (<a href="https://nederlandco.civicweb.net/document/132785/" target="_blank" rel="noopener">Oct. 20 memo</a>). Stifel's advisory agreement, extended in July 2026, covers municipal leases as well as bonds (<a href="https://nederlandco.civicweb.net/document/130472/" target="_blank" rel="noopener">agreement</a>). The Town Manager resigned in August 2026, and the Town's previous Town Manager returned as interim Town Manager on Sept. 25, 2026 (<a href="https://nederlandco.civicweb.net/document/132381/" target="_blank" rel="noopener">Aug. 18 minutes, p. 4</a>); her contract runs through Feb. 28, 2027, and recruiting a permanent Town Administrator is expected to begin after the 2027 budget is developed (<a href="https://nederlandco.civicweb.net/document/132750/" target="_blank" rel="noopener">Oct. 20 report</a>, <a href="https://nederlandco.civicweb.net/document/132766/" target="_blank" rel="noopener">reply to public comment</a>). Not in the records searched: the lease terms, a new bond amount, and any pledges. A new agreement, lease, or bond ordinance would each need Board approval at a public meeting.</p>
  </section>

  <div class="group" id="money"><span>The money</span></div>
  <section id="costs">
    <h2>What has been spent</h2>
    <p class="prose muted">The Town records Eldora acquisition invoices in one General Fund account, <span class="mono">10-00-1150</span>, "Due From," as money it expects to get back. The chart shows that account's running balance after each warrant list approved by the Board. The account first appears in October 2025, with invoices dated from August 2025. Earlier invoices, dated from January 2025, were later moved into it (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>).</p>
    <div class="figure">{chart}</div>
    <h3 id="payees">Who was paid</h3>
    <p class="prose muted">{n} payments on Board warrant lists add up to {listed}. The other {unlisted} was added to the account between warrant lists. The Town's ledger for the account, released in response to a public records request (<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>) and posted for 2026 in the Oct. 20, 2026, Board packet (<a href="https://nederlandco.civicweb.net/document/132789/" target="_blank" rel="noopener">Oct. 20 packet copy</a>), names each amount: {moved} in legal and professional-services invoices first paid on earlier warrant lists from other budget lines and later moved into the account, and a $50,000 POWDR invoice dated Jan. 6, 2026, that is on no warrant list. These amounts are included below.</p>
    <p class="prose">No invoice line names Eldora; the warrant lists give only the account. Each payee was checked against the other records searched and rated by whether a Board document states its role in the Eldora acquisition.</p>
    <ul class="evkey prose">
      <li><span class="ev ev-named">Named in Board documents</span><span>A resolution, staff memo, or the purchase agreement states this firm's role in the Eldora acquisition. Total {named}.</span></li>
      <li><span class="ev ev-coding">Account coding only</span><span>A regular Town vendor. Its other Town work is billed to normal budget lines in the same months, and only the Town's account coding links these charges to the Eldora acquisition. Total {coding}.</span></li>
      <li><span class="ev ev-none">No other record</span><span>Appears in no Board document searched except the warrant lists. Total {none}.</span></li>
    </ul>
    <div class="scroll"><table class="payees-t">
      <thead><tr><th scope="col">Firm</th><th scope="col" class="bar"><span class="sr">Share</span></th><th scope="col" class="num">Paid</th></tr></thead>
      <tbody>{vendors}</tbody>
    </table></div>
  </section>

  <section id="commitments">
    <h2>Commitments and how they'd be paid</h2>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Item</th><th scope="col">Amount</th><th scope="col">Status</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>Purchase price (no deposit; closing depended on selling the bonds)</td><td class="amount">$120,000,000</td><td><span class="status none">Expired</span></td><td><a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">Ord. 882, APA §2.5</a></td></tr>
        <tr><td>Series 2026 revenue bonds (up to 40 years, at most 9%); had to be sold by about July 19, 2026</td><td class="amount">up to $225,000,000</td><td><span class="status none">Lapsed</span></td><td><a href="https://nederlandco.civicweb.net/document/127180/" target="_blank" rel="noopener">Ord. 885 §5(c)</a></td></tr>
        <tr><td>Expected bond amount when the Board declared its intent to repay early costs from the bonds</td><td class="amount">$180,000,000</td><td><span class="status auth">Declared</span></td><td><a href="https://nederlandco.civicweb.net/document/123060/" target="_blank" rel="noopener">Res. 2025-17</a></td></tr>
        <tr><td>Planned philanthropy for capital projects, kept outside the bond debt</td><td class="amount">~$20,000,000</td><td><span class="status cont">Planned</span></td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sep 30, 2026 update</a></td></tr>
        <tr><td>Stifel financial-advisor fee, paid from bond proceeds</td><td class="amount">$325,000</td><td><span class="status cont">If bonds sell</span></td><td><a href="https://nederlandco.civicweb.net/document/130471/" target="_blank" rel="noopener">Jul 7, 2026 memo</a></td></tr>
        <tr><td>Emergency spending authority to run the resort after a closing (not for due diligence); ran 120 days from April 21, 2026</td><td class="amount">No dollar limit</td><td><span class="status none">Lapsed</span></td><td><a href="https://nederlandco.civicweb.net/document/129046/" target="_blank" rel="noopener">Res. 2026-13</a></td></tr>
        <tr id="no-limits"><td>Eldora acquisition costs in the 2025 and 2026 Town budgets; the 2026 budget "does not include sufficient appropriations." The costs don't appear as expenditures in the monthly financial and treasurer reports searched (<a href="https://nederlandco.civicweb.net/document/131731/" target="_blank" rel="noopener">July 2026 financials</a>).</td><td class="amount">$0</td><td><span class="status none">Not budgeted</span></td><td><a href="https://nederlandco.civicweb.net/document/129045/" target="_blank" rel="noopener">Apr 21, 2026 memo</a></td></tr>
        <tr><td>Dollar limit in the resolutions delegating authority to hire counsel and consultants; the last two let the Town Manager hire "additional consultants, as necessary"</td><td class="amount">None</td><td><span class="status none">No limit</span></td><td>Res. 2025-03, 2025-11, <a href="https://nederlandco.civicweb.net/document/123040/" target="_blank" rel="noopener">2025-16</a>, <a href="https://nederlandco.civicweb.net/document/123794/" target="_blank" rel="noopener">2025-19</a>, <a href="https://nederlandco.civicweb.net/document/124849/" target="_blank" rel="noopener">2025-22</a></td></tr>
      </tbody>
    </table></div>
    <h3 id="funding">Where the money comes from</h3>
    <p class="prose">Every Eldora acquisition bill to date was charged to the General Fund and paid from the Town's pooled cash (see <a href="#csafe">CSAFE</a>), recorded in the <a href="#costs">"Due From" account</a> as money owed back to the Town. Res. 2025-17 states the intent to repay it from bond proceeds, and the August 2025 legal-counsel memo says those legal fees would be "funded from the bond issuance proceeds." The bonds would pay for the purchase, improvements, reserves, early interest, and issuance costs, and repay the Town's early costs; no taxes or General Fund money are pledged (Ord. 885). The financing is being restructured (<a href="#revised-plan">where things stand</a>). In January 2025 the Board approved sending Great Outdoors Colorado a letter of interest about a possible grant (<a href="https://nederlandco.civicweb.net/document/118545/" target="_blank" rel="noopener">minutes</a>); no award appears in the records searched.</p>
  </section>

  <section id="no-sale">
    <h2>If the sale doesn't go through</h2>
    <div id="bottom-line" class="bottom-line">
      <h3>The bottom line</h3>
    <div class="scroll"><table class="commit bl">
      <thead><tr><th scope="col">&nbsp;</th><th scope="col">Amount</th><th scope="col">What it is</th></tr></thead>
      <tbody>
        <tr><td><strong>Already paid</strong></td><td class="amount">{balance}</td><td>Charged to the General Fund through the {asof} warrant list, including {powdr} to POWDR.</td></tr>
        <tr><td><strong>Owed, not yet paid</strong></td><td class="amount">about {unpaid}</td><td>The Town's estimate minus what is paid. The Town hasn't itemized it.</td></tr>
        <tr class="bl-total"><td><strong>Total</strong></td><td class="amount">about $2.5 million</td><td>The Town's estimate, to be paid from CSAFE investments (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sept. 30, 2026, update</a>).</td></tr>
        <tr><td><strong>Owed only if the deal closes</strong></td><td class="amount">$0 if it fails</td><td>The purchase price, Stifel's $325,000 fee, and bond issuance costs. The Northland and Res. 2025-11 memos describe underwriter fees as depending on a bond issue; the current underwriters' terms aren't in the records searched.</td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">The Town doesn't say whether its $2.5 million includes the {balance} already paid. This page assumes it does; if not, the total would be about {alt_total}. Earlier Eldora work is included only where the Town moved it into the account (see <a href="#figures">About these figures</a>).</p>
    </div>
    <h3>What happens to the costs</h3>
    <p class="prose">No Board vote or budget covers Eldora acquisition costs if the purchase fails. The Town addressed it in FAQ 7.0 (July 2026) and its Sept. 30, 2026, update.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Finding</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td><strong>Some costs are owed either way.</strong> FAQ 7.0 (July 2026) said "some contracts are contingent on successful closing... others will need to be paid regardless," and that the Town's reserves are "sufficient to cover the current expenses."</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sep 30, 2026 update</a>, <a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a></td></tr>
        <tr><td><strong>Each side pays its own costs whether or not the sale closes.</strong> That includes legal, accounting, investment-banking, and consultant fees.</td><td><a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">Asset Purchase Agreement §8.2</a></td></tr>
        <tr><td><strong>The risk of owing the seller's costs ended with the agreement.</strong> It applied only if every condition was met and the Town then did not close; the records searched don't show that occurring. It would return only under a new agreement with the same terms. Each side still pays its own costs (§8.2), and either can claim damages for a breach before the agreement ended (§7.2(a)(ii)); no record searched shows such a claim. [[corrected:2026-10-11]]</td><td><a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §7.1(f), §7.2(a)</a></td></tr>
        <tr><td><strong>The purchase agreement has expired.</strong> The Town says talks with POWDR "remain active" and it expects to negotiate updated agreements "if the financing proceeds." Selling bonds would require a new purchase agreement and a new or amended bond ordinance, because the authority under <a href="https://nederlandco.civicweb.net/document/127180/" target="_blank" rel="noopener">Ord. 885 §5(c)</a> lapsed on July 19, 2026 (see <a href="#revised-plan">where things stand</a>). [[corrected:2026-10-11]]</td><td><a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §7.1(d)</a>, <a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sept. 30 update</a></td></tr>
        <tr><td><strong>Under the draft agreement, the Town's share of Ikon negotiation costs doesn't depend on closing.</strong> The Town would pay 50% of the fees Alterra incurs negotiating the Ikon agreement, if Alterra requests reimbursement (§4.4(b)); ending the agreement refunds nothing already paid (§7.2), and there is no deposit. The records searched don't show whether any such fees have been paid.</td><td><a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §4.4(b), §7.2, §8.2</a></td></tr>
        <tr><td><strong>The documents searched don't say how costs would be paid if no bonds are issued.</strong> Res. 2025-17 only "preserves the option" of repayment from the bonds; payments not funded by the bonds depend on yearly budget votes; and if the purchase fails, the enterprise fund "can be retired," with nothing saying who absorbs money already spent.</td><td><a href="https://nederlandco.civicweb.net/document/123059/" target="_blank" rel="noopener">Res. 2025-17 memo</a>, <a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §10.16</a>, <a href="https://nederlandco.civicweb.net/document/118505/" target="_blank" rel="noopener">Ord. 873 memo</a></td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">The agreement terms in this table come from the draft in the January 6, 2026, Board packet. Res. 2026-07 and 2026-09 state that the Town entered into the agreement, but the signed version isn't in the Board records searched and may differ.</p>
  </section>

  <section id="afford">
    <h2>Can the Town absorb it?</h2>
    <p class="prose">In the accounts, the costs are carried by the General Fund, the Town's general operating fund. This section compares the costs with the Town's households, funds, and budgets.</p>
    <h3 id="pay-rest">Could the Town pay the rest?</h3>
    <p class="prose">If the Town's $2.5 million estimate includes what it has already paid, about {unpaid} more would be owed if the sale fails; if it doesn't, the full $2.5 million would be owed on top of what has been paid. The records searched answer only part of whether the Town could pay it. The cash exists: the Town's pooled cash and investments totaled $7,154,592 at the end of 2025, including $2,821,014 in CSAFE (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>). But most of it belongs to funds restricted to the utilities, the Downtown Development Authority, the community center, and streets and parks. The General Fund is the only fund that could pay these costs, and only with a Board appropriation, since neither the 2025 nor the 2026 budget includes them (<a href="#csafe">the Town's funds</a>, <a href="#no-limits">budgets</a>). By this page's calculation, the General Fund's own share of the pool was about $698,751 at the end of 2025, and it has since paid {since_2025} in Eldora acquisition costs, more than that share; the records searched don't show its current position. This page's reading is that paying {unpaid} more would draw on pooled cash belonging to other funds, and that writing off the costs already paid as well would leave the General Fund's balance about $1.5 million below zero, or {fb_end_m} below zero with the projected 2026 deficit (<a href="#gf-tables">tables below</a>). The records searched don't show the current balances, whether other funds' money may legally carry these costs (a question for the Town attorney or auditor), what the {unpaid} consists of or when it would be due, or which reserves FAQ 7.0 called "sufficient." Staff plan to review Eldora-related expenditures and the FY2026 and FY2027 budgets at the Nov. 5, 2026, budget work session (<a href="https://nederlandco.civicweb.net/document/132785/" target="_blank" rel="noopener">Oct. 20 memo</a>).</p>
    <div class="scroll" id="gf-tables"><table class="walk">
      <thead><tr><th scope="col">General Fund cash</th><th scope="col">Amount</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>Cash at the end of 2025 (a "negative cash balance")</td><td class="amount">−$757,482</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a></td></tr>
        <tr><td>Owed by other funds at the end of 2025, if fully repaid in 2026</td><td class="amount">+$1,456,233</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a></td></tr>
        <tr><td>Eldora acquisition payments since the last 2025 warrant list</td><td class="amount">−{since_2025}</td><td><a href="#ledger">warrant lists</a></td></tr>
        <tr><td>Rest of the Town's estimate, if paid in 2026</td><td class="amount">−{unpaid_x}</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sept. 30, 2026, update</a></td></tr>
        <tr class="bl-total"><td><strong>Before the General Fund's other 2026 income and spending</strong></td><td class="amount">{cash_end}</td><td>This page's calculation</td></tr>
      </tbody>
    </table></div>
    <p class="prose" id="receivable"><strong>Why the fund balance can look healthier than the cash.</strong> When the Town pays an Eldora acquisition bill from the General Fund, the cash leaves either way, but the books can record the payment in one of two ways. Recorded as spending, it reduces the General Fund's balance right away. Recorded as a receivable, it counts as money the Town expects to get back, so the balance on paper doesn't change, much like a personal loan that hasn't been repaid yet. The Town's account name, "Due From," and its ledger title, "Eldora - reimbursable expenses," suggest the {balance} paid so far is carried as a receivable, to be repaid from bond proceeds if the purchase closes; the Town hasn't said so directly. The records are consistent with that reading. The 2025 audit shows the General Fund's "other receivables" rising from $6,431 to $520,055 during 2025, without itemizing them, while the account reached {bal_2025} on the warrant lists ($504,396 in the Town's ledger, which includes 2025 invoices paid in 2026; <a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>). [[corrected:2026-10-13]] In 2026 the account grew by $772,243 through July, while the General Fund's balance fell only $159,439 (<a href="https://nederlandco.civicweb.net/document/131731/" target="_blank" rel="noopener">July 2026 report</a>). If the sale fails, there is no bond money to repay the Town, and the receivable would be written off.</p>
    <div class="scroll"><table class="walk">
      <thead><tr><th scope="col">General Fund balance</th><th scope="col">Amount</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>Balance at the end of 2025</td><td class="amount">$1,030,078</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a></td></tr>
        <tr><td>Change projected in the adopted 2026 budget</td><td class="amount">{bud_change}</td><td><a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a></td></tr>
        <tr><td>Write-off of the {balance} paid, plus the rest of the Town's estimate</td><td class="amount">−$2,500,000</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sept. 30, 2026, update</a></td></tr>
        <tr class="bl-total"><td><strong>End of 2026</strong></td><td class="amount">{fb_end}</td><td>This page's calculation</td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">Both tables are this page's calculations. They assume the sale fails and everything is paid in 2026, that the Town's $2.5 million includes what it has already paid, and, for the balance, that the costs are carried as a receivable. If the estimate doesn't include what has been paid, both results are about {balance} lower. Repayment by other funds turns money owed into cash; it doesn't change the fund balance. A budgeted deficit isn't the same as a change in cash.</p>
    <h3 id="gf-deficit">If the General Fund ends in deficit</h3>
    <p class="prose">The General Fund has already relied on other funds' cash: the 2025 audit reports its "negative cash balance of $757,482" as accounts payable, covered by the Town's pooled cash (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>). Colorado law sets the rules a deficit would face. A local government's budget may not "provide for expenditures in excess of available revenues and beginning fund balances," and no one may spend or contract to spend "in excess of the amounts appropriated" (<a href="https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-29.pdf" target="_blank" rel="noopener">C.R.S. 29-1-103(2), 29-1-110</a>). So paying these costs would need a Board appropriation, and a budget that starts from a deficit would have to close it with more revenue, less spending, or transfers. Under TABOR, the Town needs voter approval in advance for "any new tax, tax rate increase," or mill levy increase, and for any "multiple-fiscal year direct or indirect district debt or other financial obligation" not backed by cash reserves pledged for all future payments. The TABOR emergency reserve, $147,000 of the General Fund's balance, is "for declared emergencies only," and an emergency "excludes economic conditions, revenue shortfalls" (<a href="https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-00.pdf" target="_blank" rel="noopener">Colo. Const. art. X, §20(2)(c), (4), (5)</a>). At the General Fund's 2017–2023 average gain of {avg_op} to {avg_rep} a year, rebuilding about $1.9 million would take roughly {yrs_def} years (this page's calculation). That is a measure of scale, not a forecast: the General Fund's balance fell by $265,953 in 2024 and $192,241 in 2025, and the adopted 2026 budget projects a further decline of $446,348 (<a href="#gf-recovery">year by year</a>).</p>
    <p class="prose">The State Auditor's fiscal-health benchmark for counties and municipalities is an unrestricted General Fund balance of at least two months of expenditures, a ratio of 0.167, and it says a negative unrestricted balance "is not sustainable, and a government should address the situation as soon as possible" (<a href="https://content.leg.colorado.gov/sites/default/files/documents/audits/2129-13countyfiscalhealth2ndprintingoct2013final-0-1-accessible.pdf" target="_blank" rel="noopener">State Auditor, 2013, p. 13</a>). Nederland's ratio was about 0.26 at the end of 2025; if the sale fails in 2026, it would be about {ufb_2026} (this page's calculation). In the audits searched from 2008 through 2024, the General Fund appears as a lender to other funds, not a borrower; in 2008 it "temporarily covered the negative cash balances" of two other funds (<a href="https://nederlandco.civicweb.net/document/26065/" target="_blank" rel="noopener">2008 audit</a>), and 2025 is the first year an audit reports it with negative cash. The Town's formal loans between funds went to the Downtown Development Authority, authorized by Board resolution with repayment from the authority's tax increment revenue; one cites a 2012 election in which voters authorized borrowing up to $913,589, "repayable only from tax increment revenues" (<a href="https://nederlandco.civicweb.net/document/24440/" target="_blank" rel="noopener">Res. 2015-06</a>). The records searched don't show whether, or on what terms, each fund could lend to the General Fund, whether a loan between Town funds repaid over several years would need voter approval, or how the budget law's limit applies when a fund begins the year with a negative balance, which read literally could require closing the gap within one budget year; those are questions for the Town attorney or auditor.</p>
    <h3 id="per-household">Per household</h3>
    <p class="prose">Nederland has about 685 households (<a href="https://nederlandco.civicweb.net/document/132050/" target="_blank" rel="noopener">Sept. 15, 2026, packet</a>) and 1,471 residents (2020 Census, <a href="https://nederlandco.civicweb.net/document/132363/" target="_blank" rel="noopener">parks plan</a>). The {balance} paid so far is about {hh_paid} per household. The Town's $2.5 million estimate is about {hh_est} per household ({res_est} per resident), or about {hh_alt} if the estimate doesn't include what's already paid. No one would be billed these amounts; they only show scale. Sales tax is about 40% of the General Fund's budgeted 2026 revenue, not counting grants (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>).</p>
    <h3 id="csafe">The CSAFE investments and the Town's funds</h3>
    <p class="prose">CSAFE (the Colorado Surplus Asset Fund Trust) is a state-regulated investment pool that works like a money-market fund (C.R.S. 24-75-701). It is not set aside for any purpose. In March 2023 the Board approved investing "surplus funds... not immediately required to be disbursed" there (Res. 2023-16, on the consent agenda): $1.5 million then and $1 million more in January 2024. The Treasurer can withdraw "as funds are needed" without a new vote. The balance was $2,700,831 at the end of 2024 and $2,821,014 at the end of 2025 (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>); the monthly treasurer reports don't show its current balance.</p>
    <p class="prose">The Town pools its cash, so the CSAFE money belongs to every Town fund, not to one. Most of it comes from funds restricted by law or contract.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Fund (Dec 31, 2025)</th><th scope="col">Cash and investments</th><th scope="col">Money owed between funds</th><th scope="col">Can it pay Eldora acquisition costs?</th></tr></thead>
      <tbody>
        <tr><td>Water and Sewer (utility funds)</td><td class="amount">$4,150,620</td><td>Owes other funds $1,118,188</td><td><strong>Generally no.</strong> Utility revenue funds the utilities; $436,250 is classified as restricted.</td></tr>
        <tr><td>Downtown Development Authority</td><td class="amount">$1,695,802</td><td>None</td><td><strong>No.</strong> A separate authority's money for downtown.</td></tr>
        <tr><td>Community Center</td><td class="amount">$964,480</td><td>Owes other funds $158,347</td><td><strong>No.</strong> Restricted to the community center.</td></tr>
        <tr><td>Streets; Conservation Trust (parks)</td><td class="amount">$343,690</td><td>Owes other funds $179,698</td><td><strong>No.</strong> Restricted to roads, parks, and trails.</td></tr>
        <tr><td>General Fund</td><td class="amount">$0</td><td>Is owed $1,456,233 by other funds</td><td><strong>Yes, if the Board appropriates it.</strong> Its cash was negative: the audit says its "negative cash balance of $757,482" is "reported as accounts payable." $147,000 of its fund balance is restricted as the TABOR emergency reserve.</td></tr>
        <tr><td><strong>Total</strong></td><td class="amount"><strong>$7,154,592</strong></td><td>Amounts owed and amounts due are equal</td><td>The audit's total of deposits and investments, including the CSAFE investment, at year end.</td></tr>
      </tbody>
    </table></div>
    <p class="prose">If the other funds paid the General Fund the $1,456,233 they owed, and that covered its negative cash balance of $757,482, the General Fund would hold about $698,751 of the pooled cash and investments (this page's calculation). The audit expects the amounts owed to "clear after year end" but doesn't say how the negative balance would be settled. This is a year-end 2025 figure; for what has changed since, see <a href="#pay-rest">Could the Town pay the rest?</a></p>
    <p class="prose" id="fund-balance">The General Fund had a fund balance of $1,030,078 at the end of 2025, of which $872,173 was unassigned. That balance counts receivables as assets, which may include the Eldora acquisition costs (<a href="#receivable">see above</a>). The adopted 2026 budget already projected the balance falling to $583,730 by the end of 2026.</p>
    <p class="prose muted">Sources: <a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a> (balance sheets pp. 3 and 6; notes 3, 5, and 10), <a href="https://nederlandco.civicweb.net/document/44139/" target="_blank" rel="noopener">Mar 2023 memo</a>, <a href="https://nederlandco.civicweb.net/document/44144/" target="_blank" rel="noopener">Res. 2023-16</a>, <a href="https://nederlandco.civicweb.net/document/43689/" target="_blank" rel="noopener">Res. 2023-08</a>, <a href="https://nederlandco.civicweb.net/document/122108/" target="_blank" rel="noopener">2024 audit</a> (balance sheets pp. 3 and 6, investment note pp. 17–19), <a href="https://nederlandco.civicweb.net/document/128478/" target="_blank" rel="noopener">Dec 2025 financials</a>, <a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">2026 budget summary</a>. The amounts come from these records. Which funds can legally pay which costs is a reading of general Colorado law and accounting practice: TABOR, the rules for utility and Downtown Development Authority funds, and the audit's "restricted" classifications. The Town attorney or auditor would need to confirm it for these funds.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">What the records say</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td><strong>The CSAFE money isn't designated for the Eldora acquisition in any Board record searched.</strong> Neither the monthly treasurer reports nor the Board minutes mention a vote to use it for Eldora; the Town's September 2026 update is the only source found naming it.</td><td><a href="https://nederlandco.civicweb.net/document/131730/" target="_blank" rel="noopener">Treasurer report, Sep 2026</a></td></tr>
        <tr><td><strong>The treasurer's reports and the audit count cash differently.</strong> The treasurer's "combined bank balance, including CSAFE" fell from $5,273,959 (August 2025) to $4,324,024 (July 31, 2026), while the "Due From" account's balance rose to about $1.14 million. But that figure omits some accounts: for December 31, 2025, it shows $4,700,645, while the 2025 audit counts $7,154,592 in cash and investments. The records searched don't show how much of any change is due to Eldora.</td><td><a href="https://nederlandco.civicweb.net/document/123387/" target="_blank" rel="noopener">Aug 2025</a>, <a href="https://nederlandco.civicweb.net/document/131730/" target="_blank" rel="noopener">Sep 2026</a></td></tr>
      </tbody>
    </table></div>
    <h3 id="gf-recovery">The General Fund year by year</h3>
    <p class="prose muted">Its year-end results, from the audits:</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Year</th><th scope="col">Change in fund balance</th><th scope="col">Notes</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>2017–2021</td><td class="amount">+$149,593 to +$304,158 a year</td><td>Gains every year.</td><td><a href="https://nederlandco.civicweb.net/document/30606/" target="_blank" rel="noopener">2017</a>, <a href="https://nederlandco.civicweb.net/document/30605/" target="_blank" rel="noopener">2018</a>, <a href="https://nederlandco.civicweb.net/document/22779/" target="_blank" rel="noopener">2019</a>, <a href="https://nederlandco.civicweb.net/document/30306/" target="_blank" rel="noopener">2020</a>, <a href="https://nederlandco.civicweb.net/document/38114/" target="_blank" rel="noopener">2021</a> audits</td></tr>
        <tr><td>2022</td><td class="amount">+$83,265</td><td>Includes a $43,158 transfer in. Before it, +$40,107.</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/591/2022-Audit" target="_blank" rel="noopener">2022 audit</a></td></tr>
        <tr><td>2023</td><td class="amount">+$124,674</td><td>Includes $511,000 from the street equipment lease-purchase and a $106,155 transfer in. Before them, −$492,481.</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/593/2023-Audit" target="_blank" rel="noopener">2023 audit</a></td></tr>
        <tr><td>2024</td><td class="amount">−$265,953</td><td></td><td><a href="https://nederlandco.civicweb.net/document/122108/" target="_blank" rel="noopener">2024 audit</a></td></tr>
        <tr><td>2025</td><td class="amount">−$192,241</td><td>If the Eldora acquisition costs are carried as a receivable, they are not in this figure (this page's reading; see <a href="#receivable">receivables</a>). [[corrected:2026-10-13]]</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a></td></tr>
        <tr><td>2026 through July (unaudited)</td><td class="amount">−$159,439</td><td>The July 2026 financial report shows the balance at $814,332, down from $973,770 at the start of the year. (The audit puts the 2025 year-end balance at $1,030,078.)</td><td><a href="https://nederlandco.civicweb.net/document/131731/" target="_blank" rel="noopener">July 2026 report</a></td></tr>
        <tr><td>2026 (budget)</td><td class="amount">about −$446,000</td><td>The adopted budget projects the balance falling from $1,030,078 to $583,730.</td><td><a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a></td></tr>
      </tbody>
    </table></div>
    <p class="prose">From 2017 through 2023, the General Fund gained about {avg_rep} a year on average, or about {avg_op} without the 2023 lease proceeds. If every dollar of that went to the Eldora acquisition costs, rebuilding the Town's $2.5 million estimate would take roughly {yrs_est} years, and the {balance} already paid roughly {yrs_paid} years. The fund's balance fell in 2024 and 2025. For what a write-off would do to the fund's balance, see <a href="#gf-tables">Could the Town pay the rest?</a></p>
    <h3 id="scale">Compared with Town budgets and other spending</h3>
    <p class="prose muted">The Town's adopted 2026 budget plans about $9.4 million in spending across all funds, including about $2.25 million in grant-funded projects and the separate water, sewer, and downtown funds (<a href="https://nederlandco.civicweb.net/document/126174/" target="_blank" rel="noopener">Res. 2025-28</a>). The General Fund, which runs day-to-day Town government, spends about $3.2 million a year (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>).</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Comparison</th><th scope="col">Amount</th><th scope="col">Compared with Eldora acquisition costs</th></tr></thead>
      <tbody>
        <tr><td>General Fund operating spending, 2026 budget</td><td class="amount">$3.24 million</td><td>The {balance} paid equals about {pct_paid} of a year's General Fund operations. The $2.5 million estimate equals about {pct_est}.</td></tr>
        <tr><td>Boulder County Sheriff contract, the Town's largest single General Fund cost</td><td class="amount">about $1.05 million a year</td><td>The Eldora acquisition costs paid so far exceed a full year of law enforcement (<a href="https://nederlandco.civicweb.net/document/116150/" target="_blank" rel="noopener">2025 contract memo</a>).</td></tr>
        <tr><td>General Fund capital spending (equipment and improvements), 2024 actual to 2026 budget</td><td class="amount">$160,000–$200,000 a year</td><td>The $2.5 million estimate is more than 12 years of capital spending at that level (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>).</td></tr>
      </tbody>
    </table></div>
    <h3>Compared with other recent discretionary spending</h3>
    {scale_chart}
    <p class="prose muted">Bars are on one scale. Recurring costs such as the Sheriff contract and utility debt are not counted as discretionary. The records cover 2023 onward.</p>
  </section>

  <div class="group" id="accountability"><span>Records and statements</span></div>
  <section id="open-questions" class="open-q" aria-labelledby="open-questions-h">
    <h2 id="open-questions-h">Not in the records searched</h2>
    <p class="prose">The records searched (see <a href="#method-ai">How this research was done</a>) don't show the following; the information may be in staff or contract files, executive-session records, or other Town records. Anyone can request the records that could show it under the Colorado Open Records Act (CORA); see <a href="#get-involved">Get involved</a>.</p>
    <div class="scroll" id="records-needed"><table class="commit">
      <thead><tr><th scope="col">Not in the records searched</th><th scope="col">Records that could show it</th></tr></thead>
      <tbody>
        <tr><td>What makes up the Town's estimate of about $2.5 million owed if the sale doesn't close, including whether it includes the {balance} already paid (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>).</td><td>The calculation behind the Sept. 30, 2026, estimate, by firm or contract, showing amounts already paid, billed but unpaid, and expected, and which contracts are contingent on closing. Any cost-estimate updates given under Res. 2025-03.</td></tr>
        <tr><td>An engagement letter or stated role for <a href="#payee-hogan">Hogan Lovells</a>, paid {hogan} on the July 21 and Aug. 18, 2026, warrant lists. Res. 2025-16 authorized the Town Manager to engage acquisition counsel and named only Kline Alvarado Veio.</td><td>Hogan Lovells’ engagement letter and invoices.</td></tr>
        <tr><td>The purpose of the <a href="#payee-powdr">POWDR</a> invoices for $124,000, $10,721, and $50,000. The $50,000 invoice, dated Jan. 6, 2026, is in the Town's ledger for the account but on no warrant list searched.</td><td>POWDR invoices INV3313 and INV3475, and the invoice dated Jan. 6, 2026.</td></tr>
        <tr><td>The work done by Semple, Farrington, Everall &amp; Case; Farnsworth Group; Partner Engineering and Science; Torrent Engineering &amp; Equipment; and Bolder HR Solutions (<a href="#payees">Who was paid</a>), and what most ledger entries were for.</td><td>Their engagement letters. Invoice descriptions for the "Due From" account; the Town's ledger lists payees and amounts but describes most entries only as "Due From."</td></tr>
        <tr><td>Which Town reserves FAQ 7.0 called "sufficient to cover the current expenses associated with the work on the acquisition." A September 2026 records request asked; the records the Town provided don't identify them (<a href="{rec_reply}" target="_blank" rel="noopener">Town response</a>).</td><td>A record identifying those reserves; none was in the Town's response.</td></tr>
        <tr><td>How the 2025 audit reports the Eldora acquisition costs. It mentions them only as a planned bond financing (Note 10) and doesn't itemize the General Fund's "other receivables" (<a href="#receivable">receivables</a>).</td><td>The General Fund's year-end 2025 trial balance, showing which audit line includes the "Due From" account. The auditors' management letter for 2025, and any auditor comment on how the costs are reported.</td></tr>
        <tr><td>Whether, and on what terms, other Town funds could lend to the General Fund, and whether a loan repaid over several years would need voter approval (<a href="#gf-deficit">If the General Fund ends in deficit</a>).</td><td>Any Town policy or staff memo on loans between funds; the utility funds' bond covenants; the auditors' comments on the General Fund's negative cash.</td></tr>
        <tr><td>A proposed bond payment schedule. Ordinance 885 set only limits: up to $225 million, a final maturity within 40 years, and a net effective interest rate of no more than 9% (<a href="https://nederlandco.civicweb.net/document/127855/" target="_blank" rel="noopener">Ord. 885 §5(c)</a>). The draft Indenture of Trust leaves the bond amounts, interest rates, and maturities blank (<a href="https://nederlandco.civicweb.net/document/127181/" target="_blank" rel="noopener">draft indenture</a>).</td><td>The bond payment schedule (debt-service projections) prepared for the Series 2026 bonds.</td></tr>
        <tr><td>The financial projections behind the purchase (<a href="#profit">Profit</a>).</td><td>SE Group's final due-diligence report and five-year pro forma (Res. 2025-15); its proposal says the Town's use of the report is subject to the confidentiality agreement with POWDR (<a href="https://nederlandco.civicweb.net/document/122625/" target="_blank" rel="noopener">proposal p.3</a>). The financial model behind the projections in FAQ 3.0, and the documents prepared for bond buyers (requested in May 2026).</td></tr>
        <tr><td>The terms of the sale-leaseback: the lease, a new bond amount, and any pledges (<a href="#revised-plan">where things stand</a>).</td><td>The draft lease, bond indenture, and other financing documents for the sale-leaseback.</td></tr>
        <tr><td>Fee terms for the current underwriters and for disclosure and real estate counsel (<a href="#payees">Who was paid</a>).</td><td>Current engagement letters and fee terms for the underwriters (RBC Capital Markets and BofA Securities) and for disclosure and real estate counsel.</td></tr>
      </tbody>
    </table></div>
  </section>

  <section id="board-knowledge">
    <h2>Cost information in Board documents</h2>
    <p class="prose">What the Board documents said about expected costs, and where the spending appeared in the meeting packets.</p>

    <h3 id="estimates">Estimates compared with spending</h3>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Item</th><th scope="col">Estimate or terms in Board documents</th><th scope="col">What happened</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>SE Group due diligence (Jul 15, 2025)</td><td>"We anticipate our professional fees will not exceed $69,000," plus expenses of "typically 10%." The proposal said any increase in scope or fees, and any specialty experts, would be "provided to you for your authorization in writing" first. The Board approved the agreement "substantially in the form of the proposal" (<a href="https://nederlandco.civicweb.net/document/124156/" target="_blank" rel="noopener">Res. 2025-15</a>).</td><td><strong>$134,231 paid</strong> [[corrected:2026-10-11]]</td><td><a href="https://nederlandco.civicweb.net/document/122623/" target="_blank" rel="noopener">memo</a>, <a href="https://nederlandco.civicweb.net/document/122625/" target="_blank" rel="noopener">proposal p.4–5</a></td></tr>
        <tr><td>Plante Moran transition planning (Apr 21, 2026)</td><td>Estimated fee $90,000 to $110,000, over four to five weeks.</td><td><strong>$161,656 in Eldora acquisition charges</strong>, on invoices dated Dec. 4, 2025, to May 11, 2026, including $853 of a May 2026 invoice moved into the account from Professional Services (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>). Res. 2025-22 (Oct. 7, 2025) authorized the Town Manager to engage HR and finance consultants; it names no firm or estimate.</td><td><a href="https://nederlandco.civicweb.net/document/128983/" target="_blank" rel="noopener">engagement letter p.3</a>, <a href="https://nederlandco.civicweb.net/document/124849/" target="_blank" rel="noopener">Res. 2025-22</a></td></tr>
        <tr><td>Dickinson Wright water-rights due diligence (Jul 15, 2025)</td><td>Hourly rate only ($385); the engagement letter gives no estimate. [[corrected:2026-10-11]]</td><td>$50,149, including a $9,680 invoice first paid from the Legal budget and later moved into the account (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>)</td><td><a href="https://nederlandco.civicweb.net/document/122662/" target="_blank" rel="noopener">memo</a></td></tr>
        <tr><td>Town Attorney, Widner Juran</td><td>A July 2025 rate memo set a higher "pass-through" rate of $290 an hour from January 2026, "including enterprise fund... billings." It gave no estimate of hours.</td><td>$287,307, including $46,211 in January to July 2025 invoices first paid from the Legal budget and later moved into the account (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>)</td><td><a href="https://nederlandco.civicweb.net/document/122661/" target="_blank" rel="noopener">memo</a></td></tr>
        <tr><td>Special legal counsel (Res. 2025-03, Jan 7, 2025)</td><td>"The Town Administrator will provide updates to the Board of Trustees regarding cost estimates."</td><td>The Board documents and minutes searched include no cost-estimate update. One given aloud at a meeting or in executive session would not appear in them. [[corrected:2026-10-12]]</td><td><a href="https://nederlandco.civicweb.net/document/118137/" target="_blank" rel="noopener">memo</a></td></tr>
        <tr><td>Other legal counsel (Res. 2025-16, Aug 5, 2025)</td><td>The Town Manager "will keep the Board of Trustees informed about all necessary legal engagements."</td><td>Hogan Lovells ($148,795) and Semple, Farrington, Everall &amp; Case ($1,151) appear in no Board document searched other than the warrant lists. A briefing in executive session would not appear in public records.</td><td><a href="https://nederlandco.civicweb.net/document/123040/" target="_blank" rel="noopener">Res. 2025-16</a></td></tr>
      </tbody>
    </table></div>

    <h3 id="running-total">The running total was in the meeting packets</h3>
    <p class="prose muted">The Board approves each warrant list, usually on the consent agenda. Each payment to the "Due From" account appeared on it with the account's running balance next to it. These were the balances in the packet on nights the Board approved new Eldora acquisition items:</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Meeting</th><th scope="col">Acquisition item approved</th><th scope="col" class="num">"Due From" balance in packet</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td class="dt">Oct 7, 2025</td><td>Res. 2025-22, more consultants</td><td class="num">$67,492</td><td><a href="https://nederlandco.civicweb.net/document/124842/" target="_blank" rel="noopener">warrants</a></td></tr>
        <tr><td class="dt">Jan 6, 2026</td><td>Asset Purchase Agreement (Ord. 882)</td><td class="num">$370,841</td><td><a href="https://nederlandco.civicweb.net/document/126508/" target="_blank" rel="noopener">Dec 16 warrants</a> (no list on Jan 6)</td></tr>
        <tr><td class="dt">Jan 20, 2026</td><td>Bond ordinance (Ord. 885)</td><td class="num">$469,493</td><td><a href="https://nederlandco.civicweb.net/document/127156/" target="_blank" rel="noopener">warrants</a></td></tr>
        <tr><td class="dt">Mar 17, 2026</td><td>Res. 2026-07, license transfers</td><td class="num">$710,295</td><td><a href="https://nederlandco.civicweb.net/document/128049/" target="_blank" rel="noopener">Mar 3 warrants</a> (no list on Mar 17)</td></tr>
        <tr><td class="dt">Mar 31, 2026</td><td>IKON agreement and Forest Service permit</td><td class="num">$756,622</td><td><a href="https://nederlandco.civicweb.net/document/128662/" target="_blank" rel="noopener">warrants</a></td></tr>
        <tr><td class="dt">Apr 21, 2026</td><td>Plante Moran; emergency spending</td><td class="num">$756,822</td><td><a href="https://nederlandco.civicweb.net/document/128980/" target="_blank" rel="noopener">warrants</a></td></tr>
        <tr><td class="dt">Jul 7, 2026</td><td>Stifel ($325,000 fee).</td><td class="num">$915,922</td><td><a href="https://nederlandco.civicweb.net/document/130431/" target="_blank" rel="noopener">warrants</a></td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">The account is a balance-sheet account with a budget of $0. The balance also included {unlisted} added between lists (see <a href="#payees">Who was paid</a>). [[corrected:2026-10-11]]</p>

    <h3 id="cost-videos">Meetings where the acquisition's costs came up</h3>
    <p class="prose muted">Links to the Town's video recordings: where each item or comment period starts, and where costs come up in it. The descriptions say only what each item was about; watch the recording for what was said. The minutes are the official record.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Meeting</th><th scope="col">Item</th><th scope="col">Item starts</th><th scope="col">Costs come up</th></tr></thead>
      <tbody><tr><td class="dt">Jan. 7, 2025</td><td>Res. 2025-03, delegating authority to engage special legal counsel. The Board discussion includes how counsel fees would be paid.</td><td class="vid"><a href="https://www.youtube.com/watch?v=F3Kb-cwTvS8&amp;t=2148s" target="_blank" rel="noopener">0:35:48</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=F3Kb-cwTvS8&amp;t=2316s" target="_blank" rel="noopener">0:38:36</a></td></tr><tr><td class="dt">Jan. 21, 2025</td><td>Ord. 873, creating the Mountain Recreation Enterprise Fund. The Board discussion includes the fund if a purchase doesn't close.</td><td class="vid"><a href="https://www.youtube.com/watch?v=T9IKSJ_OoZw&amp;t=3408s" target="_blank" rel="noopener">0:56:48</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=T9IKSJ_OoZw&amp;t=3700s" target="_blank" rel="noopener">1:01:40</a></td></tr><tr><td class="dt">July 10, 2025</td><td>Board town hall on the acquisition. Public comments include questions about costs; the Board said answers would follow in a later FAQ.</td><td class="vid"><a href="https://www.youtube.com/watch?v=0AigDgranLU&amp;t=1052s" target="_blank" rel="noopener">0:17:32</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=0AigDgranLU&amp;t=2327s" target="_blank" rel="noopener">0:38:47</a>, <a href="https://www.youtube.com/watch?v=0AigDgranLU&amp;t=2712s" target="_blank" rel="noopener">0:45:12</a></td></tr><tr><td class="dt">Aug. 5, 2025</td><td>Res. 2025-17, the intent to reimburse acquisition costs from future bonds. Staff describe which costs could be reimbursed.</td><td class="vid"><a href="https://www.youtube.com/watch?v=ZgJBnuhE0-0&amp;t=1521s" target="_blank" rel="noopener">0:25:21</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=ZgJBnuhE0-0&amp;t=1562s" target="_blank" rel="noopener">0:26:02</a>, <a href="https://www.youtube.com/watch?v=ZgJBnuhE0-0&amp;t=1680s" target="_blank" rel="noopener">0:28:00</a></td></tr><tr><td class="dt">Jan. 6, 2026</td><td>Information item on the bond ordinance, including the costs the bonds would cover.</td><td class="vid"><a href="https://www.youtube.com/watch?v=WkgdzanY1IM&amp;t=2617s" target="_blank" rel="noopener">0:43:37</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=WkgdzanY1IM&amp;t=2772s" target="_blank" rel="noopener">0:46:12</a></td></tr><tr><td class="dt">Jan. 20, 2026</td><td>Ord. 885, the bond ordinance (Part 1), and public comment on it (Part 2).</td><td class="vid"><a href="https://www.youtube.com/watch?v=iFH8e_nZnWc&amp;t=1860s" target="_blank" rel="noopener">0:31:00 (Part 1)</a>, <a href="https://www.youtube.com/watch?v=J__yBhAQu10&amp;t=351s" target="_blank" rel="noopener">0:05:51 (Part 2)</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=iFH8e_nZnWc&amp;t=2124s" target="_blank" rel="noopener">0:35:24 (Part 1)</a></td></tr><tr><td class="dt">July 7, 2026</td><td>Stifel advisory agreement, with its fee contingent on a bond sale. Public comment includes questions about costs to date.</td><td class="vid"><a href="https://www.youtube.com/watch?v=bm_DSuMnc-M&amp;t=1595s" target="_blank" rel="noopener">0:26:35</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=bm_DSuMnc-M&amp;t=1630s" target="_blank" rel="noopener">0:27:10</a>, <a href="https://www.youtube.com/watch?v=bm_DSuMnc-M&amp;t=1787s" target="_blank" rel="noopener">0:29:47</a></td></tr></tbody>
    </table></div>
  </section>

  <section id="town-statements">
    <h2>What the Town told the public</h2>
    <p class="prose muted">These are the Town's FAQs and announcements about cost and funding, in date order. FAQ Round 2 was also included in the Jan. 7, 2025, Board packet; the others were posted only on the Town website. Earlier versions were on the Town's previous website and are linked here through the Internet Archive; the first FAQ (Nov. 14, 2024) was posted on the Engage Nederland site and is <a href="https://web.archive.org/web/20250815043449/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faq-on-engage-nederland" target="_blank" rel="noopener">archived</a>. [[corrected:2026-10-11]]</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Date</th><th scope="col">What the Town said</th><th scope="col">Source</th></tr></thead>
      <tbody><tr><td class="dt">Jan 7, 2025</td><td>FAQ Round 2. Estimates the price at "around $100M - $200M." Says an enterprise fund would keep the purchase "completely separated from the Town’s general fund," and that if the final offer were accepted, "we will have to provide earnest money to secure the mountain." The January 2026 draft purchase agreement has no deposit.</td><td><a href="https://nederlandco.civicweb.net/document/118136/" target="_blank" rel="noopener">FAQ Round 2 (Board packet)</a></td></tr><tr><td class="dt">Jul 8, 2025</td><td>FAQ 3.0: "We are buying Eldora!" Announces the signed term sheet. Says the bonds "will not be backed by local tax dollars," and that the bond limit "covers the acquisition, and the consultants and advisers needed to close the deal." Projects a reserve of about $10 million. Announces a partnership with 303 Ski, a group of Front Range ski-industry veterans who vetted operating plans and would "support the mountain once POWDR's contract expires."</td><td><a href="https://web.archive.org/web/20250709224556/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-30" target="_blank" rel="noopener">FAQ 3.0 (archived)</a></td></tr><tr><td class="dt">Aug 28, 2025</td><td>FAQ 4.0, in an answer about the enterprise fund and revenue bonds: "No general Town funds or taxpayer dollars are being used to purchase the mountain," and "no general Town resources will be used." Eldora due-diligence bills dated that month were later charged to the General Fund as money owed back to the Town, to be repaid from bond proceeds (Res. 2025-17), starting with the Oct. 7, 2025, warrant list (see <a href="#costs">What has been spent</a>).</td><td><a href="https://web.archive.org/web/20251112014324/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-40" target="_blank" rel="noopener">FAQ 4.0 (archived)</a></td></tr><tr><td class="dt">By Apr 2, 2026</td><td>FAQ 6.0 (reposted Oct. 5, 2026). Repeats that no general Town funds are being used "to purchase Eldora Mountain Resort." Names disclosure counsel Butler Snow and real estate counsel Brownstein Hyatt Farber Schreck. Fees are "not subject to a single fixed cap." Expects closing April 30, 2026. Asked why the Town would walk away from 303 Ski, says its "future involvement was not without cost" and that the Town declined its "requests … for reimbursement of time and expenses."</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0</a></td></tr><tr><td class="dt">Jul 23, 2026</td><td>FAQ 7.0. Confirms about $830,000 in costs "paid or advanced" as of the BusinessDen article, expected to be repaid from bond proceeds. Says the purchase might not close, that some contracts "will need to be paid regardless of closing," and that Town reserves are "sufficient to cover the current expenses." Says Stifel’s $325,000 is "in addition to the $830,000" but is owed only if the deal closes. Points readers to the warrant lists for all expenses.</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a></td></tr><tr><td class="dt">Sep 17, 2026</td><td>Request for proposals for a Town auditor: the Town is "currently in negotiations to purchase the Eldora Ski Resort," and bidders must price an audit of the Mountain Recreation Enterprise separately.</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/20" target="_blank" rel="noopener">RFP post</a></td></tr><tr><td class="dt">Sep 30, 2026</td><td>Update from Mayor Sterling and the Board. The purchase agreement "has expired," but talks continue on a restructured deal (<a href="#revised-plan">revised plan</a>). Estimates about $2.5 million in costs if the sale fails, paid from CSAFE (<a href="#bottom-line">bottom line</a>).</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a></td></tr><tr><td class="dt">Oct 20, 2026</td><td>"Eldora Transaction Update" memo in the Board packet. Pursuing the purchase at $120 million; refers to "outstanding financial obligations" without listing them; attaches the 2026 ledger and a <a href="#revised-plan">sale-leaseback overview</a>; staff will review Eldora costs at the Nov. 5, 2026, budget work session; Eldora updates become a standing agenda item (<a href="#findings-h">findings</a>).</td><td><a href="https://nederlandco.civicweb.net/document/132785/" target="_blank" rel="noopener">Oct. 20 memo</a></td></tr></tbody>
    </table></div>
    <h3 id="questions">Questions and records requests from the public</h3>
    <p class="prose">Residents' questions and open records requests about the acquisition, in date order.</p>
    <ul class="notes prose">
      <li>December 2024: a Planning Commission member urged that the Town Administrator track the hours spent on the Eldora proposal (<a href="https://nederlandco.civicweb.net/document/118183/" target="_blank" rel="noopener">minutes</a>).</li>
      <li>December 2024 to February 2025: three open records requests for Board and staff emails and records mentioning Eldora or POWDR, each picking up where the last left off. The first took about five hours of staff time (<a href="https://nederlandco.civicweb.net/document/117486/" target="_blank" rel="noopener">Dec. 2024</a>, <a href="https://nederlandco.civicweb.net/document/118502/" target="_blank" rel="noopener">Jan. 2025</a>, <a href="https://nederlandco.civicweb.net/document/119081/" target="_blank" rel="noopener">Feb. 2025</a> Clerk reports).</li>
      <li>November 2025: "Why are our tax dollars being used to research and pay legal fees in reference to the acquisition of Eldora?" (<a href="https://nederlandco.civicweb.net/document/125984/" target="_blank" rel="noopener">comment</a>).</li>
      <li>May 2026: an open records request for the documents prepared for potential buyers of the bonds (<a href="https://nederlandco.civicweb.net/document/129650/" target="_blank" rel="noopener">Clerk report</a>).</li>
      <li>June 2026: an open records request for "all contracts, consultant agreements, and payments made in connection with the Eldora acquisition." Staff estimated 12 hours of work, and the requester paid a deposit (<a href="https://nederlandco.civicweb.net/document/130055/" target="_blank" rel="noopener">June</a> and <a href="https://nederlandco.civicweb.net/document/130713/" target="_blank" rel="noopener">July</a> Clerk reports).</li>
      <li>July 2026: a former trustee and a resident asked for a breakdown of costs and what happens if the purchase fails (<a href="https://nederlandco.civicweb.net/document/130492/" target="_blank" rel="noopener">comment</a>, <a href="https://nederlandco.civicweb.net/document/130665/" target="_blank" rel="noopener">minutes</a>). FAQ 7.0 (July 23) and the Sept. 30 update gave cost totals.</li>
      <li>September 2026: an open records request (Sept. 22) asked (1) which Town reserves FAQ 7.0 called "sufficient to cover the current expenses associated with the work on the acquisition," and (2) the purpose and accounting treatment of the "Due From" account. The Town responded Sept. 25 that CORA "does not require the Town to create records that do not already exist, prepare new records, or answer questions," and provided the account's 2025–2026 ledger, used on this page, and July 2026 bank and CSAFE statements (<a href="{rec_reply}" target="_blank" rel="noopener">Town response</a>, <a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>).</li>
      <li>September 2026: the former trustee asked again for "another update please - one with substance. It's our money" (<a href="https://nederlandco.civicweb.net/document/132059/" target="_blank" rel="noopener">comment</a>).</li>
      <li>September–October 2026: the Town Clerk's Oct. 20 report lists four requests about the acquisition among 12 received in the previous 30 days: for the records released in response to BusinessDen's May 2026 request; the reserves and "Due From" request described above; the bond payment schedule; and the records behind the Town's $2.5 million estimate, unpaid invoices since July 1, 2026, and fee agreements with 14 firms (<a href="https://nederlandco.civicweb.net/document/132754/" target="_blank" rel="noopener">Clerk report</a>).</li>
    </ul>
    <p class="prose muted">The Town Clerk's monthly reports list records requests but not what was released, and the February and March 2026 reports list no requests, so the requests above may not be all of them. The Town's written answers are in the table above.</p>
    <h3 id="profit">Profit: what the Town projected, and what the bond terms say</h3>
    <ul class="notes prose">
      <li><strong>January 2025.</strong> The staff memo for Ordinance 873, which created the enterprise: "Any surplus revenue, in compliance with TABOR, may be redirected to other Town priorities" (<a href="https://nederlandco.civicweb.net/document/118505/" target="_blank" rel="noopener">memo</a>).</li>
      <li><strong>January 2025.</strong> FAQ Round 2 quoted Eldora's general manager: "Eldora is profitable." Once debt obligations and "rainy day funds" are covered, "any leftover profits will be available for the town" (<a href="https://nederlandco.civicweb.net/document/118136/" target="_blank" rel="noopener">FAQ Round 2</a>).</li>
      <li><strong>July 2025.</strong> FAQ 3.0: "Current models show we can build a reserve of $10 million in the first couple of years." Excess cash flow "does not become meaningful until the subordinate bonds are paid off," which the Town aimed to do "within ten years." "After that, free cash flow will fall between $2M - $5M+." Annexing the resort "could add $1M - $2M in annual revenue to the Town's general fund." The FAQ said it "cannot disclose exact figures" (<a href="https://web.archive.org/web/20250709224556/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-30" target="_blank" rel="noopener">FAQ 3.0</a>).</li>
      <li><strong>August 2025.</strong> FAQ 4.0: after the subordinate bonds are retired and reserves are built, the Board could direct "excess revenues" to streets, sidewalks, affordable housing, and childcare (<a href="https://web.archive.org/web/20251112014324/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-40" target="_blank" rel="noopener">FAQ 4.0</a>).</li>
      <li><strong>April 2026.</strong> FAQ 6.0 no longer gives the annexation estimate. It says much of the ski area is on Forest Service land that "is not anticipated" to be annexed, and that annexation "must be evaluated separately" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0</a>).</li>
      <li><strong>September 2026.</strong> The Town update gives no revenue or profit figures. It says the first "approximately ten years" are "more financially constrained," and that its assumptions have become more conservative (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>).</li>
    </ul>
    <p class="prose">No financial model, feasibility study, or bond-offering document is in the records searched. Under the draft Indenture of Trust (January 20, 2026, packet), revenue left after operations, debt payments, and reserves goes first to paying off the senior bonds early, all of it until revenue covers debt payments two to one for three straight years, then half. What remains goes to a "Surplus Fund" that stays available to pay the bonds. This page found no provision releasing money to the Town (<a href="https://nederlandco.civicweb.net/document/127181/" target="_blank" rel="noopener">Indenture §5.07, §5.11</a>). The final terms may differ.</p>
  </section>

  <div class="group" id="involve"></div>
  <section id="get-involved" aria-labelledby="get-involved-h">
    <h2 id="get-involved-h">Get involved</h2>
    <p class="prose muted">How residents can follow the next decisions, get records, and be heard. These are procedures, not legal advice; confirm deadlines and requirements with the Town Clerk.</p>
    <div class="tp-watch prose">
      <h3>Decisions to watch</h3>
      <ul>
        <li><strong>A new purchase agreement.</strong> The first one was approved by ordinance (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">Ord. 882</a>); the Town says talks with POWDR continue.</li>
        <li><strong>New financing.</strong> The sale-leaseback plan would need a new or amended bond ordinance, a lease, or both, since the bond authority lapsed (<a href="#revised-plan">revised plan</a>).</li>
        <li><strong>The 2027 Town budget,</strong> now being prepared (<a href="https://nederlandco.civicweb.net/document/130743/" target="_blank" rel="noopener">July 21 report</a>). The interim Town Manager says it is her priority, to "identify potential opportunities for expenditure reductions and alternative revenue sources" (<a href="https://nederlandco.civicweb.net/document/132750/" target="_blank" rel="noopener">Oct. 20 report</a>); staff plan to review Eldora-related costs at the Nov. 5, 2026, budget work session.</li>
        <li><strong>A public meeting on the deal,</strong> which the Town says it will hold after the purchase (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a>).</li>
      </ul>
    </div>
    <dl class="tp-facts prose">
      <dt>Meetings</dt><dd>Regular Board meetings are on the first and third Tuesdays at 7:00 p.m. at the Nederland Community Center. Each agenda has an online link and a call-in number (<a href="https://nederlandco.civicweb.net/document/132364/" target="_blank" rel="noopener">Oct. 6 agenda</a>). Recordings of Board meetings are posted on the Town's <a href="https://www.youtube.com/channel/UCknLzh_H3jXUCHNN2r-H37w" target="_blank" rel="noopener">YouTube channel</a>; executive sessions are not included.</dd>
      <dt>Agendas</dt><dd>Agendas and full packets are posted on the Town's <a href="https://nederlandco.civicweb.net/portal/" target="_blank" rel="noopener">CivicWeb portal</a> before each meeting. Each warrant list shows Eldora acquisition payments under the <a href="#costs">"Due From" account</a>.</dd>
      <dt>Closed sessions</dt><dd>The Board discusses the purchase in executive session. The motion to go into one is public; the discussion is not.</dd>
      <dt>Speak</dt><dd>The Mayor calls for comment on each action and discussion item, and there is a time for comment on topics not on the agenda. Comments are limited to 3 minutes; speakers state their name and whether they live in Nederland.</dd>
      <dt>Write</dt><dd>Emails to the Board at <span class="mono">BOT@nederlandco.org</span> in August 2026 were included as public comment in the next packet (<a href="https://nederlandco.civicweb.net/document/131757/" target="_blank" rel="noopener">Sept. 1 packet</a>). The Town Clerk is <span class="mono">townclerk@nederlandco.org</span>. Ask that your email be included as public comment, and send it before the meeting where the item is decided.</dd>
      <dt>Email updates</dt><dd>To get an email when this page has a major update or correction, <a href="mailto:{subscribe}?subject=Subscribe">subscribe by email</a>: send any message to {subscribe} and follow the instructions in the confirmation email. The list is used only for those announcements, members can't post to it, and the member list is private.</dd>
      <dt>Follow updates</dt><dd>Corrections and updates to this page are published as a feed, <a href="{site}feed.xml">{site}feed.xml</a>, which any feed reader can follow. No sign-up is needed.</dd>
      <dt>Records</dt><dd>Open records requests go to the Town Clerk. The first hour of staff time is free; more is charged at a rate capped by state law (C.R.S. 24-72-205). A named document is faster and cheaper than a keyword search; see the <a href="#records-needed">records list</a>. Executive-session discussions and confidential documents may be withheld. Minutes are the official record; verbatim transcripts are made only on request, for a fee (<a href="https://nederlandco.civicweb.net/document/126176/" target="_blank" rel="noopener">2026 fees</a>).</dd>
      <dt>Referendum</dt><dd>Registered voters can petition to send most ordinances to a public vote. The petition needs signatures from 5% of registered voters within 30 days after the ordinance is published, and the ordinance is on hold until the Board repeals it or voters decide (C.R.S. 31-11-105). Residents used this in 2024 on Ordinance 859, the TEENS child care approval (<a href="https://nederlandco.civicweb.net/document/116161/" target="_blank" rel="noopener">Town memo</a>). This applies to ordinances approving a purchase or bonds, even though the bonds themselves need no election.</dd>
      <dt>Initiative</dt><dd>Registered voters can propose an ordinance by a petition signed by at least 5% of registered voters. The Board must adopt it unchanged within 20 days or send it to the voters (C.R.S. 31-11-104).</dd>
      <dt>Elections</dt><dd>The next regular municipal election is in April 2028 (<a href="https://nederlandco.civicweb.net/document/130995/" target="_blank" rel="noopener">Town memo</a>). A vacant trustee seat was filled by appointment in September 2026 (<a href="https://nederlandco.civicweb.net/document/132368/" target="_blank" rel="noopener">Res. 2026-25</a>). Colorado's constitution also allows recall of elected officials by petition (Colo. Const. art. XXI).</dd>
    </dl>
    <p class="prose muted small">Nederland is a statutory town, and it applied these state petition rules in 2024. The Board has discussed converting to home rule, which would let a charter set different rules (<a href="https://nederlandco.civicweb.net/document/132582/" target="_blank" rel="noopener">Sept. 15 minutes</a>). Comments are most useful when they cite the record and ask questions with specific answers; the list of what is <a href="#open-questions">not in the records searched</a> is one starting point.</p>
  </section>

  <div class="group" id="reference"><span>Reference</span></div>
  <section id="ledger">
    <h2>Payment ledger</h2>
    <p class="prose muted">{data_links}</p>
    <div class="tools">
      <label class="sr" for="q">Filter payments</label>
      <input id="q" type="search" placeholder="Filter by payee, invoice, or date" autocomplete="off">
    </div>
    <div class="scroll ledger"><table>
      <thead><tr><th scope="col">Warrant list</th><th scope="col">Payee</th><th scope="col" class="opt">Invoice</th><th scope="col" class="opt">Invoice date</th><th scope="col" class="num">Amount</th><th scope="col" class="num opt">Account balance</th><th scope="col">Source</th></tr></thead>
      <tbody>{ledger}</tbody>
    </table></div>
  </section>

  <section class="prose" id="figures">
    <h2>About these figures</h2>
    <ul class="notes">
      <li>Why the account is treated as Eldora acquisition spending. It first appears on the Oct. 7, 2025, warrant list, right after the Board hired Eldora due-diligence consultants, whose costs were to be "reimbursed from revenue bond proceeds" (Res. 2025-19, 2025-22). Other reimbursable work, such as FEMA, CDOT, and DDA projects, has its own accounts, and no charge in the account was found to belong to another program. The Town's spreadsheet of the account's 2025–2026 entries, released in response to a public records request, is titled "Eldora - reimbursable expenses," and the entries moved into the account are labeled "Eldora Reclass" (<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>).</li>
      <li>The total covers only bills booked to the "Due From" account, which opened in August 2025. It includes {moved} in invoices the Town moved into the account from the Legal and Professional Services budget lines (see <a href="#payees">Who was paid</a>), among them Widner Juran invoices from January to July 2025. Any other Eldora acquisition work charged to ordinary budget lines and not moved isn't identified in the records searched and is not included.</li>
      <li>Totals are by warrant-list date, when the Board approved payment. Invoice dates are often earlier; some invoices dated in 2025 were paid in 2026, so the totals show when bills were approved, not when work was done.</li>
      <li>The running balance printed on each warrant list matches the listed invoices, except for the amounts added between lists (shown under Who was paid) and one Widner Juran invoice ($16,985) that reached the balance one list before it was listed. [[corrected:2026-10-11]]</li>
      <li>Amounts are rounded to the nearest dollar, so a total can differ by a dollar from the sum of its rounded parts. The data files in the <a href="https://github.com/dallasmasters/nederland-eldora-record" target="_blank" rel="noopener">project repository</a> keep the exact amounts.</li>
      <li>Source: Board of Trustees warrant lists (Council Approval Reports) on the Town's CivicWeb portal, through the October 20, 2026 meeting, and the Town's ledger for the account through Sept. 25, 2026, released in response to a public records request (<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>, <a href="{rec_reply}" target="_blank" rel="noopener">Town response</a>) and, for 2026, posted in the Oct. 20, 2026, Board packet (<a href="https://nederlandco.civicweb.net/document/132789/" target="_blank" rel="noopener">packet copy</a>).</li>
    </ul>
  </section>

{votes_html}
  <section id="changes">
    <h2>Corrections and updates</h2>
    <p class="prose muted">A <strong>correction</strong> fixes something this page got wrong. An <strong>update</strong> adds new records, such as new warrant lists or minutes. Report errors to the address at the bottom of the page. This list records each correction and update; it is also published as a <a href="{site}feed.xml">feed</a>.</p>
    {changes}
  </section>

{method}
  <footer>eldorarecord.org · An independent compilation of Town of Nederland public records.</footer>
</main>

<script>
(() => {{
  const q = document.getElementById('q');
  const rows = [...document.querySelectorAll('.ledger tbody tr')];
  q.addEventListener('input', () => {{
    const terms = q.value.toLowerCase().split(/\\s+/).filter(Boolean);
    for (const r of rows) r.classList.toggle('hide', !terms.every(t => r.dataset.text.includes(t)));
  }});
}})();
(() => {{
  // Open the change log when a "Corrected" note or a link to an entry is followed
  const box = document.querySelector('.changes-box');
  if (!box) return;
  const openFor = h => {{ if (h && h.startsWith('#change')) box.open = true; }};
  openFor(location.hash);
  window.addEventListener('hashchange', () => openFor(location.hash));
  document.querySelectorAll('.corr-note').forEach(a => a.addEventListener('click', () => {{ box.open = true; }}));
}})();
{votes_js}
</script>
'''

if __name__ == '__main__':
    main()
