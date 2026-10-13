"""Charts drawn from the record's own numbers (analysis/figures.json 'raw'), shared by the record page and the FAQ.

Each function returns one inline SVG. Pass narrow=True for the phone version (smaller canvas, shorter labels), and
show one or the other with the pages' .chart-wide / .chart-narrow rules. Colors come from the page's CSS tokens
through the classes below, so the charts follow the page's light and dark themes:
  .grid .tick .ylab .xlab .endlab   shared with the record's running-total chart
  .wf-start .wf-down .wf-end .wf-link .wf-lab .wf-cat .zero   the General Fund waterfall
  .ct-area .ct-line .ct-owed .ct-est .ct-lab .ct-note     the costs chart (paid, then confirmed owed)
"""
from datetime import date

MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
AP = 'Jan. Feb. March April May June July Aug. Sept. Oct. Nov. Dec.'.split()


def _ap(dt):
    """Oct. 7, 2025 (AP style), for tooltips."""
    return f'{AP[dt.month - 1]} {dt.day}, {dt.year}'


def _m(v, digits=2):
    """$1.03M style, with a true minus sign."""
    s = f'${abs(v) / 1e6:.{digits}f}M'
    return ('−' if v < 0 else '') + s


def _ticks(lo, hi, step):
    v = (lo // step) * step
    while v <= hi:
        yield v
        v += step


def gf_chart(raw, narrow=False):
    """Waterfall: the General Fund's balance from the end of 2025 to the end of 2026 if the sale fails in 2026."""
    W, H, L, R, T, B = (380, 300, 50, 8, 26, 56) if narrow else (760, 320, 64, 16, 28, 52)
    steps = [('start', raw['gf_bal_2025'], ['End of 2025'] if not narrow else ['End of', '2025']),
             ('down', raw['bud_change'], ['2026 budget', 'as adopted'] if not narrow else ['2026', 'budget']),
             ('down', -raw['balance'], ['Paid so far,', 'written off'] if not narrow else ['Paid,', 'written off']),
             ('down', -raw['owed'], ['Confirmed', 'owed'] if not narrow else ['Confirmed', 'owed']),
             ('end', raw['fb_end'], ['End of 2026', '(if the sale fails)'] if not narrow else ['End of', '2026'])]
    level, bars = 0, []
    for kind, v, lab in steps:
        if kind == 'start':
            a, b, level = 0, v, v
        elif kind == 'end':
            assert abs(level - v) <= 2, (level, v)   # the steps must add up to the record's own result
            a, b = 0, v
        else:
            a, b, level = level, level + v, level + v
        bars.append((kind, a, b, v, lab))
    step = 500_000 if not narrow else 1_000_000
    lo = min(min(a, b) for _, a, b, _, _ in bars)
    hi = max(max(a, b) for _, a, b, _, _ in bars)
    lo, hi = (lo // step) * step, -((-hi * 1.12) // step) * step
    sy = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)   # noqa: E731
    n = len(bars)
    slot = (W - L - R) / n
    bw = slot * (0.56 if not narrow else 0.62)
    g = []
    for v in _ticks(lo, hi, step):
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="{"zero" if v == 0 else "grid"}"/>'
                 f'<text x="{L - 8}" y="{sy(v) + 4:.1f}" class="ylab">{"$0" if v == 0 else _m(v, 0 if v % 1_000_000 == 0 else 1)}</text>')
    for i, (kind, a, b, v, lab) in enumerate(bars):
        x = L + slot * i + (slot - bw) / 2
        top, bot = sy(max(a, b)), sy(min(a, b))
        cls = {'start': 'wf-start', 'down': 'wf-down', 'end': 'wf-end'}[kind]
        g.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(bot - top, 1):.1f}" class="{cls}">'
                 f'<title>{" ".join(lab)}: {_m(v)}</title></rect>')
        if i < n - 1:   # connector to the next bar, at the running level
            lv = b if kind != 'end' else 0
            g.append(f'<line x1="{x + bw:.1f}" x2="{x + slot:.1f}" y1="{sy(lv):.1f}" y2="{sy(lv):.1f}" class="wf-link"/>')
        ly = top - 7 if kind == 'start' else bot + 15   # label above a rise, below a fall
        g.append(f'<text x="{x + bw / 2:.1f}" y="{ly:.1f}" class="wf-lab">{_m(v)}</text>')
        for j, line in enumerate(lab):
            g.append(f'<text x="{x + bw / 2:.1f}" y="{H - B + 20 + j * 14}" class="wf-cat">{line}</text>')
    label = (f'General Fund balance if the Eldora sale fails in 2026: {_m(raw["gf_bal_2025"])} at the end of 2025, '
             f'{_m(raw["bud_change"])} in the adopted 2026 budget, {_m(-raw["balance"])} paid and written off, '
             f'{_m(-raw["owed"])} confirmed owed, ending 2026 at {_m(raw["fb_end"])}')
    return (f'<svg viewBox="0 0 {W} {H}" class="{"chart-narrow" if narrow else "chart-wide"}" role="img" '
            f'aria-label="{label}">{"".join(g)}</svg>')


