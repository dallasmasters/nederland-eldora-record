"""Write analysis/cliffs_notes.html, The Eldora Deal Cliffs Notes: the acquisition told in order, in plain language.

An opinion page, like opinion.html: chapters 1 to 6 retell what the Eldora Record shows and link each part to it, and
chapter 7 is the author's view of what happens if the deal fails. Passages of the author's own reading are labeled.

Numbers that change with the record come from analysis/figures.json, which eldora_spending_page.py writes on each
build, so run that first (update.sh does). Budget figures from the adopted 2026 budget and the 2025 audit are fixed and
written in. The flow drawing in chapter 7 has a wide and a narrow version, swapped by width, as the FAQ's charts are.
"""
import json
import os

from eldora_spending_page import american_dates

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    figures = json.load(open(os.path.join(ROOT, 'analysis', 'figures.json')))
    t = figures['text']
    short = lambda s: s.replace(' million', 'M')   # noqa: E731  "$1.80 million" -> "$1.80M" for the drawing
    # "$0.11 million" reads better as "$110,000" for a general reader
    thousands = lambda s: f"${round(float(s.strip('$').split()[0]) * 1000) * 1000:,}"   # noqa: E731
    page = TEMPLATE.format(**t, R=t['site'], need_lo_s=short(t['need_lo']), need_hi_s=short(t['need_hi']),
                           left_lo_k=thousands(t['left_lo']), left_hi_k=thousands(t['left_hi']))
    page = american_dates(page)
    with open(os.path.join(ROOT, 'analysis', 'cliffs_notes.html'), 'w') as f:
        f.write(page)
    print(f'analysis/cliffs_notes.html: paid {t["balance"]}, owed {t["conf"]}, General Fund {t["fb_end"]}')


# The same boxes, arrows, and words in two layouts. Colors are the page's tokens, so both themes work.
FLOW_WIDE = '''<svg class="flow-wide" viewBox="0 50 1100 374" role="img" aria-label="If the deal fails, the bill lands on the General Fund">
        <defs><marker id="fw-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--muted)"/></marker></defs>
        <g fill="none" stroke="var(--muted)" stroke-width="1.4">
          <path d="M260 112H289" marker-end="url(#fw-arrow)"/><path d="M533 112H562" marker-end="url(#fw-arrow)"/>
          <path d="M806 112H835" marker-end="url(#fw-arrow)"/><path d="M959 154V184H550V202" marker-end="url(#fw-arrow)"/>
          <path d="M430 244H250V318" marker-end="url(#fw-arrow)"/><path d="M670 244H850V318" marker-end="url(#fw-arrow)"/>
        </g>
        <g text-anchor="middle" style="font-family: var(--body)">
          <rect x="20" y="70" width="240" height="84" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="140" y="96" font-size="15" font-weight="600" fill="var(--fg)">The effort winds down</text>
          <text x="140" y="118" font-size="12.5" fill="var(--muted)">A deadline passes, financing</text>
          <text x="140" y="136" font-size="12.5" fill="var(--muted)">fails, or POWDR sells</text>
          <rect x="293" y="70" width="240" height="84" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="413" y="96" font-size="15" font-weight="600" fill="var(--fg)">The final bills arrive</text>
          <text x="413" y="118" font-size="12.5" fill="var(--muted)">About $2.5M to $3M in all,</text>
          <text x="413" y="136" font-size="12.5" fill="var(--muted)">mostly legal fees</text>
          <rect x="566" y="70" width="240" height="84" rx="8" fill="var(--warn-soft)" stroke="var(--warn)" stroke-width="2"/>
          <text x="686" y="96" font-size="15" font-weight="600" fill="var(--fg)">Spending becomes a loss</text>
          <text x="686" y="118" font-size="12.5" fill="var(--fg)">General Fund ends {fb_end_m}</text>
          <text x="686" y="136" font-size="12.5" fill="var(--fg)">below zero</text>
          <rect x="839" y="70" width="240" height="84" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="959" y="96" font-size="15" font-weight="600" fill="var(--fg)">Water and sewer cash pays</text>
          <text x="959" y="118" font-size="12.5" fill="var(--muted)">General Fund owes Water and</text>
          <text x="959" y="136" font-size="12.5" fill="var(--muted)">Sewer {need_lo_s} to {need_hi_s}</text>
          <polygon points="430,244 550,204 670,244 550,284" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="550" y="240" font-size="14" fill="var(--fg)">Can water and sewer</text>
          <text x="550" y="258" font-size="14" fill="var(--fg)">cover it?</text>
          <text x="340" y="234" font-size="12.5" fill="var(--muted)">yes</text>
          <text x="760" y="234" font-size="12.5" fill="var(--muted)">no</text>
          <rect x="50" y="320" width="400" height="84" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="250" y="346" font-size="15" font-weight="600" fill="var(--fg)">Years of tight budgets</text>
          <text x="250" y="368" font-size="12.5" fill="var(--muted)">Land sales and staff cuts starting in 2027</text>
          <text x="250" y="386" font-size="12.5" fill="var(--muted)">Repay water and sewer over many years</text>
          <rect x="650" y="320" width="400" height="84" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="850" y="346" font-size="15" font-weight="600" fill="var(--fg)">Deeper cuts, sooner</text>
          <text x="850" y="368" font-size="12.5" fill="var(--muted)">Deeper cuts and faster land sales</text>
          <text x="850" y="386" font-size="12.5" fill="var(--muted)">Payment plans and a ballot question</text>
        </g>
      </svg>'''

