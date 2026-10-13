#!/usr/bin/env bash
# Refresh the archive from CivicWeb and rebuild the public pages. Run after each Board meeting's minutes and
# warrants are posted. Nothing is published: review the report at the end, then commit and push docs/.
#
#   ./update.sh            # full refresh (about 15-30 minutes, longer if many new scans need OCR)
#   ./update.sh --pages    # skip downloading; just rebuild analysis and pages from the current archive
set -euo pipefail
cd "$(dirname "$0")"
WORKERS="${WORKERS:-6}"   # OCR processes; more than ~6 has run this machine out of memory

step() { printf '\n=== %s\n' "$*"; }

if [[ "${1:-}" != "--pages" ]]; then
  step "Crawl the CivicWeb document tree";       python3 scripts/crawl.py          >> catalog_crawl.log 2>&1
  step "Mark Board of Trustees documents";       python3 scripts/build_catalog.py
  step "Download new documents";                 python3 scripts/fetch.py          >> fetch.log 2>&1
  step "Extract text and OCR scanned pages";     python3 scripts/extract.py "$WORKERS" >> extract.log 2>&1
  step "Re-OCR newly adopted minutes";           python3 scripts/reocr.py          >> reocr.log 2>&1
  step "Fetch Town website posts on Eldora";     python3 scripts/fetch_web.py
  step "Add records from public records responses"; python3 scripts/add_records.py
  step "Rebuild the search index";               python3 scripts/build_index.py
fi
step "Parse motions from the minutes";           python3 scripts/motions.py
step "Build the Eldora vote table";              python3 scripts/eldora_votes.py
step "Extract Eldora payments from warrants";    python3 scripts/eldora_due_from.py
step "Check the vote section";                  python3 scripts/eldora_page.py
step "Build the combined page";                 python3 scripts/eldora_spending_page.py
step "Make the data spreadsheet and CSV";      python3 scripts/make_workbook.py
step "Make the link-preview image";              python3 scripts/make_preview.py
step "Build the website in docs/";               python3 scripts/build_site.py
step "What changed";                             python3 scripts/review_changes.py
