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
from district_taxes import html as district_taxes_html, summary as district_taxes_summary
from eldora_page import fragment
from charts import costs_chart, gf_chart
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
                   'that is on no warrant list. A Jan 6, 2026, letter provides for a $50,000 advance to POWDR toward Ikon '
                   'negotiation costs, and POWDR\'s Sept 22, 2026, email says the Town "previously paid Powdr $50,000 toward these legal expenses" (records request). '
                   'The $10,721 invoice is for the "Eldora three-year audit by BDO - remaining amount"; POWDR\'s CFO called it '
                   '"the final true-up" when he sent it to the Town Manager on Apr 30, 2026, and the Town Manager replied May 5 '
                   'that he was sending it to Finance for payment (records request). The only other POWDR invoice before it is '
                   'the $124,000 one, so that is likely the earlier payment toward the BDO audit (this page\'s reading; no record '
                   'states its purpose). The $12,357.75 invoice (Sept 30, 2026) is the rest of the Town\'s half of Hogan Lovells\' fees for the Ikon agreement, '
                   'per the same email'),
    'Sno.engineering': ('SE Group', 'named', 'Eldora due diligence (Res. 2025-15). Its earlier Comprehensive Plan '
                        'work used other budget lines'),
    'Kline Veio': ('Kline Alvarado Veio', 'named', 'Eldora bond counsel (Res. 2025-16). Its Aug 2025 engagement letter '
                   'estimates $200,000 to $250,000, payable at closing, and hourly billing if no bonds are issued'),
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
    'Brownstein Hyatt Farber Schreck': ('Brownstein Hyatt Farber Schreck', 'named', 'Real estate counsel (engagement agreement '
                                        'of Jan 3, 2025, released Oct 2026). Its first payment, $40,000, is on the Nov 9, 2026, '
                                        'warrant list, charged to the new "Eldora Expense" account'),
    'Hogan Lovells US LLP': ('Hogan Lovells', 'none', 'Law firm; counsel to Alterra Mountain Company on the Ikon agreement. '
                             'Its invoices are addressed to Alterra; the two paid here are for a "Town of Nederland" matter '
                             '(invoices and emails released Nov 26, 2026)'),
    'Farnsworth Group': ('Farnsworth Group', 'none', 'Engineering firm. Land survey of two resort parcels for a fixed '
                         '$65,300 (Aug 2025 agreement, released Oct 2026). Invoices Oct 2025 to Jan 2026'),
    'Partner Assessment Corporation': ('Partner Engineering and Science', 'none', 'Invoices dated September and December 2025. '
                                       'The Nov 2025 Eldora memo reports a property condition assessment and a Phase I '
                                       'environmental site assessment, but doesn’t name who did them'),
    'Torrent Engineering & Equipment Company LLC': ('Torrent Engineering & Equipment', 'none', 'Engineering firm. One invoice, Dec 2025'),
    'Susan N. Fattor': ('Bolder HR Solutions', 'none', 'HR firm. Res. 2025-22 covers HR support for the acquisition. '
                        'Its agreement (effective Oct 6, 2025, released Oct 2026) is for transitioning Eldora employees, at $150 an hour'),
    'Datasite LLC': ('Datasite', 'none', 'Virtual data room named "Eldora"; $200 a month since Feb 2026, the minimum under '
                     'a 36-month term (statement of work released Oct 2026)'),
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
CORA_REPLY2 = 'records/2026-10-22-town-cora-response.txt'
CORA_REPLY3 = 'records/2026-10-20-town-cora-response.txt'   # Oct. 20, 2026, response to Melody Baumhover
CORA_INDENTURE = 'records/2026-05-12-indenture-of-trust-draft-v14.doc'   # posted as received
# The Town's Nov. 9, 2026, FY27 budget presentation, as screenshots from the meeting video (record 910055; the user
# approved citing them Nov. 15, 2026). Slide 4 is the General Fund table; 5-8 are the options for covering the deficit.
SLIDES = 'records/2026-11-09-fy27-budget-presentation-town.pdf'   # the Town's PDF, released Nov. 16, 2026 (910057); the screenshots (910055) match it
SCEN = 'records/2026-10-30-budget-scenarios.xlsx'                  # staff spreadsheet, released Nov. 16, 2026
BUD_REPLY = 'records/2026-11-16-town-cora-response-budget.txt'
INV_REPLY = 'records/2026-11-16-town-cora-response-invoice-emails.txt'
INV = {'powdr_audit': 'records/2026-05-05-powdr-audit-invoice-redacted.pdf', 'taft_inv': 'records/2026-01-14-taft-invoices-redacted.pdf',
       'bhfs_inv': 'records/2026-10-11-brownstein-invoice-redacted.pdf', 'wwpf_inv': 'records/2026-11-11-williams-weese-invoice-redacted.pdf',
       'other_inv': 'records/2026-06-04-other-invoice-emails-redacted.pdf', 'conf_req': 'records/2026-10-19-confirmation-requests-redacted.pdf',
       # Hogan Lovells release, Nov. 26, 2026 (records 910066-910067)
       'hl_inv': 'records/2026-11-26-hogan-lovells-invoices-and-emails-redacted.pdf', 'hl_reply': 'records/2026-11-26-town-cora-response-hogan-lovells.txt'}
# Payee rows that link to the invoices and emails released Nov. 16, 2026: display name -> (INV key, link text)
INV_LINKS = {'POWDR Corp': ('powdr_audit', 'audit invoice and emails'), 'Taft Stettinius & Hollister': ('taft_inv', 'invoices and emails'),
             'Brownstein Hyatt Farber Schreck': ('bhfs_inv', '$40,000 invoice and email'),
             'Williams Weese Pepple & Ferguson': ('wwpf_inv', 'Nov. 11 invoice and email'),
             'SE Group': ('other_inv', 'invoice emails'), 'BBA Water Consultants': ('other_inv', 'invoice emails'),
             'Farnsworth Group': ('other_inv', 'invoice email'), 'Bolder HR Solutions': ('other_inv', 'invoice email'),
             'Hogan Lovells': ('hl_inv', 'invoices and emails')}
DS2 = 'records/2026-05-13-senior-debt-service-schedule.pdf'                 # released to Karen Blakemore, Oct. 29, 2026
DS_REPLY = 'records/2026-10-29-town-cora-response-debt-service.txt'
AUDIT_EMAILS = 'records/2026-05-18-fy25-audit-subsequent-event-emails.pdf'   # released to Melody Baumhover, Nov. 13, 2026
AUDIT_REPLY = 'records/2026-11-13-town-cora-response.txt'
NOV9_MIN = 'https://nederlandco.civicweb.net/document/133372/'   # Nov. 9, 2026, minutes (Nov. 17 packet, item 3.3)
# Agreements in the Town's records released to Melody Baumhover (files dated Oct. 20, 2026; archive IDs 910009-910016)
CORA_OCT20 = {'ikon': '2026-01-06-powdr-ikon-cost-sharing-letter.pdf', 'kav': '2025-08-01-kline-alvarado-veio-engagement-letter.pdf',
              'qoe': '2025-08-12-plante-moran-qoe-engagement-letter.pdf', 'farn': '2025-08-28-farnsworth-survey-agreement.pdf',
              'bolder': '2025-10-06-bolder-hr-agreement.pdf', 'bba': '2025-10-08-bba-water-engagement-letter.pdf',
              'datasite': '2025-11-datasite-statement-of-work.pdf', 'stifel': '2025-05-23-stifel-municipal-advisory-agreement.pdf'}
SITE_RECORDS = 'https://eldorarecord.org/records/'
# Oct. 29, 2026, response to the request for the records behind the $2.5 million estimate (catalog/records.csv)
CORA_OCT29 = {'reply4': '2026-10-29-town-cora-response.txt', 'c_bhfs': '2026-10-20-brownstein-outstanding-confirmation.pdf',
              'c_kav': '2026-10-19-kline-alvarado-veio-outstanding-confirmation.pdf',
              'c_wwpf': '2026-10-19-williams-weese-outstanding-confirmation.pdf', 'wwpf_stmt': '2026-09-09-williams-weese-statement.pdf',
              'c_dw': '2026-10-23-dickinson-wright-outstanding-confirmation.pdf', 'c_taft': '2026-10-19-taft-outstanding-confirmation.pdf',
              'c_seg': '2026-10-19-se-group-outstanding-confirmation.pdf', 'c_stifel': '2026-10-19-stifel-outstanding-confirmation.pdf',
              'c_dwc': '2026-10-19-dinatale-outstanding-confirmation.pdf', 'c_jva': '2026-10-22-jva-outstanding-confirmation.pdf',
              'wj_ar': '2026-10-16-widner-juran-ar-aging.pdf', 'bhfs': '2025-01-03-brownstein-engagement-agreement.pdf',
              'butler': '2025-08-13-butler-snow-engagement-letter.pdf', 'seg_amend': '2025-se-group-first-amendment.pdf',
              'dw_emails': '2026-09-16-dickinson-wright-payment-emails-redacted.pdf'}
# Payee keys (PAYEES) for confirming firms that have also been paid
CONF_VENDOR = {'Kline Alvarado Veio': 'Kline Veio', 'Dickinson Wright': 'Dickinson Wright PLLC', 'Widner Juran': 'Widner Juran LLP',
               'SE Group': 'Sno.engineering', 'DiNatale Water Consultants': 'DiNatale Water Consultants', 'JVA': 'JVA'}
# Amounts the firms confirmed to the Town as owed as of Oct. 16, 2026 (Oct. 29 response): (firm, invoiced and unpaid,
# not yet invoiced, record key, note). Widner Juran's figure is the Eldora lines of its own receivables report.
CONFIRMED = [
    ('Brownstein Hyatt Farber Schreck', 0, 1_174_082.66, 'c_bhfs', '$1,174,083 not yet invoiced. The confirmation also listed $40,000 invoiced, which was paid on the Nov. 9, 2026, warrant list. It doesn\'t say whether the 10% discount for a failed deal is applied. The $40,000 invoice, dated Oct. 9, 2026, and addressed to the Town Attorney, came with an Oct. 11 email asking that it be "processed and paid before the end of October."'),
    ('Kline Alvarado Veio', 0, 200_000.00, 'c_kav', 'Not yet invoiced. Its engagement letter estimates a $200,000 to $250,000 fee "payable at Closing" and bills accrued time by the hour if no bonds are issued; the confirmation doesn\'t say which basis the $200,000 is on.'),
    ('Williams Weese Pepple & Ferguson', 87_595.50, 800.00, 'c_wwpf', 'Forest Service authorizations for the Town. $87,596 invoiced and $800 not yet invoiced; 13 invoices dated Aug. 11, 2025, to Aug. 14, 2026, on a statement addressed to the Town in care of Brownstein. A Nov. 11, 2026, invoice adds $566 for October, for $88,161.50 due. The firm appears in no Board document or warrant list searched.'),
    ('Dickinson Wright', 84_621.50, 0, 'c_dw', 'Invoiced and unpaid. The firm\'s emails to the Town list nine unpaid invoices in its "Eldora Ski Area purchase" matter, dated Oct. 29, 2025, to June 17, 2026; none is on a warrant list searched.'),
    ('Taft Stettinius & Hollister', 74_177.50, None, 'c_taft', 'The firm appears in no Board document or warrant list searched. $74,178 invoiced and unpaid; the "not yet invoiced" line is blank. The two invoices behind it, addressed to the Town Manager, are labeled "RE: Employee Benefits": $1,350 for work through April 30, 2025, and $72,827.50 through Dec. 31, 2025. The firm\'s billing staff entered the total on the Town\'s Eldora confirmation form; the records searched don\'t say how the work relates to the acquisition.'),
    ('Widner Juran', 0, 'na', 'wj_ar', 'Its receivables report as of Oct. 16 listed invoices labeled "Eldora" ($6,624) and "Eldora CORA" ($3,220), dated Sept. 30, 2026. Both were paid on the Nov. 9, 2026, warrant list: the $6,624 as an Eldora expense, counted here, and the $3,220 from Legal, not counted.'),
    ('SE Group', 0, 2_500.00, 'c_seg', 'Not yet invoiced.'),
    ('Stifel', 0, 0, 'c_stifel', ''),
    ('DiNatale Water Consultants', 0, 0, 'c_dwc', ''),
    ('JVA', 0, 0, 'c_jva', ''),
]
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
     'label': 'In the Town ledger (invoice dated Jan 6, 2026); on no warrant list. Purpose not stated. A letter of the same date provides for a $50,000 advance to POWDR toward Ikon negotiation costs'},
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
    ('Financing', 'Stifel', None, 'Municipal advisor: structures the financing and coordinates the deal team; owes the Town a fiduciary duty', 'Agreement of May 23, 2025 (released Oct. 2026); named in the Jan. 2026 draft purchase agreement; extended July 7, 2026', 'July 2026: agreement through June 30, 2027', None),
    ('Financing', 'RBC Capital Markets and BofA Securities', None, 'Underwriters; would buy the bonds "on a best-efforts basis"', 'Engaged by Nov. 2025; approved in Ord. 885', 'April 2026: named in FAQ 6.0', None),
    ('Financing', 'Northland Securities', None, 'Underwriter', 'Res. 2025-02', 'April 2025: last mention', None),
    ('Financing', 'J.P. Morgan Securities', None, 'Underwriter (non-binding letter of intent)', 'Res. 2025-08', 'April 2025: last mention', None),
    ('Lawyers', 'Widner Juran', 'Widner Juran LLP', 'Town Attorney; includes $46,211 in January to July 2025 invoices moved into this account from the Legal budget', 'Standing appointment', None, None),
    ('Lawyers', 'Kline Alvarado Veio', 'Kline Veio', 'Bond counsel; fee estimate $200,000 to $250,000, payable at closing, or accrued time billed hourly if no bonds are issued', 'Res. 2025-16 (named); engagement letter of Aug. 1, 2025 (released Oct. 2026)', None, None),
    ('Lawyers', 'Butler Snow', None, 'Disclosure counsel; estimated fee $100,000, paid at closing from bond proceeds', 'Named in FAQ 6.0; engagement letter of Aug. 13, 2025 (released Oct. 2026)', 'April 2026: named in FAQ 6.0', None),
    ('Lawyers', 'Brownstein Hyatt Farber Schreck', 'Brownstein Hyatt Farber Schreck', 'Real estate counsel; billed when the transaction is completed or terminated', 'Engagement agreement of Jan. 3, 2025 (released Oct. 2026); copied on notices to the Town in the Jan. 2026 draft purchase agreement; named in FAQ 6.0', None, None),
    ('Lawyers', 'Dickinson Wright', 'Dickinson Wright PLLC', 'Water-rights due diligence (its other water-law work is billed to the Water Fund); includes a $9,680 invoice moved into this account from the Legal budget', 'Engagement approved July 15, 2025', None, None),
    ('Lawyers', 'Hogan Lovells', 'Hogan Lovells US LLP', 'Counsel to Alterra Mountain Company, owner of the Ikon Pass, on the new Ikon agreement with the Town. Its invoices are addressed to Alterra. The Town paid two for a "Town of Nederland" matter, and its share of the Ikon-agreement invoices through POWDR (Ikon costs). A May 29, 2026, invoice for $8,943, "directly attributable to the Town," hasn\'t been paid', 'no engagement letter in the records searched; the Town\'s Jan. 6, 2026, letter covers half of Alterra\'s Ikon fees', None, None),
    ('Lawyers', 'Semple, Farrington, Everall & Case', 'Semple', 'Role not stated in the records searched; the Res. 2025-16 memo expects "specialized employment matters"', 'no engagement record in the Board documents searched', None, None),
    ('Due diligence', 'SE Group', 'Sno.engineering', 'Operations, market, and financial review of the resort', 'Res. 2025-15', None, None),
    ('Due diligence', 'Farnsworth Group', 'Farnsworth Group', 'Land survey of two resort parcels, including the "Cabin Parcel," for a fixed fee of $65,300', 'Agreement of Aug. 2025 (released Oct. 2026); not in the Board documents searched', None, None),
    ('Due diligence', 'Partner Engineering and Science', 'Partner Assessment Corporation', 'Role not stated in the records searched; the Nov. 2025 Eldora memo reports a property condition assessment and an environmental site assessment without naming who did them', 'no engagement record in the Board documents searched', None, None),
    ('Due diligence', 'Torrent Engineering & Equipment', 'Torrent Engineering & Equipment Company LLC', 'Engineering; work not stated in the records searched', 'no engagement record in the Board documents searched', None, None),
    ('Due diligence', 'BBA Water Consultants', 'BBA Water Consultants', "Eldora's own water consultant under the purchase agreement; engaged by the Town, with a conflict waiver, to update Eldora's 2016 water sufficiency letter for the Forest Service permit transfer", 'Purchase agreement; engagement letter of Oct. 8, 2025 (released Oct. 2026)', None, None),
    ('Due diligence', 'JVA', 'JVA', "The Town's on-call engineers", 'Regular Town vendor', None, None),
    ('Due diligence', 'DiNatale Water Consultants', 'DiNatale Water Consultants', "The Town's water engineers", 'Regular Town vendor', None, None),
    ('Transition and administration', 'Plante Moran', 'P&M Holding Group', 'Financial due diligence ("quality of earnings") on the resort, then HR and finance transition planning; since July 2026 also signs the Town\'s Treasurer reports; includes $853 moved into this account from Professional Services', 'Due diligence engagement letter of Aug. 12, 2025 (released Oct. 2026); Res. 2025-22 covers HR and finance consultants (no firm named); then Res. 2026-12', None, None),
    ('Transition and administration', 'Bolder HR Solutions', 'Susan N. Fattor', 'HR consulting for transitioning Eldora employees, at $150 an hour', 'Res. 2025-22 covers HR and finance consultants (no firm named); agreement effective Oct. 6, 2025 (released Oct. 2026)', None, None),
    ('Transition and administration', 'Datasite', 'Datasite LLC', 'Virtual data room named "Eldora"; $200 monthly minimum for a 36-month term', 'Statement of work (released Oct. 2026); not in the Board documents searched', None, None),
    ('Transition and administration', 'Vadim Municipal Software', 'Vadim Municipal Software Inc', "The Town's accounting software", 'Regular Town vendor', None, None),
    ('Transition and administration', 'Professional Management Solutions', 'Professional Management Systems', 'Role not stated in the records searched', 'no engagement record in the Board documents searched', None, None),
    ('Seller and partners', 'POWDR', 'POWDR Corp', 'The seller. Its $10,721 invoice is for the remaining cost of a three-year audit of Eldora by BDO, and its $124,000 invoice is likely the earlier payment toward that audit (this page\'s reading). Its $50,000 invoice, on no warrant list, is the advance toward Ikon negotiation costs in a Jan. 6, 2026, letter, and its $12,357.75 invoice is the rest of the Town\'s half of Hogan Lovells\' Ikon fees (POWDR\'s Sept. 22, 2026, email)', 'Purchase agreement', None, None),
    ('Seller and partners', '303 Ski', None, 'Advisory partner in 2025; the Town declined its reimbursement requests', 'Announced in FAQ 3.0', 'April 2026: FAQ 6.0', None),
]
BADGE_SAYS = {'Regular Town vendor', 'no engagement record in the Board documents searched'}
WHO_NOTE = ('Roles are as stated in Town documents. "Last documented" is the latest evidence in the records, not whether a '
            'firm is still engaged: invoices are often paid months late, and the Town has not said which firms are still '
            'working on the deal.')
