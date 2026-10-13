"""Parse every motion out of the (re-OCR'd) adopted Board of Trustees minutes.

Writes analysis/motions.csv with one row per motion:
  date, doc_id, page, item (agenda heading), mover, seconder, motion, outcome,
  unanimous, yes, no, other (abstained / recused / not present for the vote), present, absent,
  eldora (keyword flag), url
Names are normalised to surnames ("Mayor Billy" -> Giblin) and OCR misspellings are snapped to the closest
frequently-seen name. For unanimous votes `yes` is left empty: the minutes do not list individual votes then,
and `present` (the roll call) is the best record of who voted.
"""
import collections
import csv
import difflib
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE = r'(?:Mayor Pro Tem|Mayor|Trustee)'
NAME = r"[A-Z][A-Za-z'’-]+(?: (?!Mayor\b|Trustee\b)[A-Z][a-z'’-]+)?"
PERSON = re.compile(TITLE + r'\s+(' + NAME + ')')
# First names some minutes use in place of surnames, plus OCR misreads verified against the page images
ALIASES = {'Billy': 'Giblin', 'William': 'Giblin', 'Bily': 'Giblin',
           'Hest': 'Joslin'}  # 2025-12-16 minutes (doc 127831) p.4: the scan clearly reads "Trustee Joslin"
ELDORA = re.compile(r'eldora|ski\b|mountain recreation|recreational activities|purchase of property|'
                    r'great outdoors|goco|special legal counsel|northland|enterprise fund|acquisition|'
                    r'certificates? of participation|powdr|resort', re.I)
# Language that marks an attachment as being about the acquisition (not just "Eldora Road" etc.)
ACQUISITION = re.compile(r'eldora mountain|eldora ski|eldora acquisition|acquisition of eldora|purchas\w* (of )?eldora|'
                         r'mountain recreation enterprise|ski recreation|ski area', re.I)
OUTCOME = re.compile(r'(?:The )?[Mm]otion (?:was )?(unanimously )?(not )?(approved|passed|carried|failed|denied)')
# Minutes never posted as separate "Minutes - Adopted" documents; the text is the draft in the next meeting's packet.
# (attachment id, meeting date). The Oct. 2025 drafts were approved on the Nov. 5, 2025, consent agenda; the
# Sept. 15, 2026, special-meeting draft is in the Oct. 6, 2026, packet.
PACKET_MINUTES = [('125513', '2025-10-21'), ('125515', '2025-10-21'), ('125516', '2025-10-30'),
                  ('132361', '2026-09-15')]
HEADING = re.compile(r'\s*(\d{1,2}\s*[.,]\s*[\dIl|]{1,2}|\d{1,2}\.)\s+([A-Z].{3,})')


def clean(t):
    t = re.sub(r'Pro[ -]T(?:ern|ein|em)', 'Pro Tem', t)
    t = re.sub(r'(?<=[a-z])(seconded|made a motion|voted|called|joined)', r' \1', t)
    t = re.sub(r'seconded \w{0,2}the motion', 'seconded the motion', t)
    t = re.sub(r'(?<=[a-z]),(?=\S)', ', ', t)
    return t


def raw_names(s):
    return [ALIASES.get(m.group(1), m.group(1)) for m in PERSON.finditer(s)]


def roll_call(text):
    """Read the roll-call paragraph sentence by sentence.

    Returns (present, absent, notes): names marked absent are removed from `present`; sentences about late
    arrivals or early departures are kept verbatim in `notes`, since a "unanimous" vote then may not include them.
    """
    m = re.search(r'Present:(.*?)(?:Also Present|\d\.\s+[A-Z]{4})', text)
    if not m:
        return [], [], ''
    present, absent, notes = [], [], []
    for sentence in re.split(r'(?<=\.)\s+', m.group(1)):
        who = raw_names(sentence)
        if re.search(r'\babsent\b|not present', sentence, re.I):
            absent += who
        else:
            present += who
            if re.search(r'left|joined the meeting (at|after|late)|arrived', sentence, re.I):
                notes.append(sentence.strip())
    m = re.search(r'\bAbsent:(.*?)(?:Also Present|\d\.\s+[A-Z]{4})', text)
    if m:
        absent += raw_names(m.group(1))
    present = [n for n in present if n not in absent]
    return present, absent, ' '.join(notes)


