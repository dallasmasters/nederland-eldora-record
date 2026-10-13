# Nederland CivicWeb research archive

A local, searchable copy of public records from the Town of Nederland's CivicWeb portal
(https://nederlandco.civicweb.net/portal/), built to research the Town's pursuit of Eldora Mountain Resort.

## Layout

| Path | Contents |
|---|---|
| `catalog/tree.json` | Every document in the CivicWeb Document Center (id, title, folder path) |
| `catalog/web.csv` | Town website posts on Eldora (FAQs, announcements), IDs 900001+; raw pages in `web/raw/` |
| `catalog/records.csv` | Town records received outside CivicWeb and the website (public records responses), IDs 910001+, with source and SHA-256; originals in `private/records/` |
| `catalog/catalog.csv` | Same, with parsed meeting body / date / kind and a `selected` flag for what was downloaded |
| `pdf/<id>.pdf` | Downloaded originals (a few are `.html` or other types) |
| `text/<id>.txt` | Extracted text with `=== Page N ===` markers; `(OCR)` marks pages read by tesseract |
| `text/<id>.json` | Same text, per page, machine-readable |
| `archive.db` | SQLite database: `docs` metadata + `pages` full-text index (FTS5) |
| `scripts/` | The pipeline below |

The `<id>` is CivicWeb's document id; the original is always at `https://nederlandco.civicweb.net/document/<id>/`.

## What is included

* **Board of Trustees** agendas/packets and minutes (PDF versions) **from 2023-01-01 on**, plus each meeting's
  individual agenda attachments (`kind = Attachment`). Trustee work sessions, the BOT orientation and the
  Feb 2026 "Community Town Hall: Eldora Mountain Acquisition" are included.
* Other boards (DDA, Planning Commission, SAB, PROSAB, BOZA) are deliberately excluded.
* The Town's own website posts on Eldora: FAQs Round 2, 3.0 and 4.0 (old site, via the Internet Archive), FAQ 6.0,
  FAQ 7.0, the September 30, 2026 Mayor and Board update, the auditor RFP, and the 2025 audit (scanned PDF, posted
  only on the Town website under Finance > Audits). `fetch_web.py` flags new Eldora posts.
  FAQ 5.0 was not found anywhere.
* Town records released in response to public records (CORA) requests, listed in `catalog/records.csv` with
  `kind = CORA response`. They are Town records like the others, but they have no Town URL: the originals are kept
  exactly as received in `private/records/` (git-ignored), checked against their SHA-256 on every update, and the
  `url` column is filled only when a copy is posted with the site (bank account numbers cut to the last four digits).
  The requester's details are never stored with them. First set: the Town's Sept. 25, 2026, response (IDs
  910001-910006: the Town Clerk's reply with the two questions asked, the "Eldora - reimbursable expenses"
  spreadsheet for account 10-00-1150, and July 2026 CSAFE and bank statements).
* **All years** of: Resolutions, Ordinances, Finance, Board of Trustees, Documents and Information,
  Staff Reports, From the Desk of the Town Administrator, Tourism Management.

Agenda "packets" (`kind = Agenda`) usually bundle all attachments, so the same text often appears twice:
once in the packet and once as a standalone attachment.

## Searching

```
python3 scripts/search.py 'eldora AND appraisal'
python3 scripts/search.py '"purchase of property" AND recreation*' --since 2024-01-01 --body TRUSTEES
python3 scripts/search.py 'NEAR(eldora "letter of intent", 20)' -n 100
```

Query syntax is SQLite FTS5. Results list date, document title, page (cite-able) and the original URL.

Executive-session notices never name Eldora; they read *"the Town's purchase of property [and operations] for
recreational activities and other municipal services"*. Search for that wording as well as "Eldora".

## Rebuilding / updating

`./update.sh` runs every step below in order, then rebuilds the analysis and the website (see *Publishing*).

```
python3 scripts/crawl.py          # re-crawl the Document Center tree (~10 min)
python3 scripts/build_catalog.py  # parse titles, mark selection
python3 scripts/fetch.py          # download new selected documents (skips ones already present)
python3 scripts/extract.py 6      # extract text, OCR image-only pages (6 workers)
python3 scripts/fetch_web.py      # Town website FAQs and announcements on Eldora (not in CivicWeb)
python3 scripts/add_records.py    # records from public records responses (catalog/records.csv)
python3 scripts/build_index.py    # rebuild archive.db
```

The git repository holds the scripts, the analysis tables and the website. The downloaded PDFs, extracted text and
`archive.db` (about 5.5 GB) are not in git; `./update.sh` rebuilds them from CivicWeb. Records in `private/records/`
cannot be downloaded again, so back that folder up.

To add records from a new public records response: put the files, unchanged, in a new folder under
`private/records/` (e.g. `2026-11-02-cora/`); if the Town's reply came only as quoted text, save it as a `.txt` with
the requester's details removed. Add one line per file to `catalog/records.csv` (next free ID from 910001 up, title,
date of the Town's response, `kind = CORA response`, `file`, `sha256` from `sha256sum`, and `source`), then run
`python3 scripts/add_records.py && python3 scripts/build_index.py`.

OCR temp files go to `tmp/` (not `/tmp`, which is a small tmpfs).

## Analysis outputs

| Path | Contents |
|---|---|
| `analysis/motions.csv` | Every motion in the adopted BOT minutes (2023 on): mover, seconder, outcome, named yes/no votes, roll call, absences, late arrivals / early departures |
| `analysis/eldora_votes.csv` / `.md` | Curated table of Eldora acquisition votes and executive sessions, plus noticed executive sessions with no posted minutes |
| `analysis/eldora_due_from.csv` | Every Eldora payment (account 10-00-1150) from the warrant lists |
| `analysis/eldora_spending.html` | The combined public page as built for Claude's artifact viewer; `docs/index.html` is the standalone copy |

```
python3 scripts/reocr.py      # re-OCR the signed "Minutes - Adopted" scans (their embedded text layer is unreliable)
python3 scripts/motions.py    # parse motions -> analysis/motions.csv
python3 scripts/eldora_votes.py
```

Notes on the minutes:
* Use **"Minutes - Adopted"** documents. The "Minutes - Pdf" versions are unfilled agenda-shaped templates.
* Unanimous votes are recorded only as "Motion was unanimously approved"; individual votes are listed only for split votes.

## Publishing (GitHub Pages)

The public website is the `docs/` folder, served by GitHub Pages (Settings → Pages → Deploy from a branch →
`main`, folder `/docs`). The site is a single page, `docs/index.html`: spending and funding first, then how the Board
voted, then one section on how the research was done. `docs/spending.html` redirects there (it was a separate page
briefly).

| Path | Role |
|---|---|
| `scripts/eldora_due_from.py` | Pulls Eldora payments (account 10-00-1150 "Due From") from the warrant lists and checks the running balance |
| `scripts/eldora_page.py` | Builds the "How the Board voted" section (styles scoped to `#board-votes`) |
| `scripts/eldora_spending_page.py` | Builds the combined page into `analysis/eldora_spending.html`, embedding the votes section |
| `scripts/page_method.py` | The "How this research was done" section and the list of research requests |
| `scripts/build_site.py` | Turns the page into a standalone `docs/index.html` and writes redirects for old addresses |
| `scripts/review_changes.py` | Lists what changed since the last reviewed update |
| `scripts/preview_diff.py` | Marks added and removed text: review copies of previews, and the live page's "Show what changed" switch |
| `site_config.json` | `contact` (corrections line in the footer) and `base_url` (public address; a custom domain also writes `docs/CNAME`) |

### Update routine (after each Board meeting's minutes and warrants are posted)

1. `./update.sh` (or `./update.sh --pages` to rebuild pages without downloading).
2. Read the report it prints at the end:
   - **New motions.** Lines marked `*` mention Eldora-related terms. Read each one's staff memo; if it is an
     acquisition action, add it to `CURATED` in `scripts/eldora_votes.py` with a description, then
     `./update.sh --pages`. Executive sessions on the purchase are added automatically.
   - **New payments / new payees.** A new payee stops the spending page build until it is given an evidence
     rating in `PAYEES` (`scripts/eldora_spending_page.py`): `named`, `coding` or `none`, with a one-line note.
   - **Unexplained balance jumps.** Investigate, then add the amount to `KNOWN_GAPS` in
     `scripts/eldora_due_from.py` (and to `OFF_LIST` in the page script if the payee is identified).
   - **Dated statements.** Recheck each listed question; edit the page text where the answer has changed.
3. Look at `docs/index.html` in a browser. To see what changed, mark the build against the live version:
   `git show main:analysis/eldora_spending.html > /tmp/live.html && python3 scripts/preview_diff.py /tmp/live.html analysis/eldora_spending.html /tmp/marked.html`
   Added text is highlighted, removed text is struck through, and a panel steps through each change. The marked
   copy is for review only and is never published.
   For a **major update**, first run `python3 scripts/preview_diff.py --set-baseline` (on the preview branch,
   before building) so the live page's "Show what changed" switch compares against the version being replaced.
   The baseline is kept in `private/`. Minor updates leave it alone, so their changes add to the marks.
   Republish the claude.ai copy from `python3 scripts/preview_diff.py --mirror <file>`, which includes the switch.
4. Publish as a single commit, so old versions of the page are not kept on GitHub:
   `git add -A && git commit --amend -m "Nederland Eldora record: current version" && git push --force origin main`
   (`private/` and `transcripts/` are ignored. A backup of the history before Oct. 13, 2026, is in `private/`.)
5. `python3 scripts/review_changes.py --accept` to mark this state as reviewed.

### Corrections and updates log

The page has a public "Corrections and updates" section built from `analysis/changes.json`, newest first:

```json
[{"date": "2026-11-17", "type": "Update", "text": "Updated with Board records through Nov. 17, 2026."},
 {"date": "2026-11-03", "type": "Correction", "text": "The page said X. The record shows Y. The text has been corrected."}]
```

* **Correction:** something the page got wrong. Also put `[[corrected:2026-11-03]]` next to the corrected text in
  `scripts/eldora_spending_page.py`; it renders as a small "Corrected Nov. 3, 2026" note linking to the log.
* **Update:** new records added (one entry per update is enough).
* **Headline:** for a major update or correction, add `"headline": "<one sentence>"` to its entry. The newest entry
  with a headline is shown at the top of the page as "Latest major update" (or "Latest major correction"); routine updates without
  one leave it in place.
* `build_site.py` also writes `docs/feed.xml`, an Atom feed of this log (linked under Get involved and in the page
  head), so readers can follow corrections and updates. Entries are only ever appended, which keeps their feed IDs stable.
* Old versions of the page are not published: the repository keeps a single commit (see step 4), and this log is
  the public record of what changed.