UNPAID = [
    ('Fees owed only if the sale closes', [
        ('Stifel', 'Municipal advisor: structures the financing and coordinates the deal team, and owes the Town a fiduciary duty "to act in your best interests without regard to our financial or other interests." Named in the Jan. 2026 draft purchase agreement; extended July 7, 2026', '$325,000 at bond sale', 'agreement runs through June 30, 2027; confirmed $0 owed as of Oct. 16, 2026', 130472),
        ('Northland Securities', 'Underwriter under a non-binding engagement (Res. 2025-02). "If no bonds are issued, no fees will be incurred"', 'Share of bonds', 'last mentioned April 2025', 118128),
        ('Butler Snow', 'Disclosure counsel. Its Aug. 13, 2025, engagement letter estimates a $100,000 fee, "paid at Closing out of proceeds of the Bonds" (released Oct. 2026)', 'Est. $100,000 at closing', 'last named April 2026 (FAQ 6.0)', None),
    ]),
    ('Named in Town records; fee terms not in the records searched', [
        ('RBC Capital Markets and BofA Securities', 'Underwriters, engaged by Nov. 2025 and approved in Ord. 885, to buy the bonds "on a best-efforts basis." The Res. 2025-11 memo anticipates pay contingent on a financing', 'Not in records searched', 'last named April 2026 (FAQ 6.0)', 125525),
        ('J.P. Morgan Securities', 'Underwriter under a non-binding letter of intent (Res. 2025-08)', 'None stated', 'last mentioned April 2025', 120603),
        ('303 Ski', 'Advisory partner announced in FAQ 3.0; by April 2026 the Town had decided not to go forward with it and had declined its requests for reimbursement', 'None', 'last mentioned April 2026 (FAQ 6.0)', None),
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
    rows = [('Eldora, if the sale fails (paid plus confirmed owed)', estimate, 0, None, 'no grants'),
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
    due_bal, extra = 0.0, 0.0
    for r in rows:
        r['amt'] = float(r['amount'])
        if r['account'] == '10-00-1150':
            due_bal = -amt(r['account_balance_after'])
        else:   # "Eldora Expense" (10-10-7000): its listed balance is year-to-date, so add each payment to the total
            extra += r['amt']
        r['bal'] = due_bal + extra
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
    # Paid and owed in one table: each firm's payments and what it confirmed it is owed as of Oct. 16, 2026
    num = lambda v: v if isinstance(v, float | int) else 0   # noqa: E731
    base = json.load(open(os.path.join(ROOT, 'site_config.json'))).get('base_url', 'https://eldorarecord.org/')
    conf_by = {CONF_VENDOR.get(firm, firm): (inv + num(unb), key, note, inv, unb) for firm, inv, unb, key, note in CONFIRMED}
    conf_total = sum(c[0] for c in conf_by.values())
    entries = [(total, PAYEES[v][0], PAYEES[v][1], v) for v, total in vendors]
    if abs(unattributed) >= 0.5:
        entries.append((unattributed, 'Not on any warrant list', 'unk', None))
    entries += [(0, k, 'owed', k) for k, c in conf_by.items() if k not in by_vendor and c[0] > 0]
    owed_of = lambda v: conf_by[v][0] if v in conf_by else 0   # noqa: E731
    top = max(t + owed_of(v) for t, _, _, v in entries)
    who_by_firm = {w[1]: w for w in WHO}
    tag_text = dict(EVIDENCE, unk='Payee not in the records searched', owed='No payments yet')
    vrows = []
    for total, name, tier, v in sorted(entries, key=lambda x: -(x[0] + owed_of(x[3]))):
        key = 'unk' if tier == 'unk' else (v if v in PAYEE_ANCHORS else None)
        fid = PAYEE_ANCHORS.get(key) if key else None
        cls = 'unk' if tier == 'unk' else ''
        if tier == 'owed':
            w = who_by_firm.get(v)
            role = e(f'{w[3]} · {w[4]}' if w else conf_by[v][2]).replace('&amp;', '&')
        elif v:
            w = who_by_vendor[v]
            li = last_invoice[v]
            # The evidence badge already says these, so the role line leaves them out
            basis = '' if w[4] in BADGE_SAYS else f' · {w[4]}'
            role = (e(f'{w[3]}{basis} · ').replace('&amp;', '&')
                    + f'<span class="lastdoc">latest paid invoice {MONTHS_FULL[li.month - 1]} {li.year}</span>')
        else:
            role = e('Added to the account between warrant lists; payee not in the records searched')
        doc = INV_LINKS.get(name)   # invoices and emails released Nov. 16, 2026 (records request)
        if doc:
            role += f' · <a href="{base}{INV[doc[0]]}" target="_blank" rel="noopener">{doc[1]}</a>'
        c = conf_by.get(v)
        if c and c[2] and not (tier == 'owed' and v not in who_by_firm):
            role += f'<div class="owednote">Owed: {e(c[2]).replace("&amp;", "&")}</div>'
        owed = c[0] if c else 0
        none = '<span class="muted" title="No confirmation in the records released">&mdash;</span>'
        part = lambda v: (f'<a href="{base}records/{CORA_OCT29[c[1]]}" target="_blank" rel="noopener">{money(v, True)}</a>'   # noqa: E731
                          if isinstance(v, float | int) else '<span class="muted" title="Left blank, or not covered by the firm\'s report">&mdash;</span>')
        owed_cells = (f'<td class="num" data-label="Invoiced, unpaid">{part(c[3])}</td><td class="num" data-label="Not yet invoiced">{part(c[4])}</td>' if c
                      else f'<td class="num" data-label="Invoiced, unpaid">{none}</td><td class="num" data-label="Not yet invoiced">{none}</td>')
        vrows.append(f'<tr{f" class=\"{cls}\"" if cls else ""}{f" id=\"{fid}\"" if fid else ""}><td class="who">{e(name)} '
                     f'<span class="ev ev-{tier} sm">{tag_text[tier]}</span><div class="role">{role}</div></td>'
                     f'<td class="bar"><span class="stack"><span class="b-{tier}" style="width:{total / top * 100:.1f}%"></span>'
                     f'<span class="b-owed" style="width:{owed / top * 100:.1f}%"></span></span></td>'
                     f'<td class="num" data-label="Paid">{money(total, True)}</td>{owed_cells}</tr>')
    conf_inv_t = money(sum(r[1] for r in CONFIRMED))
    conf_unb_t = money(sum(r[2] for r in CONFIRMED if isinstance(r[2], float | int)))
    vrows.append(f'<tr class="pay-total"><td class="who"><strong>Total: {money(balance + conf_total)}</strong>'
                 f'<div class="role">Paid plus owed</div></td><td class="bar"></td>'
                 f'<td class="num" data-label="Paid"><strong>{money(balance, True)}</strong></td><td class="num" data-label="Invoiced, unpaid"><strong>{conf_inv_t}</strong></td>'
                 f'<td class="num" data-label="Not yet invoiced"><strong>{conf_unb_t}</strong></td></tr>')
    for heading, firms in UNPAID:
        vrows.append(f'<tr class="who-group"><td colspan="5">{e(heading)}</td></tr>')
        for firm, role, fee, lastdoc, doc in firms:
            src = (f' (<a href="https://nederlandco.civicweb.net/document/{doc}/" target="_blank" rel="noopener">source</a>)'
                   if doc else '')
            conf_link = (f' (<a href="{base}records/{CORA_OCT29[conf_by[firm][1]]}" target="_blank" rel="noopener">confirmation</a>)'
                         if firm in conf_by else '')
            vrows.append(f'<tr class="unpaid"><td class="who">{e(firm)}<div class="role">{e(role)}{src} · '
                         f'<span class="lastdoc">{e(lastdoc)}</span>{conf_link}</div></td><td class="bar"></td>'
                         f'<td class="num" colspan="3">{e(fee)}</td></tr>')

    site = json.load(open(os.path.join(ROOT, 'site_config.json'))).get('base_url', 'https://eldorarecord.org/')
    rec_ledger, rec_reply, rec_reply2 = site + CORA_LEDGER, site + CORA_REPLY, site + CORA_REPLY2
    rec_ind = site + CORA_INDENTURE
    rec_reply3 = site + CORA_REPLY3
    rec_slides = site + SLIDES
    rec_x = dict(rec_ds2=site + DS2, rec_ds_reply=site + DS_REPLY, rec_audit_emails=site + AUDIT_EMAILS,
                 rec_audit_reply=site + AUDIT_REPLY, rec_scen=site + SCEN, rec_bud_reply=site + BUD_REPLY,
                 rec_inv_reply=site + INV_REPLY, **{f'rec_{k}': site + v for k, v in INV.items()})
    rec_oct20 = {f'rec_{k}': f'{site}records/{v}' for k, v in CORA_OCT20.items()}
    rec_oct20.update({f'rec_{k}': f'{site}records/{v}' for k, v in CORA_OCT29.items()})
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
    town_estimate = 2_760_000     # Town's latest estimate of costs not reimbursed if the sale fails: draft Res. 2026-31 (Nov. 9, 2026), citing "Sept. 30, 2026, updated estimates" (not itemized); its Sept. 30 update said about $2.5M
    # This page's itemized total, used in the calculations: paid plus what firms confirmed owed as of Oct. 16, 2026
    estimate = balance + conf_total
    unpaid = conf_total
    # Whose cash would pay (this page's calculation from the Town's Sept. 30, 2026, balance sheets, September financials):
    # each utility's pooled cash less its state-loan reserve and an operating reserve; the funds owed each other nothing then
    w_avail = 2_237_641 - 306_250 - 175_921
    s_avail = 918_807 - 130_000 - 172_296
    since_sep = round(sum(r['amt'] for r in rows if r['warrant_meeting'] > '2026-09-30'))   # Eldora paid after Sept. 30
    gf_short = -105_870 - since_sep
    # the General Fund's operating result for the rest of 2026 isn't included (the Town forecasts -$220,004 for the year)
    need_lo = need_hi = -gf_short + conf_total
    mm = lambda v: f'${v / 1e6:.2f} million'   # noqa: E731
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
    # General Fund at the end of 2026. The Town's own forecast (Nov. 9, 2026, budget presentation) charges its Eldora
    # estimate to the General Fund: $622,925 in 2025 and $2,135,661 in 2026. This page's figure uses the same 2025 audit
    # balance and the Town's 2026 forecast without Eldora, with this page's itemized total in place of the Town's estimate.
    gf_cash_2025, gf_owed_2025, gf_bal_2025, gf_bud_2026 = -757_482, 1_456_233, 1_030_078, 583_730
    town_ops_2026, town_eldora, town_fb_2026, town_fb_2027 = -220_004, 622_925 + 2_135_661, -1_948_512, -2_132_122
    assert gf_bal_2025 + town_ops_2026 - town_eldora == town_fb_2026
    since = round(balance) - round(bal_2025)
    cash_end = gf_cash_2025 + gf_owed_2025 - since - (estimate - balance)
    fb_end = gf_bal_2025 + town_ops_2026 - estimate
    neg = lambda v: '\u2212' + money(-v) if v < 0 else money(v)   # noqa: E731
    # The same numbers, for the short-form FAQ (scripts/faq_page.py) and its charts, so the two pages can't drift apart
    raw = dict(balance=round(balance), owed=round(conf_total), total=round(estimate), town_estimate=town_estimate,
               gf_bal_2025=gf_bal_2025, bud_change=gf_bud_2026 - gf_bal_2025, fb_end=round(fb_end), gf_ops=gf_ops,
               town_ops_2026=town_ops_2026, town_eldora=town_eldora, town_fb_2026=town_fb_2026,
               points=[(dt.isoformat(), round(v)) for dt, v in points])
    fig = dict(
        w_avail=money(w_avail), s_avail=money(s_avail), u_avail=money(w_avail + s_avail), u_avail_m=mm(w_avail + s_avail),
        w_avail_m=mm(w_avail), s_avail_m=mm(s_avail), gf_short=neg(gf_short), since_sep=money(since_sep), conf_inv2=money(sum(r[1] for r in CONFIRMED)),
        need_lo=mm(need_lo), need_hi=mm(need_hi), left_hi=mm(w_avail + s_avail - need_lo), left_lo=mm(w_avail + s_avail - need_hi),
        hh_paid=per_hh(balance), hh_est=per_hh(estimate), hh_town=per_hh(town_estimate),
        owed=money(estimate), owed_m=m(estimate), owed_short=f'${estimate / 1e6:.1f}M', neg_owed=neg(-estimate),
        wo_m=f'about ${-(gf_bal_2025 - estimate) / 1e6:.1f} million', cap_yrs=f'{int(estimate // 200_000)}',
        res_est=money(estimate / 1471), avg_rep=money(round(avg_rep, -3)), avg_op=money(round(avg_op, -3)),
        yrs_est=f'{yrs(estimate, avg_rep)} to {yrs(estimate, avg_op)}', yrs_paid=f'{yrs(balance, avg_rep)} to {yrs(balance, avg_op)}',
        data_links=data_links,
        cash_after=money(gf_cash_2025 + gf_owed_2025), unpaid_x=money(estimate - balance),
        cash_end=neg(cash_end),
        fb_end=neg(fb_end), fb_end_m=f'about ${-fb_end / 1e6:.1f} million', bud_change=neg(gf_bud_2026 - gf_bal_2025),
        yrs_def=f'{yrs(2_180_816, avg_rep)} to {yrs(2_180_816, avg_op)}',
        town_fb=neg(town_fb_2026), town_fb_m=f'about ${-town_fb_2026 / 1e6:.1f} million', town_fb27=neg(town_fb_2027), town_fb27_m=f'about ${-town_fb_2027 / 1e6:.1f} million',
        town_ops=neg(town_ops_2026), town_eldora=money(town_eldora), fb_gap=money(town_fb_2026 - fb_end),
        ufb_2026=f'\u2212{-(town_fb_2026 - 147_000 - 10_905) / gf_ops:.2f}',   # unrestricted = balance less restricted and nonspendable (2025 audit)
        scale_chart=scale_chart(balance, estimate),
        pct_paid=f'{balance / gf_ops:.0%}', pct_est=f'{estimate / gf_ops:.0%}', x_comp=f'{balance / 205_188:.0f}',
        changes=change_log(), latest=latest_update(),
        hogan=money(by_vendor['Hogan Lovells US LLP']),
        powdr=money(by_vendor['POWDR Corp']), pct_unpaid=f'{unpaid / gf_ops:.0%}', unpaid_4=money(round(unpaid / 4, -3)), unpaid=m(unpaid), unpaid_short=f'${unpaid / 1e6:.1f}M',
        method=method_html('record'), district_taxes=district_taxes_html(), **district_taxes_summary(), cov_from=cov_from, cov_through=cov_through, cov_updated=cov_updated,
        votes_css=votes['css'], votes_html=votes['html'], votes_js=votes['js'],
        n_actions=votes['n_actions'], n_sessions=votes['n_sessions'], n_es_gaps=votes['n_gaps'], first_es=votes['first'],
        n_pay=len(rows) + len(OFF_LIST), balance=money(balance), balance_c=money(balance, True), since_2025=money(round(balance) - round(bal_2025)), bal_2025=money(bal_2025), listed=money(listed), n=len(rows),
        unlisted=money(balance - listed), unlisted_about=f'about ${round((balance - listed) / 1000):,},000', moved=money(moved), site=site, subscribe=SUBSCRIBE, rec_ledger=rec_ledger, rec_reply=rec_reply, rec_reply2=rec_reply2, rec_reply3=rec_reply3, rec_slides=rec_slides, **rec_x, nov9_min=NOV9_MIN, rec_ind=rec_ind, **rec_oct20, kline=money(by_vendor['Kline Veio']), top=e(top_payees), asof=fmt(points[-1][0]), chart=costs_chart(raw) + costs_chart(raw, narrow=True),
        vendors=''.join(vrows), ledger=''.join(ledger),
        conf=money(conf_total), conf_m=m(conf_total),
        conf_inv=money(sum(r[1] for r in CONFIRMED)),
        conf_unb=money(sum(r[2] for r in CONFIRMED if isinstance(r[2], float | int))), conf_short=f'${conf_total / 1e6:.1f}M',
        conf_all=money(conf_total + balance), conf_all_m=m(conf_total + balance),
        disc_total=f'about ${(estimate - 0.1 * (40_000 + 1_174_082.66)) / 1e6:.2f} million',   # Brownstein's 10% broken-deal discount on all its confirmed fees
        named=money(tier_total['named']), coding=money(tier_total['coding']), none=money(tier_total['none']))
    fig['gf_chart'] = gf_chart(raw) + gf_chart(raw, narrow=True)
    export = {k: v for k, v in fig.items() if isinstance(v, str) and '<' not in v and not k.startswith('votes_')}
    export.update(top_payees=top_payees, n_actions=str(fig['n_actions']), n_sessions=str(fig['n_sessions']))
    with open(os.path.join(ROOT, 'analysis', 'figures.json'), 'w') as f:
        json.dump({'text': export, 'raw': raw}, f, indent=1)
    page = TEMPLATE.format(**fig)
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
/* Links to the site's other pages, at the top of the record */
.site-pages {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin: 6px 0 2px; }}
.site-pages a {{ display: grid; gap: 4px; grid-template-rows: auto 1fr auto; padding: 10px 12px; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; color: var(--fg); text-decoration: none; }}
.site-pages a:hover, .site-pages a:focus-visible {{ border-color: var(--accent); }}
.site-pages b {{ color: var(--accent); font-size: 15px; line-height: 1.25; }}
.site-pages span {{ font-size: 13px; color: var(--muted); line-height: 1.35; }}
.site-pages .pk {{ font: 500 10.5px var(--mono); font-style: normal; text-transform: uppercase; letter-spacing: .08em; margin-top: 2px; padding: 0; }}
.site-pages .pk-fact {{ color: var(--accent); }}
.site-pages .pk-op {{ color: var(--warn); }}
.zero {{ stroke: var(--muted); stroke-width: 1.2; }}
.wf-start {{ fill: var(--accent); }}
.wf-down {{ fill: var(--warn); }}
.wf-end {{ fill: var(--fg); }}
.wf-link {{ stroke: var(--muted); stroke-dasharray: 3 3; }}
.wf-lab {{ fill: var(--fg); font: 600 12px var(--mono); text-anchor: middle; }}
.wf-cat {{ fill: var(--muted); font: 11px var(--body); text-anchor: middle; }}
.site-check {{ border-left: 3px solid var(--warn); padding-left: 16px; display: grid; gap: 14px; }}
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
.dot {{ fill: var(--warn); }}
.ct-area {{ fill: var(--warn-soft); stroke: none; }}
.ct-line {{ fill: none; stroke: var(--warn); stroke-width: 2; }}
.ct-owed {{ fill: var(--warn); }}
.ct-est {{ stroke: var(--fg); stroke-dasharray: 5 4; stroke-width: 1.2; }}
.ct-lab {{ fill: var(--fg); font: 600 13px var(--mono); }}
.ct-note {{ fill: var(--muted); font: 11px var(--mono); }}
.scroll {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
th, td {{ padding: 9px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); }}
tbody tr:last-child td {{ border-bottom: 0; }}
thead th {{ font: 600 12px/1.2 var(--body); color: var(--muted); text-transform: uppercase; letter-spacing: .05em; background: var(--surface); position: sticky; top: 0; }}
.num {{ font-family: var(--mono); font-size: 13.5px; text-align: right; white-space: nowrap; }}
th.num {{ text-align: right; }}
.mono, .dt {{ font-family: var(--mono); font-size: 13px; white-space: nowrap; }}
td.who {{ min-width: 200px; }}
.payees-t th.num {{ white-space: normal; min-width: 7em; }}
.role {{ font-size: 13px; color: var(--muted); }}
td.bar {{ width: 28%; min-width: 120px; vertical-align: middle; }}
td.bar span {{ display: block; height: 10px; border-radius: 2px; background: var(--warn); opacity: .85; }}
tr.unk td.bar span {{ background: repeating-linear-gradient(45deg, var(--warn) 0 4px, transparent 4px 8px); }}
td.bar span.b-coding {{ opacity: .6; }}
td.bar span.b-none {{ opacity: .35; }}
td.bar span.stack {{ display: flex; background: none; opacity: 1; border-radius: 0; }}
td.bar span.stack span {{ flex: none; border-radius: 0; }}
td.bar span.stack span:first-child {{ border-radius: 2px 0 0 2px; }}
td.bar span.b-owed {{ background: repeating-linear-gradient(45deg, var(--warn) 0 2px, var(--warn-soft) 2px 5px); box-shadow: inset 0 0 0 1px var(--warn); opacity: 1; border-radius: 0 2px 2px 0; }}
.bar-key span {{ display: inline-block; width: 18px; height: 10px; vertical-align: middle; border-radius: 2px; }}
.bar-key .key-paid {{ background: var(--warn); opacity: .85; }}
.bar-key .key-owed {{ background: repeating-linear-gradient(45deg, var(--warn) 0 2px, var(--warn-soft) 2px 5px); box-shadow: inset 0 0 0 1px var(--warn); }}
.ev-owed {{ border: 1px solid var(--warn); color: var(--warn); }}
.owednote {{ margin-top: 2px; }}
tr.pay-total td {{ border-top: 2px solid var(--line); }}
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
  /* each firm becomes a block: name and notes, then its three amounts side by side, each labeled */
  .scroll:has(> table.payees-t) {{ overflow: visible; }}
  .payees-t thead {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }}
  .payees-t tr {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 10px; padding: 10px 12px; border-bottom: 1px solid var(--line); }}
  .payees-t td {{ display: block; border: 0; padding: 2px 0; }}
  .payees-t td.who, .payees-t tr.who-group td, .payees-t tr.unpaid td.num {{ grid-column: 1 / -1; }}
  .payees-t td.num {{ text-align: left; }}
  .payees-t .lastdoc {{ white-space: normal; }}
  .payees-t td.num[data-label]::before {{ content: attr(data-label); display: block; font: 600 10px/1.3 var(--body); text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }}
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
tr.unpaid td.num {{ font-size: 13px; color: var(--muted); white-space: normal; text-align: right; }}
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
    <nav class="site-pages" aria-label="Other pages on this site">
      <a href="{site}citizen-plan.html"><b>Citizen Plan</b><span>A proposal from residents to pay the Eldora costs and balance the 2027 budget</span><em class="pk pk-op">Proposal</em></a>
      <a href="{site}cliffs-notes.html"><b>The Eldora Deal Cliffs Notes</b><span>The whole story in order, in plain language, and what may happen next</span><em class="pk pk-op">Facts and a prediction</em></a>
      <a href="{site}opinion.html"><b>My opinions</b><span>The odds the deal closes, the price, and what the Board should do</span><em class="pk pk-op">Opinion</em></a>
      <a href="{site}resolution.html"><b>Resolution 2026-31</b><span>My proposed amendments limiting acquisition spending</span><em class="pk pk-op">Opinion</em></a>
    </nav>
    <p class="lede">As of the {asof} warrant list, the Town had paid <strong>{balance_c}</strong> in Eldora acquisition costs, and firms had confirmed another <strong>{conf}</strong> owed, for <strong>about {owed_m}</strong> in all (<a href="#payees">who was paid and who is owed</a>); the Town estimates <a href="#bottom-line">about $2.76 million</a>, not itemized. All of it is charged to the General Fund. <a href="#no-limits">No budget line was set for it</a>, and until Nov. 17 no dollar limit was either, but the costs count against the General Fund&rsquo;s 2026 appropriation, set for the fund as a whole, and staff forecast 2026 spending including them at <a href="#deficit-law">$180,221 under it</a>. The <a href="#no-sale">purchase agreement expired</a> in April 2026, and the Town is pursuing a <a href="#revised-plan">restructured deal</a> and listing possible donations and partners. Staff&rsquo;s Nov. 16 tables put the General Fund&rsquo;s available balance at <a href="#gf-tables">&minus;$2,180,816 at the end of 2026</a> and &minus;$2,528,102 at the end of 2027; the Nov. 9 forecast was {town_fb} and {town_fb27}, and with this page's itemized total its 2026 figure would be about {fb_end}. To close the gap, staff now propose <a href="#nov16-plan">transfers from the Community Center, Water, and Sewer Funds</a>, citing user fees and the Board's power to transfer money between funds; for Dec. 1 they no longer propose amending the 2026 budget, saying the General Fund is likely to stay within its 2026 appropriation. By <a href="#budget-check">this site's check</a>, the plan's split asks more of the Sewer Fund than its stated limit and its cash, relies on Community Center money that <a href="#fund-dedications">voters approved for the Community Center</a>, and closes only if nearly all of the money in all three funds can be used. <a href="#res-2026-31">Resolution 2026-31</a>, adopted Nov. 17, limits further acquisition spending, requires monthly cost reports and a Dec. 15 accounting, and ends the Town&rsquo;s pursuit if a milestone passes without an extension, the first a term sheet by Feb. 15, 2027; the Interim Town Manager told eight firms Nov. 20 to pause billable work, and staff report about $170,000 in potential fee reductions. Records released Nov. 26 show that <a href="#ikon-advance">Hogan Lovells</a>, paid $148,795, is Alterra Mountain Company's counsel on the Ikon agreement, whose fees the Town shares with POWDR. The page also covers what would change <a href="#if-closes">if the purchase closes</a>, including the <a href="#bond-schedule">bond payment schedules</a> and <a href="#district-taxes">property taxes</a> for the fire and library districts; <a href="#town-statements">what the Town has told the public</a>; <a href="#open-questions">what the records searched don't show</a>; and every <a href="#board-votes">Board vote on the acquisition</a>, each unanimous among the trustees present.</p>
    <p class="disclaimer">This is an independent compilation, not affiliated with, endorsed by, or produced by the Town of Nederland, Eldora Mountain Resort, or POWDR. It is built from the Town's own public records: Board of Trustees meeting records from {cov_from} through {cov_through} on the Town's CivicWeb portal, and other Town boards' meeting records from January 2024; resolutions, ordinances, finance documents, and staff reports from all years; posts on the Town website and Facebook page; and Town records released in response to a public records request. The section on <a href="#district-taxes">property taxes</a> also uses Boulder County Assessor and Treasurer records. Statements that something isn't in the records refer only to the records searched (see <a href="#method-ai">How this research was done</a>). Last updated {cov_updated}; the page is updated about once a month, and sooner when there is significant news. Corrections are welcome: <a href="mailto:corrections@eldorarecord.org">corrections@eldorarecord.org</a>.</p>
    <nav class="toc" aria-label="On this page">
      <div><b>Overview</b><a href="#findings-h">Findings</a><a href="#in-brief">The acquisition in brief</a></div>
      <div><b>Spent and owed</b><a href="#costs">Who was paid and who is owed</a><a href="#recorded">How the costs are recorded</a></div>
      <div><b>The cost to the Town</b><a href="#bottom-line">The bottom line</a><a href="#gf-deficit">General Fund deficit</a><a href="#other-funds">Could other funds cover it?</a><a href="#afford">How big is it?</a></div>
      <div><b>If the purchase closes</b><a href="#commitments">Commitments</a><a href="#profit">Profit</a><a href="#district-taxes">Property taxes</a></div>
      <div><b>Records and statements</b><a href="#town-statements">What the Town said</a><a href="#board-knowledge">Cost information</a></div>
      <div><b>Get involved</b><a href="#get-involved">How to get involved</a></div>
      <div><b>Reference</b><a href="#ledger">Payments</a><a href="#open-questions">Not in the records searched</a><a href="#board-votes">Votes</a><a href="#changes">Changelog</a><a href="#method-ai">How this was built</a></div>
    </nav>
    {latest}
  </header>

  <div class="facts">
    <div class="fact spent"><span class="tag paid">Already paid</span><b>{balance}</b><span>Charged to the <a href="#funding">General Fund</a> through the <a href="#ledger">{asof} warrant list</a></span></div>
    <div class="fact spent"><span class="tag paid">Owed, not yet paid</span><b>~{conf_short}</b><span><a href="#owed-confirmed">Confirmed by firms</a> as of Oct. 16, 2026, less invoices paid Nov. 9, including {conf_inv} <a href="#overdue">already invoiced</a>, some more than a year ago</span></div>
    <div class="fact"><span class="tag auth">Expired</span><b>$120M</b><span>Purchase price in the <a href="#commitments">agreement approved Jan 6, 2026</a></span></div>
    <div class="fact spent"><span class="tag paid">Total costs</span><b>~{owed_short}</b><span>What is paid plus what firms confirmed owed, now counted as spending whether or not the sale closes (<a href="#bottom-line">this page's itemized total</a>). The Town estimates about $2.76M, not itemized</span></div>
  </div>

  <section class="findings" aria-labeledby="findings-h">
    <h2 id="findings-h">Summary of findings based on records searched</h2>
    <ol>
      <li><strong>The Town has <a href="#costs">paid {balance}</a>, all charged to its <a href="#funding">General Fund</a></strong>, at first as money it expected to recover from <a href="#commitments">revenue bonds</a> that haven't been sold; the Town's Nov. 9, 2026, forecast now counts the costs as <a href="#receivable">spending</a>. The <a href="#no-sale">purchase agreement has expired</a>. The Town says it is pursuing a <a href="#revised-plan">restructured sale-leaseback</a>, but as of Oct. 22, 2026, the lease &ldquo;has not been drafted&rdquo; (<a href="{rec_reply2}" target="_blank" rel="noopener">Town response</a>).</li>
      <li><strong>The costs come to <a href="#bottom-line">about {owed_m}</a> by this page's itemized total, and the Town now counts them as spending whether or not the sale closes (<a href="#per-household">{hh_est} per household</a>): {balance} paid and {conf} that firms confirmed owed.</strong> The Town estimates about $2.76 million, not itemized (<a href="#bottom-line">the bottom line</a>). The General Fund has little or no cash of its own, so paying would use other funds' pooled cash, mostly the Water and Sewer Funds' (<a href="#other-funds">Could other funds cover it?</a>). The Town's own Nov. 9 forecast already charges its estimate to the General Fund, ending 2026 at <a href="#gf-tables">{town_fb}</a>; with this page's itemized total, the figure would be about {fb_end}. Neither <a href="#bankruptcy">bankruptcy nor dissolving the Town</a> would remove the costs.</li>
      <li><strong>To cover the deficit, staff propose transfers from the Community Center, Water, and Sewer Funds; by this site's check, the plan doesn't close as presented.</strong> The Nov. 16 memo lists up to $800,000 from the Community Center and $2.3 million from the utilities, from &ldquo;user fees&rdquo; (<a href="#nov16-plan">the Nov. 16 plan</a>). Voters approved the Community Center's sales tax for the Community Center, most recently in April 2022, and dedicated the utilities' sales tax to their debt; the Town's own Sept. 30 balance sheet and the 2025 audit report the whole Community Center Fund as restricted, and staff's own Oct. 30 spreadsheet assumed it was (<a href="#fund-dedications">what voters approved</a>). The memo's 75% Sewer share exceeds Sewer's stated limit and its cash, and without the Community Center money the utilities' maximum falls short of the gap (<a href="#budget-check">this site's check</a>).</li>
      <li id="overdue"><strong>Some Eldora invoices have gone unpaid for more than a year.</strong> Of what is owed, {conf_inv} had been invoiced and was unpaid as of Oct. 16, 2026, and wasn't paid on the Nov. 9 warrant list, including Williams Weese Pepple &amp; Ferguson invoices dating to Aug. 11, 2025, with $84,457 more than 90 days past due on its Sept. 9 statement (<a href="{rec_wwpf_stmt}" target="_blank" rel="noopener">statement</a>), and Dickinson Wright invoices dating to Oct. 29, 2025. Dickinson Wright's emails listing its unpaid invoices went to the Mayor from November 2025, and the Mayor replied to the January email, &ldquo;Thanks Sarah&rdquo;; from May 2026 they also went to the Town Manager and the Town's accounts payable (<a href="{rec_dw_emails}" target="_blank" rel="noopener">emails</a>). None of these unpaid invoices is on a warrant list searched. A Hogan Lovells invoice of May 29, 2026, for $8,943, which POWDR says is &ldquo;directly attributable to the Town,&rdquo; is also unpaid; the Town Attorney sent it to the Town's accounts payable Oct. 29, and it isn't in the firms' confirmations (<a href="{rec_hl_inv}" target="_blank" rel="noopener">invoices and emails</a>).</li>
      <li><strong>No budget covers the acquisition costs, and every Board vote on the acquisition was unanimous among the trustees present.</strong> <a href="#no-limits">Neither the 2025 nor the 2026 budget includes them</a>. The warrant lists the Board approved <a href="#running-total">showed the payments and the account's running balance</a>. The Board made <a href="#board-votes">{n_actions} decisions and {n_sessions} votes to meet in closed session</a> on the acquisition since {first_es}.</li>
      <li><strong>Lawyers and consultants received most of the money.</strong> The <a href="#payees">largest payees</a> are {top}. {named} went to firms whose role is stated in a Board document, {coding} to regular Town vendors linked to the acquisition only by account coding, and {none} to firms that appear in no Board document searched except the warrant lists. The resolutions delegating authority to hire them <a href="#no-limits">set no dollar limits</a>.</li>
      <li><strong>The Town hasn't itemized its <a href="#bottom-line">estimate</a>, now about $2.76 million.</strong> Asked for the records behind its Sept. 30 estimate of about $2.5 million, the Town released on Oct. 29, 2026, the firms' confirmations of what they were owed as of Oct. 16, but no worksheet for the estimate (<a href="{rec_reply4}" target="_blank" rel="noopener">Town response</a>). Most of what is owed, $1,174,083, not yet invoiced, is to real estate counsel Brownstein Hyatt Farber Schreck, whose agreement bills when the transaction is completed or terminated. The response includes no confirmation from Hogan Lovells, Plante Moran, or POWDR (<a href="#payees">who is owed</a>).</li>
      <li><strong>If the purchase closes, the fire and library districts would lose part of their tax base.</strong> By this page's estimate, if the sellers' property became tax-exempt Town property, the Nederland Fire Protection District would stop collecting {dt_fire} a year ({dt_fire_pct} of its property tax) and the Nederland Community Library District {dt_lib} ({dt_lib_pct}) (<a href="#district-taxes">Property taxes on the resort</a>).</li>
    </ol>
    <p class="prose muted">Gaps in the records are listed under <a href="#open-questions">Not in the records searched</a>, with the records that could fill them.</p>
  </section>

  <aside class="statement prose" id="statement" aria-label="Statement from the researcher">
      <b>Why I made this page</b>
      <p>I built this page while researching the Town's public records on its website and CivicWeb portal. Like many residents, my views on the Eldora acquisition have changed over time, but from the start I worried about the cost of pursuing it and the risk to the Town if the deal fell through, since those costs would be repaid only if the sale closed. This page tracks those costs from the Town's own records and gathers information scattered across thousands of documents, to help us figure out the best path forward.</p>
      <p><strong>My opinions about what will happen and what the Town should do are on <a href="{site}opinion.html">a separate page</a>, so that they stay apart from the record. Because the sale is still more likely to fail than close, I recommend that the Board limit spending on the acquisition, set firm deadlines for ending the effort that it can extend only by a vote, and focus on the Town's finances and the 2027 budget. I've drafted <a href="{site}resolution.html">a resolution</a> that would do that; the Town Attorney revised it as <a href="#res-2026-31">Resolution 2026-31</a>, and I recommend adopting it with the amendments on <a href="{site}opinion.html#recommendation">my opinion page</a>. On <a href="{site}opinion.html#debt-check">my rough review of the numbers</a>, any future attempt should start from a cash price of about $70 million or less.</strong></p>
      <p class="sig">— Dallas Masters, Nederland resident · Questions and corrections: <a href="mailto:corrections@eldorarecord.org">corrections@eldorarecord.org</a></p>
    </aside>

  <section id="in-brief" class="prose">
    <h2>The acquisition in brief</h2>
    <p>POWDR put Eldora Mountain Resort, the ski area just west of Nederland, up for sale in 2024. The Town plans to buy it through a new Town-owned business, the Mountain Recreation Enterprise, and pay with <a href="#funding">revenue bonds repaid only from the resort's income</a>, not taxes. In the May 2026 draft bond documents, part of the price would have been paid in <a href="#may-draft">bonds to POWDR</a>, repaid only after the senior bonds. A January 2026 draft agreement would also have the Town pay POWDR <a href="#transition-services">at least $1 million a year</a> for two years of transition services after closing. Its stated reasons are local control and <a href="#profit">long-term revenue</a> (<a href="https://nederlandco.civicweb.net/document/118506/" target="_blank" rel="noopener">Ord. 873</a>, <a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0</a>), including "addressing recurring budget shortfalls through a more stable revenue base" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a>). The plan is being restructured (<a href="#revised-plan">see below</a>).</p>
    <ol class="steps">
      <li><strong>November 2024:</strong> the Town said it was pursuing the purchase, and on Nov. 19 the Board first discussed it in open session, as a discussion item with no vote (<a href="https://nederlandco.civicweb.net/document/116860/" target="_blank" rel="noopener">memo</a>, <a href="https://nederlandco.civicweb.net/document/118154/" target="_blank" rel="noopener">minutes</a>). Closed sessions on purchasing &ldquo;property for recreational activities&rdquo; began Sept. 3, 2024 (<a href="#board-votes">Board votes</a>).</li>
      <li><strong>July 2025:</strong> <a href="#town-statements">non-binding term sheet</a> signed with POWDR (<a href="https://web.archive.org/web/20250709224556/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-30" target="_blank" rel="noopener">FAQ 3.0</a>).</li>
      <li><strong>January 2026:</strong> Board approved <a href="#commitments">a $120 million purchase and up to $225 million in bonds</a> (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">Ord. 882</a>, <a href="https://nederlandco.civicweb.net/document/127180/" target="_blank" rel="noopener">Ord. 885</a>).</li>
      <li><strong>April 30, 2026:</strong> the purchase agreement's <a href="#no-sale">closing deadline passed without a closing</a> (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §7.1(d)</a>, <a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a>).</li>
      <li><strong>July 19, 2026:</strong> the Board's <a href="#commitments">authority to sell the bonds ran out</a> with no bonds sold (<a href="https://nederlandco.civicweb.net/document/127180/" target="_blank" rel="noopener">Ord. 885 §5(c)</a>).</li>
      <li><strong>September 30, 2026:</strong> the Town said the agreement had expired but it is still pursuing the purchase with <a href="#revised-plan">restructured financing</a> (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>).</li>
    </ol>
    <p id="revised-plan"><strong>Where things stand.</strong></p>
    <ul class="notes">
      <li id="nda-terms"><strong>The agreements.</strong> No purchase agreement is in force; a few terms of the expired one continue, including that <a href="#no-sale">each side pays its own costs</a> (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §7.2, §8.2</a>). The Town remains bound by its confidentiality agreement with POWDR, dated Jan. 10, 2025, and signed for the Town by the Town Administrator. It covers information POWDR provides and anything the Town prepares from it, and ends two years after signing or at closing, whichever comes first, except for material POWDR identifies in writing as a trade secret (§5(a)). Lenders, investors, and financial advisors may see the material only with POWDR's written consent (§1(a)). If Colorado law requires disclosure, the Town agreed, as far as the law allows, to notify POWDR first and to disclose only after POWDR's written consent (§1(d)). Amendments on July 8 and July 10, 2025, signed by the Mayor, let the Town disclose 12 listed items, such as that a term sheet exists and the financing structure, but not the term sheet's contents (<a href="https://www.nederlandco.gov/DocumentCenter/View/674" target="_blank" rel="noopener">agreement and amendments</a>).</li>
      <li id="new-deal"><strong>The new deal.</strong> The Town's Sept. 30 update describes a revised plan: a "sale-leaseback structure tied to the asset," less debt, and <a href="#commitments">about $20 million in philanthropy</a> for capital projects, with the State of Colorado the first potential contributor, "at the beginning stages" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>). Draft Resolution 2026-31 says the Town has been restructuring the deal &ldquo;in response to feedback from prospective bondholders&rdquo;: to &ldquo;reduce the overall amount of debt, to model interest rates and poor snow years more conservatively using the most recent season&rsquo;s actual results,&rdquo; and to separate discretionary capital improvements from the order of bond payments. It says the new deal &ldquo;requires additional work before a term sheet can be presented to the Board&rdquo; (<a href="https://nederlandco.civicweb.net/document/133363/" target="_blank" rel="noopener">Res. 2026-31</a>). Under an Oct. 16 overview, the Enterprise would transfer legal title to the land and improvements to the bond trustee, which would lease the resort back to the Enterprise; after a default, the trustee could act &ldquo;without first completing a traditional foreclosure process,&rdquo; and &ldquo;those remedies could affect who operates or leases the resort.&rdquo; Title would return once the bonds are paid (<a href="https://nederlandco.civicweb.net/document/132788/" target="_blank" rel="noopener">sale-leaseback overview</a>). On Oct. 22 the interim Town Manager wrote that the lease &ldquo;has not been drafted&rdquo; and provided the newest draft indenture, dated as of May 1, 2026, before the sale-leaseback plan (<a href="{rec_reply2}" target="_blank" rel="noopener">Town response</a>); no new bond amount or pledges are in the records searched. A new agreement, lease, or bond ordinance would each need Board approval at a public meeting. Stifel's advisory agreement, extended in July 2026, covers municipal leases as well as bonds (<a href="https://nederlandco.civicweb.net/document/130472/" target="_blank" rel="noopener">agreement</a>).</li>
      <li><strong>Who is doing the work.</strong> An Oct. 20 staff memo says the Town is pursuing the purchase "at the previously negotiated purchase price of $120 million" and exploring "revenue bonds, governmental grants, foundation funding, and private contributions." It says this work "is primarily being performed by the Mayor" and that "the Town is not paying outside consultants to perform this work" (<a href="https://nederlandco.civicweb.net/document/132785/" target="_blank" rel="noopener">Oct. 20 memo</a>).</li>
      <li id="donors"><strong>Donations and partners.</strong> Two documents in the Nov. 17, 2026, packet, also posted on the Town website, list possible ways to raise money for the purchase and later improvements. One says that, &ldquo;as part of the acquisition financing, the Town could recognize people who make substantial contributions,&rdquo; with options such as naming rights, reserved parking, ski storage, and long-term or &ldquo;lifetime&rdquo; passes. It says long-term passes need advance approval by the Forest Service's Regional Forester, may number no more than 200, can't last beyond the term of the special use permit, and must use their proceeds &ldquo;for qualifying capital improvements&rdquo; (<a href="https://nederlandco.civicweb.net/document/133376/" target="_blank" rel="noopener">donor options</a>). The other lists possible support from governments, residents, major donors, foundations, land trusts, and businesses, and says &ldquo;the Town welcomes additional ideas&rdquo; (<a href="https://nederlandco.civicweb.net/document/133377/" target="_blank" rel="noopener">partner support</a>). Neither gives dollar amounts, a goal, a timeline, or named donors or partners (<a href="https://nederlandco.civicweb.net/document/133375/" target="_blank" rel="noopener">Nov. 17 Eldora memo</a>).</li>
      <li><strong>Town staff.</strong> The Town Manager resigned in August 2026, and the Town's previous Town Manager returned as interim Town Manager on Sept. 25, 2026 (<a href="https://nederlandco.civicweb.net/document/132381/" target="_blank" rel="noopener">Aug. 18 minutes, p. 4</a>); her contract runs through Feb. 28, 2027, and recruiting a permanent Town Administrator is expected to begin after the 2027 budget is developed (<a href="https://nederlandco.civicweb.net/document/132750/" target="_blank" rel="noopener">Oct. 20 report</a>, <a href="https://nederlandco.civicweb.net/document/132766/" target="_blank" rel="noopener">reply to public comment</a>). The Town Treasurer retired in 2026 (<a href="https://nederlandco.civicweb.net/document/130712/" target="_blank" rel="noopener">July 21, 2026, Town Manager report</a>; <a href="https://nederlandco.civicweb.net/document/132048/" target="_blank" rel="noopener">Sept. 15, 2026, budget memo</a>); since July 2026, the Town&rsquo;s monthly treasurer reports have been issued by Plante Moran as Town Treasurer (<a href="https://nederlandco.civicweb.net/document/130714/" target="_blank" rel="noopener">July 21 report</a>). The Board packets searched have a report for July (Sept. 1 packet) and then one for September (Nov. 17 packet); none has an August report, and the Sept. 15, Oct. 6, Oct. 20, and Nov. 9 packets have no monthly financial report (<a href="https://nederlandco.civicweb.net/document/131731/" target="_blank" rel="noopener">July report</a>, <a href="https://nederlandco.civicweb.net/document/133493/" target="_blank" rel="noopener">September Treasurer report</a>). The Town Manager's Nov. 17 report lists &ldquo;filling critical Finance Department vacancies (Finance Support Specialist and Town Treasurer)&rdquo; among her immediate priorities (<a href="https://nederlandco.civicweb.net/document/133378/" target="_blank" rel="noopener">Nov. 17 report</a>).</li>
    </ul>
  </section>

  <div class="group" id="money"><span>Spent and owed</span></div>
  <section id="costs">
    <h2>What has been spent and what is owed</h2>
    <p class="prose muted">The Town recorded Eldora acquisition invoices in one General Fund account, <span class="mono">10-00-1150</span>, "Due From," as money it expects to get back, and from the Nov. 9, 2026, warrant list in a new account, &ldquo;Eldora Expense&rdquo; (<a href="#eldora-expense">the new account</a>). The chart shows the total paid after each warrant list approved by the Board, then what firms confirmed is still owed as of Oct. 16, 2026 (<a href="#payees">who is owed</a>). The dashed line is the Town's estimate, about $2.76 million (<a href="#bottom-line">the bottom line</a>). The account first appears in October 2025, with invoices dated from August 2025. Earlier invoices, dated from January 2025, were later moved into it (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>).</p>
    <div class="figure">{chart}</div>
    <h3 id="payees">Who was paid and who is owed</h3>
    <p class="prose muted">{n} payments on Board warrant lists add up to {listed}. The other {unlisted} was added to the &ldquo;Due From&rdquo; account between warrant lists. The Town's ledger for the account, released in response to a public records request (<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>) and posted for 2026 in the Oct. 20, 2026, Board packet (<a href="https://nederlandco.civicweb.net/document/132789/" target="_blank" rel="noopener">Oct. 20 packet copy</a>), names each amount: {moved} in legal and professional-services invoices first paid on earlier warrant lists from other budget lines and later moved into the account, and a $50,000 POWDR invoice dated Jan. 6, 2026, that is on no warrant list. These amounts are included below.</p>
    <p class="prose">No invoice line names Eldora; the warrant lists give only the account. Each payee was checked against the other records searched and rated by whether a Board document states its role in the Eldora acquisition.</p>
    <ul class="evkey prose">
      <li><span class="ev ev-named">Named in Board documents</span><span>A resolution, staff memo, or the purchase agreement states this firm's role in the Eldora acquisition. Total {named}.</span></li>
      <li><span class="ev ev-coding">Account coding only</span><span>A regular Town vendor. Its other Town work is billed to normal budget lines in the same months, and only the Town's account coding links these charges to the Eldora acquisition. Total {coding}.</span></li>
      <li><span class="ev ev-none">No other record</span><span>Appears in no Board document searched except the warrant lists. Total {none}.</span></li>
    </ul>
    <p class="prose" id="owed-confirmed">On Oct. 19, 2026, the interim Town Manager asked firms to confirm what they were owed for the Eldora transaction as of Oct. 16: invoiced amounts still unpaid, and an estimate for work done but not yet invoiced. The request forms are her letters; the Town Attorney emailed them to the firms, saying the Town&rsquo;s &ldquo;contract accounting firm has requested confirmation of any outstanding amounts &hellip; as part of the preparation of the Town&rsquo;s 2026 financial statements and 2027 budget&rdquo; (<a href="{rec_conf_req}" target="_blank" rel="noopener">request emails</a>, released Nov. 16, 2026). The Town released the replies on Oct. 29 in response to a records request for the records behind the $2.5 million estimate, unpaid invoices, and fee agreements (<a href="{rec_reply4}" target="_blank" rel="noopener">Town response</a>). The confirmations postdate the Sept. 30 estimate, and the Town hasn't said how they relate to it.</p>
    <p class="prose muted bar-key"><span class="key-paid"></span> paid &nbsp; <span class="key-owed"></span> owed, as confirmed by the firm as of Oct. 16, 2026 &nbsp; &mdash; no confirmation in the records released, or no answer for that column (Taft left &ldquo;not yet invoiced&rdquo; blank; Widner Juran's receivables report doesn't cover unbilled work). $0 means the firm wrote zero. Each owed amount links to the firm's confirmation; Widner Juran's is from its receivables report. Amounts are rounded to the dollar, so a column may not add exactly.</p>
    <div class="scroll"><table class="payees-t">
      <thead><tr><th scope="col">Firm</th><th scope="col" class="bar"><span class="sr">Share</span></th><th scope="col" class="num">Paid</th><th scope="col" class="num">Invoiced, unpaid</th><th scope="col" class="num">Not yet invoiced</th></tr></thead>
      <tbody>{vendors}</tbody>
    </table></div>
    <ul class="notes prose">
      <li>Brownstein's agreement says that if the transaction terminates before completion, the firm "will provide a 10% broken deal discount on all fees incurred," and that its bill comes "upon completion or termination of the transaction" (<a href="{rec_bhfs}" target="_blank" rel="noopener">engagement agreement p.2</a>). Shareholders bill $800 an hour and associates $500.</li>
      <li>The Williams Weese invoices total $87,595.50, of which $84,456.50 was more than 90 days past due on its Sept. 9, 2026, statement (<a href="{rec_wwpf_stmt}" target="_blank" rel="noopener">statement</a>). The statement is addressed to the Town in care of Brownstein, and the records don't say whether Brownstein's unbilled amount includes any of Williams Weese's fees. If it did, the owed total above would count them twice.</li>
      <li>Dickinson Wright's emails to the Town, from Nov. 24, 2025, to Sept. 16, 2026, list its unpaid invoices by matter; those in its Eldora matter match the $84,621.50 it confirmed. In May, August, and September 2026 it asked when they would be paid. The emails are posted here with email addresses and the firm's phone numbers blacked out (<a href="{rec_dw_emails}" target="_blank" rel="noopener">emails</a>).</li>
      <li>The response includes confirmations only from the firms with an amount owed in the table and from Stifel. It includes none from the other firms, among them Hogan Lovells, Plante Moran (whose due-diligence fees are &ldquo;not contingent on the successful closing&rdquo;), POWDR, Butler Snow, Northland, Farnsworth Group, Partner Engineering and Science, Bolder HR Solutions, Datasite, and Torrent Engineering &amp; Equipment, and doesn't say whether they were asked. Butler Snow's and Northland's fees are paid only from bond proceeds (<a href="{rec_butler}" target="_blank" rel="noopener">Butler Snow letter</a>, <a href="https://nederlandco.civicweb.net/document/118130/" target="_blank" rel="noopener">Northland letter</a>).</li>
      <li>Invoice emails the Town released Nov. 16, 2026, in response to a records request, show who received the bills. Invoices from Taft, BBA Water Consultants, Farnsworth Group, and Bolder HR Solutions went to the Town Manager; SE Group's went to the Town's accounts payable address and the Town Manager; Brownstein's $40,000 invoice went to the Town Attorney, with a copy to the interim Town Manager; and Williams Weese's Nov. 11 invoice went to Brownstein and the interim Town Manager. POWDR's $10,721 audit invoice went to the Town Manager, whose May 5, 2026, reply approving it for payment was addressed to POWDR's CFO, the Town Attorney, the Mayor, and accounts payable (<a href="{rec_powdr_audit}" target="_blank" rel="noopener">POWDR</a>, <a href="{rec_taft_inv}" target="_blank" rel="noopener">Taft</a>, <a href="{rec_bhfs_inv}" target="_blank" rel="noopener">Brownstein</a>, <a href="{rec_wwpf_inv}" target="_blank" rel="noopener">Williams Weese</a>, <a href="{rec_other_inv}" target="_blank" rel="noopener">others</a>; email addresses and phone numbers blacked out by this site). The release covered the free first hour of the request (<a href="#questions">records requests</a>).</li>
      <li>The Town said that &ldquo;No records exist&rdquo; of written cost-estimate updates to the Board under Res. 2025-03 (<a href="{rec_reply4}" target="_blank" rel="noopener">Town response</a>).</li>
    </ul>
  </section>

  <section id="recorded">
    <h2>How the costs are recorded and paid</h2>
    <h3 id="funding">Where the money comes from</h3>
    <p class="prose">Every Eldora acquisition bill to date was charged to the General Fund and paid from the Town's pooled cash (see <a href="#csafe">CSAFE</a>). How they were recorded changed in November 2026 (<a href="#receivable">below</a>). Res. 2025-17 states the intent to repay it from bond proceeds, and the August 2025 legal-counsel memo says those legal fees would be "funded from the bond issuance proceeds." The bonds would pay for the purchase, improvements, reserves, early interest, and issuance costs, and repay the Town's early costs; no taxes or General Fund money are pledged (Ord. 885). The financing is being restructured (<a href="#revised-plan">where things stand</a>). In January 2025 the Board approved sending Great Outdoors Colorado a letter of interest about a possible grant (<a href="https://nederlandco.civicweb.net/document/118545/" target="_blank" rel="noopener">minutes</a>); no award appears in the records searched.</p>
    <p class="prose" id="receivable"><strong>How the costs were recorded, and how that changed.</strong> When the Town pays an Eldora acquisition bill from the General Fund, the cash leaves either way, but the books can record the payment in one of two ways. Recorded as spending, it reduces the General Fund's balance right away. Recorded as a receivable, it counts as money the Town expects to get back, so the balance on paper doesn't change, much like a personal loan that hasn't been repaid yet. Through the Oct. 20, 2026, warrant list, the Town recorded the bills in the <a href="#costs">"Due From" account</a>, in a ledger titled "Eldora - reimbursable expenses," as money to be repaid from bond proceeds if the purchase closes. The 2025 audit shows the General Fund's "other receivables" rising from $6,431 to $520,055 during 2025, without itemizing them, while the account reached {bal_2025} on the warrant lists ($504,396 in the Town's ledger, which includes 2025 invoices paid in 2026; <a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>). [[corrected:2026-10-13]] In 2026 the account grew by $772,243 through July, while the General Fund's balance fell only $159,439 (<a href="https://nederlandco.civicweb.net/document/131731/" target="_blank" rel="noopener">July 2026 report</a>). In November the Town changed course. New invoices on the Nov. 9 warrant list went to an &ldquo;Eldora Expense&rdquo; account (<a href="#eldora-expense">below</a>), and the Town's Nov. 9 budget forecast records all of its Eldora estimate as General Fund spending in 2025 and 2026, whether or not the sale closes (<a href="#gf-tables">General Fund deficit</a>). It says the 2025 payments "are expected to be recorded through audit adjustments, which will increase 2025 expenditures and reduce beginning fund balance and accounts receivable" (<a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a>). The Treasurer's report for September explains the change: the costs &ldquo;were initially recorded as a receivable in anticipation of potential reimbursement from future transaction proceeds,&rdquo; and on review the Town &ldquo;determined that recognition as expenditures is the appropriate treatment.&rdquo; It says the 2026 figure, $2,135,661, includes &ldquo;amounts paid or incurred through October 15, 2026,&rdquo; and the September balance sheet lists $1,556,213 in accounts payable, so the Town's total counts unpaid bills as well as payments (<a href="https://nederlandco.civicweb.net/document/133493/" target="_blank" rel="noopener">September Treasurer report</a>, <a href="https://nederlandco.civicweb.net/document/133492/#page=8" target="_blank" rel="noopener">September financials</a>, p. 8). The records searched don't yet say which audit will record the 2025 adjustment, or whether the 2025 statements will be reissued. Staff's Nov. 16 budget memo recommends amending the 2026 budget to record the fund transfers this year and expects to bring the amendments to the Board on Dec. 1, 2026; the Dec. 1 memo says staff won't present one, because the General Fund is likely to stay within its 2026 appropriation (<a href="https://nederlandco.civicweb.net/document/133495/" target="_blank" rel="noopener">Nov. 16 budget memo</a>, <a href="#nov16-plan">the Nov. 16 plan</a>); Resolution 2026-31, adopted Nov. 17, requires an appropriation before further acquisition spending (<a href="#res-2026-31">Resolution 2026-31</a>).</p>
    <p class="prose" id="enterprise-fund">The Town created a separate fund for the acquisition, but the records searched don't show it being used. Ordinance 873 (Jan. 21, 2025) established the Mountain Recreation Fund as a TABOR enterprise to "be kept separate from the Town's general fund and other funds," and its staff memo listed "Feasibility Studies and Planning" and costs of "potential acquisition efforts" among its uses (<a href="https://nederlandco.civicweb.net/document/118506/" target="_blank" rel="noopener">Ord. 873</a>, <a href="https://nederlandco.civicweb.net/document/118505/" target="_blank" rel="noopener">memo</a>). The fund isn't among the ten funds appropriated in the 2026 budget (<a href="https://nederlandco.civicweb.net/document/126174/" target="_blank" rel="noopener">Res. 2025-28</a>), and the 2025 audit reports two enterprise funds, Water and Sewer, naming the Mountain Recreation Enterprise only as the intended issuer of the bonds (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>, note 10). The records searched don't say why the acquisition costs were charged to the General Fund instead. Draft Resolution 2026-31 would have the 2027 budget materials explain how the costs are recorded and why they were charged to the General Fund rather than the Mountain Recreation Fund (<a href="https://nederlandco.civicweb.net/document/133099/" target="_blank" rel="noopener">§10</a>).</p>
    <p class="prose" id="audit-note"><strong>What the 2025 audit says about Eldora.</strong> The audit&rsquo;s only mention of the acquisition is a note on subsequent events: the Town &ldquo;intends to finance the acquisition of Eldora Mountain Resort&rdquo; through its Mountain Recreation Enterprise &ldquo;through the issuance of revenue bonds,&rdquo; the Board &ldquo;has approved a purchase agreement for the acquisition and adopted an ordinance authorizing the issuance of such bonds,&rdquo; and the final terms &ldquo;will be established at pricing&rdquo; (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>, p. 26). Emails released in response to a records request show how the note was prepared. On May 8, 2026, the audit manager asked whether there were subsequent events to disclose, including &ldquo;the upcoming purchase of the ski resort.&rdquo; The Town Manager answered that the acquisition &ldquo;is definitely anticipated to happen this year, likely this summer,&rdquo; and, asked about financing, &ldquo;Revenue Bonds and a CAB most likely.&rdquo; The audit manager said a note was needed, typically giving &ldquo;payment terms, total amount, interest rate, etc. if available,&rdquo; and sent two sample notes, one for financing a government intends to issue and one for financing already issued. On May 18 the Town Manager forwarded them to the Town Attorney and the Mayor: &ldquo;I need to figure out what we want to say about the eldora acquisition in the audit. I think statement #1 could work&rdquo; (<a href="{rec_audit_emails}" target="_blank" rel="noopener">emails</a>). The note in the audit follows the first sample&rsquo;s form. It doesn&rsquo;t mention the acquisition costs already paid, which the audit carried as a <a href="#receivable">receivable</a>.</p>
    <p class="prose" id="eldora-expense"><strong>A new &ldquo;Eldora Expense&rdquo; account (November 2026).</strong> The warrant list in the Nov. 9, 2026, packet, printed Oct. 29, charges three Eldora invoices to a General Fund account that doesn't appear on earlier warrant lists, <span class="mono">10-10-7000</span>, &ldquo;Eldora Expense,&rdquo; with a budget of $0. They are Brownstein Hyatt Farber Schreck's $40,000, its first appearance on a warrant list; a POWDR invoice for $12,357.75 (INV3984, dated Sept. 30, 2026); and Widner Juran's $6,624, for $58,981.75 in all. Widner Juran's $3,220 invoice of the same date, which its receivables report labels &ldquo;Eldora CORA,&rdquo; is charged to Legal. The &ldquo;Due From&rdquo; account doesn't appear on the list (<a href="https://nederlandco.civicweb.net/document/133064/" target="_blank" rel="noopener">Nov. 9 warrants, pp. 2&ndash;4</a>).</p>
    <p class="prose">The list shows the new account's year-to-date balance as ($2,188,218.53). On these reports, the year-to-date column for other accounts changes from one list to the next by exactly the amounts charged on the newer list; for example, Legal's balance falls by $10,547 and Professional Services' by $8,100, matching the charges to each on the Nov. 9 list. Read the same way, the new account already held about $2,129,237 before these three charges (this page's reading), close to the $2,135,661 the Town's Nov. 9 budget presentation shows in Eldora expenditures for 2026 (<a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a>). It is also about $933,287 more than the $1,195,949 &ldquo;Due From&rdquo; balance on the Oct. 20 list, and no warrant list between Oct. 20 and Nov. 9 paid any Eldora invoice, so the rest reached the account through entries that don't appear on warrant lists. The Treasurer's September report says the Town's 2026 Eldora figure includes amounts &ldquo;paid or incurred&rdquo; through Oct. 15 (<a href="#receivable">above</a>), which would account for the difference; the records searched don't show the entries themselves. The Board approved the list on Nov. 9 with the consent agenda (<a href="{nov9_min}" target="_blank" rel="noopener">minutes</a>), and this page's totals include the $58,981.75.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Budget and limits</th><th scope="col">Amount</th><th scope="col">Status</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr id="no-limits"><td>Eldora acquisition costs in the 2025 and 2026 Town budgets; the 2026 budget "does not include sufficient appropriations." The costs don't appear as expenditures in the monthly financial and treasurer reports searched (<a href="https://nederlandco.civicweb.net/document/131731/" target="_blank" rel="noopener">July 2026 financials</a>).</td><td class="amount">$0</td><td><span class="status none">Not budgeted</span></td><td><a href="https://nederlandco.civicweb.net/document/129045/" target="_blank" rel="noopener">Apr 21, 2026 memo</a></td></tr>
        <tr><td>Dollar limit in the resolutions delegating authority to hire counsel and consultants; the last two let the Town Manager hire "additional consultants, as necessary"</td><td class="amount">None</td><td><span class="status none">No limit</span></td><td>Res. 2025-03, 2025-11, <a href="https://nederlandco.civicweb.net/document/123040/" target="_blank" rel="noopener">2025-16</a>, <a href="https://nederlandco.civicweb.net/document/123794/" target="_blank" rel="noopener">2025-19</a>, <a href="https://nederlandco.civicweb.net/document/124849/" target="_blank" rel="noopener">2025-22</a></td></tr>
        <tr><td>Limit on further acquisition spending: up to $80,000 toward a term sheet, only after a supplemental appropriation; a Board vote to continue if total costs, paid and owed, pass $3 million; and Board approval of any new engagement. Fees payable only at a closing are exempt.</td><td class="amount">$80,000</td><td><span class="status auth">Adopted Nov. 17, 2026</span></td><td><a href="#res-2026-31">Res. 2026-31</a></td></tr>
      </tbody>
    </table></div>
  </section>

  <div class="group" id="if-fails"><span>The cost to the Town</span></div>
  <section id="no-sale">
    <h2>What the Town would owe, and whether it could pay</h2>
    <div id="bottom-line" class="bottom-line">
      <h3>The bottom line</h3>
    <div class="scroll"><table class="commit bl">
      <thead><tr><th scope="col">&nbsp;</th><th scope="col">Amount</th><th scope="col">What it is</th></tr></thead>
      <tbody>
        <tr><td><strong>Already paid</strong></td><td class="amount">{balance}</td><td>Charged to the General Fund through the {asof} warrant list, including {powdr} to POWDR.</td></tr>
        <tr><td><strong>Invoiced, not yet paid</strong></td><td class="amount">{conf_inv}</td><td>Invoices the firms reported as unpaid as of Oct. 16, 2026, less those paid on the Nov. 9 warrant list; some date to August 2025 (<a href="#payees">by firm</a>, <a href="#overdue">overdue invoices</a>).</td></tr>
        <tr><td><strong>Work done, not yet invoiced</strong></td><td class="amount">{conf_unb}</td><td>Mostly Brownstein's, which its agreement bills when the transaction is completed or terminated, and bond counsel's $200,000 (<a href="#payees">by firm</a>). Firms that sent no confirmation in the records released aren't included in either row.</td></tr>
        <tr class="bl-total"><td><strong>Total</strong></td><td class="amount">about {owed_m}</td><td>This page's itemized total, used in the calculations below.</td></tr>
        <tr><td><strong>The Town's estimate</strong></td><td class="amount">about $2.76 million</td><td>Not itemized. Cited in Resolution 2026-31 as the Town&rsquo;s &ldquo;Sept. 30, 2026, updated estimates&rdquo; of costs that would not be reimbursed (<a href="https://nederlandco.civicweb.net/document/133099/" target="_blank" rel="noopener">Res. 2026-31</a>). On Sept. 30 the Town put them at about $2.5 million and said they "would be paid through our CSAFE investments" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sept. 30, 2026, update</a>). The Town's Nov. 9 budget presentation shows the same total, {town_eldora}, as Eldora expenditures of $622,925 in 2025 and $2,135,661 in 2026 (<a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a>).</td></tr>
        <tr><td><strong>Owed only if the deal closes</strong></td><td class="amount">$0 if it fails</td><td>The purchase price, Stifel's $325,000 fee, disclosure counsel Butler Snow's fee (estimated at $100,000), and bond issuance costs. Northland's engagement letter and the Res. 2025-11 memo describe underwriter fees as depending on a bond issue; the current underwriters' terms aren't in the records searched.</td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">Each part of this total links to a Town record: the warrant lists and the Town's ledger for what has been paid, and the firms' confirmations for what is owed. The Town's estimate of about $2.76 million (<a href="https://nederlandco.civicweb.net/document/133099/" target="_blank" rel="noopener">Resolution 2026-31</a>), like its Sept. 30 estimate of about $2.5 million (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">update</a>), isn't itemized in the records searched and can't be traced to specific firms or invoices. The itemized total could change. It doesn't include firms that sent no confirmation, such as Hogan Lovells, Plante Moran, and POWDR, or work after Oct. 16, 2026; it would be lower if Brownstein's 10% discount for a failed deal applies (if it applies to all of Brownstein's fees, the total would be {disc_total}) or if Williams Weese's fees are part of Brownstein's figure (<a href="#owed-confirmed">Who was paid and who is owed</a>). The Nov. 9 presentation's footnote says its Eldora figures "are limited to amounts paid through October 15, 2026"; the warrant lists, the Town's ledger, and the recital in Resolution 2026-31 show $1,195,949 paid as of the Oct. 20 warrant list (<a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a>, <a href="https://nederlandco.civicweb.net/document/133363/" target="_blank" rel="noopener">Res. 2026-31</a>, <a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>). The records searched don't explain the difference. Earlier Eldora work is included only where the Town moved it into the account (see <a href="#figures">About these figures</a>).</p>
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
        <tr id="ikon-advance"><td><strong>The Town's share of Ikon negotiation costs doesn't depend on closing.</strong> Under the draft agreement, the Town would pay 50% of the fees Alterra incurs negotiating the Ikon agreement, if Alterra requests reimbursement (§4.4(b)), and ending the agreement refunds nothing already paid (§7.2). A Jan. 6, 2026, letter signed for the Town (POWDR's acceptance is blank in the copy released) provides for a $50,000 advance to POWDR before talks with Alterra, to be applied to the Town's share; &ldquo;any portion of the advance not required for such reimbursement shall be promptly refunded by POWDR to the Town.&rdquo; The Town's ledger records a $50,000 POWDR invoice dated Jan. 6, 2026, that is on no warrant list (<a href="#payee-powdr">Who was paid</a>). <strong>What was billed.</strong> Alterra's lawyers, Hogan Lovells, billed $124,715.50 for the &ldquo;Eldora Ikon Agreement&rdquo; from February to April 2026, and POWDR paid it. On Sept. 22, 2026, POWDR's corporate secretary wrote to the Mayor and the Town Attorney that the parties had agreed to split those fees, that the Town &ldquo;previously paid Powdr $50,000 toward these legal expenses,&rdquo; and that POWDR would invoice the remaining $12,358; the Town paid that invoice ($12,357.75) on the Nov. 9 warrant list. A fourth invoice, $8,943 (May 29, 2026), &ldquo;relates to legal matters directly attributable to the Town&rdquo; and is to be paid by the Town to Hogan Lovells; it is unpaid. Separately, Hogan Lovells billed the Town $148,314.50 on June 24, 2026, for a &ldquo;Town of Nederland&rdquo; matter (103.2 hours, Jan. 22 to March 31, 2026), and $480 on July 27; a Hogan Lovells partner sent the first to the Town Attorney, accounts payable, and the Town Manager as &ldquo;the Hogan Lovells fees that Nederland has agreed to bear pursuant to its agreement with Powdr,&rdquo; and the Town paid both (July 21 and Aug. 18 warrant lists). Hogan Lovells' first Ikon invoice (Feb. 26, $71,915.50) was voided and reissued at $36,640.50; 17 of the 20 January time entries on the June 24 invoice match entries on the voided version (same date, lawyer, and hours). In all, the Town's share is about $220,095 of the $282,453 Hogan Lovells billed on the two matters. The records released don't include the agreement under which the Town pays the &ldquo;Town of Nederland&rdquo; matter in full. The Town redacted the descriptions of the work as attorney-client privileged (<a href="{rec_hl_inv}" target="_blank" rel="noopener">invoices and emails</a>, <a href="{rec_hl_reply}" target="_blank" rel="noopener">Town response</a>).</td><td><a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §4.4(b), §7.2, §8.2</a>, <a href="{rec_ikon}" target="_blank" rel="noopener">Jan. 6, 2026, letter</a>, <a href="{rec_hl_inv}" target="_blank" rel="noopener">Hogan Lovells invoices and emails</a></td></tr>
        <tr><td><strong>The documents searched don't say how costs would be paid if no bonds are issued.</strong> Res. 2025-17 only "preserves the option" of repayment from the bonds; payments not funded by the bonds depend on yearly budget votes; and if the purchase fails, the enterprise fund "can be retired," with nothing saying who absorbs money already spent.</td><td><a href="https://nederlandco.civicweb.net/document/123059/" target="_blank" rel="noopener">Res. 2025-17 memo</a>, <a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §10.16</a>, <a href="https://nederlandco.civicweb.net/document/118505/" target="_blank" rel="noopener">Ord. 873 memo</a></td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">The agreement terms in this table come from the draft in the January 6, 2026, Board packet. Res. 2026-07 and 2026-09 state that the Town entered into the agreement, but the signed version isn't in the Board records searched and may differ.</p>
    <h3 id="gf-deficit">If the General Fund ends in deficit</h3>
    <p class="prose" id="fund-balance">The General Fund had a fund balance of $1,030,078 at the end of 2025, of which $872,173 was unassigned. That balance counts receivables as assets, including 2025 Eldora payments the Town says it will move to spending (<a href="#receivable">receivables</a>). The Town's Nov. 9, 2026, budget presentation charges its Eldora estimate to the General Fund and forecasts the balance below (<a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a>). Its 2025 column restates the audit: the same revenue and spending (counting transfers) and beginning balance, plus $622,925 in Eldora costs, which lowers the 2025 ending balance from $1,030,078 to $407,153.</p>
    <div class="figure" role="figure" aria-label="The General Fund in the Town's Nov. 9, 2026, forecast">{gf_chart}</div>
    <div class="scroll" id="gf-tables"><table class="walk">
      <thead><tr><th scope="col">General Fund balance</th><th scope="col">Amount</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>Balance at the end of 2025</td><td class="amount">$1,030,078</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a></td></tr>
        <tr><td>2026, without Eldora (Town forecast)</td><td class="amount">{town_ops}</td><td><a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a></td></tr>
        <tr><td>Eldora costs, the Town's estimate ($622,925 in 2025 and $2,135,661 in 2026)</td><td class="amount">&minus;{town_eldora}</td><td><a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a></td></tr>
        <tr class="bl-total"><td><strong>End of 2026 (Town forecast)</strong></td><td class="amount">{town_fb}</td><td><a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a></td></tr>
        <tr><td>End of 2027 (Town forecast; 2027 Eldora costs "TBD")</td><td class="amount">{town_fb27}</td><td><a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a></td></tr>
        <tr><td>Sept. 30, 2026, actual, preliminary</td><td class="amount">&minus;$1,923,260</td><td><a href="https://nederlandco.civicweb.net/document/133492/#page=8" target="_blank" rel="noopener">September financials</a>, p. 8</td></tr>
        <tr><td>End of 2026, Nov. 16 forecast: balance available, not counting $163,882 restricted</td><td class="amount">&minus;$2,180,816</td><td><a href="https://nederlandco.civicweb.net/document/133496/" target="_blank" rel="noopener">Nov. 16 budget tables</a>, p. 1</td></tr>
        <tr><td>End of 2027, Nov. 16 forecast, available, with no raise for employees (with a 3% raise: &minus;$2,563,003)</td><td class="amount">&minus;$2,528,102</td><td><a href="https://nederlandco.civicweb.net/document/133496/" target="_blank" rel="noopener">Nov. 16 budget tables</a>, p. 1</td></tr>
        <tr><td>End of 2026 with this page's itemized total of {owed} in place of the Town's estimate</td><td class="amount">{fb_end}</td><td>This page's calculation</td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">Through September, the General Fund's revenue was $2,267,884, 35% below the budget to date, mostly because state transportation (CDOT) grant revenue came in lower than expected, and its spending was $4,598,280, 19% above it (<a href="https://nederlandco.civicweb.net/document/133493/" target="_blank" rel="noopener">September Treasurer report</a>). All rows but the last are the Town's figures. The Nov. 16 forecast lowers 2026 revenue to $2,981,446 and doesn't yet include the transfers staff propose (<a href="#nov16-plan">the Nov. 16 plan</a>). Its forecast charges the whole Eldora estimate to the General Fund whether or not the sale closes, and its footnote says the figures "should be considered preliminary": 2025 and 2026 spending "may increase," because the forecast doesn't include services performed but not yet invoiced (<a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a>). On the Town&rsquo;s own figures, $2,758,586 paid or incurred through Oct. 15, less $1,195,949 paid through the Oct. 20 warrant list, leaves $1,562,637 recorded but unpaid. On Oct. 16, the firms confirmed $1,623,777 owed plus a $40,000 Brownstein invoice since paid, so about $100,000 of what they listed may not yet be recorded (this page's calculation). The last row is this page's calculation: the same starting balance and 2026 forecast, with this page's itemized total, which is {fb_gap} more than the Town's estimate. Amounts owed to firms that sent no confirmation, or for work after Oct. 16, would make it lower; Brownstein's discount for a failed deal would make it higher. Until Nov. 15, 2026, this page used the adopted 2026 budget's projected decline of $446,348 for the rest of the year; the Town's Nov. 9 forecast replaces it. A transfer from another fund, as staff proposed, would raise the General Fund's balance; by staff's analysis a loan would not, because the money comes with an equal debt (<a href="#budget-options">the Town's options</a>). The Town adopts its General Fund budget &ldquo;on a basis consistent with generally accepted accounting principles&rdquo; (2025 audit). The Town's 2016 audit, though, reported a loan from the Water Fund as a financing source of the fund that borrowed it (<a href="#utility-loan">the earlier loans</a>). [[corrected:2026-11-22]] A deficit in the fund balance isn't the same as a change in cash; for the cash, see <a href="#pay-rest">Could the Town pay the rest?</a></p>
    <p class="prose" id="deficit-law">The General Fund has already relied on other funds' cash: the 2025 audit reports its "negative cash balance of $757,482" as accounts payable, covered by the Town's pooled cash (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>). Colorado law sets the rules a deficit would face. A local government's budget may not "provide for expenditures in excess of available revenues and beginning fund balances," and no one may spend or contract to spend "in excess of the amounts appropriated" (<a href="https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-29.pdf" target="_blank" rel="noopener">C.R.S. 29-1-103(2), 29-1-110</a>). The 2026 General Fund appropriation is $5,674,176, set for the fund as a whole (<a href="https://nederlandco.civicweb.net/document/126174/" target="_blank" rel="noopener">Res. 2025-28</a>), and the Eldora costs count against it as 2026 spending. Staff&rsquo;s Nov. 16 forecast of 2026 spending, including them, is $5,493,955, which is $180,221 under it (<a href="https://nederlandco.civicweb.net/document/133496/" target="_blank" rel="noopener">budget tables</a>). Part of the room is in the grant budget: the General Fund&rsquo;s grant lines, budgeted at $2,250,000, had spent about $100,000 by the Nov. 9 warrant list, and the grant revenue that would have paid for them didn&rsquo;t come (<a href="https://nederlandco.civicweb.net/document/133064/" target="_blank" rel="noopener">Nov. 9 warrants</a>). A budget that starts from a deficit would have to close it with more revenue, less spending, or transfers. For scale, {unpaid} is about {pct_unpaid} of the General Fund's 2026 operating budget of $3,236,824, and {owed_m} is about {pct_est} (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>). Under TABOR, the Town needs voter approval in advance for "any new tax, tax rate increase," or mill levy increase, and for any "multiple-fiscal year direct or indirect district debt or other financial obligation" not backed by cash reserves pledged for all future payments. The TABOR emergency reserve, $147,000 of the General Fund's balance, is "for declared emergencies only," and an emergency "excludes economic conditions, revenue shortfalls" (<a href="https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-00.pdf" target="_blank" rel="noopener">Colo. Const. art. X, §20(2)(c), (4), (5)</a>). At the General Fund's 2017–2023 average gain of {avg_op} to {avg_rep} a year, rebuilding the Nov. 16 forecast's available-balance deficit of about $2.2 million would take roughly {yrs_def} years (this page's calculation). That is a measure of scale, not a forecast: the General Fund's balance fell by $265,953 in 2024 and $192,241 in 2025, and the Town's Nov. 9 forecast shows the fund spending more than it takes in, before any Eldora costs, in 2026 ({town_ops}) and 2027 (&minus;$183,610) (<a href="#gf-recovery">year by year</a>).</p>
    <p class="prose">The State Auditor's fiscal-health benchmark for counties and municipalities is an unrestricted General Fund balance of at least two months of expenditures, a ratio of 0.167, and it says a negative unrestricted balance "is not sustainable, and a government should address the situation as soon as possible" (<a href="https://content.leg.colorado.gov/sites/default/files/documents/audits/2129-13countyfiscalhealth2ndprintingoct2013final-0-1-accessible.pdf" target="_blank" rel="noopener">State Auditor, 2013, p. 13</a>). Nederland's ratio was about 0.26 at the end of 2025; at the end of 2026 in the Town's forecast, it would be about {ufb_2026} (this page's calculation). In the audits searched from 2008 through 2024, the General Fund appears as a lender to other funds, not a borrower; in 2008 it "temporarily covered the negative cash balances" of two other funds (<a href="https://nederlandco.civicweb.net/document/26065/" target="_blank" rel="noopener">2008 audit</a>), and 2025 is the first year an audit reports it with negative cash. The Town's formal loans between funds have gone to the Downtown Development Authority, not the General Fund (<a href="#utility-loan">below</a>). The records searched don't show how the budget law's limit applies when a fund begins the year with a negative balance, which read literally could require closing the gap within one budget year; that is a question for the Town attorney or auditor.</p>
    <p class="prose" id="bankruptcy"><strong>Bankruptcy and dissolution.</strong> Neither would remove these costs. A local government can file for federal municipal bankruptcy (Chapter 9) only if its state specifically authorizes it (<a href="https://www.uscourts.gov/court-programs/bankruptcy/bankruptcy-basics/chapter-9-bankruptcy-basics" target="_blank" rel="noopener">U.S. Courts</a>). The Colorado statute that does so names only an &ldquo;irrigation or drainage district&rdquo; (<a href="https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-37.pdf" target="_blank" rel="noopener">C.R.S. 37-32-102</a>), and no statute searched authorizes a town. A town can end its incorporation only if 25% of its registered voters petition and two-thirds vote to do so, and only after it &ldquo;has made proper provisions for the payment of all of its indebtedness&rdquo; and its contracts, levying taxes if needed (<a href="https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-31.pdf" target="_blank" rel="noopener">C.R.S. 31-3-101, 31-3-104</a>). A town that goes five years without holding elections or maintaining a government can be declared abandoned, but its debts &ldquo;shall not be abrogated,&rdquo; and the county takes over to pay them (<a href="https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-31.pdf" target="_blank" rel="noopener">C.R.S. 31-3-201, 31-3-202</a>). The Eldora bonds would not be a Town debt: the January 2026 draft indenture says they &ldquo;shall not constitute or become an indebtedness, a debt, or a liability or a charge against the general credit or taxing power of the Town&rdquo; (<a href="https://nederlandco.civicweb.net/document/127181/" target="_blank" rel="noopener">draft indenture §7.01</a>); the sale-leaseback documents aren't public. By this page's reading, the acquisition costs are a General Fund budget problem the Board would address through its budgets, not a threat to the Town's existence.</p>
  </section>

  <section id="other-funds">
    <h2>Could other funds cover it?</h2>
    <h3 id="budget-options">The Town's options (Nov. 9 and Nov. 16, 2026)</h3>
    <p class="prose">At the Board's Nov. 9, 2026, meeting, staff presented three ways to cover the General Fund's deficit, each with a &ldquo;potential impact on total GF fund balance,&rdquo; and noted that the &ldquo;figures presented are forecasted and subject to change&rdquo; (<a href="{rec_slides}#page=5" target="_blank" rel="noopener">budget slides, pp. 5&ndash;8</a>).</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Option</th><th scope="col">Potential impact</th><th scope="col">What staff said</th></tr></thead>
      <tbody>
        <tr><td>1. Consolidate the Community Center Fund into the General Fund</td><td class="amount">$0.9 million</td><td>&ldquo;Mostly an accounting change; doesn&rsquo;t impact operations.&rdquo; The fund &ldquo;should have been allocating funding already&rdquo; to the General Fund for administrative support. Staff would assess how much is restricted; &ldquo;charges for service (user fees) may be considered unrestricted funds&rdquo; (<a href="{rec_slides}#page=6" target="_blank" rel="noopener">p. 6</a>).</td></tr>
        <tr><td>2. Transfer from the Water and Sewer Funds</td><td class="amount">$2.0 million</td><td>&ldquo;A transfer from water/sewer savings with no expectation of repayment.&rdquo; Staff would assess how much is restricted; user fees and sales tax &ldquo;may be considered unrestricted funds&rdquo; (<a href="{rec_slides}#page=7" target="_blank" rel="noopener">p. 7</a>).</td></tr>
        <tr><td>3. Dissolve the Downtown Development Authority</td><td class="amount">$1.9 million</td><td>&ldquo;The $1,907,362 is the current account balance.&rdquo; Dissolving it &ldquo;does remove the mill being paid by the parcels in the district.&rdquo; Staff would assess how much is restricted and the effect on other taxing districts (<a href="{rec_slides}#page=8" target="_blank" rel="noopener">p. 8</a>).</td></tr>
      </tbody>
    </table></div>
    <p class="prose">Staff also listed possible new revenue (paid parking, speed cameras, more sheriff's extra-duty traffic enforcement, and a higher sustainability fee) and possible spending cuts, including &ldquo;evaluating staffing levels&rdquo; (<a href="{rec_slides}#page=9" target="_blank" rel="noopener">pp. 9&ndash;10</a>). The Board agreed to have staff &ldquo;research combined implementation and restrictions of the presented options to balance the general fund&rdquo; (<a href="{nov9_min}" target="_blank" rel="noopener">Nov. 9 minutes</a>). The Nov. 9 schedule called for a public hearing Dec. 1 and adoption at a Dec. 8 special session, with Dec. 15 as the fallback (<a href="{rec_slides}#page=2" target="_blank" rel="noopener">p. 2</a>). Staff updated these options on Nov. 16 (<a href="#nov16-plan">below</a>); what the records say each fund's money can pay is in <a href="#fund-dedications">what voters approved</a> and <a href="#csafe">the Town's funds</a>.</p>
    <p class="prose" id="staff-scenarios"><strong>Staff's Oct. 30 spreadsheet.</strong> A staff spreadsheet released Nov. 16 in response to a records request, titled &ldquo;Budget Scenarios for Discussion&rdquo; and marked &ldquo;Preliminary talking points,&rdquo; was created Oct. 30, 2026, and last saved Nov. 16, the day it was released. It has four options rather than the three presented, and for each it estimates the effect on the General Fund's total balance and on its unassigned, spendable balance (<a href="{rec_scen}" target="_blank" rel="noopener">spreadsheet</a>, <a href="{rec_bud_reply}" target="_blank" rel="noopener">Town response</a>).</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Option in the spreadsheet</th><th scope="col">Total balance</th><th scope="col">Spendable balance</th><th scope="col">Staff's note</th></tr></thead>
      <tbody>
        <tr><td>1. Merge the Community Center Fund</td><td class="amount">$996,123</td><td class="amount">$0</td><td>&ldquo;ASSUMPTION: 100% restricted. CC Fund is primarily funded by dedicated sales tax (~$404K of ~$583K annual revenue). Confirm ballot/ordinance language.&rdquo;</td></tr>
        <tr><td>2. Loan from the Water and Sewer Funds ($2 million; 5 years and 1% are &ldquo;placeholder&rdquo; assumptions)</td><td class="amount">$0</td><td class="amount">$0</td><td>&ldquo;Asset and liability offset - $0 by design.&rdquo; Repayment, about $412,000 a year on those assumptions, &ldquo;must be appropriated in future GF budgets.&rdquo;</td></tr>
        <tr><td>3. Transfer from the Water and Sewer Funds ($2 million, &ldquo;will not be repaid&rdquo;)</td><td class="amount">$2,000,000</td><td class="amount">$2,000,000</td><td>Assumes none of it is restricted; &ldquo;Confirm no bond/loan covenant or grant condition follows the utility resources.&rdquo; It would be 65% of the two funds' estimated unrestricted net position at the end of 2026, $3,099,804.</td></tr>
        <tr><td>4. Dissolve the Downtown Development Authority</td><td class="amount">$1,907,362</td><td class="amount">$0</td><td>Treated as all restricted. The same file's source data shows the authority's combined projected ending balance for 2026 as $211,637.</td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">The loan option is the one staff dropped: the spreadsheet shows that a loan leaves the General Fund's balance unchanged, because the money comes with an equal debt, while a transfer raises it. The spreadsheet also lists the General Fund's $69,119 of tax-increment revenue passed to the Downtown Development Authority in 2026 and the Community Center Fund's $34,716 administrative payment to the General Fund (<a href="{rec_scen}" target="_blank" rel="noopener">Baseline Data</a>).</p>
    <h3 id="nov16-plan">The Nov. 16 plan: transfers from three funds</h3>
    <p class="prose">A revised budget memo added to the Nov. 17 packet on Nov. 16 updates the options (<a href="https://nederlandco.civicweb.net/document/133495/" target="_blank" rel="noopener">Nov. 16 budget memo</a>, <a href="https://nederlandco.civicweb.net/document/133496/" target="_blank" rel="noopener">Nov. 16 budget tables</a>):</p>
    <ul class="notes prose">
      <li><strong>Transfers, not loans, from three funds.</strong> Staff estimate the amounts available as &ldquo;up to&rdquo; $900,000 from the Community Center Fund, $1,400,000 from the Water Fund, and $900,000 from the Sewer Fund. Debt requirements in the Water and Sewer Funds &ldquo;are still under review and may change the amounts,&rdquo; and &ldquo;choosing to utilize the maximum amounts could bring the available budgetary ending balances to $0 in each of these funds.&rdquo;</li>
      <li><strong>The source and the authority cited.</strong> &ldquo;The proposed transfers would utilize revenues generated from user fees within the respective funds.&rdquo; The memo cites Town Code Sec. 4-11, under which the Board may &ldquo;transfer out of any fund any amount at any time to be used for such purpose as the Board of Trustees may direct.&rdquo;</li>
      <li><strong>The split.</strong> Of the Community Center's $900,000, $100,000 would be kept for capital projects (weight room, West Wing alarm and smoke detection, and doors). About 75% of the combined Water and Sewer transfer would come from the Sewer Fund and 25% from the Water Fund. Staff note that using utility money &ldquo;may affect the Town's ability to pay for future infrastructure improvements,&rdquo; and that more user-fee increases may follow the 9% water and 4% sewer increases already directed for 2027.</li>
      <li><strong>The Downtown Development Authority.</strong> Not in the preliminary budget. Its reserves are estimated at $1.7 million to $1.9 million; staff and the authority's chair, Trustee Andrew Dewart, presented different balances on Nov. 9 and were to meet Nov. 18 to reconcile them. If the authority were dissolved and its reserves returned to the taxing entities by their share of the levy, the Town's share would be about $246,500 to $275,500.</li>
      <li><strong>Two 2027 scenarios.</strong> A flat budget with no cost-of-living raise has a projected 2027 deficit of $2.6 million, the memo says; a 3% raise would bring the transfers needed to about $2.7 million. The budget tables' General Fund balances are in <a href="#gf-tables">the General Fund table</a>.</li>
      <li><strong>Two figures in the tables that don&rsquo;t add up.</strong> In the General Fund table, 2027 spending exceeds revenue by $497,155, but the available balance falls by $347,286. A smaller restricted balance accounts for $61,446 of the $149,869 difference, and the tables don&rsquo;t explain the other $88,423. In the Sewer Fund table, the 2026 ending balance of $1,258,630 plus 2027 revenue of $1,108,301, less 2027 spending of $1,032,451, is $1,334,480, but the table shows a 2027 ending balance of $1,191,381. The $143,099 difference equals the fund&rsquo;s 2026 revenue less its 2026 spending (this page&rsquo;s calculations from the <a href="https://nederlandco.civicweb.net/document/133496/" target="_blank" rel="noopener">Nov. 16 budget tables</a>).</li>
      <li><strong>Recording it in 2026.</strong> Staff recommend amending the 2026 budget so the transfers count this year, &ldquo;rather than carrying that deficit forward into FY27,&rdquo; and expect to bring the 2026 amendments and a revised 2027 budget on Dec. 1, 2026. The Dec. 1 memo drops the 2026 amendment for now: the General Fund &ldquo;is likely not to exceed the budgeted 2026 appropriations&rdquo; (<a href="https://nederlandco.civicweb.net/document/133768/" target="_blank" rel="noopener">Dec. 1 budget memo</a>).</li>
    </ul>
    <p class="prose">The memo asks the Board whether to make the transfers and in what amounts, whether to give the 3% raise, what to do about the Downtown Development Authority, and whether to amend the 2026 budget. A special meeting at 6 p.m. Nov. 17 was set for two executive sessions: one on the purchase and negotiations, and one &ldquo;to receive legal advice regarding acquisition diligence expenses, options for payment of those expenses, and applicable Colorado budget requirements&rdquo; (<a href="https://nederlandco.civicweb.net/document/133479/" target="_blank" rel="noopener">special meeting agenda</a>).</p>
    <h3 id="fund-dedications">What voters approved for these funds' sales tax</h3>
    <p class="prose">Part of each fund's income is a share of the Town's sales tax. Town Code Sec. 4-57, as rewritten by the Board in 2022 (Ord. 831), sends 52.95% of the sales tax to the General Fund &ldquo;to be used for any municipal purpose,&rdquo; 11.76% each to the Water and Sewer Funds, and 17.65% to the Community Center Fund, without stating a purpose for those shares (<a href="https://library.municode.com/co/nederland/codes/code_of_ordinances" target="_blank" rel="noopener">Town Code</a>, <a href="https://nederlandco.civicweb.net/document/43301/" target="_blank" rel="noopener">Ord. 831</a>). Earlier versions, and the ballot questions behind them, did:</p>
    <ul class="notes prose">
      <li><strong>The Community Center.</strong> Voters approved a 0.42% sales tax in 1997. In November 2002 they extended it &ldquo;for the acquisition, renovation, repair, operation and maintenance&rdquo; of the Community Center building; the ballot question refers to &ldquo;the Town sales tax which are dedicated to the Community Center&rdquo; (<a href="https://nederlandco.civicweb.net/document/25964/" target="_blank" rel="noopener">2002 ballot notice</a>). In April 2022, voters approved continuing it without expiration for the 2002 debt and &ldquo;funding the improvement, renovation, and repair to the community center and the operation and maintenance of the community center and other community center purposes as approved by the trustees&rdquo; (<a href="https://nederlandco.civicweb.net/document/34114/" target="_blank" rel="noopener">Res. 2022-08</a>; the 2023 budget book says voters &ldquo;overwhelmingly approved&rdquo; it, <a href="https://nederlandco.civicweb.net/document/43307/" target="_blank" rel="noopener">p. 30</a>). Until 2022, the Town Code said the Community Center's share is &ldquo;used exclusively&rdquo; for the building (<a href="https://nederlandco.civicweb.net/document/114617/" target="_blank" rel="noopener">Ord. 703</a>). The Town's own Sept. 30, 2026, balance sheet shows the fund's $890,426 as &ldquo;Restricted for Community Center&rdquo; and its unrestricted fund balance as $0 (<a href="https://nederlandco.civicweb.net/document/133492/#page=9" target="_blank" rel="noopener">September financials, p. 9</a>), as the 2025 audit did for its $830,528 (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>, p. 20). Sales tax was about $404,000 of the fund's $583,000 in yearly revenue, and fitness, rental, and other fees about $140,000 to $157,000 (<a href="{rec_scen}" target="_blank" rel="noopener">staff spreadsheet</a>; <a href="https://nederlandco.civicweb.net/document/128215/" target="_blank" rel="noopener">2026 budget, p. 158</a>). The 2025 audit also states that &ldquo;when both restricted and unrestricted resources are available for use, it is the Town&rsquo;s practice to use restricted resources first, then unrestricted resources as they are needed&rdquo; (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>, PDF p. 30). The 2013 ordinance that refinanced the Community Center&rsquo;s bonds applied the sales tax to the bonds &ldquo;and after such payment, to other purposes authorized by law from time to time&rdquo; (<a href="https://nederlandco.civicweb.net/document/114631/" target="_blank" rel="noopener">Ord. 719</a>, Sec. 12).</li>
      <li><strong>Water and Sewer.</strong> In November 1998, voters dedicated the utilities' share of the sales tax to water debt and then sewer debt; in April 2012 they split it &ldquo;one half … to pay water debt … and one half … to pay sewer debt&rdquo; (<a href="https://nederlandco.civicweb.net/document/114617/" target="_blank" rel="noopener">Ord. 703</a>, <a href="https://nederlandco.civicweb.net/document/114624/" target="_blank" rel="noopener">Ord. 711</a>). Ord. 711 says this sales tax was &ldquo;pledged to the repayment&rdquo; of the utilities' state loans. The 2026 budget says each fund's $275,000 of sales tax is &ldquo;designated&rdquo; for its debt (<a href="https://nederlandco.civicweb.net/document/128215/" target="_blank" rel="noopener">2026 budget, pp. 138&ndash;139</a>). User fees, the source the Nov. 16 memo names, were not part of these votes.</li>
      <li><strong>What the Town Code says about changing these uses.</strong> Sec. 4-58 lets the Board amend the sales tax article without a vote, &ldquo;except as to the sales tax rate,&rdquo; the items taxed, &ldquo;and the use of the sales tax revenues provided for in Sections 4-32 and 4-57.&rdquo; Sec. 4-32 says amounts in the Sales Tax Capital Improvement Fund &ldquo;shall be used solely to provide capital improvements or to pay debt services&rdquo; on obligations issued for them (<a href="https://library.municode.com/co/nederland/codes/code_of_ordinances" target="_blank" rel="noopener">Town Code</a>).</li>
      <li><strong>The 2018 sewer debt vote.</strong> In April 2018, voters approved up to $2 million of debt for wastewater biosolids improvements. The ballot issue let the Town pledge &ldquo;the rates, fees, payments and charges of the wastewater system and any portion of the Town&rsquo;s sales tax as hereafter determined by the Board of Trustees&rdquo; (<a href="https://nederlandco.civicweb.net/document/47106/" target="_blank" rel="noopener">April 3, 2018, sample ballot</a>, Ballot Issue 2B).</li>
    </ul>
    <p class="prose muted">This page doesn't decide whether a transfer would be lawful. Whether Sec. 4-11 or the 2022 code rewrite can change a purpose voters approved, and whether the transferred money can be traced to user fees, are questions for the Town Attorney; the Nov. 17 executive session lists &ldquo;applicable Colorado budget requirements&rdquo; among its topics.</p>
    <section class="site-check" id="budget-check" aria-labelledby="budget-check-h">
    <h3 id="budget-check-h">Does the proposed budget close? This site's check</h3>
    <p class="prose"><strong>This is this site's analysis of the Town's figures, not a Town finding.</strong> It uses the Nov. 16 memo and tables, the staff spreadsheet, and the records above.</p>
    <div class="scroll"><table class="walk">
      <thead><tr><th scope="col">Flat 2027 budget (no raise)</th><th scope="col">Amount</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>Gap to close, as the memo states it</td><td class="amount">$2,600,000</td><td><a href="https://nederlandco.civicweb.net/document/133495/" target="_blank" rel="noopener">Nov. 16 budget memo</a></td></tr>
        <tr><td>From the Community Center ($900,000 less $100,000 kept)</td><td class="amount">&minus;$800,000</td><td><a href="https://nederlandco.civicweb.net/document/133495/" target="_blank" rel="noopener">Nov. 16 budget memo</a></td></tr>
        <tr><td>Left for Water and Sewer</td><td class="amount">$1,800,000</td><td>This site's calculation</td></tr>
        <tr><td>Sewer's share at 75%</td><td class="amount">$1,350,000</td><td>This site's calculation</td></tr>
        <tr><td>Sewer's stated limit (&ldquo;up to&rdquo;)</td><td class="amount">$900,000</td><td><a href="https://nederlandco.civicweb.net/document/133495/" target="_blank" rel="noopener">Nov. 16 budget memo</a></td></tr>
        <tr><td>Sewer Fund's pooled cash on Sept. 30, 2026, less the $130,000 its state loans require</td><td class="amount">$788,807</td><td><a href="https://nederlandco.civicweb.net/document/133492/#page=12" target="_blank" rel="noopener">September financials, p. 12</a></td></tr>
        <tr><td>Sewer Fund's ending balance, 2026 forecast (budgetary basis)</td><td class="amount">$1,258,630</td><td><a href="https://nederlandco.civicweb.net/document/133496/" target="_blank" rel="noopener">Nov. 16 budget tables</a>, p. 3</td></tr>
        <tr><td>Water's share at 25%</td><td class="amount">$450,000</td><td>This site's calculation</td></tr>
        <tr class="bl-total"><td><strong>Most all three funds could give, at the stated limits</strong></td><td class="amount">$3,100,000</td><td>This site's calculation</td></tr>
        <tr class="bl-total"><td><strong>Without the Community Center</strong></td><td class="amount">$2,300,000</td><td>This site's calculation</td></tr>
      </tbody>
    </table></div>
    <ul class="notes prose">
      <li><strong>The math as presented doesn't work.</strong> At 75%, Sewer's share would be about $1.35 million, more than the memo's own &ldquo;up to $900,000&rdquo; for Sewer, more than the fund's forecast ending balance, and about 1.7 times the $788,807 of cash Sewer had on Sept. 30 after the reserve its state loans require. Even the $900,000 limit is more than that cash. Water had $1,931,391 after its required reserve, so its $1.4 million limit would leave about $530,000. The split works only the other way around, about 75% from Water, which is close to the 68% Water share the Oct. 30 spreadsheet used.</li>
      <li><strong>The memo and the tables give different gaps.</strong> The memo says $2.6 million (about $2.7 million with a raise); the tables show available balances of &minus;$2,528,102 and &minus;$2,563,003 at the end of 2027. The tables also don't include the transfers the memo says the preliminary budget &ldquo;assumes&rdquo;: the General Fund still ends 2027 in deficit, and the utilities' balances barely change.</li>
      <li><strong>About $88,000 a year is unexplained.</strong> In the tables, the General Fund's 2026 starting balance plus revenue, less spending and transfers out, comes out about $88,000 lower than the balance shown, and 2027 does the same. It may be transfers in from other funds, which the tables don't list.</li>
      <li><strong>The Town's books report the Community Center money as restricted.</strong> Voters approved its sales tax for Community Center purposes, and the Town's own books and staff's spreadsheet treat all of it as restricted (<a href="#fund-dedications">what voters approved</a>). Its fees are about $140,000 to $157,000 a year, and the memo doesn't show how $800,000 was traced to user fees.</li>
      <li><strong>Part of the utility money is dedicated to debt.</strong> The utilities' sales tax, about $550,000 a year, was dedicated by voters to water and sewer debt and pledged to the state loans. The memo says the transfers would use user fees, which weren't part of those votes, but the records searched don't show how the funds' balances would be traced to fees, and staff say the debt requirements are still under review.</li>
      <li><strong>2026 alone.</strong> The 2026 gap, the &minus;$2,180,816 available balance, could be covered on paper without the Community Center: Water&rsquo;s $1.4 million plus Sewer&rsquo;s $788,807 of cash after its loan reserve is about $2.19 million. But that would take both utilities to about $0 available, and 2027 would then add about $350,000 more with no utility money left.</li>
      <li><strong>Whether it closes.</strong> At the stated limits, the three funds could give about $3.1 million against a gap of $2.5 million to $2.6 million, so the plan closes only if nearly all of that money can be used: the Community Center down to $100,000 and the utilities giving about 80% of what staff list as available. Without the Community Center, the utilities' $2.3 million falls short of the $2.53 million in the flat scenario even with both funds at $0. The Town's share of the Downtown Development Authority's reserves, $246,500 to $275,500 if it were dissolved, would bring the flat scenario to about even, but not the 3% scenario. And the Town says its Eldora costs &ldquo;may be materially higher&rdquo; than reported (<a href="https://nederlandco.civicweb.net/document/133493/" target="_blank" rel="noopener">September Treasurer report</a>).</li>
      <li><strong>In short:</strong> by this site's reading of the Town's own figures, the proposed budget doesn't close as presented, relies on Community Center money that the Town's books report as restricted, and would close only with spending cuts, new revenue, or money from sources not yet in the budget.</li>
    </ul>
    </section>
    <h3 id="pay-rest">Could the Town pay the rest?</h3>
    <p class="prose"><strong>In short: the cash exists, but almost none of it is the General Fund's.</strong> The Town keeps all its funds' cash in one shared pool. Paying the rest would use the Water and Sewer Funds' cash, leave them roughly {left_lo} above their reserves, and leave the General Fund owing them about {need_lo} (this page's calculation, in three steps, starting from the Town's Sept. 30, 2026, balance sheets and <a href="#bottom-line">the bottom line</a>).</p>
    <div class="scroll"><table class="walk">
      <thead><tr><th scope="col">Step 1. The General Fund has little or no cash of its own</th><th scope="col">Amount</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>Its share of the pooled cash, Sept. 30, 2026</td><td class="amount">&minus;$105,870</td><td><a href="https://nederlandco.civicweb.net/document/133492/#page=8" target="_blank" rel="noopener">September financials, p. 8</a></td></tr>
        <tr><td>Eldora paid on warrant lists after Sept. 30</td><td class="amount">&minus;{since_sep}</td><td><a href="#ledger">warrant lists</a></td></tr>
        <tr class="bl-total"><td><strong>Already short</strong></td><td class="amount">{gf_short}</td><td>This page's calculation</td></tr>
      </tbody>
    </table></div>
    <div class="scroll"><table class="walk">
      <thead><tr><th scope="col">Step 2. The Water and Sewer Funds' spare cash (Sept. 30, 2026)</th><th scope="col">Water</th><th scope="col">Sewer</th></tr></thead>
      <tbody>
        <tr><td>Pooled cash (<a href="https://nederlandco.civicweb.net/document/133492/#page=12" target="_blank" rel="noopener">September financials, p. 12</a>&ndash;13)</td><td class="amount">$2,237,641</td><td class="amount">$918,807</td></tr>
        <tr><td>Less the reserve required by their state loans</td><td class="amount">−$306,250</td><td class="amount">−$130,000</td></tr>
        <tr><td>Less an operating reserve (about a quarter of a year's operating costs, as in the Town's utility plans)</td><td class="amount">−$175,921</td><td class="amount">−$172,296</td></tr>
        <tr class="bl-total"><td><strong>Available</strong></td><td class="amount">{w_avail}</td><td class="amount">{s_avail}</td></tr>
      </tbody>
    </table></div>
    <div class="scroll"><table class="walk">
      <thead><tr><th scope="col">Step 3. If they paid all of it</th><th scope="col">Amount</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>Water and Sewer cash available</td><td class="amount">{u_avail}</td><td>Step 2</td></tr>
        <tr><td>The General Fund's shortfall and the {conf} still owed</td><td class="amount">−{need_lo}</td><td>Step 1, <a href="#bottom-line">bottom line</a></td></tr>
        <tr class="bl-total"><td><strong>Left above their reserves</strong></td><td class="amount">{left_lo}</td><td>This page's calculation</td></tr>
      </tbody>
    </table></div>
    <ul class="notes prose">
      <li><strong>The utility budgets aren't being spent on Eldora.</strong> In the records searched, no Eldora costs are charged to the Water or Sewer budgets, and both 2026 budgets are funded by their own revenue (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>).</li>
      <li><strong>Their spare cash is already committed.</strong> The water plan spends most of it on fire-flow improvements in 2030&ndash;2031, and the utilities repay $3,070,436 in state loans from their revenue and a set share of the sales tax (<a href="#utility-loan">below</a>). The Downtown Development Authority's and Community Center's money can be used only for their own purposes (<a href="#csafe">below</a>).</li>
      <li><strong>The Board would have to act first,</strong> by appropriating the money, and the General Fund would need an estimated {yrs_def} years to repay the utilities (<a href="#gf-deficit">above</a>).</li>
    </ul>
    <p class="prose muted">Steps 1 to 3 are this page's calculations from the Town's Sept. 30, 2026, balance sheets, which show no money owed between the funds. They leave out the General Fund's own results for the rest of 2026; the Town forecasts it will spend $220,004 more than it takes in for the whole year, before Eldora, which would leave less (<a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a>). With the 180-day operating reserve the Town's utility presentation targets, about $175,000 more for each fund, less would be left. Until Nov. 17, 2026, these steps used the end-of-2025 audit figures. Most of the Eldora bills were still unpaid on Sept. 30.</p>
    <p class="prose">Whether other funds' money may legally carry these costs isn't settled in the records searched; staff's Nov. 16 memo cites the Board's transfer authority and says the utilities' debt requirements are still under review (<a href="#nov16-plan">the Nov. 16 plan</a>, <a href="#fund-dedications">what voters approved</a>, <a href="#open-questions">not in the records searched</a>).</p>
    <h3 id="csafe">CSAFE and the Town's pooled cash</h3>
    <p class="prose">CSAFE (the Colorado Surplus Asset Fund Trust) is a state-regulated investment pool that works like a money-market fund (C.R.S. 24-75-701). It is not set aside for any purpose. In March 2023 the Board approved investing "surplus funds... not immediately required to be disbursed" there (Res. 2023-16, on the consent agenda): $1.5 million then and $1 million more in January 2024. The Treasurer can withdraw "as funds are needed" without a new vote. The balance was $2,700,831 at the end of 2024 and $2,821,014 at the end of 2025 (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>); the September Treasurer report gives the Town's investment accounts as $2,903,146.69 and its combined bank and CSAFE balance as $4,332,895.36 on Sept. 30, 2026 (<a href="https://nederlandco.civicweb.net/document/133493/" target="_blank" rel="noopener">September Treasurer report</a>). CSAFE statements released in response to records requests show $2,884,216 on July 31, 2026, and no deposits or withdrawals in any month provided (December 2024, July 2025, December 2025, and July 2026); the growth was reinvested interest. They don't cover the other months (<a href="#questions">records requests</a>).</p>
    <p class="prose">The Town pools its cash, so the CSAFE money belongs to every Town fund, not to one. The Town says its cash is held in five accounts, two at CSAFE and three at UMB (two money market accounts and a checking account), and that it tracks each fund's share in its general ledger rather than in separate bank accounts (<a href="{rec_reply3}" target="_blank" rel="noopener">Town response</a>, Oct. 20, 2026). Most of it comes from funds restricted by law or contract.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Fund (Dec 31, 2025)</th><th scope="col">Cash and investments</th><th scope="col">Money owed between funds</th><th scope="col">Can it pay Eldora acquisition costs?</th></tr></thead>
      <tbody>
        <tr><td>Water and Sewer (utility funds)</td><td class="amount">$4,150,620</td><td>Owes other funds $1,118,188</td><td><strong>Limited, if at all.</strong> Utility revenue and the utilities' share of the sales tax fund the utilities; $436,250 is classified as restricted. See <a href="#utility-loan">the utility funds</a>.</td></tr>
        <tr><td>Downtown Development Authority</td><td class="amount">$1,695,802</td><td>None</td><td><strong>No.</strong> A separate authority's money for downtown.</td></tr>
        <tr><td>Community Center</td><td class="amount">$964,480</td><td>Owes other funds $158,347</td><td><strong>No.</strong> Restricted to the community center.</td></tr>
        <tr><td>Streets; Conservation Trust (parks)</td><td class="amount">$343,690</td><td>Owes other funds $179,698</td><td><strong>No.</strong> Restricted to roads, parks, and trails.</td></tr>
        <tr><td>General Fund</td><td class="amount">$0</td><td>Is owed $1,456,233 by other funds</td><td><strong>Yes, if the Board appropriates it.</strong> Its cash was negative: the audit says its "negative cash balance of $757,482" is "reported as accounts payable." $147,000 of its fund balance is restricted as the TABOR emergency reserve.</td></tr>
        <tr><td><strong>Total</strong></td><td class="amount"><strong>$7,154,592</strong></td><td>Amounts owed and amounts due are equal</td><td>The audit's total of deposits and investments, including the CSAFE investment, at year end.</td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">On Sept. 30, 2026, the Town's balance sheets show no money owed between these funds, and these shares of the pooled cash: Water $2,237,641, Sewer $918,807, Community Center $906,470, Streets $101,671, Conservation Trust $38,444, and the General Fund &minus;$105,870 (<a href="https://nederlandco.civicweb.net/document/133492/#page=8" target="_blank" rel="noopener">September financials</a>, pp. 8&ndash;13). The Downtown Development Authority's accounts aren't in that report.</p>
    <p class="prose muted">Sources: <a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a> (balance sheets pp. 3 and 6; notes 3, 5, and 10), <a href="https://nederlandco.civicweb.net/document/44139/" target="_blank" rel="noopener">Mar 2023 memo</a>, <a href="https://nederlandco.civicweb.net/document/44144/" target="_blank" rel="noopener">Res. 2023-16</a>, <a href="https://nederlandco.civicweb.net/document/43689/" target="_blank" rel="noopener">Res. 2023-08</a>, <a href="https://nederlandco.civicweb.net/document/122108/" target="_blank" rel="noopener">2024 audit</a> (balance sheets pp. 3 and 6, investment note pp. 17–19), <a href="https://nederlandco.civicweb.net/document/128478/" target="_blank" rel="noopener">Dec 2025 financials</a>, <a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">2026 budget summary</a>. The amounts come from these records. Which funds can legally pay which costs is a reading of general Colorado law and accounting practice: TABOR, the rules for utility and Downtown Development Authority funds, and the audit's "restricted" classifications. The Town attorney or auditor would need to confirm it for these funds.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">What the records say</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td><strong>The CSAFE money isn't designated for the Eldora acquisition in any Board record searched.</strong> Neither the monthly treasurer reports nor the Board minutes mention a vote to use it for Eldora; the Town's September 2026 update is the only source found naming it.</td><td><a href="https://nederlandco.civicweb.net/document/131730/" target="_blank" rel="noopener">Treasurer report, Sep 2026</a></td></tr>
        <tr id="cash-accounts"><td><strong>The treasurer's reports and the audit count cash differently.</strong> The treasurer's "combined year-to-date bank balance," which "includes CSAFE investments," fell from $5,273,959 on July 31, 2025, to $4,324,024 on July 31, 2026, while the "Due From" account's balance rose to about $1.14 million. The July 31, 2026, figure equals, to the cent, the total of the statements for the five accounts the Town says hold its pooled cash, two at CSAFE and three at UMB (<a href="{rec_reply3}" target="_blank" rel="noopener">Town response</a>). The audits count more. At Dec. 31, 2025, the audit's bank balances ($3,681,753) plus CSAFE ($2,821,014) total $6,502,767, while the treasurer's figure is $4,700,645, a difference of $1,802,122. The differences at the end of 2023 ($1,354,086) and 2024 ($1,628,732) are similar. Each year the difference is close to the Downtown Development Authority's cash in the audit ($1,695,802 at the end of 2025); the records searched don't say whether the DDA keeps accounts outside the five. They also don't show how much of any change is due to Eldora.</td><td><a href="https://nederlandco.civicweb.net/document/123387/" target="_blank" rel="noopener">Jul 2025</a>, <a href="https://nederlandco.civicweb.net/document/128497/" target="_blank" rel="noopener">Dec 2025</a>, <a href="https://nederlandco.civicweb.net/document/131730/" target="_blank" rel="noopener">Jul 2026</a> treasurer reports; <a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a></td></tr>
      </tbody>
    </table></div>
    <h3 id="utility-loan">Could the utility funds lend or transfer money to the General Fund?</h3>
    <p class="prose">The Water and Sewer Funds hold most of the Town's pooled cash (<a href="#csafe">the Town's funds</a>), and they have lent money before. From 2012 through 2016 they lent the Downtown Development Authority $842,500 in four loans: $482,500 from the Water Fund in 2012, repaid by 2016; $7,000 from the Water Fund in 2014 and $13,000 from the Sewer Fund in 2015, each due within months and not outstanding in the year-end audits; and $340,000 from the Water Fund in 2016, repaid in 2017 (<a href="https://nederlandco.civicweb.net/document/30607/" target="_blank" rel="noopener">2016 audit</a>, <a href="https://nederlandco.civicweb.net/document/30606/" target="_blank" rel="noopener">2017 audit</a>). The 2016 audit reported the $340,000 in the authority's fund as &ldquo;Proceeds from Issuance of Debt,&rdquo; a financing source that raised that fund's balance, and the authority's budget schedule listed it as &ldquo;Proceeds from Loan.&rdquo; The audit describes the authority as &ldquo;a blended component unit of the Town.&rdquo; Staff's 2026 analysis treats a loan to the General Fund differently, as leaving its balance unchanged (<a href="#budget-options">the Town's options</a>); the records searched don't say whether the Town's auditor would report a loan to the General Fund as the 2016 audit did. Each of the 2014–2016 loans was approved by Board resolution with an interest rate, a deadline, and repayment from the authority's tax increment revenue, and each resolution found that the lending fund could provide the money &ldquo;without hampering the operations or replacement schedules&rdquo; of that fund. The resolutions count the loans against borrowing voters approved in 2012 (<a href="https://nederlandco.civicweb.net/document/24492/" target="_blank" rel="noopener">Res. 2014-33</a>, <a href="https://nederlandco.civicweb.net/document/24440/" target="_blank" rel="noopener">2015-06</a>, <a href="https://nederlandco.civicweb.net/document/24426/" target="_blank" rel="noopener">2016-20</a>). In the audits searched from 2008 through 2025, the General Fund has never been the borrower on a loan from another fund.</p>
    <p class="prose">The Town's draft 10-year utility plans, presented Sept. 1, 2026, show how much of the utilities' cash is already planned for. The Board &ldquo;expressed concern about rate increases&rdquo; and supported the draft plans (<a href="https://nederlandco.civicweb.net/document/132389/" target="_blank" rel="noopener">Sept. 1 minutes</a>).</p>
    <div class="scroll"><table class="walk">
      <thead><tr><th scope="col">Draft utility plans (Sept. 1, 2026)</th><th scope="col">Water Fund</th><th scope="col">Sewer Fund</th></tr></thead>
      <tbody>
        <tr><td>Cash at the start of 2026</td><td class="amount">$2,757,777</td><td class="amount">$1,229,798</td></tr>
        <tr><td>Cash above the plan's operating reserve, end of 2026</td><td class="amount">$2,651,035</td><td class="amount">$1,125,465</td></tr>
        <tr><td>Lowest cash above that reserve, 2026&ndash;2034</td><td class="amount">$228,716 (2032)</td><td class="amount">$399,409 (2033)</td></tr>
        <tr><td>Largest planned project</td><td>Fire-flow improvements, about $7.9 million in 2030&ndash;2031, partly borrowed</td><td>Sewer improvements, about $2.5 million in 2033, partly borrowed</td></tr>
        <tr><td>Debt service coverage in 2026, without plant investment fees (existing loans require 1.10)</td><td class="amount">1.43</td><td class="amount">1.12</td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">Sources: <a href="https://nederlandco.civicweb.net/document/131747/" target="_blank" rel="noopener">water plan</a> and <a href="https://nederlandco.civicweb.net/document/131748/" target="_blank" rel="noopener">sewer plan</a>, cash-and-debt scenario; <a href="https://nederlandco.civicweb.net/document/131746/" target="_blank" rel="noopener">presentation</a>; <a href="https://nederlandco.civicweb.net/document/131745/" target="_blank" rel="noopener">staff memo</a>. Coverage compares a utility's revenue after operating costs with its loan payments. The presentation sets a reserve target of &ldquo;180 days or 50% of O&amp;M,&rdquo; but the plan tables use about a quarter of operating costs (for water, $175,921 of $703,684), so cash above a 180-day reserve would be about $175,000 lower for each fund. The <a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a> shows the utilities owing other funds $1,118,188 at the end of 2025; the plans don't show that amount separately.</p>
    <p class="prose">By this page's reading of those plans, the Water Fund could lend about {unpaid} only for a few years: the plan spends most of its cash on the fire-flow project in 2030&ndash;2031. Repaying {unpaid} by 2030 would take about {unpaid_4} a year, well above the General Fund's average annual gain of {avg_op} to {avg_rep} in 2017&ndash;2023. A loan repaid over the {yrs_def} years this page estimates the General Fund would need would reach the years when the plan needs that cash, and the Sewer Fund's 2026 coverage of 1.12 leaves little room above the 1.10 its loans require.</p>
    <p class="prose">The records searched also don't settle whether such a loan or transfer would be allowed:</p>
    <ul class="notes prose">
      <li><strong>Voter approval.</strong> TABOR requires advance voter approval for a &ldquo;multiple-fiscal year&rdquo; financial obligation (<a href="#gf-deficit">above</a>). The Town asked voters before its multi-year utility borrowing ($6.9 million in 2008, <a href="https://nederlandco.civicweb.net/document/25978/" target="_blank" rel="noopener">Ord. 696</a>) and the authority's borrowing (2012). The records don't say whether a multi-year loan between the Town's own funds needs a vote.</li>
      <li><strong>Sales tax set aside for the utilities.</strong> 11.76% of the Town's sales tax goes to each utility fund (<a href="https://nederlandco.civicweb.net/document/43301/" target="_blank" rel="noopener">Ord. 831</a>), and part of the sales tax is pledged to repay the utilities' state loans (<a href="https://nederlandco.civicweb.net/document/114624/" target="_blank" rel="noopener">Ord. 711</a>). In 2012 the Town said that changing &ldquo;the purposes for which tax revenue is used&rdquo; requires voter approval under TABOR (<a href="https://nederlandco.civicweb.net/document/114623/" target="_blank" rel="noopener">Ord. 710</a>).</li>
      <li><strong>Loan terms.</strong> The utilities' $3,070,436 in loans from the Colorado Water Resources and Power Development Authority are repaid from pledged revenue: water and sewer revenue and a set share of the sales tax (2025 audit; <a href="https://nederlandco.civicweb.net/document/25978/" target="_blank" rel="noopener">Ord. 696</a>, <a href="https://nederlandco.civicweb.net/document/114617/" target="_blank" rel="noopener">Ord. 703</a>, <a href="https://nederlandco.civicweb.net/document/114624/" target="_blank" rel="noopener">Ord. 711</a>). The loan agreements, which would state any limits on that revenue, aren't in the records searched.</li>
    </ul>
    <p class="prose"><strong>If no fund can lend or transfer the money.</strong> The costs would still be owed; <a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a> says some contracts &ldquo;will need to be paid regardless of closing.&rdquo; In practice, the pooled cash would pay the bills first, as it already covers the General Fund's negative cash, and the General Fund would owe that money back. Under the budget law above, the Board would then have to close the gap in later budgets: by cutting or delaying spending, which could mean fewer staff or reduced services; by negotiating payment terms with the firms; by selling Town property, such as land; or by asking voters to approve a new tax or multi-year borrowing. The General Fund's largest 2026 costs are law enforcement ($1,249,399), administration and finance ($646,542), streets ($465,297), and parks ($390,630) (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>). Real estate used or held for parks or another governmental purpose can be sold only with voter approval; other Town real estate can be sold by ordinance (<a href="https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-31.pdf" target="_blank" rel="noopener">C.R.S. 31-15-713</a>).</p>
  </section>

  <section id="afford">
    <h2>How big is it for Nederland?</h2>
    <p class="prose">These comparisons use the costs the General Fund carries: the {balance} paid and this page's itemized total of {owed_m}.</p>
    <h3 id="per-household">Per household</h3>
    <p class="prose">Nederland has about 685 households (<a href="https://nederlandco.civicweb.net/document/132050/" target="_blank" rel="noopener">Sept. 15, 2026, packet</a>) and 1,471 residents (2020 Census, <a href="https://nederlandco.civicweb.net/document/132363/" target="_blank" rel="noopener">parks plan</a>). The {balance} paid so far is about {hh_paid} per household. This page's itemized total of {owed_m} is about {hh_est} per household ({res_est} per resident); the Town's $2.76 million estimate would be about {hh_town}. No one would be billed these amounts; they only show scale. Sales tax is about 40% of the General Fund's budgeted 2026 revenue, not counting grants (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>).</p>
    <h3 id="gf-recovery">The General Fund year by year</h3>
    <p class="prose muted">Its year-end results, from the audits:</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Year</th><th scope="col">Change in fund balance</th><th scope="col">Notes</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>2017–2021</td><td class="amount">+$149,593 to +$304,158 a year</td><td>Gains every year.</td><td><a href="https://nederlandco.civicweb.net/document/30606/" target="_blank" rel="noopener">2017</a>, <a href="https://nederlandco.civicweb.net/document/30605/" target="_blank" rel="noopener">2018</a>, <a href="https://nederlandco.civicweb.net/document/22779/" target="_blank" rel="noopener">2019</a>, <a href="https://nederlandco.civicweb.net/document/30306/" target="_blank" rel="noopener">2020</a>, <a href="https://nederlandco.civicweb.net/document/38114/" target="_blank" rel="noopener">2021</a> audits</td></tr>
        <tr><td>2022</td><td class="amount">+$83,265</td><td>Includes a $43,158 transfer in. Before it, +$40,107.</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/591/2022-Audit" target="_blank" rel="noopener">2022 audit</a></td></tr>
        <tr><td>2023</td><td class="amount">+$124,674</td><td>Includes $511,000 from the street equipment lease-purchase and a $106,155 transfer in. Before them, −$492,481.</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/593/2023-Audit" target="_blank" rel="noopener">2023 audit</a></td></tr>
        <tr><td>2024</td><td class="amount">−$265,953</td><td></td><td><a href="https://nederlandco.civicweb.net/document/122108/" target="_blank" rel="noopener">2024 audit</a></td></tr>
        <tr><td>2025</td><td class="amount">−$192,241</td><td>Does not include the Eldora acquisition costs, which were carried as a receivable. The Town's Nov. 9, 2026, budget presentation restates 2025 with $622,925 in Eldora costs, a change of &minus;$815,166 (<a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a>; <a href="#receivable">receivables</a>). [[corrected:2026-10-13]]</td><td><a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a></td></tr>
        <tr><td>2026 through July (unaudited)</td><td class="amount">−$159,439</td><td>The July 2026 financial report shows the balance at $814,332, down from $973,770 at the start of the year. (The audit puts the 2025 year-end balance at $1,030,078.)</td><td><a href="https://nederlandco.civicweb.net/document/131731/" target="_blank" rel="noopener">July 2026 report</a></td></tr>
        <tr><td>2026 (budget)</td><td class="amount">about −$446,000</td><td>The adopted budget projects the balance falling from $1,030,078 to $583,730.</td><td><a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a></td></tr>
        <tr><td>2026 (Town forecast, Nov. 9)</td><td class="amount">{town_ops} without Eldora</td><td>With $2,135,661 in Eldora costs, &minus;$2,355,665, ending the year at {town_fb}.</td><td><a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a></td></tr>
        <tr><td>2027 (Town preliminary, Nov. 9)</td><td class="amount">&minus;$183,610</td><td>Eldora costs &ldquo;TBD&rdquo;; ending the year at {town_fb27}.</td><td><a href="{rec_slides}#page=4" target="_blank" rel="noopener">budget slides, p. 4</a></td></tr>
      </tbody>
    </table></div>
    <p class="prose">From 2017 through 2023, the General Fund gained about {avg_rep} a year on average, or about {avg_op} without the 2023 lease proceeds. These averages are the basis of the rebuilding estimate under <a href="#gf-deficit">General Fund deficit</a>.</p>
    <h3 id="scale">Compared with Town budgets and other spending</h3>
    <p class="prose muted">The Town's adopted 2026 budget plans about $9.4 million in spending across all funds, including about $2.25 million in grant-funded projects and the separate water, sewer, and downtown funds (<a href="https://nederlandco.civicweb.net/document/126174/" target="_blank" rel="noopener">Res. 2025-28</a>). The General Fund, which runs day-to-day Town government, spends about $3.2 million a year (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>).</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Comparison</th><th scope="col">Amount</th><th scope="col">Compared with Eldora acquisition costs</th></tr></thead>
      <tbody>
        <tr><td>General Fund operating spending, 2026 budget</td><td class="amount">$3.24 million</td><td>The {balance} paid equals about {pct_paid} of a year's General Fund operations. The itemized total of {owed_m} equals about {pct_est}.</td></tr>
        <tr><td>Boulder County Sheriff contract, the Town's largest single General Fund cost</td><td class="amount">$931,629 (2026)</td><td>The Eldora acquisition costs paid so far exceed a full year of the Sheriff contract. For 2025 the Town chose about 50% coverage, priced at $885,798, rather than $1,054,037 to keep its 2024 coverage (<a href="https://nederlandco.civicweb.net/document/116629/" target="_blank" rel="noopener">Nov. 2024 budget presentation, pp. 26&ndash;27</a>, <a href="https://nederlandco.civicweb.net/document/127190/" target="_blank" rel="noopener">2026 contract</a>). [[corrected:2026-11-17]]</td></tr>
        <tr><td>General Fund capital spending (equipment and improvements), 2024 actual to 2026 budget</td><td class="amount">$160,000–$200,000 a year</td><td>The itemized total of {owed_m} is more than {cap_yrs} years of capital spending at that level (<a href="https://nederlandco.civicweb.net/document/126178/" target="_blank" rel="noopener">budget summary</a>).</td></tr>
      </tbody>
    </table></div>
    <h3>Compared with other recent discretionary spending</h3>
    {scale_chart}
    <p class="prose muted">Bars are on one scale. Recurring costs such as the Sheriff contract and utility debt are not counted as discretionary. The records cover 2023 onward.</p>
  </section>

  <div class="group" id="if-closes"><span>If the purchase closes</span></div>
  <section id="commitments">
    <h2>Commitments if the purchase closes</h2>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Item</th><th scope="col">Amount</th><th scope="col">Status</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>Purchase price (no deposit; closing depended on selling the bonds)</td><td class="amount">$120,000,000</td><td><span class="status none">Expired</span></td><td><a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">Ord. 882, APA §2.5</a></td></tr>
        <tr><td>Series 2026 revenue bonds (up to 40 years, at most 9%); had to be sold by about July 19, 2026</td><td class="amount">up to $225,000,000</td><td><span class="status none">Lapsed</span></td><td><a href="https://nederlandco.civicweb.net/document/127180/" target="_blank" rel="noopener">Ord. 885 §5(c)</a></td></tr>
        <tr><td>Expected bond amount when the Board declared its intent to repay early costs from the bonds</td><td class="amount">$180,000,000</td><td><span class="status auth">Declared</span></td><td><a href="https://nederlandco.civicweb.net/document/123060/" target="_blank" rel="noopener">Res. 2025-17</a></td></tr>
        <tr><td>Planned philanthropy for capital projects, kept outside the bond debt</td><td class="amount">~$20,000,000</td><td><span class="status cont">Planned</span></td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Sep 30, 2026 update</a></td></tr>
        <tr><td>Stifel financial-advisor fee, paid from bond proceeds</td><td class="amount">$325,000</td><td><span class="status cont">If bonds sell</span></td><td><a href="https://nederlandco.civicweb.net/document/130471/" target="_blank" rel="noopener">Jul 7, 2026 memo</a></td></tr>
        <tr><td>Emergency spending authority to run the resort after a closing (not for due diligence); ran 120 days from April 21, 2026</td><td class="amount">No dollar limit</td><td><span class="status none">Lapsed</span></td><td><a href="https://nederlandco.civicweb.net/document/129046/" target="_blank" rel="noopener">Res. 2026-13</a></td></tr>
      </tbody>
    </table></div>
  </section>

  <section id="profit-sec">
    <h2 id="profit">Profit: what the Town projected, and what the bond terms say</h2>
    <ul class="notes prose">
      <li><strong>January 2025.</strong> The staff memo for Ordinance 873, which created the enterprise: "Any surplus revenue, in compliance with TABOR, may be redirected to other Town priorities" (<a href="https://nederlandco.civicweb.net/document/118505/" target="_blank" rel="noopener">memo</a>).</li>
      <li><strong>January 2025.</strong> FAQ Round 2 quoted Eldora's general manager: "Eldora is profitable." Once debt obligations and "rainy day funds" are covered, "any leftover profits will be available for the town" (<a href="https://nederlandco.civicweb.net/document/118136/" target="_blank" rel="noopener">FAQ Round 2</a>).</li>
      <li><strong>July 2025.</strong> FAQ 3.0: "Current models show we can build a reserve of $10 million in the first couple of years." Excess cash flow "does not become meaningful until the subordinate bonds are paid off," which the Town aimed to do "within ten years." "After that, free cash flow will fall between $2M - $5M+." Annexing the resort "could add $1M - $2M in annual revenue to the Town's general fund." The FAQ said it "cannot disclose exact figures" (<a href="https://web.archive.org/web/20250709224556/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-30" target="_blank" rel="noopener">FAQ 3.0</a>).</li>
      <li><strong>August 2025.</strong> FAQ 4.0: after the subordinate bonds are retired and reserves are built, the Board could direct "excess revenues" to streets, sidewalks, affordable housing, and childcare (<a href="https://web.archive.org/web/20251112014324/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-40" target="_blank" rel="noopener">FAQ 4.0</a>).</li>
      <li><strong>April 2026.</strong> FAQ 6.0 no longer gives the annexation estimate. It says much of the ski area is on Forest Service land that "is not anticipated" to be annexed, and that annexation "must be evaluated separately" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0</a>).</li>
      <li><strong>September 2026.</strong> The Town update gives no revenue or profit figures. It says the first "approximately ten years" are "more financially constrained," and that its assumptions have become more conservative (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>).</li>
    </ul>
    <p class="prose">No financial model, feasibility study, or bond-offering document is in the records searched. Under the draft Indenture of Trust (January 20, 2026, packet), revenue left after operations, debt payments, and reserves goes first to paying off the senior bonds early, all of it until revenue covers debt payments two to one for three straight years, then half. What remains goes to a "Surplus Fund" that stays available to pay the bonds; that draft has no provision releasing money to the Town (<a href="https://nederlandco.civicweb.net/document/127181/" target="_blank" rel="noopener">Indenture §5.07, §5.11</a>). The May 2026 draft keeps the early-payoff rule, returns it to 100% after any draw on the reserves, and says money in the Surplus Fund "may be used for any lawful purpose by the Town" (<a href="{rec_ind}" target="_blank" rel="noopener">May draft</a> §5.07, §5.11, §5.12; <a href="{rec_reply2}" target="_blank" rel="noopener">Town response</a>). The final terms may differ.</p>
    <p class="prose" id="may-draft">The May 2026 draft also shows part of the price being paid in bonds. Subordinate "capital appreciation" bonds were to be "delivered to or at the direction of the Seller in consideration for a portion of the purchase price," with the investor letter drafted for the "initial purchase by Powdr Corp." These bonds pay no current interest; their value grows, compounding every six months. They can't be transferred before Oct. 1, 2036, have no reserve, and are paid only after the senior bonds and required deposits, beginning in November 2036 (<a href="{rec_ind}" target="_blank" rel="noopener">May draft</a> §2.05, §2.06, §3.02, §5.07, Exhibit I). In the January draft, the subordinate bonds were to be sold for cash. The Town materials searched mention subordinate bonds but not that the seller would hold them. Other May draft terms, some still marked as tentative: the senior bonds would be sold only to institutional investors, without a rating, at no more than 9%; bond proceeds would pay interest until about April 2029, with added deposits of $1.2 million each March from 2027 to 2029; principal payments would begin about November 2035; and the senior bonds would mature by 2039 and 2056. An independent consultant would approve the resort's annual budgets; the Town couldn't end POWDR's <a href="#transition-services">transition agreement</a> early without bondholder consent, though the January draft of that agreement would let the Town end it on 60 days' notice (<a href="https://nederlandco.civicweb.net/document/126804/" target="_blank" rel="noopener">draft agreement §5.03</a>); and while the bonds are outstanding, the Town would keep its corporate existence and not seek bankruptcy or dissolution (§6.10, §6.11, §6.16, §6.17). All bond amounts and rates are blank (<a href="{rec_ind}" target="_blank" rel="noopener">May draft</a>, <a href="{rec_reply2}" target="_blank" rel="noopener">Town response</a>).</p>
    <p class="prose" id="bond-schedule"><strong>The bond payment schedules.</strong> Two pages from the bond offering documents show the scheduled payments. One, which the Town posted Nov. 6, 2026, from the Preliminary Limited Offering Memorandum of March 19, 2026, shows &ldquo;2026 Bond Debt Service&rdquo; of $12,459,950 a year in 2027&ndash;2035, rising to $21,993,850 in 2056, $481,370,357 in all (<a href="https://www.nederlandco.gov/DocumentCenter/View/677" target="_blank" rel="noopener">debt service</a>). The other, released to Karen Blakemore in response to her records request and from the May 13, 2026, supplement according to the Town, is a &ldquo;Schedule of Estimated Revenue, Expenses, Senior Debt Service and Senior Debt Service Coverage.&rdquo; It shows &ldquo;Scheduled 2026A Bond Debt Service&rdquo; of $4,032,635 in 2026, $11,707,650 a year in 2027&ndash;2036, and more each year after that, reaching $20,188,500 in 2056, $443,554,910 in all (<a href="{rec_ds2}" target="_blank" rel="noopener">senior schedule</a>). On both pages, every other column is blank, including operating revenue, expenses, &ldquo;EBITA Net Revenues,&rdquo; net revenue available for debt service, and coverage ratios; the Town said it redacted information that was &ldquo;not responsive&rdquo; or &ldquo;confidential commercial or financial information&rdquo; under C.R.S. 24-72-204(3)(a)(IV) (<a href="{rec_ds_reply}" target="_blank" rel="noopener">Town response</a>). Asked why the payments rise, the Town wrote that the draft indenture requires that once the resort&rsquo;s &ldquo;operating, reserve and scheduled debt payments are covered, all the remaining revenue must go toward paying down the senior bonds early,&rdquo; so &ldquo;the amount paid to the debt can rise over time even though the scheduled payments are fixed&rdquo; (<a href="https://nederlandco.civicweb.net/document/133375/" target="_blank" rel="noopener">Nov. 17 Eldora memo</a>). The column on the released page is itself labeled &ldquo;Scheduled&rdquo; and rises about 2.5% a year from 2038 to 2056. Both pages are from offering documents for bonds that were not sold, prepared before the restructuring the Town describes (<a href="#revised-plan">where things stand</a>).</p>
  </section>
{district_taxes}
  <div class="group" id="accountability"><span>Records and statements</span></div>
  <section id="town-statements">
    <h2>What the Town told the public</h2>
    <p class="prose muted">These are the Town's FAQs and announcements about cost and funding, in date order. FAQ Round 2 was also included in the Jan. 7, 2025, Board packet; the others were posted only on the Town website. Earlier versions were on the Town's previous website and are linked here through the Internet Archive; the first FAQ (Nov. 14, 2024) was posted on the Engage Nederland site and is <a href="https://web.archive.org/web/20250815043449/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faq-on-engage-nederland" target="_blank" rel="noopener">archived</a>. [[corrected:2026-10-11]]</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Date</th><th scope="col">What the Town said</th><th scope="col">Source</th></tr></thead>
      <tbody><tr><td class="dt">Jan 7, 2025</td><td>FAQ Round 2. Estimates the price at "around $100M - $200M." Says an enterprise fund would keep the purchase "completely separated from the Town’s general fund," and that if the final offer were accepted, "we will have to provide earnest money to secure the mountain." The January 2026 draft purchase agreement has no deposit.</td><td><a href="https://nederlandco.civicweb.net/document/118136/" target="_blank" rel="noopener">FAQ Round 2 (Board packet)</a></td></tr><tr><td class="dt">Jul 8, 2025</td><td>FAQ 3.0: "We are buying Eldora!" Announces the signed term sheet. Says the bonds "will not be backed by local tax dollars," and that the bond limit "covers the acquisition, and the consultants and advisers needed to close the deal." Projects a reserve of about $10 million. Announces a partnership with 303 Ski, a group of Front Range ski-industry veterans who vetted operating plans and would "support the mountain once POWDR's contract expires."</td><td><a href="https://web.archive.org/web/20250709224556/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-30" target="_blank" rel="noopener">FAQ 3.0 (archived)</a></td></tr><tr><td class="dt">Aug 28, 2025</td><td>FAQ 4.0, in an answer about the enterprise fund and revenue bonds: "No general Town funds or taxpayer dollars are being used to purchase the mountain," and "no general Town resources will be used." Eldora due-diligence bills dated that month were later charged to the General Fund as money owed back to the Town, to be repaid from bond proceeds (Res. 2025-17), starting with the Oct. 7, 2025, warrant list (see <a href="#costs">What has been spent</a>).</td><td><a href="https://web.archive.org/web/20251112014324/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-40" target="_blank" rel="noopener">FAQ 4.0 (archived)</a></td></tr><tr><td class="dt">By Apr 2, 2026</td><td>FAQ 6.0 (reposted Oct. 5, 2026). Repeats that no general Town funds are being used "to purchase Eldora Mountain Resort." Names disclosure counsel Butler Snow and real estate counsel Brownstein Hyatt Farber Schreck. Fees are "not subject to a single fixed cap." Expects closing April 30, 2026. Asked why the Town would walk away from 303 Ski, says its "future involvement was not without cost" and that the Town declined its "requests … for reimbursement of time and expenses." Says the Town intends to rely on Eldora's existing management, with "direct integration" between the Town Manager and the resort's CEO, and that after POWDR's two-year transition agreement it "anticipates relying on professional on-mountain management."</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0</a></td></tr><tr><td class="dt">Jul 23, 2026</td><td>FAQ 7.0. Confirms about $830,000 in costs "paid or advanced" as of the BusinessDen article, expected to be repaid from bond proceeds. Says the purchase might not close, that some contracts "will need to be paid regardless of closing," and that Town reserves are "sufficient to cover the current expenses." Says Stifel’s $325,000 is "in addition to the $830,000" but is owed only if the deal closes. Points readers to the warrant lists for all expenses.</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a></td></tr><tr><td class="dt">Sep 17, 2026</td><td>Request for proposals for a Town auditor: the Town is "currently in negotiations to purchase the Eldora Ski Resort," and bidders must price an audit of the Mountain Recreation Enterprise separately.</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/20" target="_blank" rel="noopener">RFP post</a></td></tr><tr><td class="dt">Sep 30, 2026</td><td>Update from Mayor Sterling and the Board. The purchase agreement "has expired," but talks continue on a restructured deal (<a href="#revised-plan">revised plan</a>). Estimates transaction-related costs of about $2.5 million if the sale fails, which it says "would be paid through our CSAFE investments" (<a href="#bottom-line">bottom line</a>).</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a></td></tr><tr><td class="dt">Oct 20, 2026</td><td>"Eldora Transaction Update" memo in the Board packet. Pursuing the purchase at $120 million; refers to "outstanding financial obligations" without listing them; attaches the 2026 ledger and a <a href="#revised-plan">sale-leaseback overview</a>; staff will review Eldora costs at the Nov. 5, 2026, budget work session (later moved to Nov. 9); Eldora updates become a standing agenda item (<a href="#findings-h">findings</a>).</td><td><a href="https://nederlandco.civicweb.net/document/132785/" target="_blank" rel="noopener">Oct. 20 memo</a></td></tr><tr><td class="dt">Oct 27, 2026</td><td>Meeting notice on the Town&rsquo;s Facebook page. The Board&rsquo;s Nov. 3 meeting, first moved to Nov. 5, is now Monday, Nov. 9, at 7 p.m. The Board will begin discussing the FY2027 budget and &ldquo;will consider adopting a resolution related to the future of Eldora Mountain Resort and the Town&rsquo;s ongoing efforts surrounding its potential acquisition&rdquo;. The notice doesn&rsquo;t describe the resolution.</td><td><a href="https://www.facebook.com/NederlandCO/posts/pfbid0PTD4EZ1WSTcbVcEkrtTNMKnTKpZeGVz5HK5mij7ig5KRfAyQEKg79SK7gRD2zzqJl" target="_blank" rel="noopener">Town notice</a></td></tr><tr><td class="dt">Nov 6, 2026</td><td>A new page on the Town website for records released under public records requests, which the Town says it will keep updating. It posts the confidentiality agreements for the acquisition (with POWDR, Alterra, RBC Capital Markets, prospective bond investors, and the Board and Town Administrator; the signed investor form posted is from accounts managed by First Eagle Investment Management, LLC, for the March 19, 2026, preliminary offering memorandum), saying their release required the other parties&rsquo; permission; a debt-service schedule from the bonds&rsquo; preliminary offering memorandum; the May 2026 draft indenture as &ldquo;the proposed or substantially final forms of the indenture and other bond-related documents referenced in Ordinance 885&rdquo;; the firms&rsquo; October confirmations; engagement agreements; the sale-leaseback overview; and an &ldquo;Expenditure Summary,&rdquo; the &ldquo;Due From&rdquo; ledger through Sept. 25, 2026. It says that &ldquo;upon successful completion of the acquisition, the Town would be reimbursed for these expenditures through bond proceeds.&rdquo;</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/27" target="_blank" rel="noopener">Town records page</a></td></tr><tr><td class="dt">Nov 9, 2026</td><td>Board packet (posted before the meeting). An &ldquo;Eldora Mountain Resort Acquisition Update&rdquo; memo says staff will review &ldquo;the financial impacts of the proposed Eldora Mountain Resort acquisition on the FY26 and FY27 budgets&rdquo; (<a href="https://nederlandco.civicweb.net/document/133097/" target="_blank" rel="noopener">memo</a>). Draft <a href="#res-2026-31">Resolution 2026-31</a> says &ldquo;the Town&rsquo;s Sept. 30, 2026, updated estimates show that the Town has incurred about $2.76 million in transaction-related costs that would not be reimbursed if the transaction does not close,&rdquo; describes the restructured deal (<a href="#revised-plan">where things stand</a>), and says the Board has incurred costs for analyses by SE Group and Causey Public Finance, LLC, and that the bond financing was reviewed by the underwriters, RBC Capital Markets and BofA Securities (<a href="https://nederlandco.civicweb.net/document/133099/" target="_blank" rel="noopener">Res. 2026-31</a>).</td><td><a href="https://nederlandco.civicweb.net/document/133099/" target="_blank" rel="noopener">Nov. 9 packet</a></td></tr><tr><td class="dt">Nov 9, 2026</td><td>Budget presentation to the Board, not in the packet. Forecasts the General Fund at {town_fb} at the end of 2026 and {town_fb27} at the end of 2027 after Eldora costs of $622,925 in 2025 and $2,135,661 in 2026, and presents three ways to cover the deficit: folding in the Community Center Fund, a transfer from the Water and Sewer Funds, or dissolving the Downtown Development Authority (<a href="#gf-deficit">General Fund deficit</a>, <a href="#budget-options">the Town's options</a>).</td><td><a href="{rec_slides}" target="_blank" rel="noopener">budget slides</a></td></tr><tr><td class="dt">Nov 17, 2026</td><td>Board packet (posted before the meeting). The Eldora memo answers a resident&rsquo;s question about why the bond payments rise (<a href="#bond-schedule">the bond payment schedules</a>) and adds two documents listing possible donations and partners (<a href="#donors">donations and partners</a>). The revised draft of <a href="#res-2026-31">Resolution 2026-31</a> keeps the $2.76 million estimate.</td><td><a href="https://nederlandco.civicweb.net/document/133375/" target="_blank" rel="noopener">Nov. 17 Eldora memo</a></td></tr><tr><td class="dt">Nov 16, 2026</td><td>Added to the Nov. 17 packet. The September financial report says the Town reassessed its Eldora costs and now records them as spending, including amounts &ldquo;paid or incurred&rdquo; through Oct. 15, and that they &ldquo;could materially increase&rdquo; (<a href="#receivable">how the costs were recorded</a>). A revised budget memo proposes transfers from the Community Center, Water, and Sewer Funds and an amended 2026 budget (<a href="#nov16-plan">the Nov. 16 plan</a>).</td><td><a href="https://nederlandco.civicweb.net/document/133493/" target="_blank" rel="noopener">September Treasurer report</a>, <a href="https://nederlandco.civicweb.net/document/133495/" target="_blank" rel="noopener">Nov. 16 budget memo</a></td></tr><tr><td class="dt">Nov 17, 2026</td><td>Special meeting notice: two executive sessions at 6 p.m., one on the purchase and negotiations and one &ldquo;to receive legal advice regarding acquisition diligence expenses, options for payment of those expenses, and applicable Colorado budget requirements.&rdquo;</td><td><a href="https://nederlandco.civicweb.net/document/133479/" target="_blank" rel="noopener">special meeting agenda</a></td></tr></tbody>
    </table></div>
    <h3 id="questions">Questions and records requests from the public</h3>
    <p class="prose">Residents' questions and open records requests about the acquisition, in date order.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">When</th><th scope="col">Who</th><th scope="col">What was asked, and the answer</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td class="dt">Dec. 2024</td><td>Planning Commission member</td><td>Urged that the Town Administrator track the hours spent on the Eldora proposal.</td><td><a href="https://nederlandco.civicweb.net/document/118183/" target="_blank" rel="noopener">minutes</a></td></tr>
        <tr><td class="dt">Dec. 2024 to Feb. 2025</td><td>Three records requests</td><td>Board and staff emails and records mentioning Eldora or POWDR, each picking up where the last left off; the first took about five hours of staff time.</td><td>Clerk reports, <a href="https://nederlandco.civicweb.net/document/117486/" target="_blank" rel="noopener">Dec.</a>, <a href="https://nederlandco.civicweb.net/document/118502/" target="_blank" rel="noopener">Jan.</a>, <a href="https://nederlandco.civicweb.net/document/119081/" target="_blank" rel="noopener">Feb.</a></td></tr>
        <tr><td class="dt">July 2025</td><td>Residents at the town hall</td><td>How much had been spent on due diligence, and whether the purchase would cost the Town money; the Board said answers would follow in a later FAQ, and FAQ 4.0 didn't give the amount.</td><td>video, <a href="https://www.youtube.com/watch?v=0AigDgranLU&amp;t=2327s" target="_blank" rel="noopener">0:38:47</a>, <a href="https://www.youtube.com/watch?v=0AigDgranLU&amp;t=2712s" target="_blank" rel="noopener">0:45:12</a></td></tr>
        <tr><td class="dt">Nov. 2025</td><td>Public comment</td><td>&ldquo;Why are our tax dollars being used to research and pay legal fees in reference to the acquisition of Eldora?&rdquo;.</td><td><a href="https://nederlandco.civicweb.net/document/125984/" target="_blank" rel="noopener">comment</a></td></tr>
        <tr><td class="dt">May 2026</td><td>Records request</td><td>The documents prepared for potential buyers of the bonds.</td><td><a href="https://nederlandco.civicweb.net/document/129650/" target="_blank" rel="noopener">Clerk report</a></td></tr>
        <tr><td class="dt">June 2026</td><td>Records request</td><td>&ldquo;All contracts, consultant agreements, and payments made in connection with the Eldora acquisition&rdquo;; staff estimated 12 hours, and the requester paid a deposit.</td><td>Clerk reports, <a href="https://nederlandco.civicweb.net/document/130055/" target="_blank" rel="noopener">June</a>, <a href="https://nederlandco.civicweb.net/document/130713/" target="_blank" rel="noopener">July</a></td></tr>
        <tr><td class="dt">July 2026</td><td>A former trustee and a resident</td><td>A breakdown of costs and what happens if the purchase fails; FAQ 7.0 and the Sept. 30 update later gave totals.</td><td><a href="https://nederlandco.civicweb.net/document/130492/" target="_blank" rel="noopener">comment</a>, <a href="https://nederlandco.civicweb.net/document/130665/" target="_blank" rel="noopener">minutes</a></td></tr>
        <tr><td class="dt">Sept. 2026</td><td>Melody Baumhover</td><td>Which reserves FAQ 7.0 called &ldquo;sufficient,&rdquo; and how the &ldquo;Due From&rdquo; account works. The Town said CORA doesn't require it to &ldquo;answer questions&rdquo; and released the account's 2025&ndash;2026 ledger and July 2026 bank and CSAFE statements.</td><td><a href="{rec_reply}" target="_blank" rel="noopener">Town response</a>, <a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a></td></tr>
        <tr><td class="dt">Sept. 2026</td><td>The former trustee</td><td>&ldquo;Another update please - one with substance. It's our money&rdquo;.</td><td><a href="https://nederlandco.civicweb.net/document/132059/" target="_blank" rel="noopener">comment</a></td></tr>
        <tr><td class="dt">Oct. 2026</td><td>Melody Baumhover</td><td>Engagement records for the 18 firms paid from the &ldquo;Due From&rdquo; account, bank statements, and where five funds are held. Within the free first hour, the Town explained its pooled cash and released agreements and the Ikon cost-sharing letter, posted here; nine firms' records, including Hogan Lovells', weren't included.</td><td><a href="{rec_reply3}" target="_blank" rel="noopener">Town response</a>; <a href="{rec_stifel}" target="_blank" rel="noopener">Stifel</a>, <a href="{rec_kav}" target="_blank" rel="noopener">Kline Alvarado Veio</a>, <a href="{rec_qoe}" target="_blank" rel="noopener">Plante Moran</a>, <a href="{rec_farn}" target="_blank" rel="noopener">Farnsworth</a>, <a href="{rec_bolder}" target="_blank" rel="noopener">Bolder HR</a>, <a href="{rec_bba}" target="_blank" rel="noopener">BBA</a>, <a href="{rec_datasite}" target="_blank" rel="noopener">Datasite</a>, <a href="{rec_ikon}" target="_blank" rel="noopener">Ikon letter</a></td></tr>
        <tr><td class="dt">Oct. 2026</td><td>A resident</td><td>The bond-document forms on file with the Clerk, and the latest indenture and lease drafts. The Town provided a draft indenture dated as of May 1, 2026, and said the lease &ldquo;has not been drafted&rdquo;.</td><td><a href="{rec_reply2}" target="_blank" rel="noopener">Town response</a>, <a href="{rec_ind}" target="_blank" rel="noopener">Word file</a></td></tr>
        <tr><td class="dt">Oct. 2026</td><td>Karen Blakemore</td><td>The bond payment schedule or debt-service projections. The Town released two pages with every column except debt service redacted, and answered her question about rising payments in its Nov. 17 memo.</td><td><a href="{rec_ds_reply}" target="_blank" rel="noopener">Town response</a>, <a href="#bond-schedule">the bond payment schedules</a></td></tr>
        <tr><td class="dt">Oct. 2026</td><td>A resident</td><td>The records behind the $2.5 million estimate, unpaid invoices, fee agreements, and written cost-estimate updates. The Town released the firms' confirmations and three agreements, but no worksheet and no agreements for Hogan Lovells, U.S. Bank, Partner Engineering and Science, Semple, Farrington, Everall &amp; Case, or Torrent, and said no cost-estimate updates exist.</td><td><a href="{rec_reply4}" target="_blank" rel="noopener">Town response</a>, <a href="#owed-confirmed">confirmations</a></td></tr>
        <tr><td class="dt">Oct. 2026</td><td>A resident</td><td>The non-confidential parts of Plante Moran's quality-of-earnings report. The Town said Nov. 6 that POWDR considers it &ldquo;confidential in its entirety&rdquo; and that it has asked POWDR to reconsider &ldquo;because portions of the report appear not to contain confidential information&rdquo;.</td><td><a href="https://eldorarecord.org/records/2026-11-06-town-cora-response.txt" target="_blank" rel="noopener">Town response</a></td></tr>
        <tr><td class="dt">Oct. 2026</td><td>13 residents at the Oct. 20 meeting</td><td>Eight expressed concern about the debt incurred; four urged adoption of a resident's draft resolution; two urged the Board to back away; one supported the purchase; others asked about transparency, the Forest Service permit, and the lack of a recent financial report.</td><td><a href="https://nederlandco.civicweb.net/document/133102/" target="_blank" rel="noopener">draft minutes, pp. 2&ndash;3</a></td></tr>
        <tr><td class="dt">Nov. 2026</td><td>A resident</td><td>The acquisition's confidentiality agreements; answered Nov. 4 with the seven agreements the Town posted Nov. 6.</td><td><a href="https://www.nederlandco.gov/m/newsflash/home/detail/27" target="_blank" rel="noopener">Town records page</a></td></tr>
        <tr><td class="dt">Nov. 2026</td><td>Melody Baumhover</td><td>Emails between Mayor Sterling and the former Town Manager, April through September 2026, containing any of six financial terms. The Town released one thread, about the 2025 audit, and withheld &ldquo;certain additional emails&rdquo; as privileged without listing them.</td><td><a href="{rec_audit_reply}" target="_blank" rel="noopener">Town response</a>, <a href="#audit-note">the audit note</a></td></tr>
        <tr><td class="dt">Nov. 2026</td><td>A resident</td><td>The Nov. 9 budget slides and any analysis behind the options. Answered Nov. 16 with the slides and staff&rsquo;s Oct. 30 &ldquo;Budget Scenarios&rdquo; spreadsheet.</td><td><a href="{rec_bud_reply}" target="_blank" rel="noopener">Town response</a>, <a href="#staff-scenarios">the spreadsheet</a></td></tr>
        <tr><td class="dt">Oct.&ndash;Nov. 2026</td><td>A resident</td><td>Emails from 20 firms to Town addresses since Jan. 1, 2025, sending Eldora invoices or payment notices, with all recipients shown. After a seven-working-day extension, the Town released on Nov. 16 what it pulled in the free first hour, mostly invoice emails from the Town Manager&rsquo;s mailbox for nine firms, and estimated 10 more hours, with a $413.70 deposit, for the rest. After the deposit was paid, the Town released Hogan Lovells' records on Nov. 26, redacting the descriptions of the work as attorney-client privileged and the firm's bank details (C.R.S. 24-72-204(3)(a)(IV)); the other firms' records are to follow.</td><td><a href="{rec_inv_reply}" target="_blank" rel="noopener">Town response</a>; <a href="{rec_hl_reply}" target="_blank" rel="noopener">Nov. 26 response</a>, <a href="{rec_hl_inv}" target="_blank" rel="noopener">Hogan Lovells</a>, <a href="{rec_powdr_audit}" target="_blank" rel="noopener">POWDR</a>, <a href="{rec_taft_inv}" target="_blank" rel="noopener">Taft</a>, <a href="{rec_bhfs_inv}" target="_blank" rel="noopener">Brownstein</a>, <a href="{rec_wwpf_inv}" target="_blank" rel="noopener">Williams Weese</a>, <a href="{rec_other_inv}" target="_blank" rel="noopener">others</a>, <a href="{rec_conf_req}" target="_blank" rel="noopener">confirmation requests</a></td></tr>
      </tbody>
    </table></div>
    <p class="prose muted">The Town Clerk's monthly reports list records requests but not what was released, and the February and March 2026 reports list no requests, so the requests above may not be all of them. The Town's written answers are in the table above.</p>
    <p class="prose" id="cora-fees"><strong>Help cover records-request fees.</strong> The Town charges for records requests that take more than an hour of staff time. The current request for the firms' invoice emails needed a $413.70 deposit, which has been paid (<a href="{rec_inv_reply}" target="_blank" rel="noopener">Town estimate</a>). If you'd like to help, Venmo <a href="https://venmo.com/u/Dallas-Masters" target="_blank" rel="noopener">@Dallas-Masters</a> (please choose &ldquo;Friends &amp; Family&rdquo;). I'll post what comes in and what it pays for. I don't accept money from anyone with a financial stake in the acquisition.</p>
  </section>

  <section id="board-knowledge">
    <h2>Cost information in Board documents</h2>
    <p class="prose">What the Board documents said about expected costs, and where the spending appeared in the meeting packets.</p>

    <h3 id="estimates">Estimates compared with spending</h3>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Item</th><th scope="col">Estimate or terms in Board documents</th><th scope="col">What happened</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr><td>SE Group due diligence (Jul 15, 2025)</td><td>"We anticipate our professional fees will not exceed $69,000," plus expenses of "typically 10%." The proposal said any increase in scope or fees, and any specialty experts, would be "provided to you for your authorization in writing" first. The Board approved the agreement "substantially in the form of the proposal" (<a href="https://nederlandco.civicweb.net/document/124156/" target="_blank" rel="noopener">Res. 2025-15</a>).</td><td><strong>$134,231 paid</strong> [[corrected:2026-10-11]]. An undated first amendment, signed by the Town Manager under Res. 2025-22, continues the work hourly &ldquo;until the Town’s due diligence efforts are complete&rdquo; and says the total contract amount is increased, without stating an amount (<a href="{rec_seg_amend}" target="_blank" rel="noopener">amendment</a>). The firm confirmed $2,500 not yet invoiced as of Oct. 16, 2026.</td><td><a href="https://nederlandco.civicweb.net/document/122623/" target="_blank" rel="noopener">memo</a>, <a href="https://nederlandco.civicweb.net/document/122625/" target="_blank" rel="noopener">proposal p.4–5</a></td></tr>
        <tr><td>Plante Moran financial due diligence (Aug 12, 2025) and transition planning (Apr 21, 2026)</td><td>Due diligence (&ldquo;quality of earnings&rdquo;) on the resort's finances: $55,000 to $65,000 plus costs, &ldquo;not contingent on the successful closing,&rdquo; signed by the Town Administrator Aug. 14, 2025; not in the Board documents searched. Transition planning: $90,000 to $110,000, over four to five weeks.</td><td><strong>$161,656 in Eldora acquisition charges</strong>, on invoices dated Dec. 4, 2025, to May 11, 2026, including $853 of a May 2026 invoice moved into the account from Professional Services (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>). The ledger doesn't say which engagement each invoice was for. Res. 2025-22 (Oct. 7, 2025) authorized the Town Manager to engage HR and finance consultants; it names no firm or estimate.</td><td><a href="{rec_qoe}" target="_blank" rel="noopener">due diligence letter</a>, <a href="https://nederlandco.civicweb.net/document/128983/" target="_blank" rel="noopener">transition letter p.3</a>, <a href="https://nederlandco.civicweb.net/document/124849/" target="_blank" rel="noopener">Res. 2025-22</a></td></tr>
        <tr><td>Bond counsel, Kline Alvarado Veio (Aug 1, 2025)</td><td>$200,000 to $250,000, plus expenses of no more than $5,000, &ldquo;payable at Closing.&rdquo; &ldquo;If the Bonds are not issued, for whatever reason,&rdquo; the firm will bill its accrued time at $695 and $450 an hour. The Town's acceptance is blank in the copy released.</td><td>{kline} paid, on an invoice dated June 16, 2026 (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>). The firm confirmed $200,000 not yet invoiced as of Oct. 16, 2026, without saying whether that is accrued time or its estimated fee at closing (<a href="{rec_c_kav}" target="_blank" rel="noopener">confirmation</a>).</td><td><a href="{rec_kav}" target="_blank" rel="noopener">engagement letter p.3–4</a></td></tr>
        <tr id="transition-services"><td>POWDR transition services agreement (draft, Jan 6, 2026)</td><td>A two-year agreement to be signed at closing. POWDR's support services and the applications listed in Exhibit B for &ldquo;a fee of $1,000,000 for each 12 month period,&rdquo; paid &ldquo;quarterly in advance, initially in $250,000 installments&rdquo;; the applications in Exhibit C billed monthly at &ldquo;the fees in effect&rdquo; when provided; and reimbursement of pre-approved out-of-pocket costs, which can include &ldquo;insurance premiums, self-funded claims and expenses.&rdquo; Exhibits B and C aren't attached to the draft in the packet. The bond memo says bond proceeds would also cover &ldquo;related costs, such as transition services.&rdquo;</td><td>Not in effect; the sale hasn't closed.</td><td><a href="https://nederlandco.civicweb.net/document/126804/" target="_blank" rel="noopener">draft agreement §1.02, §5.01, §6.13</a>, <a href="https://nederlandco.civicweb.net/document/126800/" target="_blank" rel="noopener">bond memo</a></td></tr>
        <tr><td>Farnsworth Group survey (Aug 2025)</td><td>A fixed fee of $65,300, including expenses, for a land survey of two resort parcels.</td><td>$65,300 paid, on invoices dated Oct. 16, 2025, to Jan. 16, 2026</td><td><a href="{rec_farn}" target="_blank" rel="noopener">agreement</a></td></tr>
        <tr><td>Dickinson Wright water-rights due diligence (Jul 15, 2025)</td><td>Hourly rate only ($385); the engagement letter gives no estimate. [[corrected:2026-10-11]]</td><td>$50,149, including a $9,680 invoice first paid from the Legal budget and later moved into the account (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>)</td><td><a href="https://nederlandco.civicweb.net/document/122662/" target="_blank" rel="noopener">memo</a></td></tr>
        <tr><td>Town Attorney, Widner Juran</td><td>A July 2025 rate memo set a higher "pass-through" rate of $290 an hour from January 2026, "including enterprise fund... billings." It gave no estimate of hours.</td><td>$293,931, including $46,211 in January to July 2025 invoices first paid from the Legal budget and later moved into the account (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>)</td><td><a href="https://nederlandco.civicweb.net/document/122661/" target="_blank" rel="noopener">memo</a></td></tr>
        <tr><td>Special legal counsel (Res. 2025-03, Jan 7, 2025)</td><td>"The Town Administrator will provide updates to the Board of Trustees regarding cost estimates." At the meeting, Trustee Luke Miller asked how counsel would be paid "if we don't end up moving forward and issuing bonds." Town Administrator Jon Cain answered, "We have that obligation," said, "we've done some risk analysis on it and I think we have a reasonable case to move forward," and added, "this is real costs that we are incurring." Town Attorney Jennifer Madsen said that if the deal doesn't close, bond counsel "would need to be paid by the town" (<a href="https://www.youtube.com/watch?v=F3Kb-cwTvS8&amp;t=2313s" target="_blank" rel="noopener">video, 0:38:33</a>).</td><td>The Board documents and minutes searched include no cost-estimate update. One given aloud at a meeting or in executive session would not appear in them. [[corrected:2026-10-12]] Asked for written updates under the resolution, the Town said on Oct. 29, 2026, that &ldquo;No records exist&rdquo; (<a href="{rec_reply4}" target="_blank" rel="noopener">Town response</a>).</td><td><a href="https://nederlandco.civicweb.net/document/118137/" target="_blank" rel="noopener">memo</a></td></tr>
        <tr><td>Other legal counsel (Res. 2025-16, Aug 5, 2025)</td><td>The Town Manager "will keep the Board of Trustees informed about all necessary legal engagements."</td><td>Hogan Lovells ($148,795), counsel to Alterra Mountain Company on the Ikon agreement, and Semple, Farrington, Everall &amp; Case ($1,151) appear in no Board document searched other than the warrant lists. Williams Weese Pepple &amp; Ferguson and Taft Stettinius &amp; Hollister, which confirmed unpaid amounts in October 2026 (<a href="#owed-confirmed">Who was paid and who is owed</a>), appear in no Board document or warrant list searched. A briefing in executive session would not appear in public records.</td><td><a href="https://nederlandco.civicweb.net/document/123040/" target="_blank" rel="noopener">Res. 2025-16</a></td></tr>
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
    <p class="prose muted">The minutes searched, from the first warrant list with the account (October 2025) through the Oct. 6, 2026, meeting, record no discussion of the warrant lists or the "Due From" entries; each list was approved with the rest of the consent agenda. The account is a balance-sheet account with a budget of $0. The balance also included {unlisted} added between lists (see <a href="#payees">Who was paid</a>). [[corrected:2026-10-11]]</p>

    <h3 id="cost-videos">Meetings where the acquisition's costs came up</h3>
    <p class="prose muted">Links to the Town's video recordings: where each item or comment period starts, and where costs come up in it. The descriptions say only what each item was about; watch the recording for what was said. The minutes are the official record.</p>
    <details class="changes-box"><summary>Show the meetings and video links</summary>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Meeting</th><th scope="col">Item</th><th scope="col">Item starts</th><th scope="col">Costs come up</th></tr></thead>
      <tbody><tr><td class="dt">Jan. 7, 2025</td><td>Res. 2025-03, delegating authority to engage special legal counsel. The Board discussion includes how counsel fees would be paid.</td><td class="vid"><a href="https://www.youtube.com/watch?v=F3Kb-cwTvS8&amp;t=2148s" target="_blank" rel="noopener">0:35:48</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=F3Kb-cwTvS8&amp;t=2316s" target="_blank" rel="noopener">0:38:36</a></td></tr><tr><td class="dt">Jan. 21, 2025</td><td>Ord. 873, creating the Mountain Recreation Enterprise Fund. The Board discussion includes the fund if a purchase doesn't close.</td><td class="vid"><a href="https://www.youtube.com/watch?v=T9IKSJ_OoZw&amp;t=3408s" target="_blank" rel="noopener">0:56:48</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=T9IKSJ_OoZw&amp;t=3700s" target="_blank" rel="noopener">1:01:40</a></td></tr><tr><td class="dt">July 10, 2025</td><td>Board town hall on the acquisition. Public comments include questions about costs; the Board said answers would follow in a later FAQ.</td><td class="vid"><a href="https://www.youtube.com/watch?v=0AigDgranLU&amp;t=1052s" target="_blank" rel="noopener">0:17:32</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=0AigDgranLU&amp;t=2327s" target="_blank" rel="noopener">0:38:47</a>, <a href="https://www.youtube.com/watch?v=0AigDgranLU&amp;t=2712s" target="_blank" rel="noopener">0:45:12</a></td></tr><tr><td class="dt">Aug. 5, 2025</td><td>Res. 2025-17, the intent to reimburse acquisition costs from future bonds. Staff describe which costs could be reimbursed.</td><td class="vid"><a href="https://www.youtube.com/watch?v=ZgJBnuhE0-0&amp;t=1521s" target="_blank" rel="noopener">0:25:21</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=ZgJBnuhE0-0&amp;t=1562s" target="_blank" rel="noopener">0:26:02</a>, <a href="https://www.youtube.com/watch?v=ZgJBnuhE0-0&amp;t=1680s" target="_blank" rel="noopener">0:28:00</a></td></tr><tr><td class="dt">Jan. 6, 2026</td><td>Information item on the bond ordinance, including the costs the bonds would cover.</td><td class="vid"><a href="https://www.youtube.com/watch?v=WkgdzanY1IM&amp;t=2617s" target="_blank" rel="noopener">0:43:37</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=WkgdzanY1IM&amp;t=2772s" target="_blank" rel="noopener">0:46:12</a></td></tr><tr><td class="dt">Jan. 20, 2026</td><td>Ord. 885, the bond ordinance (Part 1), and public comment on it (Part 2).</td><td class="vid"><a href="https://www.youtube.com/watch?v=iFH8e_nZnWc&amp;t=1860s" target="_blank" rel="noopener">0:31:00 (Part 1)</a>, <a href="https://www.youtube.com/watch?v=J__yBhAQu10&amp;t=351s" target="_blank" rel="noopener">0:05:51 (Part 2)</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=iFH8e_nZnWc&amp;t=2124s" target="_blank" rel="noopener">0:35:24 (Part 1)</a></td></tr><tr><td class="dt">July 7, 2026</td><td>Stifel advisory agreement, with its fee contingent on a bond sale. Public comment includes questions about costs to date.</td><td class="vid"><a href="https://www.youtube.com/watch?v=bm_DSuMnc-M&amp;t=1595s" target="_blank" rel="noopener">0:26:35</a></td><td class="vid"><a href="https://www.youtube.com/watch?v=bm_DSuMnc-M&amp;t=1630s" target="_blank" rel="noopener">0:27:10</a>, <a href="https://www.youtube.com/watch?v=bm_DSuMnc-M&amp;t=1787s" target="_blank" rel="noopener">0:29:47</a></td></tr></tbody>
    </table></div>
    </details>
  </section>

  <div class="group" id="involve"></div>
  <section id="get-involved" aria-labelledby="get-involved-h">
    <h2 id="get-involved-h">Get involved</h2>
    <p class="prose muted">How residents can follow the next decisions, get records, and be heard. These are procedures, not legal advice; confirm deadlines and requirements with the Town Clerk.</p>
    <div class="tp-watch prose">
      <h3>Decisions to watch</h3>
      <ul>
        <li id="res-2026-31"><strong>Resolution 2026-31, adopted Nov. 17, 2026.</strong> The Town Attorney revised it from a resolution a resident submitted (<a href="https://nederlandco.civicweb.net/document/133098/" target="_blank" rel="noopener">memo</a>). On Nov. 9 the Board had staff amend it, &ldquo;including but not limited to the language about milestones&rdquo; (<a href="{nov9_min}" target="_blank" rel="noopener">Nov. 9 minutes</a>). On Nov. 17 the Board adopted the draft in the packet, with dated milestones rather than the alternative without dates, and moved the first two milestones two weeks later. The signed resolution matches the Nov. 17 draft with those two dates changed (<a href="https://nederlandco.civicweb.net/document/133556/" target="_blank" rel="noopener">signed resolution</a>, <a href="https://nederlandco.civicweb.net/document/133362/" target="_blank" rel="noopener">Nov. 17 memo</a>). The draft minutes in the Dec. 1 packet record the Mayor's motion with the new dates; they don't record a second or the vote (<a href="https://nederlandco.civicweb.net/document/133760/" target="_blank" rel="noopener">draft minutes</a>). It took effect on adoption (Section 11). What it requires:
          <ul>
            <li><strong>Stop work (Section 2).</strong> Within three business days, by Nov. 20, the Town Manager directs each firm in writing to stop billable work, other than work toward a term sheet and the accounting below. On Nov. 20 the Interim Town Manager emailed eight firms (Brownstein, Butler Snow, Dickinson Wright, Kline Alvarado Veio, SE Group, Taft, Widner Juran, and Williams Weese) to &ldquo;pause billable work effective immediately,&rdquo; with any more to be authorized in advance by the Town Manager; the list doesn't include Plante Moran or Stifel. Staff are also negotiating fee reductions, or fees payable only if the purchase closes, and report &ldquo;potential reductions totaling approximately $170,000 to date&rdquo; (<a href="https://nederlandco.civicweb.net/document/133769/" target="_blank" rel="noopener">Dec. 1 memo</a>).</li>
            <li><strong>Limits (Section 2).</strong> Up to $80,000 for firms already engaged to work toward a term sheet, but none until the Board adopts a supplemental appropriation for it under C.R.S. 29-1-109. If total acquisition costs, paid and owed, pass $3 million, no more may be incurred until the Board votes to continue. Neither limit applies to &ldquo;services performed that are not payable until such time that the Eldora transaction closes.&rdquo;</li>
            <li><strong>New engagements (Section 3).</strong> No new engagement, contract amendment, or expansion of scope without a Board resolution.</li>
            <li><strong>Reports (Sections 4 and 8).</strong> A written accounting by firm at the Dec. 15, 2026, meeting, compared with the $2.5 million and $2.76 million estimates; and at the first regular meeting of each month, a report of costs paid, billed, and owed, each milestone's status, and each fund's share of the pooled cash.</li>
            <li><strong>Milestones (Section 5).</strong> A term sheet presented to the Board by Feb. 15, 2027; a signed purchase agreement and written financing commitments by April 15, 2027 [[corrected:2026-11-21]]; and a closing by June 30, 2027. If a date passes without an extension adopted by resolution beforehand, the Town&rsquo;s pursuit ends, firms stop work except to wind down, and a final accounting follows at the next regular meeting.</li>
            <li><strong>Budget (Sections 7, 9, and 10).</strong> The Board will choose how to pay for the costs through the budget process. The Town Manager presents a transfer, supplemental appropriation, or revised appropriation for 2026 acquisition costs; a separate 2027 line for them; and a General Fund plan if the deal doesn&rsquo;t close, with budget materials explaining how the costs were recorded and why they were charged to the General Fund.</li>
          </ul></li>
        <li id="open-seat"><strong>The open Board seat.</strong> Trustee Topher Donahue resigned after the Oct. 20, 2026, meeting (<a href="#board-votes">How the Board voted</a>), leaving six members. On Nov. 19, 2026, the Town posted that it is accepting applications for the seat, due Monday, Dec. 28, 2026, at 5 p.m. (<a href="https://nederlandco.gov/m/newsflash/home/detail/29" target="_blank" rel="noopener">Town notice</a>). When Trustee Kennedy resigned in summer 2026, the Board considered its options Aug. 4, the Town took applications through Aug. 25, and the Board appointed Andrew Dewart Sept. 1. The Clerk's memo cites C.R.S. 31-4-303: the Board may appoint a qualified resident to serve until the next regular election, in April 2028, or call a special election (<a href="https://nederlandco.civicweb.net/document/130995/" target="_blank" rel="noopener">Aug. 4 memo</a>, <a href="https://nederlandco.civicweb.net/document/131732/" target="_blank" rel="noopener">Sept. 1 memo</a>, <a href="https://nederlandco.civicweb.net/document/131741/" target="_blank" rel="noopener">Res. 2026-25</a>).</li>
        <li><strong>A new purchase agreement.</strong> The first one was approved by ordinance (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">Ord. 882</a>); the Town says talks with POWDR continue.</li>
        <li><strong>New financing.</strong> The sale-leaseback plan would need a new or amended bond ordinance, a lease, or both, since the bond authority lapsed (<a href="#revised-plan">revised plan</a>). As of Oct. 22, 2026, the Town said the lease had not been drafted (<a href="{rec_reply2}" target="_blank" rel="noopener">Town response</a>).</li>
        <li><strong>The 2026 and 2027 Town budgets.</strong> The Nov. 17 agenda asked the Board whether to transfer money from the Community Center, Water, and Sewer Funds, and how much; whether to give a 3% raise; what to do about the Downtown Development Authority; and whether to amend the 2026 budget (<a href="#nov16-plan">the Nov. 16 plan</a>). The draft minutes record the Board's direction: staff are to research transfers from the Community Center, Water, and Sewer Funds and which amounts would come from each, research spending reductions, give the 3% raise, and keep the Downtown Development Authority (<a href="https://nederlandco.civicweb.net/document/133760/" target="_blank" rel="noopener">draft minutes</a>). For Dec. 1, staff won't present an amended 2026 budget, because &ldquo;the General Fund is likely not to exceed the budgeted 2026 appropriations,&rdquo; and are still evaluating &ldquo;the legal and audit considerations behind not passing an amended budget.&rdquo; The memo also says &ldquo;aspects of the Citizen Plan,&rdquo; a proposal from residents, will be in the proposed 2027 budget, whose documents were to be added to the packet by Nov. 30 (<a href="https://nederlandco.civicweb.net/document/133768/" target="_blank" rel="noopener">Dec. 1 budget memo</a>). The Nov. 9 schedule set adoption for a Dec. 8 special session (<a href="{rec_slides}#page=2" target="_blank" rel="noopener">budget slides, p. 2</a>), and the Town's updated schedule moves adoption to Dec. 15, with continued discussion Dec. 1 and the public hearing at a Dec. 8 special meeting (<a href="https://nederlandco.gov/m/newsflash/home/detail/28" target="_blank" rel="noopener">Town notice</a>). The Downtown Development Authority discusses its budget Nov. 18.</li>
        <li><strong>A public meeting on the deal,</strong> which the Town says it will hold after the purchase (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/17" target="_blank" rel="noopener">FAQ 7.0</a>).</li>
      </ul>
    </div>
    <dl class="tp-facts prose">
      <dt>Meetings</dt><dd>Regular Board meetings are on the first and third Tuesdays at 7:00 p.m. at the Nederland Community Center. Each agenda has an online link and a call-in number (<a href="https://nederlandco.civicweb.net/document/132364/" target="_blank" rel="noopener">Oct. 6 agenda</a>). Recordings of Board meetings are posted on the Town's <a href="https://www.youtube.com/channel/UCknLzh_H3jXUCHNN2r-H37w" target="_blank" rel="noopener">YouTube channel</a>; executive sessions are not included.</dd>
      <dt>Agendas</dt><dd>Agendas and full packets are posted on the Town's <a href="https://nederlandco.civicweb.net/portal/" target="_blank" rel="noopener">CivicWeb portal</a> before each meeting. Each warrant list shows Eldora acquisition payments under the <a href="#costs">"Due From" account</a> or, since Nov. 9, 2026, the <a href="#eldora-expense">&ldquo;Eldora Expense&rdquo; account</a>.</dd>
      <dt>Public review process</dt><dd>In 2012 the Board adopted a review process for Town projects, the Nederland Planning Process (called the Nederland Public Process in the minutes), in which advisory boards and the public review a proposal before the Board decides. The Board may invoke it for projects it chooses (<a href="https://nederlandco.civicweb.net/document/24535/" target="_blank" rel="noopener">Res. 2012-12</a>). No record found shows it was invoked for the Eldora purchase. In July 2025 the Sustainability Advisory Board listed the &ldquo;Decision to purchase Eldora Mtn Resort&rdquo; among projects its Sustainability Scorecard could evaluate (<a href="https://nederlandco.civicweb.net/document/122263/" target="_blank" rel="noopener">SAB summary</a>).</dd>
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
    <p class="prose muted">Payments are listed by the warrant list that first shows them in the "Due From" account or, from the Nov. 9, 2026, list, the &ldquo;Eldora Expense&rdquo; account, where the balance column shows this page's running total. The "Due From" account first appears on the Oct. 7, 2025, list. The earliest invoices are older: seven Widner Juran invoices dated Jan. 31 to July 31, 2025, totaling $46,211, were paid from the Legal budget on warrant lists from Feb. 18 to Sept. 2, 2025, and moved into the account by a Town ledger entry dated Sept. 30, 2025. They are listed under Nov. 5, 2025, the first warrant list whose balance includes them, and each notes the list where it was first paid (<a href="{rec_ledger}" target="_blank" rel="noopener">Town ledger</a>).</p>
    <p class="prose muted">{data_links}</p>
    <details class="changes-box"><summary>Show all {n_pay} payments</summary>
    <div class="tools">
      <label class="sr" for="q">Filter payments</label>
      <input id="q" type="search" placeholder="Filter by payee, invoice, or date" autocomplete="off">
    </div>
    <div class="scroll ledger"><table>
      <thead><tr><th scope="col">Warrant list</th><th scope="col">Payee</th><th scope="col" class="opt">Invoice</th><th scope="col" class="opt">Invoice date</th><th scope="col" class="num">Amount</th><th scope="col" class="num opt">Account balance</th><th scope="col">Source</th></tr></thead>
      <tbody>{ledger}</tbody>
    </table></div>
    </details>
  </section>

  <section class="prose" id="figures">
    <h2>About these figures</h2>
    <ul class="notes">
      <li>Why the account is treated as Eldora acquisition spending. It first appears on the Oct. 7, 2025, warrant list, right after the Board hired Eldora due-diligence consultants, whose costs were to be "reimbursed from revenue bond proceeds" (Res. 2025-19, 2025-22). Other reimbursable work, such as FEMA, CDOT, and DDA projects, has its own accounts, and no charge in the account was found to belong to another program. The Town's spreadsheet of the account's 2025–2026 entries, released in response to a public records request, is titled "Eldora - reimbursable expenses," and the entries moved into the account are labeled "Eldora Reclass" (<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>).</li>
      <li>The total covers only bills booked to the "Due From" account, which opened in August 2025, and from Nov. 9, 2026, to the &ldquo;Eldora Expense&rdquo; account. It includes {moved} in invoices the Town moved into the account from the Legal and Professional Services budget lines (see <a href="#payees">Who was paid</a>), among them Widner Juran invoices from January to July 2025. Any other Eldora acquisition work charged to ordinary budget lines and not moved isn't identified in the records searched and is not included.</li>
      <li>The Town moved the earlier invoices in one journal entry dated Sept. 30, 2025, eight weeks after the Board declared its intent to reimburse acquisition costs from bond proceeds (<a href="https://nederlandco.civicweb.net/document/123060/" target="_blank" rel="noopener">Res. 2025-17</a>, Aug. 5, 2025). The entry includes a Dickinson Wright invoice first paid on the Oct. 7, 2025, warrant list (<a href="https://nederlandco.civicweb.net/document/124842/" target="_blank" rel="noopener">p.3</a>), so it was made after Sept. 30 and dated to September (<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>).</li>
      <li>Most invoices dated in 2025 but paid in 2026 appear in the Town's 2025 ledger, including two entries recorded as accruals on Dec. 31, 2025. Three do not: a Plante Moran invoice dated Dec. 4, 2025 ($69,000), and two Partner Assessment Corporation invoices dated Sept. 30 and Dec. 31, 2025 ($43,000). The ledger lists them only in 2026; they were paid on the July 21 and Oct. 6, 2026, warrant lists, the longest gaps between invoice and payment in the account (<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>).</li>
      <li>Totals are by warrant-list date, when the Board approved payment. Invoice dates are often earlier; some invoices dated in 2025 were paid in 2026, so the totals show when bills were approved, not when work was done.</li>
      <li>The running balance printed on each warrant list matches the listed invoices, except for the amounts added between lists (shown under Who was paid) and one Widner Juran invoice ($16,985) that reached the balance one list before it was listed. [[corrected:2026-10-11]]</li>
      <li>Amounts are rounded to the nearest dollar, so a total can differ by a dollar from the sum of its rounded parts. The data files in the <a href="https://github.com/dallasmasters/nederland-eldora-record" target="_blank" rel="noopener">project repository</a> keep the exact amounts.</li>
      <li>Source: Board of Trustees warrant lists (Council Approval Reports) on the Town's CivicWeb portal, through the Nov. 9, 2026, meeting, and the Town's ledger for the account through Sept. 25, 2026, released in response to a public records request (<a href="{rec_ledger}" target="_blank" rel="noopener">ledger</a>, <a href="{rec_reply}" target="_blank" rel="noopener">Town response</a>) and, for 2026, posted in the Oct. 20, 2026, Board packet (<a href="https://nederlandco.civicweb.net/document/132789/" target="_blank" rel="noopener">packet copy</a>).</li>
    </ul>
  </section>

  <section id="open-questions" class="open-q" aria-labelledby="open-questions-h">
    <h2 id="open-questions-h">Not in the records searched</h2>
    <p class="prose">The records searched (see <a href="#method-ai">How this research was done</a>) don't show the following; the information may be in staff or contract files, executive-session records, or other Town records. Anyone can request the records that could show it under the Colorado Open Records Act (CORA); see <a href="#get-involved">Get involved</a>.</p>
    <details class="changes-box oq-box"><summary>Show all 21 items, in four groups</summary>
    <div class="scroll" id="records-needed"><table class="commit">
      <thead><tr><th scope="col">Not in the records searched</th><th scope="col">Records that could show it</th></tr></thead>
      <tbody>
        <tr class="who-group"><td colspan="2">The Town&rsquo;s estimate and cost updates</td></tr>
        <tr><td>What makes up the Town's estimate, about $2.76 million (about $2.5 million on Sept. 30), which the Treasurer's September report says includes amounts &ldquo;paid or incurred&rdquo; through Oct. 15, 2026 (<a href="#receivable">how the costs were recorded</a>). Asked for the records behind it, the Town released the firms' confirmations but no worksheet, and said no written cost-estimate updates under Res. 2025-03 exist (<a href="{rec_reply4}" target="_blank" rel="noopener">Town response</a>).</td><td>The calculation behind the Sept. 30, 2026, estimate and the $2.76 million figure, by firm or contract, and the general ledger detail behind the Nov. 9 presentation&rsquo;s Eldora expenditures for 2025 and 2026. Confirmations or statements from the firms not in the Oct. 29 response, including Hogan Lovells, Plante Moran, and POWDR.</td></tr>
        <tr><td>The "risk analysis" the Town Administrator mentioned when the Board delegated authority to hire special counsel on Jan. 7, 2025 (<a href="https://www.youtube.com/watch?v=F3Kb-cwTvS8&amp;t=2353s" target="_blank" rel="noopener">video, 0:39:13</a>), and the cost-estimate updates the staff memo said he would provide (<a href="#estimates">Estimates compared with spending</a>). Asked for written updates under Res. 2025-03, the Town said on Oct. 29, 2026, &ldquo;No records exist&rdquo; (<a href="{rec_reply4}" target="_blank" rel="noopener">Town response</a>).</td><td>Any written risk analysis of the acquisition's costs, and any cost-estimate updates given to the Board.</td></tr>
        <tr class="who-group"><td colspan="2">Firms and invoices</td></tr>
        <tr><td>The agreement under which the Town pays <a href="#payee-hogan">Hogan Lovells</a>, Alterra's counsel, in full for a &ldquo;Town of Nederland&rdquo; matter ({hogan} paid July 21 and Aug. 18, 2026). The Jan. 6, 2026, letter covers only half of Alterra's Ikon fees (<a href="#ikon-advance">Ikon costs</a>).</td><td>The &ldquo;agreement with Powdr&rdquo; that Hogan Lovells' June 25, 2026, email cites.</td></tr>
        <tr><td>Confirmation of what the <a href="#payee-powdr">POWDR</a> invoice for $124,000 was for (likely the earlier payment toward the BDO audit; the $10,721 invoice was for the remaining cost of a three-year audit of Eldora by BDO; <a href="{rec_powdr_audit}" target="_blank" rel="noopener">invoice and emails</a>). POWDR's Sept. 22, 2026, email accounts for the $50,000 and $12,357.75 invoices (<a href="#ikon-advance">Ikon costs</a>).</td><td>POWDR invoice INV3313.</td></tr>
        <tr><td>The work done by Semple, Farrington, Everall &amp; Case; Partner Engineering and Science; and Torrent Engineering &amp; Equipment (<a href="#payees">Who was paid</a>), and what most ledger entries were for. Agreements for Farnsworth Group (a <a href="{rec_farn}" target="_blank" rel="noopener">land survey</a>) and Bolder HR Solutions (<a href="{rec_bolder}" target="_blank" rel="noopener">HR transition consulting</a>) were released in October 2026.</td><td>Their engagement letters. Invoice descriptions for the "Due From" account; the Town's ledger lists payees and amounts but describes most entries only as "Due From."</td></tr>
        <tr><td>The work, engagement, and cost of Causey Public Finance, LLC, which Resolution 2026-31 says prepared analyses relating to the acquisition. The firm appears in no warrant list or other Board document searched (<a href="https://nederlandco.civicweb.net/document/133099/" target="_blank" rel="noopener">Res. 2026-31 §6</a>).</td><td>Causey Public Finance&rsquo;s engagement letter, invoices, and analyses, and who paid for them.</td></tr>
        <tr><td>Why three invoices dated in 2025, from Plante Moran and Partner Assessment Corporation, were paid 7 to 12 months later, and what Vadim Municipal Software invoice 457143 was for (<a href="#figures">About these figures</a>).</td><td>The invoices, with the dates the Town received and approved them; Vadim invoice 457143. A list of the account's costs the Town expects to be reimbursed from bond proceeds, if any has been prepared.</td></tr>
        <tr><td>Fee terms for the current underwriters and for disclosure and real estate counsel (<a href="#payees">Who was paid</a>).</td><td>Current engagement letters and fee terms for the underwriters (RBC Capital Markets and BofA Securities) and for disclosure and real estate counsel.</td></tr>
        <tr class="who-group"><td colspan="2">Accounting and other funds</td></tr>
        <tr><td>Which Town reserves FAQ 7.0 called "sufficient to cover the current expenses associated with the work on the acquisition." A September 2026 records request asked; the records the Town provided don't identify them (<a href="{rec_reply}" target="_blank" rel="noopener">Town response</a>).</td><td>A record identifying those reserves; none was in the Town's response.</td></tr>
        <tr><td>Where the 2025 audit reports the Eldora acquisition costs. It mentions the acquisition only as a planned bond financing and doesn't itemize the General Fund's "other receivables"; the Treasurer's September report says the costs &ldquo;were initially recorded as a receivable,&rdquo; and the Town's Nov. 9 budget presentation says the 2025 payments will be moved to spending through audit adjustments (<a href="#receivable">receivables</a>, <a href="#audit-note">the audit note</a>).</td><td>The General Fund's year-end 2025 trial balance, showing which audit line includes the "Due From" account. The auditors' management letter for 2025, and any auditor comment on how the costs are reported.</td></tr>
        <tr><td>What the amounts the other funds owed the General Fund were for, and how they were settled. The 2025 audit calls them a timing difference expected to clear after year end; they grew from $915,951 (2023) to $1,172,725 (2024) to $1,456,233 (2025), while the General Fund's cash fell from $778,593 to −$757,482. The Town's Sept. 30, 2026, balance sheets show none, so they were cleared during 2026 (<a href="https://www.nederlandco.gov/DocumentCenter/View/594/2025-Nederland-Financials-Audit" target="_blank" rel="noopener">2025 audit</a>, <a href="https://nederlandco.civicweb.net/document/122108/" target="_blank" rel="noopener">2024 audit</a>).</td><td>A schedule of the amounts owed between funds at Dec. 31, 2025, showing what each was for and how and when it was settled.</td></tr>
        <tr><td>Whether the transfers staff propose from the Community Center, Water, and Sewer Funds are lawful, given the voter-approved purposes of their sales tax and the utilities' state loans, and how the transferred amounts would be traced to user fees (<a href="#nov16-plan">the Nov. 16 plan</a>, <a href="#fund-dedications">what voters approved</a>, <a href="#utility-loan">the utility funds</a>).</td><td>The Town's loan agreements with the Colorado Water Resources and Power Development Authority dated as of June 15, 2009 (water), Nov. 1 and Nov. 3, 2011 (wastewater), and 2018 (biosolids), with their 2012 amendments, and their limits on pledged revenue; Ordinance 696 (2011) and Ordinance 711 (2012) approved them but don't include them (<a href="https://nederlandco.civicweb.net/document/25978/" target="_blank" rel="noopener">Ord. 696</a>, <a href="https://nederlandco.civicweb.net/document/114624/" target="_blank" rel="noopener">Ord. 711</a>); a written Town Attorney opinion on the transfers; the 1998 ballot question; the auditors' comments on the General Fund's negative cash.</td></tr>
        <tr><td>The entries behind the &ldquo;Eldora Expense&rdquo; account&rsquo;s balance: about $2.13 million before the Nov. 9 charges by this page's reading, $933,287 more than the Oct. 20 &ldquo;Due From&rdquo; balance. The Treasurer's September report says the Town's 2026 figure includes amounts &ldquo;paid or incurred,&rdquo; and the balance sheet lists $1,556,213 in accounts payable, but the journal entries, and whether the &ldquo;Due From&rdquo; balance was moved into the account, aren't public (<a href="#eldora-expense">the new account</a>).</td><td>The 2026 general ledger detail for account 10-10-7000, including each journal entry, and the activity in account 10-00-1150 since Oct. 20, 2026.</td></tr>
        <tr class="who-group"><td colspan="2">Deal terms</td></tr>
        <tr><td>How a long-term pass program for donors could be approved before the Town holds the Forest Service permit, and who would hold the permit under the sale-leaseback (<a href="#donors">donations and partners</a>).</td><td>Any correspondence with the Forest Service about the permit transfer or a pass program, and any estimate of what the donor options could raise.</td></tr>
        <tr><td>Which emails between the Mayor and the former Town Manager, April through September 2026, were withheld as protected by attorney-client privilege (<a href="#questions">records requests</a>).</td><td>A list of the withheld emails with their dates, senders, and recipients.</td></tr>
        <tr><td>The revenue forecast and bond amounts behind the bond payment schedules, whose revenue, expense, and coverage columns were redacted (<a href="#bond-schedule">the bond payment schedules</a>). Ordinance 885 set only limits: up to $225 million, a final maturity within 40 years, and a net effective interest rate of no more than 9% (<a href="https://nederlandco.civicweb.net/document/127855/" target="_blank" rel="noopener">Ord. 885 §5(c)</a>).</td><td>The Preliminary Limited Offering Memorandum of March 19, 2026, and its May 13, 2026, supplement, including any revenue forecast and the bond amounts behind the schedule.</td></tr>
        <tr><td>How much of the bond proceeds would be set aside at closing for capital projects, reserves, and early interest. Ordinance 885 allowed the proceeds to fund capital improvements, reserve funds, capitalized interest, and issuance costs (<a href="https://nederlandco.civicweb.net/document/127179/" target="_blank" rel="noopener">Ord. 885 memo</a>). The January 2026 draft Indenture of Trust lists closing deposits to a CapEx Fund, a Capital Maintenance Fund, a capitalized interest account, debt service reserves, and an O&amp;M Stabilization Fund, but leaves every amount blank (<a href="https://nederlandco.civicweb.net/document/127181/" target="_blank" rel="noopener">draft indenture §3.02</a>). The May 2026 draft also leaves the deposits blank but sets requirements: an operating reserve (the O&amp;M Stabilization Fund) of $11,685,000 at closing, $6,210,000 from Oct. 1, 2026, and from Oct. 1, 2027, the greater of $6,469,000 or 90 days of cash on hand; a senior debt service reserve equal to the next 12 months of senior bond payments; capital maintenance deposits of 5% of the prior year's revenue; and a CapEx requirement of $47,488,000 (<a href="{rec_ind}" target="_blank" rel="noopener">May draft</a>, Exhibit A, released Oct. 22, 2026; <a href="{rec_reply2}" target="_blank" rel="noopener">Town response</a>). The Town has described &ldquo;a two-year debt service reserve&rdquo; (<a href="https://nederlandco.civicweb.net/document/125525/" target="_blank" rel="noopener">Nov. 5, 2025, memo</a>) and &ldquo;a $10 million reserve fund&rdquo; (<a href="https://web.archive.org/web/20251112014324/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-40" target="_blank" rel="noopener">FAQ 4.0</a>).</td><td>The sources and uses of funds prepared for the Series 2026 bonds, showing the amount of each closing deposit.</td></tr>
        <tr><td>The complete <a href="#transition-services">transition services agreement</a> with POWDR. The draft in the Jan. 6, 2026, packet omits Exhibits B and C, which list the applications POWDR would provide and set the monthly charges for those in Exhibit C, so it doesn't show the agreement's full cost. Its dates and signatures are blank (<a href="https://nederlandco.civicweb.net/document/126804/" target="_blank" rel="noopener">draft agreement §1.01, §1.02</a>).</td><td>Exhibits B and C, and the final or most recent version of the agreement.</td></tr>
        <tr><td>What it would cost to replace POWDR's services when the two-year transition agreement ends. The draft requires the Town to move each service to its own staff or other providers and pay the costs of switching; FAQ 6.0 gives no costs (<a href="https://nederlandco.civicweb.net/document/126804/" target="_blank" rel="noopener">draft agreement §1.01, §1.05</a>, <a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0</a>).</td><td>Any estimate or budget for the resort's technology, payroll, finance, and marketing services after the agreement ends.</td></tr>
        <tr><td>The financial projections behind the purchase (<a href="#profit">Profit</a>), and Plante Moran&rsquo;s quality-of-earnings report on Eldora&rsquo;s finances. Asked for the report&rsquo;s non-confidential parts, the Town said on Nov. 6, 2026, that POWDR &ldquo;has taken the position that the report is confidential in its entirety&rdquo; and that the Town has asked POWDR to reconsider (<a href="https://eldorarecord.org/records/2026-11-06-town-cora-response.txt" target="_blank" rel="noopener">Town response</a>).</td><td>The parts of Plante Moran&rsquo;s report that POWDR agrees aren&rsquo;t confidential. SE Group's final due-diligence report and five-year pro forma (Res. 2025-15); its proposal says the Town's use of the report is subject to the confidentiality agreement with POWDR (<a href="https://nederlandco.civicweb.net/document/122625/" target="_blank" rel="noopener">proposal p.3</a>). The financial model behind the projections in FAQ 3.0, and the documents prepared for bond buyers (requested in May 2026).</td></tr>
        <tr><td>The terms of the sale-leaseback: the lease, a new bond amount, and any pledges (<a href="#new-deal">the new deal</a>). The Town says the lease &ldquo;has not been drafted&rdquo; (<a href="{rec_reply2}" target="_blank" rel="noopener">Town response</a>). On Nov. 6, 2026, it posted the May 2026 draft indenture as the &ldquo;proposed or substantially final forms&rdquo; of the bond documents Ordinance 885 said would be on file with the Clerk; the other bond documents aren't posted (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/27" target="_blank" rel="noopener">Town records page</a>).</td><td>The draft lease and the other financing documents for the sale-leaseback.</td></tr>
        <tr><td>The results of the Town's review with the County Assessor of which parcels would become Town-owned, which FAQ 6.0 said would be shared, and whether the property would be tax-exempt while a bond trustee holds title under the sale-leaseback (<a href="#district-taxes">Property taxes on the resort</a>).</td><td>The Town's or the Assessor's list of the parcels and accounts expected to become Town-owned, with their current assessed values; any Assessor or bond-counsel view on the property's tax status while the trustee holds title; and any estimate given to the fire, library, or EcoPass districts.</td></tr>
        <tr><td>Which land is in the sale. The purchase agreement defines it as all land owned by any seller and lists the parcels in Schedule 5.7(a), which isn't in the records searched (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA §5.7(a)</a>).</td><td>Schedule 5.7(a) and the other disclosure schedules to the purchase agreement.</td></tr>
      </tbody>
    </table></div>
    </details>
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
  // and open any collapsed box that holds the target of a followed link
  const openFor = h => {{
    if (!h || h.length < 2) return;
    let el = document.getElementById(decodeURIComponent(h.slice(1)));
    if (!el && h.startsWith('#change')) el = document.getElementById('changes');
    for (let p = el; p; p = p.parentElement) if (p.tagName === 'DETAILS') p.open = true;
    if (el && el.id === 'changes') {{ const b = el.querySelector('.changes-box'); if (b) b.open = true; }}
  }};
  openFor(location.hash);
  window.addEventListener('hashchange', () => openFor(location.hash));
  document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', () => openFor(a.getAttribute('href'))));
}})();
{votes_js}
</script>
'''

if __name__ == '__main__':
    main()