def flatten(pages):
    """Join all pages into one string; return it with [(offset, page, heading)] markers."""
    flat, marks, item = [], [], ''
    pos = 0
    for p in pages:
        for line in clean(p['text']).splitlines():
            h = HEADING.match(line)
            if h:
                label = ' '.join(h.group(0).split())
                if label.split(' ', 1)[0] != item.split(' ', 1)[0]:
                    item = label
            marks.append((pos, p['n'], item))
            line = ' '.join(line.split())
            if line:
                flat.append(line)
                pos += len(line) + 1
    return ' '.join(flat), marks


def at(marks, offset):
    page, item = 1, ''
    for pos, pg, it in marks:
        if pos > offset:
            break
        page, item = pg, it
    return page, item


def doc_text(doc_id):
    tj = os.path.join(ROOT, 'text', f'{doc_id}.json')
    if os.path.exists(tj):
        return ' '.join(p['text'] for p in json.load(open(tj))['pages'])
    pdf = os.path.join(ROOT, 'pdf', f'{doc_id}.pdf')
    if os.path.exists(pdf):
        return subprocess.run(['pdftotext', pdf, '-'], capture_output=True, text=True, errors='replace').stdout
    return ''


def item_no(label):
    m = re.match(r'(\d{1,2})\s*[.,]\s*([\dIl|]{1,2})', label or '')
    return f"{m.group(1)}.{re.sub(r'[Il|]', '1', m.group(2))}" if m else ''


def acquisition_items(catalog):
    """{(date, '5.1'): [attachment titles]} for BOT agenda items whose attachments discuss the acquisition."""
    hits = collections.defaultdict(list)
    for r in catalog:
        if r['kind'] == 'Attachment' and 'TRUSTEES' in r['body'].upper():
            no = item_no(r['title'])
            if no and ACQUISITION.search(r['title'] + ' ' + doc_text(r['id'])):
                hits[(r['date'], no)].append(r['title'])
    return hits


def parse(doc_id, date, url, acq=None):
    acq = acq or {}
    pages = json.load(open(os.path.join(ROOT, 'text', f'{doc_id}.json')))['pages']
    text, marks = flatten(pages)
    present, absent, roll_notes = roll_call(text)
    # Consent-agenda items whose titles are Eldora-related (one motion approves the whole block)
    consent_hits = {}
    for line in clean('\n'.join(p['text'] for p in pages)).split('CONSENT AGENDA', 1)[-1].splitlines()[:80]:
        line = ' '.join(line.split())
        if re.match(r'\d{1,2}\.\s+[A-Z ]{6,}$', line) and not line.startswith('3'):
            break
        if re.search(r'Minutes|Warrants', line):
            continue
        if re.match(r'\d', line) and not re.match(r'\S+ (AIM|Reso|JC|Ord)', line) and \
                (ELDORA.search(line) or (date, item_no(line)) in acq):
            consent_hits.setdefault(item_no(line) or line.split(' ', 1)[0], line)

    starts = [mm for mm in re.finditer(r'(' + TITLE + r'\s+' + NAME + r')?\s*made a motion', text)]
    rows = []
    for i, mm in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        seg = text[mm.start():min(end, mm.start() + 1500)]
        out = OUTCOME.search(seg)
        if out:
            seg = seg[:out.end()]
        else:
            seg = seg[:600]
        sec = re.search(r'([^.]*?)seconded the motion', seg)
        body_end = min(x for x in (sec.start() if sec else len(seg), out.start() if out else len(seg)))
        what = seg[seg.find('made a motion') + len('made a motion'):body_end].strip(' .,')
        if not sec and not out:
            what = what.split('. ')[0]
        yes, no, other = [], [], []
        for sentence in re.split(r'(?<=\.)\s+', seg[body_end:]):
            if re.search(r'voted (yes|aye|in favor)', sentence, re.I):
                yes += raw_names(sentence)
            elif re.search(r'voted (no|nay|against)', sentence, re.I):
                no += raw_names(sentence)
            elif re.search(r'abstain|recus|not present for the vote', sentence, re.I):
                other += raw_names(sentence)
        page, item = at(marks, mm.start())
        row = {
            'date': date, 'doc_id': doc_id, 'page': page, 'item': item,
            'mover': raw_names(mm.group(0))[:1], 'seconder': raw_names(sec.group(1))[-1:] if sec else [],
            'motion': what,
            'outcome': '' if not out else ('not approved' if out.group(2) or out.group(3) in ('failed', 'denied')
                                           else 'approved'),
            'unanimous': int(bool(out and out.group(1))),
            'yes': yes, 'no': no, 'other': other, 'present': present, 'absent': absent, 'roll_notes': roll_notes,
            'eldora': int(bool(ELDORA.search(what + ' ' + item)) or (date, item_no(item)) in acq), 'url': url}
        if sec and not row['seconder']:
            row['seconder'] = ['(not named)']
        if re.search(r'consent agenda', what, re.I) and consent_hits:
            row['item'] = 'CONSENT AGENDA incl. ' + ' | '.join(sorted(consent_hits.values()))
            row['eldora'] = 1
        rows.append(row)
    return rows


