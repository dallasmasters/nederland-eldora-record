"""Make docs/citizen-plan-preview.png, the 1200x630 image shown when a link to the Citizen Plan is shared.

Same size, fonts, and colors as docs/preview.png (make_preview.py). It draws the plan's 2027-2031 chart: the General
Fund's balance at the end of each year under the Citizen Plan and under the Town's proposal, each starting from $0 at the
end of 2027. The yearly figures are the plan's own and are typed here; change them when the plan's figures change.
"""
import os

from PIL import Image, ImageDraw

from make_preview import ACCENT, BG, FG, H, MUTED, ROOT, W, WARN, font

YEARS = [2027, 2028, 2029, 2030, 2031]
PLAN = [0, 90, 165, 224, 267]            # thousands: revenue minus spending, added up, before loan payments
STAFF = [0, -512, -1039, -1582, -2141]   # thousands: $497,155 a year, growing 3%


def main():
    img = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(img)
    pad = 64
    dr.text((pad, 44), 'CITIZEN PLAN · A PROPOSAL FROM NEDERLAND RESIDENTS', font=font('mono', 20), fill=ACCENT)
    dr.text((pad, 80), "Citizen Plan for Nederland's Budget Crisis", font=font('sans', 50, 800), fill=FG)
    dr.text((pad, 146), "General Fund balance at the end of each year, from $0 at the end of 2027",
            font=font('sans', 25, 400), fill=MUTED)
    # plot area
    x0, x1, y_top, y_bot = pad + 96, W - pad - 20, 214, 470
    lo, hi = -2400, 400
    X = lambda i: x0 + (x1 - x0) * i / 4
    Y = lambda v: y_top + (hi - v) / (hi - lo) * (y_bot - y_top)
    for v, lab in ((0, '$0'), (-1000, '−$1M'), (-2000, '−$2M')):
        dr.line([(x0, Y(v)), (x1, Y(v))], fill='#2b3a40' if v else '#93a6ad', width=2 if v else 2)
        f = font('mono', 20)
        dr.text((x0 - 16 - dr.textlength(lab, font=f), Y(v) - 13), lab, font=f, fill=MUTED)
    for i, yr in enumerate(YEARS):
        f = font('mono', 20); t = str(yr)
        dr.text((X(i) - dr.textlength(t, font=f) / 2, y_bot + 12), t, font=f, fill=MUTED)
    for vals, color in ((STAFF, WARN), (PLAN, ACCENT)):
        pts = [(X(i), Y(v)) for i, v in enumerate(vals)]
        dr.line(pts, fill=color, width=6, joint='curve')
        for x, y in pts:
            dr.ellipse([x - 9, y - 9, x + 9, y + 9], fill=color, outline=BG, width=3)
    f = font('sans', 28, 700)
    t = 'Citizen Plan: about +$0.3 million'
    dr.text((X(4) - dr.textlength(t, font=f), Y(PLAN[-1]) + 22), t, font=f, fill=ACCENT)
    t = "Town's proposal: −$2.1 million"
    dr.text((X(1) - 40, Y(STAFF[3]) - 6), t, font=f, fill=WARN)
    dr.line([(pad, H - 96), (pad + 64, H - 96)], fill=WARN, width=4)
    dr.text((pad, H - 80), 'eldorarecord.org', font=font('sans', 34, 600), fill=FG)
    dr.text((pad + 330, H - 72), 'Loans that are repaid, not transfers · not a Town document',
            font=font('sans', 22, 400), fill=MUTED)
    out = os.path.join(ROOT, 'docs', 'citizen-plan-preview.png')
    img.save(out, optimize=True)
    print(f'{out}: {os.path.getsize(out) // 1024} KB')


if __name__ == '__main__':
    main()
