"""Render analysis/eldora_votes.csv (+ the agenda-only list in eldora_votes.md) as the "How the Board voted" part of
the combined page built by scripts/eldora_spending_page.py.

Every vote on the acquisition was unanimous among the trustees present, so the section is a short history: one
timeline row per decision, the closed sessions in a paragraph, and the one attendance fact that matters. The full
per-trustee data stays in analysis/eldora_votes.csv. fragment() returns the section's CSS, HTML and script, scoped to
#board-votes. Run after scripts/eldora_votes.py.
"""
import csv
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def e(s):
    return html.escape(s or '')


from motions import PACKET_MINUTES  # noqa: E402


def fmt_date(d):
    y, m, dd = d.split('-')
    return f'{MONTHS[int(m) - 1]} {int(dd)}, {y}'


def counts():
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'analysis', 'eldora_votes.csv'))))
    md = open(os.path.join(ROOT, 'analysis', 'eldora_votes.md')).read()
    gaps = re.findall(r'^- (\d{4}-\d\d-\d\d): \[agenda\]\((\S+)\)', md, re.M)
    canceled = re.findall(r'^- (\d{4}-\d\d-\d\d): canceled \(\[agenda\]\((\S+)\)\)', md, re.M)
    return rows, gaps, canceled


def link(url, text):
    return f'<a href="{e(url)}" target="_blank" rel="noopener">{text}</a>'


# Where each decision starts in the Town's YouTube recording: (date, category) -> [(video id, seconds, label)].
# Action items start where the item is called; consent items where the consent agenda is taken up. Two meetings were
# posted in two parts, so the item starts in Part 1 and the vote is in Part 2. Times were found with a machine
# transcript of the recording (navigation only; the transcript isn't a source) and checked by viewing (Oct. 14, 2026).
VIDEO = {
    ('2025-01-07', 'Consent'): [('F3Kb-cwTvS8', 1698, '')],
    ('2025-01-07', 'Action'): [('F3Kb-cwTvS8', 2148, '')],
    ('2025-01-21', 'Action'): [('T9IKSJ_OoZw', 3408, '')],
    ('2025-04-15', 'Consent'): [('xKnXR7OjDwo', 793, '')],
    ('2025-05-20', 'Consent'): [('m0IScYz4IKE', 1208, '')],
    ('2025-07-15', 'Consent'): [('yAJn-0ifXlk', 1027, '')],
    ('2025-08-05', 'Consent'): [('ZgJBnuhE0-0', 298, '')],
    ('2025-08-05', 'Action'): [('ZgJBnuhE0-0', 1521, '')],
    ('2025-09-02', 'Consent'): [('Xs-07zuAVw8', 426, '')],
    ('2025-10-07', 'Consent'): [('3NtGCQUB8YY', 1153, '')],
    ('2026-01-06', 'Action'): [('WkgdzanY1IM', 3186, '')],
    ('2026-01-20', 'Action'): [('iFH8e_nZnWc', 1860, 'Part 1'), ('J__yBhAQu10', 1321, 'vote, Part 2')],
    ('2026-03-17', 'Consent'): [('9qQh_WAjj8E', 598, '')],
    ('2026-03-31', 'Consent'): [('mlxwy88Kt0M', 329, '')],
    ('2026-04-21', 'Consent'): [('6jQN1SbWuQY', 1382, '')],
    ('2026-04-21', 'Action'): [('6jQN1SbWuQY', 10660, 'Part 1'), ('CE5L6KNdjXk', 121, 'vote, Part 2')],
    ('2026-07-07', 'Action'): [('bm_DSuMnc-M', 1595, '')],
}


def hms(t):
    return f'{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}'


def video_links(r):
    parts = VIDEO.get((r['date'], r['category']), [])
    if not parts:
        return '<span class="muted">none posted</span>'
    return ', '.join(link(f'https://www.youtube.com/watch?v={v}&t={t}s', hms(t) + (f' ({lab})' if lab else ''))
                     for v, t, lab in parts)


def fragment():
    rows, gaps, canceled = counts()
    actions = sorted((r for r in rows if r['category'] in ('Action', 'Consent')), key=lambda r: r['date'])
    sessions = [r for r in rows if r['category'] == 'Executive session']
    related = [r for r in rows if r['category'] == 'Related']
    timeline = ''.join(
        f'<tr><td class="dt">{fmt_date(r["date"])}</td><td>{e(r["description"])}</td>'
        f'<td>{link(r["source"], "p. " + e(r["minutes_page"]))}</td><td class="vid">{video_links(r)}</td></tr>' for r in actions)
    es_dates = ', '.join(link(r['source'], fmt_date(r['date'])) for r in sessions)
    apa = next(r for r in actions if 'Ord. 882' in r['description'])
    apa_present = len([x for x in apa['present'].split('; ') if x])
    apa_absent = ' and '.join(apa['absent'].split('; '))
    gap_items = '; '.join(link(u, fmt_date(d)) for d, u in gaps)
    canceled_note = ' '.join(f'A special meeting for an executive session on the purchase on {link(u, fmt_date(d))} '
                             f', was canceled.' for d, u in canceled)
    packet = {f'/document/{i}/' for i, _ in PACKET_MINUTES}
    drafts = [fmt_date(r['date']) for r in sessions if any(p in r['source'] for p in packet)]
    draft_note = (f' For {", ".join(drafts[:-1]) + (", and " if len(drafts) > 2 else " and ") + drafts[-1] if len(drafts) > 1 else drafts[0]}'
                  f', the minutes are the drafts in the next meeting\'s packet, since no separate adopted minutes '
                  f'were posted.') if drafts else ''
    w = related[0]
    body = HTML.format(
        n_actions=len(actions), n_sessions=len(sessions), n_gaps=len(gaps),
        first=fmt_date(sessions[0]['date']), last=fmt_date(sessions[-1]['date']),
        timeline=timeline, es_dates=es_dates, gaps=gap_items, canceled=canceled_note, drafts=draft_note,
        apa_date=fmt_date(apa['date']), apa_present=apa_present, apa_absent=apa_absent,
        apa_link=link(apa['source'], 'minutes'),
        water=link(w['source'], fmt_date(w['date'])))
    return {'css': CSS, 'html': body, 'js': '', 'n_actions': len(actions), 'n_sessions': len(sessions),
            'n_gaps': len(gaps), 'first': fmt_date(sessions[0]['date'])}


