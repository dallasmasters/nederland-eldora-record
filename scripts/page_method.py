"""Shared "How this research was done" section for the Eldora page."""
import csv
import os
import sqlite3
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHS = 'January February March April May June July August September October November December'.split()


def long_date(d):
    return f'{MONTHS[d.month - 1]} {d.day}, {d.year}'


def archive_through():
    """Date of the latest Board of Trustees agenda or minutes in the archive."""
    db = sqlite3.connect(os.path.join(ROOT, 'archive.db'))
    (d,) = db.execute("SELECT max(date) FROM docs WHERE body LIKE '%TRUSTEES%' AND kind IN ('Agenda', 'Minutes')").fetchone()
    return date.fromisoformat(d)


def archive_from():
    """Date of the earliest Board of Trustees agenda or minutes in the archive."""
    db = sqlite3.connect(os.path.join(ROOT, 'archive.db'))
    (d,) = db.execute("SELECT min(date) FROM docs WHERE body LIKE '%TRUSTEES%' AND kind IN ('Agenda', 'Minutes') "
                      "AND date LIKE '____-__-__'").fetchone()
    return date.fromisoformat(d)


def archive_counts():
    """The archive's size, for the method note: catalog rows, documents selected, other boards' documents from
    2024 on (catalog/catalog.csv), and pages and OCR pages in archive.db."""
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'catalog', 'catalog.csv'))))
    sel = [r for r in rows if r['selected'] == '1']
    other = [r for r in sel if 'TRUSTEES' not in (r['body'] or '') and r['body'] and (r['date'] or '') >= '2024']
    n_pages, n_ocr = sqlite3.connect(os.path.join(ROOT, 'archive.db')).execute(
        'SELECT count(*), sum(ocr) FROM pages').fetchone()
    return dict(n_cat=len(rows), n_sel=len(sel), n_other=len(other), n_pages=n_pages, n_ocr=n_ocr)


ARCHIVE_METHOD = '''
      <li><strong>Collecting the records.</strong> All {n_cat:,} documents listed in the Town's CivicWeb Document Center
        were cataloged. {n_sel:,} of them were selected and downloaded:
        <ul>
          <li>Board of Trustees agendas, packets, agenda attachments, and minutes from January 2023 on, including
            executive-session agendas and the February 2026 town hall on the acquisition.</li>
          <li>Agendas, packets, and minutes of the Town's other boards and commissions from January 2024 on: the
            Downtown Development Authority, Planning Commission, Sustainability Advisory Board, Parks, Recreation,
            and Open Space Advisory Board, and Board of Zoning Adjustment ({n_other:,} documents).</li>
          <li>All years of resolutions, ordinances, finance documents, and staff reports.</li>
        </ul></li>
      <li><strong>Reading the text.</strong> Text was taken directly from each PDF where possible. The {n_ocr:,} pages
        that were scanned images were read with optical character recognition (OCR, the Tesseract program). All
        {n_pages:,} pages went into a searchable database, so every finding can be traced to a document and page.</li>'''

VOTES_METHOD = '''
      <li><strong>Reading the minutes.</strong> The signed "Minutes - Adopted" scans carry a built-in text layer that
        often garbles names and votes. All 123 adopted Board minutes since 2023 were therefore re-read with OCR at
        high resolution. Names were checked against the page images wherever they were unclear. Four sets of
        minutes were never posted as separate adopted minutes; for those (Oct. 21, 2025, regular and special,
        Oct. 30, 2025, and the Sept. 15, 2026, special meeting), the drafts in the next meeting's packet were used.</li>
      <li><strong>Finding the motions.</strong> 500 motions were extracted with mover, seconder, outcome, roll call,
        absences and late arrivals. Votes on the acquisition were chosen by reading each candidate item's staff memo
        and attachments, because a search for "Eldora" alone also returns items that mention it only in passing.
        Every executive session whose motion cites the purchase of property for recreational activities was
        included.</li>
      <li><strong>Checking for gaps.</strong> Agendas were checked for executive sessions on the purchase that have
        no motion in any minutes. Those are listed separately, along with one whose agenda is marked canceled. No
        minutes were found for four special meetings (Dec. 23, 2024, and May 30, July 21, and July 29, 2025).</li>'''