FLOW_NARROW = '''<svg class="flow-narrow" viewBox="0 0 380 640" role="img" aria-label="If the deal fails, the bill lands on the General Fund">
        <defs><marker id="fn-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--muted)"/></marker></defs>
        <g fill="none" stroke="var(--muted)" stroke-width="1.4">
          <path d="M190 74V92" marker-end="url(#fn-arrow)"/><path d="M190 158V176" marker-end="url(#fn-arrow)"/>
          <path d="M190 242V260" marker-end="url(#fn-arrow)"/><path d="M190 326V344" marker-end="url(#fn-arrow)"/>
          <path d="M190 414V438" marker-end="url(#fn-arrow)"/><path d="M310 380H370V580H362" marker-end="url(#fn-arrow)"/>
        </g>
        <g text-anchor="middle" style="font-family: var(--body)">
          <rect x="20" y="10" width="340" height="64" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="190" y="34" font-size="14.5" font-weight="600" fill="var(--fg)">The effort winds down</text>
          <text x="190" y="56" font-size="12" fill="var(--muted)">A deadline passes, financing fails, or POWDR sells</text>
          <rect x="20" y="94" width="340" height="64" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="190" y="118" font-size="14.5" font-weight="600" fill="var(--fg)">The final bills arrive</text>
          <text x="190" y="140" font-size="12" fill="var(--muted)">About $2.5M to $3M in all, mostly legal fees</text>
          <rect x="20" y="178" width="340" height="64" rx="8" fill="var(--warn-soft)" stroke="var(--warn)" stroke-width="2"/>
          <text x="190" y="202" font-size="14.5" font-weight="600" fill="var(--fg)">Spending becomes a loss</text>
          <text x="190" y="224" font-size="12" fill="var(--fg)">General Fund ends {fb_end_m} below zero</text>
          <rect x="20" y="262" width="340" height="64" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="190" y="286" font-size="14.5" font-weight="600" fill="var(--fg)">Water and sewer cash pays</text>
          <text x="190" y="308" font-size="12" fill="var(--muted)">General Fund owes Water and Sewer {need_lo_s} to {need_hi_s}</text>
          <polygon points="70,380 190,346 310,380 190,414" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="190" y="376" font-size="13.5" fill="var(--fg)">Can water and sewer</text>
          <text x="190" y="393" font-size="13.5" fill="var(--fg)">cover it?</text>
          <text x="174" y="432" font-size="12" text-anchor="end" fill="var(--muted)">yes</text>
          <text x="340" y="372" font-size="12" fill="var(--muted)">no</text>
          <rect x="20" y="440" width="340" height="80" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="190" y="464" font-size="14.5" font-weight="600" fill="var(--fg)">Years of tight budgets</text>
          <text x="190" y="486" font-size="12" fill="var(--muted)">Land sales and staff cuts starting in 2027</text>
          <text x="190" y="504" font-size="12" fill="var(--muted)">Repay water and sewer over many years</text>
          <rect x="20" y="540" width="340" height="80" rx="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.2"/>
          <text x="190" y="564" font-size="14.5" font-weight="600" fill="var(--fg)">Deeper cuts, sooner</text>
          <text x="190" y="586" font-size="12" fill="var(--muted)">Deeper cuts and faster land sales</text>
          <text x="190" y="604" font-size="12" fill="var(--muted)">Payment plans and a ballot question</text>
        </g>
      </svg>'''