def normalise(rows):
    """Snap OCR-mangled surnames to the closest name seen at least 5 times across all minutes."""
    fields = ('mover', 'seconder', 'yes', 'no', 'other', 'present', 'absent')
    freq = collections.Counter(n for r in rows for f in fields for n in r[f])
    known = [n for n, c in freq.items() if c >= 5 and not n.startswith('(')]
    fix = {}
    for n in freq:
        if n in known or n.startswith('('):
            continue
        close = difflib.get_close_matches(n, known, n=1, cutoff=0.7)
        fix[n] = close[0] if close else n
    for r in rows:
        for f in fields:
            r[f] = '; '.join(dict.fromkeys(fix.get(n, n) for n in r[f]))
        # Flag split votes whose voters don't line up with the roll call (OCR error, late arrival, or appointment)
        voters = set(filter(None, (r['yes'] + '; ' + r['no'] + '; ' + r['other']).split('; ')))
        present = set(filter(None, r['present'].split('; ')))
        odd = sorted(voters - present) if present else []
        r['check'] = ('not in roll call: ' + ', '.join(odd)) if odd else ''
    return fix


if __name__ == '__main__':
    with open(os.path.join(ROOT, 'catalog', 'catalog.csv')) as f:
        docs = [r for r in csv.DictReader(f) if r['selected'] == '1' and r['kind'] == 'Minutes'
                and r['fmt'] == 'Adopted' and 'TRUSTEES' in r['body'].upper()]
    with open(os.path.join(ROOT, 'catalog', 'catalog.csv')) as f:
        acq = acquisition_items([r for r in csv.DictReader(f) if r['selected'] == '1'])
    docs += [{'id': i, 'date': d, 'url': f'https://nederlandco.civicweb.net/document/{i}/'} for i, d in PACKET_MINUTES]
    rows = []
    for d in sorted(docs, key=lambda d: (d['date'], d['id'])):
        if os.path.exists(os.path.join(ROOT, 'text', f"{d['id']}.json")):
            rows += parse(d['id'], d['date'], d['url'], acq)
    fixes = normalise(rows)
    os.makedirs(os.path.join(ROOT, 'analysis'), exist_ok=True)
    with open(os.path.join(ROOT, 'analysis', 'motions.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} motions from {len(docs)} minutes; {sum(r['eldora'] for r in rows)} flagged Eldora-related")
    print('name fixes:', {k: v for k, v in fixes.items() if k != v})
    print('unmatched names:', sorted(k for k, v in fixes.items() if k == v))