SPENDING_METHOD = '''
      <li><strong>Tracing the payments.</strong> Every warrant list (the bills the Board approves at each meeting) was
        parsed for payments to the General Fund account 10-00-1150, "Due From," and, from the Nov. 9, 2026, list, account 10-10-7000, "Eldora Expense." The "Due From" account's running balance printed
        on each list was reconciled against the listed invoices. That check found three amounts posted between
        lists. The Town's ledger for the account, from a public records response, identifies the entries that make up
        each one; it was checked
        entry by entry against the warrant lists, including the earlier lists where moved invoices were first paid.</li>
      <li><strong>Checking each payee.</strong> Every payee was searched for across the whole archive, including
        contracts, engagement letters, staff memos, and minutes. Their other Town billings were compared to see whether
        "Due From" charges were kept separate. Each payee was then rated by whether a Board document states its role
        in the Eldora acquisition.</li>
      <li><strong>Reading the contracts.</strong> The draft Asset Purchase Agreement, the Transition Services Agreement,
        the bond ordinance and the delegation resolutions were read for cost-sharing, refund, termination, and spending
        limits.</li>
      <li><strong>The Town's website.</strong> The Town's Eldora FAQs and announcements are posted on its website;
        only FAQ Round 2 also appears in CivicWeb, in the Jan. 7, 2025, Board packet. Current posts (FAQ 6.0, FAQ 7.0, the September 30, 2026, update, and the auditor request for
        proposals) came from nederlandco.gov. Earlier FAQs were on the Town's previous website, which no longer serves
        them, so they came from the Internet Archive. FAQ 5.0 could not be found. The 2022, 2023, and 2025 audits are also
        posted only on the Town website. They are scanned PDFs and were read with OCR. All were added to the same searchable database
        as the Board records.</li>
      <li><strong>Records from public records requests.</strong> Records the Town released in response to an open
        records (CORA) request are used like the Town's other records. The Town's ledger for account 10-00-1150,
        "Due From," came from its Sept. 25, 2026, response to a resident's request, which the requester shared with
        this project. The ledger matches every warrant-list payment on this page and the account's running balance to
        the cent. Records released to residents are posted with this page; requesters are named only with their consent,
        and their contact details are not posted. These records were added to the same searchable database as the Board records.</li>
      <li><strong>Meeting videos.</strong> The Town posts recordings of Board meetings on its YouTube channel. To link
        each decision to the moment it comes up in the recording, the recordings of the meetings with Eldora decisions
        were transcribed by machine (whisper.cpp), and YouTube's automatic captions were searched for other meetings. The
        transcripts were used only to find those times, and each link was checked by watching the recording; they are not a
        source for anything on this page, because they are unofficial and contain errors. The minutes are the official
        record. The one exception is the Town's Nov. 9, 2026, budget presentation, which wasn't in the meeting packet:
        screenshots of its slides from the recording are posted and cited as the Town's presentation.</li>
      <li><strong>Outside sources.</strong> State statutes and the Colorado Constitution are cited for CSAFE, for the budget and TABOR rules a General Fund deficit would face, and under Get involved; they come from the official 2024 Colorado Revised Statutes. The State Auditor's 2013 fiscal-health analysis for counties and municipalities is cited for its General Fund reserve benchmark. The section on property taxes uses Boulder County records: the Assessor's account data (Oct. 17, 2026, download), its 2025 mill levy file and certifications of value to each district, and the Treasurer's account pages for the three largest accounts, printed Oct. 27, 2026. Accounts were matched to the sellers by owner name and mailing address. Everything else
        on this page comes from the Town's own records, website, and Facebook page. FAQ 7.0 refers to a BusinessDen article; the
        article itself is not used as a source.</li>'''
PAGE_METHOD = {'record': SPENDING_METHOD + VOTES_METHOD}


def method_html(page):
    return f'''
  <section id="method-ai" class="method">
    <style>
      .method {{ display: grid; gap: 14px; min-width: 0; border-top: 1px solid var(--line); padding-top: 28px; }}
      .method .notes ul {{ margin: 6px 0 0; padding-left: 20px; display: grid; gap: 4px; }}
    </style>
    <h2>How this research was done</h2>
    <p class="prose">This page was researched and built by Claude, an AI model made by Anthropic, working in Claude Code
      at the direction of Dallas Masters. The research began in October 2026. Claude collected, read, and analyzed the documents.
      The researcher chose the questions and decided what went on the page.</p>
    <details class="changes-box"><summary>Show how the records were collected, read, and checked</summary>
    <ul class="notes prose">{ARCHIVE_METHOD.format(**archive_counts())}{PAGE_METHOD[page]}
      <li><strong>Data.</strong> The searchable archive behind this page, a SQLite database of the Town's public
        documents with a list of them, can be downloaded from the
        <a href="https://github.com/dallasmasters/nederland-eldora-record/releases" target="_blank" rel="noopener">data
        snapshots on GitHub</a>, with the code that builds it. It leaves out the records released through records
        requests; the posted ones are linked on this page.</li>
      <li><strong>Limits.</strong> When this page says something isn't in the records, it means
        the records searched; it may be documented elsewhere. OCR can misread scanned text, and an AI can misread or misjudge a document. Every
        figure and claim on this page links to its source document, so check those before relying on them. Executive
        sessions are confidential and the public record has gaps, so this page cannot show everything the Board knew
        or decided.</li>
    </ul>
    </details>
  </section>
'''