def costs_chart(raw, narrow=False):
    """Step chart of the costs paid after each warrant list, then a bar for what firms confirmed is still owed."""
    W, H, L, R, T, B = (380, 280, 50, 92, 24, 34) if narrow else (760, 320, 64, 170, 24, 36)
    pts = [(date.fromisoformat(d), v) for d, v in raw['points']]
    x0 = date(2025, 10, 1)
    x1 = date(pts[-1][0].year + (pts[-1][0].month == 12), pts[-1][0].month % 12 + 1, 1)   # month after the last list
    step = 500_000 if not narrow else 1_000_000
    total = raw['balance'] + raw['owed']
    ymax = -((-max(total, raw['town_estimate']) * 1.06) // step) * step
    sx = lambda dt: L + (dt - x0).days / (x1 - x0).days * (W - L - R)   # noqa: E731
    sy = lambda v: T + (1 - v / ymax) * (H - T - B)   # noqa: E731
    g = []
    for v in _ticks(0, ymax, step):
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/>'
                 f'<text x="{L - 8}" y="{sy(v) + 4:.1f}" class="ylab">{"$0" if v == 0 else _m(v, 0 if v % 1_000_000 == 0 else 1)}</text>')
    months = [(2025, 10), (2026, 4), (2026, 10)] if narrow else [(2025, 10), (2026, 1), (2026, 4), (2026, 7), (2026, 10)]
    for y, m in months:
        x = sx(date(y, m, 1))
        if x <= W - R:
            g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{H - B}" y2="{H - B + 5}" class="tick"/>'
                     f'<text x="{x:.1f}" y="{H - B + 20}" class="xlab">{MONTHS[m - 1]} {y}</text>')
    path, prev = [f'M{sx(x0):.1f},{sy(0):.1f}'], 0
    for dt, v in pts:
        path.append(f'L{sx(dt):.1f},{sy(prev):.1f}L{sx(dt):.1f},{sy(v):.1f}')
        prev = v
    end_x = sx(pts[-1][0])
    line = ''.join(path)
    g.append(f'<path d="{line}L{end_x:.1f},{sy(0):.1f}Z" class="ct-area"/><path d="{line}" class="ct-line"/>')
    # one dot per warrant list, with its date and the account's balance on hover
    g.append(''.join(f'<circle cx="{sx(dt):.1f}" cy="{sy(v):.1f}" r="{2.5 if narrow else 3}" class="dot">'
                     f'<title>{_ap(dt)}: ${v:,.0f}</title></circle>' for dt, v in pts))
    # what is still owed, stacked on what has been paid, just right of the last warrant list
    bx, bw = end_x + 8, (14 if narrow else 22)
    g.append(f'<rect x="{bx:.1f}" y="{sy(total):.1f}" width="{bw}" height="{sy(raw["balance"]) - sy(total):.1f}" class="ct-owed">'
             f'<title>Confirmed owed: {_m(raw["owed"])}</title></rect>'
             f'<rect x="{bx:.1f}" y="{sy(raw["balance"]):.1f}" width="{bw}" height="{sy(0) - sy(raw["balance"]):.1f}" class="ct-area">'
             f'<title>Paid: {_m(raw["balance"])}</title></rect>')
    tx = bx + bw + 6
    g.append(f'<text x="{tx:.1f}" y="{sy(total) + 4:.1f}" class="ct-lab">{_m(total, 1)}{'' if narrow else ' total'}</text>'
             f'<text x="{tx:.1f}" y="{(sy(total) + sy(raw["balance"])) / 2 + 4:.1f}" class="ct-note">+{_m(raw["owed"], 1)} owed</text>'
             f'<text x="{tx:.1f}" y="{sy(raw["balance"]) + 14:.1f}" class="ct-note">{_m(raw["balance"], 1)} paid</text>')
    ey = sy(raw['town_estimate'])
    g.append(f'<line x1="{L}" x2="{bx + bw:.1f}" y1="{ey:.1f}" y2="{ey:.1f}" class="ct-est"/>'
             f'<text x="{L + 6}" y="{ey - 6:.1f}" class="ct-note">{'Town est.' if narrow else 'Town estimate:'} {_m(raw["town_estimate"], 2)}</text>')
    label = (f'Eldora acquisition costs paid by the General Fund, rising from {_m(pts[0][1])} in October 2025 to '
             f'{_m(raw["balance"])}, plus {_m(raw["owed"])} firms confirmed is still owed, for about {_m(total, 1)}; '
             f'the Town estimates {_m(raw["town_estimate"], 2)}')
    return (f'<svg viewBox="0 0 {W} {H}" class="{"chart-narrow" if narrow else "chart-wide"}" role="img" '
            f'aria-label="{label}">{"".join(g)}</svg>')


CSS = '''.grid {{ stroke: var(--line); stroke-width: 1; }}
.zero {{ stroke: var(--muted); stroke-width: 1.2; }}
.tick {{ stroke: var(--muted); }}
.ylab, .xlab {{ fill: var(--muted); font: 11px var(--mono); }}
.ylab {{ text-anchor: end; }}
.xlab {{ text-anchor: middle; }}
.wf-start {{ fill: var(--accent); }}
.wf-down {{ fill: var(--warn); }}
.wf-end {{ fill: var(--fg); }}
.wf-link {{ stroke: var(--muted); stroke-dasharray: 3 3; }}
.wf-lab {{ fill: var(--fg); font: 600 12px var(--mono); text-anchor: middle; }}
.wf-cat {{ fill: var(--muted); font: 11px var(--body); text-anchor: middle; }}
.ct-area {{ fill: var(--warn-soft); stroke: none; }}
.ct-line {{ fill: none; stroke: var(--warn); stroke-width: 2; }}
.dot {{ fill: var(--warn); }}
.ct-owed {{ fill: var(--warn); }}
.ct-est {{ stroke: var(--fg); stroke-dasharray: 5 4; stroke-width: 1.2; }}
.ct-lab {{ fill: var(--fg); font: 600 13px var(--mono); }}
.ct-note {{ fill: var(--muted); font: 11px var(--mono); }}'''
