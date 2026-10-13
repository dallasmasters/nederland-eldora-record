"""Make docs/preview.png, the 1200x630 image shown when the page link is shared (Open Graph / social cards).

It shows the page's four headline figures, computed from analysis/eldora_due_from.csv, with an "as of" date so a
cached card is still accurate about its date. update.sh regenerates it with each update.

Fonts: Public Sans and IBM Plex Mono (the page's fonts) from tmp/fonts/ if present, otherwise Noto Sans.
  curl -L -o tmp/fonts/PublicSans.ttf 'https://github.com/google/fonts/raw/main/ofl/publicsans/PublicSans%5Bwght%5D.ttf'
  curl -L -o tmp/fonts/PlexMono.ttf 'https://github.com/google/fonts/raw/main/ofl/ibmplexmono/IBMPlexMono-Medium.ttf'
"""
import csv
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630
BG, FG, MUTED, ACCENT, WARN = '#11191c', '#e3ecee', '#93a6ad', '#6cc7b1', '#f0a774'


def font(kind, size, weight=400):
    pub, mono = os.path.join(ROOT, 'tmp', 'fonts', 'PublicSans.ttf'), os.path.join(ROOT, 'tmp', 'fonts', 'PlexMono.ttf')
    try:
        if kind == 'mono':
            return ImageFont.truetype(mono, size)
        f = ImageFont.truetype(pub, size)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        return f
    except OSError:
        bold = weight >= 600
        return ImageFont.truetype(f'/usr/share/fonts/noto/NotoSans-{"Bold" if bold else "Regular"}.ttf', size)


def wrap(draw, text, f, width):
    lines, line = [], ''
    for word in text.split():
        trial = f'{line} {word}'.strip()
        if draw.textlength(trial, font=f) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


MONTHS = 'Jan. Feb. March April May June July Aug. Sept. Oct. Nov. Dec.'.split()



def main():
    img = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(img)
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'analysis', 'eldora_due_from.csv'))))
    paid = max(-float(r['account_balance_after'].replace('$', '').replace(',', '').replace('(', '-').replace(')', ''))
               for r in rows)
    y_, m_, d_ = rows[-1]['warrant_meeting'].split('-')
    asof = f'{MONTHS[int(m_) - 1]} {int(d_)}, {y_}'
    mil = lambda v: f'${v / 1e6:.1f}M'
    # what firms confirmed they are owed as of Oct. 16, 2026 (same figures as the page)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from eldora_spending_page import CONFIRMED
    owed = sum(inv + (unb if isinstance(unb, float | int) else 0) for _, inv, unb, _, _ in CONFIRMED)

    pad = 64
    dr.text((pad, 52), 'CITIZEN RESEARCH · COMPILED FROM TOWN OF NEDERLAND PUBLIC RECORDS', font=font('mono', 20), fill=ACCENT)
    dr.text((pad, 92), "Nederland's Eldora acquisition", font=font('sans', 64, 800), fill=FG)
    dr.text((pad, 176), 'Summary, costs, and where the money is coming from', font=font('sans', 32, 400), fill=MUTED)

    # the four headline figures
    tiles = [('ALREADY PAID', mil(paid), f'through {asof}', WARN),
             ('OWED, NOT YET PAID', '~' + mil(owed), 'confirmed by firms', WARN),
             ('IF THE SALE FAILS', '~' + mil(paid + owed), 'paid plus owed', WARN),
             ('PURCHASE PRICE', '$120M', 'agreement expired', ACCENT)]
    gap, top, h = 16, 268, 190
    w = (W - 2 * pad - 3 * gap) / 4
    for k, (label, value, note, color) in enumerate(tiles):
        x = pad + k * (w + gap)
        dr.rounded_rectangle([x, top, x + w, top + h], radius=10, fill='#172226', outline='#2b3a40', width=2)
        dr.text((x + 20, top + 22), label, font=font('mono', 17), fill=color)
        dr.text((x + 20, top + 58), value, font=font('mono', 56), fill=FG)
        dr.text((x + 20, top + 140), note, font=font('sans', 21, 400), fill=MUTED)

    dr.line([(pad, H - 108), (pad + 64, H - 108)], fill=WARN, width=4)
    dr.text((pad, H - 90), 'eldorarecord.org', font=font('sans', 34, 600), fill=FG)
    dr.text((pad + 330, H - 82), 'Independent · not affiliated with the Town or the resort',
            font=font('sans', 22, 400), fill=MUTED)

    out = os.path.join(ROOT, 'docs', 'preview.png')
    img.save(out, optimize=True)
    print(f'{out}: {os.path.getsize(out) // 1024} KB (paid {mil(paid)} through {asof})')


if __name__ == '__main__':
    main()