TEMPLATE = '''<title>The Eldora Deal Cliffs Notes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;800&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column of numbered chapters, same palette and type as the Eldora Record and the FAQ */
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
body {{ background: var(--bg); color: var(--fg); font: 15px/1.55 var(--body); margin: 0; }}
.wrap {{ max-width: 1200px; margin: 0 auto; padding-inline: 20px; padding-block: 40px 64px; display: grid; gap: 22px; }}
.wrap > *, section.q > *, .opinion > * {{ min-width: 0; }}
/* Text keeps a readable measure; tables and the drawing use the full width, as on the record page */
p, ul, ol, nav.toc {{ max-width: 80ch; }}
.eyebrow {{ font: 500 12px var(--mono); text-transform: uppercase; letter-spacing: .08em; color: var(--accent); }}
h1 {{ font: 800 clamp(28px, 4.5vw, 42px)/1.1 var(--body); margin: 4px 0 0; text-wrap: balance; letter-spacing: -.01em; }}
.byline {{ color: var(--muted); margin: 0; font-size: 15px; }}
.lead {{ font-size: 17px; margin: 0; }}
.note {{ background: var(--accent-soft); border-left: 4px solid var(--accent); padding: 12px 16px; margin: 0; border-radius: 0 6px 6px 0; }}
a {{ color: var(--accent); }}
nav.toc {{ display: grid; gap: 4px; font-size: 15px; }}
nav.toc b {{ font: 500 11px var(--mono); text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-top: 6px; }}
nav.toc ol {{ margin: 0; padding-left: 22px; display: grid; gap: 2px; }}
section.q {{ display: grid; gap: 10px; scroll-margin-top: 16px; }}
section.q h2 {{ font-size: 21px; line-height: 1.25; margin: 0; text-wrap: balance; display: flex; gap: 10px; }}
section.q h2 .n {{ font: 600 15px/1.9 var(--mono); color: var(--accent); flex: none; }}
section.q p, section.q ul, section.q ol {{ margin: 0; }}
section.q ul, section.q ol {{ padding-left: 20px; display: grid; gap: 6px; }}
section.q ol ul {{ margin-top: 6px; }}
.src {{ font-size: 14px; color: var(--muted); }}
.src a {{ font-weight: 600; }}
.mine {{ border-left: 3px solid var(--warn); padding-left: 12px; }}
.mine b.tag, .opinion .tag {{ font: 500 11px var(--mono); text-transform: uppercase; letter-spacing: .08em; color: var(--warn); }}
.opinion {{ background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--warn); border-radius: 6px; padding: 14px 18px; display: grid; gap: 10px; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 15px; font-variant-numeric: tabular-nums; background: var(--surface); }}
th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
thead th {{ font: 500 12px var(--mono); text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }}
td.when {{ white-space: nowrap; }}
td.num {{ text-align: right; white-space: nowrap; }}
tr.total td {{ font-weight: 600; border-top: 2px solid var(--line); }}
.figs {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
.fig {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; display: grid; gap: 2px; min-width: 0; }}
.fig b {{ font: 600 22px var(--mono); font-variant-numeric: tabular-nums; }}
.fig span {{ font-size: 13px; color: var(--muted); }}
.fig.total {{ border-color: var(--warn); }}
.figure {{ background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 14px; margin: 0; display: grid; gap: 6px; max-width: none; }}
.figure figcaption {{ font-weight: 600; }}
.figure .cap {{ font-size: 13px; color: var(--muted); }}
.figure svg {{ display: block; width: 100%; height: auto; }}
.figure .flow-narrow {{ display: none; max-width: 420px; margin: 0 auto; }}
footer {{ border-top: 1px solid var(--line); padding-top: 14px; font-size: 14px; color: var(--muted); display: grid; gap: 6px; }}
footer p {{ margin: 0; }}
@media (max-width: 560px) {{
  h1 {{ font-size: 27px; }}
  .figs {{ grid-template-columns: 1fr; }}
  th, td {{ padding: 6px 5px; }}
  table {{ font-size: 14px; }}
  .opinion {{ padding: 12px; }}
  .figure {{ padding: 10px; }}
  .figure .flow-wide {{ display: none; }}
  .figure .flow-narrow {{ display: block; }}
}}
</style>

<main class="wrap">
  <header style="display:grid;gap:12px">
    <div class="eyebrow">Opinion · not part of the record</div>
    <h1>The Eldora Deal Cliffs Notes</h1>
    <p class="byline">Dallas Masters, Nederland resident · Nov. 12, 2026 · Figures through the {asof} warrant list, updated with the record, last {cov_updated}</p>
    <p class="lead">Nederland has spent two years trying to buy Eldora Mountain Resort. The purchase hasn't happened, but the Town has run up about {owed_m} in bills trying to make it happen. If the deal never closes, the Town has to cover that itself. That is nearly as much as the General Fund spends on everything else in a year.</p>
    <p class="note">This page tells the story in order, in plain language. Chapters 1 through 6 retell what <a href="{R}">the Eldora Record</a> shows, and each ends with links to the part of the record that has the details and sources; if the two ever differ, the record is correct. Passages marked &ldquo;My reading&rdquo; and all of chapter 7 are my opinion. For facts only, see <a href="{R}faq.html">the Eldora FAQ</a>; my fuller opinions are on <a href="{R}opinion.html">a separate page</a>.</p>
    <nav class="toc" aria-label="Chapters">
      <b>How we got here</b><ol start="1"><li><a href="#c1">The plan to buy Eldora</a></li><li><a href="#c2">The lawyers and consultants</a></li><li><a href="#c3">The deal stalled, and the bills grew</a></li></ol>
      <b>The money</b><ol start="4"><li><a href="#c4">How the Town recorded the costs</a></li><li><a href="#c5">What the law allows</a></li><li><a href="#c6">If the deal closes</a></li></ol>
      <b>What comes next</b><ol start="7"><li><a href="#c7">What I think will happen</a></li><li><a href="#watch">What to watch</a></li><li><a href="#terms">Definitions</a></li></ol>
    </nav>
  </header>

  <section class="q" id="c1">
    <h2><span class="n">1.</span>The plan to buy Eldora</h2>
    <p>In 2024, POWDR, the company that owns Eldora, put the ski area up for sale, and the Town decided to try to buy it. The Board began discussing it in closed session on Sept. 3, 2024. Its first open discussion was on Nov. 19, 2024.</p>
    <p>The Town gave two main reasons: local control of the mountain, and long-term revenue, including &ldquo;addressing recurring budget shortfalls through a more stable revenue base.&rdquo;</p>
    <ul>
      <li><strong>A new Town business.</strong> The resort would be owned by the Mountain Recreation Enterprise, a Town-owned business set up for this purpose.</li>
      <li><strong>Borrowing paid back by the resort.</strong> The Town would sell revenue bonds, which are loans from investors. Lift tickets, passes, and other resort income would repay them. Property taxes and the Town's regular budget would not.</li>
      <li><strong>Big numbers.</strong> In January 2026, the Board approved a $120 million purchase price and up to $225 million in bonds.</li>
    </ul>
    <p>Think of it like buying a rental house with a loan that only the rent can repay. If the rent falls short, the lender takes the house, not your paycheck. But you still have to pay the lawyers and inspectors you hire before closing, even if you never get the keys. That is where Nederland's money is at risk now.</p>
    <p class="src">Details and sources: <a href="{R}#in-brief">The acquisition in brief</a></p>
  </section>

  <section class="q" id="c2">
    <h2><span class="n">2.</span>The lawyers and consultants the Town hired</h2>
    <p>Starting in January 2025, the Town hired real estate lawyers, bond lawyers, water-rights lawyers, accountants to check the resort's books, ski-industry consultants, surveyors, and a financial advisor. The resolutions that let staff hire them set no dollar limits.</p>
    <p>Some firms get paid only if the sale closes. Others get paid either way:</p>
    <div class="scroll"><table>
      <thead><tr><th scope="col">Paid only if the sale closes</th><th scope="col">Paid either way</th></tr></thead>
      <tbody>
        <tr><td>Financial advisor Stifel ($325,000 fee at the bond sale)</td><td>Real estate lawyers Brownstein, billed when the deal is completed <em>or</em> ended</td></tr>
        <tr><td>Disclosure lawyers Butler Snow (about $100,000)</td><td>Bond lawyers Kline Alvarado Veio, hourly if no bonds are sold</td></tr>
        <tr><td>The bond underwriters</td><td>The Town Attorney, accountants, consultants, surveyors, and others</td></tr>
      </tbody>
    </table></div>
    <p>The purchase agreement also said each side pays its own costs, whether or not the sale closes. The Town planned to pay itself back from the bond money at closing. Until then, it pays the bills itself.</p>
    <p class="src">Details and sources: <a href="{R}#payees">Who was paid and who is owed</a> · <a href="{R}#no-limits">Budget and limits</a> · <a href="{R}#no-sale">What happens to the costs</a></p>
  </section>

  <section class="q" id="c3">
    <h2><span class="n">3.</span>The deal stalled, and the bills grew</h2>
    <p>The closing deadline was April 30, 2026. It passed without a closing, and the bills have grown to about {owed_m}.</p>
    <div class="scroll"><table>
      <thead><tr><th scope="col">When</th><th scope="col">What happened</th></tr></thead>
      <tbody>
        <tr><td class="when">July 2025</td><td>The Town and POWDR signed a non-binding term sheet.</td></tr>
        <tr><td class="when">Jan. 2026</td><td>The Board approved the $120 million purchase and up to $225 million in bonds.</td></tr>
        <tr><td class="when">April 30, 2026</td><td>The deadline to close passed without a closing. No bonds had been sold.</td></tr>
        <tr><td class="when">July 19, 2026</td><td>The Board's authority to sell the bonds ran out.</td></tr>
        <tr><td class="when">Summer 2026</td><td>The Town Manager resigned and the Town Treasurer retired. A former Town Manager returned as interim on Sept. 25.</td></tr>
        <tr><td class="when">Sept. 30, 2026</td><td>The Town said the agreement had expired but it was still pursuing a restructured &ldquo;sale-leaseback&rdquo; deal. It estimated the costs at about $2.5 million.</td></tr>
        <tr><td class="when">Oct. 22, 2026</td><td>The Town said the lease the new deal needs &ldquo;has not been drafted.&rdquo;</td></tr>
        <tr><td class="when">Nov. 9, 2026</td><td>A draft resolution said the Town was restructuring the deal &ldquo;in response to feedback from prospective bondholders,&rdquo; and cited updated cost estimates of about $2.76 million.</td></tr>
      </tbody>
    </table></div>
    <p>The Eldora Record's count, checked firm by firm against Town records:</p>
    <div class="figs">
      <div class="fig"><span>Already paid</span><b>{balance}</b><span>through the {asof} warrant list</span></div>
      <div class="fig"><span>Owed</span><b>{conf}</b><span>as the firms confirmed, as of Oct. 16, 2026</span></div>
      <div class="fig total"><span>Total if the deal fails</span><b>~{owed_short}</b><span>about {hh_est} per household</span></div>
    </div>
    <p>About $1.2 million of what is owed goes to the real estate lawyers. Their agreement sends the bill when the deal is completed or ended, so most of it hasn't been invoiced yet. Some other firms' invoices have gone unpaid for more than a year. And while the effort continues, some costs keep adding up every month, such as the Town Attorney's time and the online data room.</p>
    <p class="src">Details and sources: <a href="{R}#revised-plan">Where things stand</a> · <a href="{R}#bottom-line">The bottom line</a> · <a href="{R}#overdue">Overdue invoices</a></p>
  </section>

  <section class="q" id="c4">
    <h2><span class="n">4.</span>How the Town recorded the costs</h2>
    <p>The Town didn't treat the Eldora bills as spending. It recorded them in a General Fund account called &ldquo;Due From,&rdquo; as money it expects to be paid back from the bonds. Accountants call this a receivable.</p>
    <ul>
      <li><strong>The costs weren't in the budget.</strong> Neither the 2025 nor the 2026 budget includes them. The Board approved the payments on the regular bill lists (&ldquo;warrant lists&rdquo;), each approved with the rest of the consent agenda.</li>
      <li><strong>The General Fund's balance looked better than its cash.</strong> The General Fund pays for the Town's day-to-day work: administration, police, streets, parks, and the like. At the end of 2025 it showed a balance of about $1 million, a figure that counts receivables, which may include the Eldora costs, as assets. Its cash was negative by $757,482.</li>
      <li><strong>Other funds' cash covered the gap.</strong> The Town keeps all its funds' cash in one bank pool and tracks each fund's share on paper. When the General Fund's share runs out, its bills are paid with cash that belongs to the Water Fund, the Sewer Fund, and others.</li>
    </ul>
    <p>The Town gets this money back only if bonds are sold. Right now there is no purchase agreement and no authority to sell bonds. If the deal ends, the {balance} already paid becomes a loss, and the {conf} still owed must be paid too.</p>
    <p>On the Nov. 9, 2026, warrant list, Eldora invoices started going to a new General Fund account called &ldquo;Eldora Expense,&rdquo; with a $0 budget. The Town hasn't explained the change, and the records searched don't explain the balance shown for the account.</p>
    <p class="mine"><b class="tag">My reading</b><br>The Town may be starting to count the costs as spending instead of money it will get back. If so, they would need to be in the budget.</p>
    <p class="src">Details and sources: <a href="{R}#receivable">How the costs are recorded</a> · <a href="{R}#eldora-expense">The new account</a> · <a href="{R}#csafe">The pooled cash</a></p>
  </section>

  <section class="q" id="c5">
    <h2><span class="n">5.</span>What the law allows</h2>
    <p>State law, the Colorado Constitution, and taxes voters approved for specific uses all limit how the Town can pay these costs.</p>
    <ul>
      <li><strong>Spending needs Board approval in the budget.</strong> Colorado law says a town can't spend or contract to spend more than its budget authorizes (&ldquo;appropriates&rdquo;) for each fund. The 2026 General Fund authority is $5,674,176, but $2,250,000 of it is for grant projects, and grant money can be spent only on the project it was given for. Whether the rest covers the Eldora bills depends on 2026 spending to date, which isn't public. Either way, paying them needs the Board's approval in a budget.</li>
      <li><strong>A budget can't spend more than the Town has.</strong> Spending can't be more than expected revenue plus money left over from past years. A fund that starts the year below zero has to make up the difference with more revenue, less spending, or money from somewhere else.</li>
      <li><strong>TABOR requires a public vote</strong> for any new tax or tax increase, and for debt or other financial obligations lasting more than a year that aren't backed by cash set aside in advance. TABOR's emergency reserve, $147,000, can't be used for a revenue shortfall.</li>
      <li><strong>Some money can be used only for certain purposes.</strong> The Community Center Fund ($830,528 at the end of 2025) comes from a sales tax voters approved for community-center purposes. The Downtown Development Authority's money ($1,695,723) is mostly property tax collected for downtown projects and debts, from every taxing district's levy, not just the Town's. Moving either into the General Fund doesn't change what it can be spent on.</li>
      <li><strong>Water and sewer money comes from rates and a dedicated sales tax,</strong> and repays their state loans. The water and sewer funds could lend to the General Fund, but a loan has to be paid back. Whether a loan or transfer is allowed is a question for the Town attorney or auditor.</li>
      <li><strong>Bankruptcy and dissolving the Town aren't ways out.</strong> The record found no Colorado law that lets a town file for bankruptcy, and a town can dissolve only after providing for all its debts.</li>
    </ul>
    <p>In short, the General Fund will have to pay the {owed_m}, most likely over several years.</p>
    <p class="src">Details and sources: <a href="{R}#gf-deficit">If the General Fund ends in deficit</a> · <a href="{R}#other-funds">Could other funds cover it?</a> · <a href="{R}#bankruptcy">Bankruptcy and dissolution</a></p>
  </section>

  <section class="q" id="c6">
    <h2><span class="n">6.</span>If the deal closes</h2>
    <p>If the deal closes, bond money would repay the Town for most of the {owed_m}. But owning a ski area has its own risks.</p>
    <ul>
      <li><strong>The debt would be large.</strong> The Board authorized up to $225 million in bonds, and an earlier plan expected about $180 million. The Town now models interest rates near 8.5%. The restructured deal is meant to borrow less, but no new amount has been made public.</li>
      <li><strong>Only the resort pays it back.</strong> The bonds would be repaid from resort income alone, not from taxes. That protects the Town's budget from the debt itself, but a run of poor snow years could leave too little to pay bondholders.</li>
      <li><strong>The resort could change hands if the bonds default.</strong> Under the sale-leaseback, a bond trustee would hold title and lease the resort back to the Town's business. If the bonds defaulted, the trustee could act &ldquo;without first completing a traditional foreclosure process,&rdquo; which could change who runs the resort.</li>
      <li><strong>The Town might not see profits for years.</strong> Under the May 2026 draft bond documents, an outside consultant would approve the resort's budgets, and money would reach the Town only after the resort earned twice its main bond payments for three years in a row.</li>
      <li><strong>Other local districts would lose tax revenue.</strong> Town-owned property is generally tax-exempt. By the record's estimate, the Nederland Fire Protection District would lose {dt_fire} a year and the library district {dt_lib}.</li>
    </ul>
    <p class="mine"><b class="tag">My reading</b><br>My rough review of the resort's reported earnings suggests it can support about $90 million to $95 million in borrowing. That points to a cash price of about $70 million or less, well below $120 million. The Town hasn't named where the difference would come from.</p>
    <p class="src">Details and sources: <a href="{R}#if-closes">If the purchase closes</a> · <a href="{R}#may-draft">The May 2026 draft</a> · <a href="{R}#district-taxes">Property taxes on the resort</a> · <a href="{R}opinion.html#debt-check">My rough review</a></p>
  </section>

  <section class="q" id="c7">
    <h2><span class="n">7.</span>What I think will happen if the deal fails</h2>
    <div class="opinion">
      <span class="tag">Opinion</span>
      <p>I think the deal is more likely to fail than to close. The main reasons are a gap between the $120 million price and what the resort's earnings can support, harder financing at today's interest rates, staff turnover, and the need to redo every major document. Nothing stops POWDR from selling to someone else.</p>
      <p>If it fails, here is the sequence I expect:</p>
      <ol>
        <li><strong>The effort winds down slowly.</strong> The Board votes Nov. 17 on Resolution 2026-31, which limits new spending and requires monthly cost reports. Work continues into 2027, adding modest costs each month, until a deadline passes, financing can't be found, or POWDR moves on.</li>
        <li><strong>The final bills arrive.</strong> The real estate lawyers bill when the deal ends: about $1.2 million, perhaps less a 10% discount their agreement offers for a failed deal. The bond lawyers bill their hours. Firms that haven't confirmed what they're owed may send more. The total lands around $2.5 million to $3 million.</li>
        <li><strong>The money spent becomes a loss.</strong> The {balance} the Town expected to get back is written off as a loss. Together with the bills, that would leave the General Fund {fb_end_m} below zero if it happens in 2026, in a fund that spends about $3.2 million a year on operations and was already budgeted to shrink.</li>
        <li><strong>Water and sewer cash pays the bills.</strong> Because all funds share one cash pool, the money to pay the firms would effectively come from the Water and Sewer Funds. That would leave the General Fund owing them about {need_lo} to {need_hi}, and leave those funds only about {left_lo_k} to {left_hi_k} above their own reserves.</li>
        <li><strong>Little other money is available.</strong> Community Center and Downtown Development Authority money can be used only for certain purposes, so it can't cover much. The water and sewer funds can lend, but a loan has to be repaid, and customers may ask why their water and sewer money is paying for a ski-area deal.</li>
        <li><strong>Land sales and staff cuts start in 2027.</strong> Even before Eldora, the 2026 budget planned to spend about $207,000 more on operations than the General Fund takes in. Repaying the water and sewer funds would add more, perhaps $400,000 a year over five years. The Town will likely do two things:
          <ul>
            <li><strong>Selling land,</strong> one of the few ways to raise a large sum without a tax vote. Park and government land needs voter approval to sell, sales are slow, and the money comes only once.</li>
            <li><strong>Cutting staff.</strong> Law enforcement, streets and parks, and administration take most of the $3.24 million operating budget, much of it in wages, so real savings likely mean fewer staff.</li>
          </ul>
        </li>
        <li><strong>Years of tight budgets.</strong> The General Fund would repay the water and sewer funds over many years. At the General Fund's average yearly gains from 2017 to 2023, rebuilding {fb_end_m} would take roughly {yrs_def} years, and its balance fell in 2024 and 2025. Expect continued cuts to services, little money for anything new, payment plans with the firms, and possibly a tax question on the ballot, which needs voter approval.</li>
        <li><strong>If the water and sewer funds can't cover it,</strong> the cuts come sooner and go deeper: faster land sales, longer payment plans with the firms, and an earlier tax question for voters.</li>
      </ol>
      <figure class="figure" role="figure" aria-label="If the deal fails, the bill lands on the General Fund">
        <figcaption>If the deal fails, the bill lands on the General Fund</figcaption>
        ''' + FLOW_WIDE + '''
        ''' + FLOW_NARROW + '''
        <span class="cap">My view of the likely sequence; amounts from the Eldora Record. Either way, the General Fund ends up owing the water and sewer funds, and the Community Center and Downtown Development Authority money can't do much to change that.</span>
      </figure>
      <p><strong>What doesn't happen:</strong> the Town doesn't go bankrupt or dissolve, because Colorado law allows neither as a way out of debts. Residents' homes aren't on the line, and no bonds default, because none were ever sold. This is a long-term budget problem, not a collapse. But it would limit what the Town can do for a decade or more.</p>
    </div>
    <p class="src">Details and sources: <a href="{R}#gf-deficit">If the General Fund ends in deficit</a> · <a href="{R}#pay-rest">Could the Town pay the rest?</a> · <a href="{R}#gf-recovery">The General Fund year by year</a> · <a href="{R}opinion.html">My opinions</a></p>
  </section>

  <section class="q" id="watch">
    <h2>What to watch</h2>
    <div class="scroll"><table>
      <thead><tr><th scope="col">When</th><th scope="col">What to watch for</th></tr></thead>
      <tbody>
        <tr><td class="when">Nov. 17, 2026</td><td>The Board's vote on Resolution 2026-31, which limits spending and requires monthly cost reports.</td></tr>
        <tr><td class="when">Dec. 1, 2026</td><td>A final accounting of what's owed, if the Board adopts my proposed amendment.</td></tr>
        <tr><td class="when">December 2026</td><td>The 2027 budget: does it show the Eldora costs and a plan if the deal fails?</td></tr>
        <tr><td class="when">Jan. 31, 2027</td><td>My proposed deadline for a term sheet.</td></tr>
        <tr><td class="when">Feb. 28, 2027</td><td>The interim Town Manager's contract ends.</td></tr>
        <tr><td class="when">March 31, 2027</td><td>My proposed deadline for a signed agreement and committed financing.</td></tr>
        <tr><td class="when">June 30, 2027</td><td>My proposed deadline to close.</td></tr>
      </tbody>
    </table></div>
    <p>The proposed deadlines and the final accounting are in <a href="{R}resolution.html">my amendments</a>; the Board hasn't adopted them. Residents can comment at any Board meeting.</p>
    <p class="src">Details and sources: <a href="{R}#get-involved">Get involved</a></p>
  </section>

  <section class="q" id="terms">
    <h2>Definitions</h2>
    <div class="scroll"><table>
      <thead><tr><th scope="col">Term</th><th scope="col">What it means</th></tr></thead>
      <tbody>
        <tr><td><strong>General Fund</strong></td><td>The Town's main account for everyday services. The Eldora costs are charged here.</td></tr>
        <tr><td><strong>Appropriation</strong></td><td>The spending limit the Board sets for each fund in the budget.</td></tr>
        <tr><td><strong>Warrant list</strong></td><td>The list of bills the Board approves for payment at each meeting.</td></tr>
        <tr><td><strong>Receivable</strong></td><td>Money a fund expects to be paid back. Here, the Eldora costs the Town expects to recover from bonds.</td></tr>
        <tr><td><strong>Pooled cash</strong></td><td>One shared pool holding every fund's cash, tracked separately on paper.</td></tr>
        <tr><td><strong>Revenue bonds</strong></td><td>Loans from investors repaid only from a specific source, here the resort's income.</td></tr>
        <tr><td><strong>Sale-leaseback</strong></td><td>A bond trustee holds the resort's title and leases it back to the Town's business until the bonds are paid.</td></tr>
        <tr><td><strong>TABOR</strong></td><td>Colorado's Taxpayer's Bill of Rights, which requires voter approval for new taxes and multi-year debt.</td></tr>
        <tr><td><strong>Restricted money</strong></td><td>Money that law or a ballot measure limits to certain uses.</td></tr>
      </tbody>
    </table></div>
  </section>

  <footer>
    <p>This is an independent opinion page, not affiliated with, endorsed by, or produced by the Town of Nederland, Eldora Mountain Resort, or POWDR, and not affiliated with the CliffsNotes study guides. Its figures are updated with <a href="{R}">the Eldora Record</a>, and the record governs if the two ever differ.</p>
  </footer>
</main>
'''

if __name__ == '__main__':
    main()