CSS = """
#board-votes { display: grid; gap: 22px; min-width: 0; }
#board-votes td.vid { white-space: nowrap; font-variant-numeric: tabular-nums; }
#board-votes .part-head { display: grid; gap: 12px; border-top: 3px solid var(--fg); padding-top: 24px; }
#board-votes .part-head h2 { font-size: clamp(24px, 3.4vw, 32px); }
#board-votes h3 { font: 800 19px/1.25 var(--body); margin: 0; text-wrap: balance; }
#board-votes .sub { display: grid; gap: 12px; min-width: 0; }
#board-votes td.dt { white-space: nowrap; }
"""

HTML = '''
  <section id="board-votes" aria-labelledby="board-votes-h">
    <div class="part-head prose">
      <h2 id="board-votes-h">How the Board voted</h2>
      <p class="lede">Every recorded Board of Trustees vote on the acquisition passed unanimously among the trustees present. No minutes record a no vote, an abstention, or a recusal.</p>
      <p class="prose"><strong>Who is on the Board now.</strong> Four current members were on the Board for the decisions through January 2026: Mayor Nichole Sterling (a trustee until she was elected mayor in April 2026), Mayor Pro Tem Luke Miller and Trustee Kristopher Larsen (terms through April 2028), and Trustee Billy Giblin (mayor until April 2026, appointed trustee in May 2026). Trustee Andrew Joslin was appointed in December 2025 and elected in April 2026. Trustees Topher Donahue (May 2026) and Andrew Dewart (September 2026) were appointed after the purchase agreement expired. Members who took part in earlier decisions and have since left are Tanya Corvalan and Tierney Maris (terms ended April 2026) and Aaron Tye (resigned November 2025); Matthew Kennedy served from April to August 2026 (<a href="https://nederlandco.civicweb.net/document/112330/" target="_blank" rel="noopener">April 2024</a> and <a href="https://nederlandco.civicweb.net/document/129027/" target="_blank" rel="noopener">April 2026</a> oath memos, <a href="https://nederlandco.civicweb.net/document/126598/" target="_blank" rel="noopener">Res. 2025-33</a>, and minutes of <a href="https://nederlandco.civicweb.net/document/129941/" target="_blank" rel="noopener">May 19</a> and <a href="https://nederlandco.civicweb.net/document/132389/" target="_blank" rel="noopener">Sept. 1, 2026</a>).</p>
    </div>

    <div class="sub" id="votes">
      <h3>Decisions on the acquisition ({n_actions})</h3>
      <p class="prose muted">Ordinances, resolutions, and agreements, in date order. Some passed on the consent agenda, in one vote with other routine items. Each links to the page of the adopted minutes, and to the Town's video recording at the start of the item (for consent items, the start of the consent agenda). The minutes are the official record. YouTube's automatic transcript (under the video, "…more," then "Show transcript") can help find a moment in a recording; it is machine-generated and often misspells names.</p>
      <div class="scroll"><table class="commit">
        <thead><tr><th scope="col">Date</th><th scope="col">What the Board approved</th><th scope="col">Minutes</th><th scope="col">Video</th></tr></thead>
        <tbody>{timeline}</tbody>
      </table></div>
      <p class="prose">The purchase agreement passed on {apa_date} with {apa_present} of 7 trustees present; Trustees {apa_absent} were absent ({apa_link}).</p>
    </div>

    <div class="sub prose" id="sessions">
      <h3>Closed sessions on the purchase ({n_sessions})</h3>
      <p>The Board voted to meet in executive session on the purchase {n_sessions} times, from {first} to {last}. The motions describe the subject as "the Town's purchase of property [and operations] for recreational activities and other municipal services" under C.R.S. 24-6-402(4). Starting in October 2025 the motions added confidential commercial information, and starting in June 2026, issues subject to negotiation. Eldora first appeared as a public agenda item on Nov. 19, 2024.</p>
      <p class="muted">Dates, each linked to its minutes: {es_dates}.{drafts}</p>
      <p class="muted">Another {n_gaps} executive sessions on the purchase were noticed on agendas, with no minutes found in the records searched (minutes for the most recent meeting may not yet be available): {gaps}. {canceled} A related session on {water}, covered water-court matters, including Eldora's own water-rights application, in which Nederland had filed a statement of opposition.</p>
      <p class="muted">The vote-by-vote data, including who moved, seconded, and attended each vote, is in the <a href="https://github.com/dallasmasters/nederland-eldora-record/blob/main/analysis/eldora_votes.csv" target="_blank" rel="noopener">project repository</a>.</p>
    </div>
  </section>
'''

JS = ""


if __name__ == '__main__':
    f = fragment()
    print(f"{f['n_actions']} actions, {f['n_sessions']} executive sessions, {f['n_gaps']} gaps")
