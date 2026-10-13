"""Write analysis/faq.html, the Eldora FAQ: a short-form version of the Eldora Record in question-and-answer form.

Facts only, like the record: each answer restates what the record says and links to the part of the record that
has the sources. Opinions stay on the opinion page; the FAQ only points to it (the note at the top).

Every number that changes with the record comes from analysis/figures.json, which eldora_spending_page.py writes on
each build, so run that first (update.sh does). The two charts are drawn from the same numbers (scripts/charts.py).
Sentences that state facts in words (a new deadline, a new Town statement) are reviewed by hand at each update,
like the record's opening paragraph; review_changes.py reminds.
"""
import json
import os

from charts import CSS as CHART_CSS, costs_chart, gf_chart
from eldora_spending_page import american_dates

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    figures = json.load(open(os.path.join(ROOT, 'analysis', 'figures.json')))
    t, raw = figures['text'], figures['raw']
    page = TEMPLATE.format(**t, R=t['site'], chart_css=CHART_CSS.format(),
                           costs_chart=costs_chart(raw) + costs_chart(raw, narrow=True),
                           gf_chart=gf_chart(raw) + gf_chart(raw, narrow=True))
    page = american_dates(page)
    with open(os.path.join(ROOT, 'analysis', 'faq.html'), 'w') as f:
        f.write(page)
    print(f'analysis/faq.html: paid {t["balance"]}, owed {t["conf"]}, General Fund {t["fb_end"]}')


TEMPLATE = '''<title>The Eldora FAQ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;800&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column of numbered questions, same palette and type as the Eldora Record */
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
.wrap > *, section.q > * {{ min-width: 0; }}
/* Text keeps a readable measure; tables and charts use the full width, as on the record page */
p, ul, ol, nav.toc {{ max-width: 80ch; }}
.eyebrow {{ font: 500 12px var(--mono); text-transform: uppercase; letter-spacing: .08em; color: var(--accent); }}
h1 {{ font: 800 clamp(28px, 4.5vw, 42px)/1.1 var(--body); margin: 4px 0 0; text-wrap: balance; letter-spacing: -.01em; }}
.byline {{ color: var(--muted); margin: 0; font-size: 15px; }}
.note {{ background: var(--accent-soft); border-left: 4px solid var(--accent); padding: 12px 16px; margin: 0; border-radius: 0 6px 6px 0; display: grid; gap: 8px; }}
.note p {{ margin: 0; }}
a {{ color: var(--accent); }}
nav.toc {{ display: grid; gap: 4px; font-size: 15px; }}
nav.toc b {{ font: 500 11px var(--mono); text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-top: 6px; }}
nav.toc ol {{ margin: 0; padding-left: 22px; display: grid; gap: 2px; }}
.part {{ font: 600 12px var(--mono); text-transform: uppercase; letter-spacing: .1em; color: var(--muted);
  border-top: 2px solid var(--fg); padding-top: 8px; margin: 18px 0 0; }}
section.q {{ display: grid; gap: 10px; scroll-margin-top: 16px; }}
section.q h2 {{ font-size: 21px; line-height: 1.25; margin: 0; text-wrap: balance; display: flex; gap: 10px; }}
section.q h2 .n {{ font: 600 15px/1.9 var(--mono); color: var(--accent); flex: none; }}
section.q p, section.q ul {{ margin: 0; }}
section.q ul {{ padding-left: 20px; display: grid; gap: 4px; }}
.src {{ font-size: 14px; color: var(--muted); }}
.src a {{ font-weight: 600; }}
.pointer {{ border-left: 3px solid var(--warn); padding-left: 12px; color: var(--muted); font-size: 15px; }}
.figs {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
.fig {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; display: grid; gap: 2px; min-width: 0; }}
.fig b {{ font: 600 22px var(--mono); font-variant-numeric: tabular-nums; }}
.fig span {{ font-size: 13px; color: var(--muted); }}
.fig.total {{ border-color: var(--warn); }}
.figure {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px; margin: 0; display: grid; gap: 6px; }}
.figure figcaption {{ font-weight: 600; }}
.figure .cap {{ font-size: 13px; color: var(--muted); }}
.figure svg {{ display: block; width: 100%; height: auto; }}
.figure .chart-narrow {{ display: none; }}
{chart_css}
footer {{ border-top: 1px solid var(--line); padding-top: 14px; font-size: 14px; color: var(--muted); display: grid; gap: 6px; }}
footer p {{ margin: 0; }}
@media (max-width: 560px) {{
  h1 {{ font-size: 27px; }}
  .figs {{ grid-template-columns: 1fr; }}
  .figure {{ padding: 10px; }}
  .figure .chart-wide {{ display: none; }}
  .figure .chart-narrow {{ display: block; }}
}}
</style>

<main class="wrap">
  <header style="display:grid;gap:12px">
    <div class="eyebrow">The Eldora Record · short version</div>
    <h1>The Eldora FAQ</h1>
    <p class="byline">Dallas Masters, Nederland resident · Figures through the {asof} warrant list · Updated with the record, last {cov_updated}</p>
    <div class="note">
      <p>Short answers to the questions residents ask about the Town's pursuit of Eldora Mountain Resort. Each answer comes from <a href="{R}">the Eldora Record</a> and ends with a link to the part of the record that has the details and the Town sources.</p>
      <p>The record is built from the Town's own public records: Board meeting records from {cov_from} through {cov_through}, resolutions, ordinances, finance documents, staff reports, Town website and Facebook posts, and records released under the Colorado Open Records Act. Where it does its own math, it says so; where it can't find something, it says "not in the records searched." Corrections are logged (<a href="{R}#method-ai">how this was done</a>).</p>
      <p>Like the record, this page is facts only. <a href="{R}opinion.html">My opinions</a>, <a href="{R}resolution.html">Resolution 2026-31</a> with my amendments, and the plain-language <a href="{R}cliffs-notes.html">Eldora Deal Cliffs Notes</a> are on separate pages.</p>
    </div>
    <nav class="toc" aria-label="Questions">
      <b>The costs</b><ol start="1"><li><a href="#q1">How much has the Town paid, and did the Board know?</a></li><li><a href="#q2">How much does the Town owe in all?</a></li></ol>
      <b>Paying for it</b><ol start="3"><li><a href="#q3">Does the General Fund have the cash?</a></li><li><a href="#q4">How would the budget cover it?</a></li><li><a href="#q5">What does Resolution 2026-31 require?</a></li></ol>
      <b>The deal</b><ol start="6"><li><a href="#q6">Where does the deal stand?</a></li><li><a href="#q7">What would the purchase commit the Town to?</a></li><li><a href="#q8">What would it mean for the fire and library districts?</a></li></ol>
      <b>What's next</b><ol start="9"><li><a href="#q9">What don't we know yet?</a></li><li><a href="#q10">What can I do?</a></li></ol>
    </nav>
  </header>

  <p class="part">The costs</p>

  <section class="q" id="q1">
    <h2><span class="n">1.</span>How much has the Town paid, and did the Board know?</h2>
    <p>{balance} through the {asof} warrant list, mostly to lawyers and consultants. The largest payees are {top_payees}. All of it is charged to the General Fund, which pays for day-to-day Town services, and neither the 2025 nor the 2026 budget included it. The Board of Trustees, which includes the Mayor, approved every step: the purchase agreement, the bond ordinance, and five 2025 resolutions letting staff hire counsel and consultants with no dollar limit. Every recorded vote on the acquisition was unanimous among the trustees present.</p>
    <p>The running total was in the packets the Board approved: each warrant list showed the Eldora payments and the account's balance, $915,922 by July 7, 2026. The minutes searched record no discussion of it. The risk was raised in January 2025, when the Town Attorney said bond counsel "would need to be paid by the town" if the deal didn't close. Until November 2026 the payments were carried as money the Town expected to recover from bonds; its Nov. 9 forecast now counts them as spending.</p>
    <figure class="figure" role="figure" aria-label="Eldora acquisition costs: the running total">
      <figcaption>Eldora acquisition costs: the running total</figcaption>
      {costs_chart}
      <span class="cap">Paid from the General Fund after each warrant list, then what firms confirmed is still owed as of Oct. 16, 2026. The dashed line is the Town's estimate, about $2.76 million, not itemized.</span>
    </figure>
    <p class="src">Details and sources: <a href="{R}#payees">Who was paid</a> · <a href="{R}#running-total">The running total in the packets</a> · <a href="{R}#receivable">How the costs are recorded</a> · <a href="{R}#board-votes">How the Board voted</a></p>
  </section>

  <section class="q" id="q2">
    <h2><span class="n">2.</span>How much does the Town owe in all?</h2>
    <div class="figs">
      <div class="fig"><span>Already paid</span><b>{balance}</b><span>through the {asof} warrant list</span></div>
      <div class="fig"><span>Confirmed owed</span><b>{conf}</b><span>by the firms as of Oct. 16, 2026, less bills paid Nov. 9</span></div>
      <div class="fig total"><span>Total</span><b>~{owed_short}</b><span>about {hh_est} per household</span></div>
    </div>
    <p>This total can be traced firm by firm: the warrant lists for what has been paid, and the firms' signed confirmations, released Oct. 29, for what is owed. Most of what is owed is real estate counsel Brownstein Hyatt Farber Schreck's $1,174,083, billed when the deal is completed or ends, with a 10% discount if it fails. The Town's own estimate, about $2.76 million, isn't itemized.</p>
    <p>The total could rise. It leaves out firms that sent no confirmation, such as Hogan Lovells, Plante Moran, and POWDR, and work after Oct. 16. It would be lower if Brownstein's discount applies ({disc_total} if it applies to all of its fees).</p>
    <p class="src">Details and sources: <a href="{R}#bottom-line">The bottom line</a> · <a href="{R}#payees">Who is owed</a></p>
  </section>

  <p class="part">Paying for it</p>

  <section class="q" id="q3">
    <h2><span class="n">3.</span>Does the General Fund have the cash? Could the Town go bankrupt?</h2>
    <p>Barely any of the cash is the General Fund's. The Town keeps all its funds' cash in one pool, including CSAFE, and on Sept. 30, 2026, the General Fund's share was below zero, at &minus;$105,870. Paying the rest would in effect use Water and Sewer cash, leaving those funds roughly {left_lo} above their required reserves.</p>
    <p>Bankruptcy and dissolving aren't ways out. Colorado law allows municipal bankruptcy only for irrigation and drainage districts, and a town can dissolve only after providing for its debts. By the record's reading, this is a budget problem the Board must close over later budgets, by cutting or delaying spending, negotiating with the firms, selling Town property (park land needs voter approval), or asking voters for a tax.</p>
    <p class="src">Details and sources: <a href="{R}#csafe">CSAFE and the pooled cash</a> · <a href="{R}#other-funds">Could other funds cover it?</a> · <a href="{R}#bankruptcy">Bankruptcy and dissolution</a></p>
  </section>

  <section class="q" id="q4">
    <h2><span class="n">4.</span>How would the budget cover it?</h2>
    <p>The Town's Nov. 9, 2026, forecast has the General Fund ending 2026 at {town_fb} and 2027 at {town_fb27}, in a fund that spends about $3.2 million a year. With the record's itemized total, 2026 would end at about {fb_end}.</p>
    <figure class="figure" role="figure" aria-label="The General Fund in the Town's Nov. 9, 2026, forecast">
      <figcaption>The General Fund in 2026: the Town's forecast</figcaption>
      {gf_chart}
      <span class="cap">From the Town's Nov. 9, 2026, budget presentation, which says its figures are preliminary and may grow.</span>
    </figure>
    <p>A Nov. 16 staff memo proposes transfers, not loans, of up to $800,000 from the Community Center Fund and up to $2.3 million from the Water and Sewer Funds, described as "user fees," recorded in an amended 2026 budget on Dec. 1. Voters approved the Community Center's sales tax for the Community Center, most recently in 2022, and the Town's books list that fund as fully restricted; voters dedicated the utilities' sales tax to their state loans. By the record's check, the memo's 75% share from Sewer exceeds Sewer's cash, and the plan closes only if nearly all of the money in the three funds can be used. Whether the transfers are lawful is a question for the Town Attorney. The 2027 budget hearing is Dec. 1, and adoption is set for Dec. 8.</p>
    <p class="src">Details and sources: <a href="{R}#gf-tables">The General Fund deficit</a> · <a href="{R}#nov16-plan">The Nov. 16 plan</a> · <a href="{R}#fund-dedications">What voters approved</a> · <a href="{R}#budget-check">The record's check</a></p>
  </section>

  <section class="q" id="q5">
    <h2><span class="n">5.</span>What does Resolution 2026-31 require?</h2>
    <p>The Board adopted it Nov. 17, 2026, and it took effect that day. It's the Town Attorney's revision of a resident's draft. It:</p>
    <ul>
      <li>stops billable work by the firms, except toward a term sheet, with written notice due by Nov. 20;</li>
      <li>allows up to $80,000 toward a term sheet, only after the Board appropriates it, and requires a vote to continue if total costs pass $3 million;</li>
      <li>requires Board approval of any new engagement;</li>
      <li>requires monthly cost reports starting Dec. 1 and a firm-by-firm accounting at the Dec. 15 meeting;</li>
      <li>requires budget items for the costs and a General Fund plan if the deal fails; and</li>
      <li>sets deadlines the Board can extend only by a vote before each passes: a term sheet by Feb. 14, 2027, a signed agreement and financing by April 14, and a closing by June 30. If one passes without an extension, the Town's pursuit ends.</li>
    </ul>
    <p class="src">Details and sources: <a href="{R}#res-2026-31">Resolution 2026-31</a> · <a href="{R}resolution.html">The adopted text</a></p>
  </section>

  <p class="part">The deal</p>

  <section class="q" id="q6">
    <h2><span class="n">6.</span>Where does the deal stand, and who would run the resort?</h2>
    <p>No purchase agreement is in force. The April 30, 2026, closing deadline passed, and the Town said Sept. 30 that the agreement "has expired." No bonds have been sold, and the Board's authority to sell them ran out July 19, 2026. The Town says talks with POWDR "remain active." Its new plan is a sale-leaseback, in which a bond trustee would hold title and lease the resort back to the Town's enterprise; on Oct. 22 the interim Town Manager wrote that the lease "has not been drafted." Any new agreement, lease, or bond ordinance would need Board approval at a public meeting.</p>
    <p>The Town dropped its planned operating partner, 303 Ski, by April 2026 and said it would rely on Eldora's existing management, then "professional on-mountain management" after a two-year transition agreement with POWDR.</p>
    <p class="src">Details and sources: <a href="{R}#revised-plan">Where things stand</a> · <a href="{R}#transition-services">Transition services</a></p>
  </section>

  <section class="q" id="q7">
    <h2><span class="n">7.</span>What would the purchase commit the Town to, and what would bondholders control?</h2>
    <ul>
      <li>A $120 million price, with no deposit, in the agreement approved Jan. 6, 2026, which has expired.</li>
      <li>Revenue bonds of up to $225 million, for up to 40 years at no more than 9%, repaid only from the resort's income, not taxes. The Board expected to borrow $180 million.</li>
      <li>At least $1 million a year to POWDR for two years of transition services, in a January 2026 draft.</li>
    </ul>
    <p>The May 2026 draft bond documents, the newest released, would have an independent consultant approve the resort's budgets, send spare revenue first to paying off the senior bonds early, bar the Town from ending POWDR's transition agreement without bondholder consent, and pay part of the price in subordinate bonds to POWDR, paid only after the senior bonds. Under the sale-leaseback, the trustee could act after a default "without first completing a traditional foreclosure process." No financial model or offering document with revenue forecasts is public.</p>
    <p class="pointer">Whether the numbers can work is a judgment, so it's on the <a href="{R}opinion.html#debt-check">opinion page</a>.</p>
    <p class="src">Details and sources: <a href="{R}#commitments">Commitments</a> · <a href="{R}#may-draft">The May 2026 draft</a> · <a href="{R}#profit">Profit</a></p>
  </section>

  <section class="q" id="q8">
    <h2><span class="n">8.</span>What would the purchase mean for the fire and library districts?</h2>
    <p>Town-owned property is generally exempt from property tax. The sellers' property now pays {dt_total} a year to all taxing authorities. By the record's estimate at 2025 rates, the Nederland Fire Protection District would lose {dt_fire} a year ({dt_fire_pct} of its property tax), the library district {dt_lib} ({dt_lib_pct}), and the EcoPass district {dt_eco}. These are estimates: the County Assessor decides, leased Town property can stay taxable, and under the sale-leaseback a bond trustee, not the Town, would hold title.</p>
    <p class="src">Details and sources: <a href="{R}#district-taxes">Property taxes on the resort</a></p>
  </section>

  <p class="part">What's next</p>

  <section class="q" id="q9">
    <h2><span class="n">9.</span>What don't we know yet?</h2>
    <p>Among the most important gaps in the records searched:</p>
    <ul>
      <li>What makes up the Town's $2.76 million estimate, and what firms that sent no confirmation are owed.</li>
      <li>The financial projections behind the purchase, including SE Group's final report and Plante Moran's review of Eldora's earnings, which POWDR says is confidential in its entirety.</li>
      <li>The full bond offering memorandum, including any revenue forecast.</li>
      <li>The sale-leaseback's lease, its bond amount, and the status of talks with POWDR.</li>
      <li>Hogan Lovells' role, and the purpose of POWDR's invoices.</li>
    </ul>
    <p class="src">Details and sources: <a href="{R}#open-questions">Not in the records searched</a> · <a href="{R}#questions">Records requests from the public</a></p>
  </section>

  <section class="q" id="q10">
    <h2><span class="n">10.</span>What can I do?</h2>
    <ul>
      <li><strong>Speak</strong> during public comment (3 minutes), or <strong>write</strong> to the Board at BOT@nederlandco.org and ask that your email be included as public comment. The 2027 budget hearing is Dec. 1.</li>
      <li><strong>Petition.</strong> Registered voters can petition to send most ordinances, including one approving a new purchase agreement or bonds, to a public vote, with signatures from 5% of registered voters within 30 days after the ordinance is published.</li>
      <li><strong>Ask for records</strong> from the Town Clerk under CORA; the first hour of staff time is free. The Town posts released records on <a href="https://www.nederlandco.gov/m/newsflash/home/detail/27" target="_blank" rel="noopener">its website</a>.</li>
      <li><strong>Follow updates</strong> to the record by email or feed, and send corrections to <a href="mailto:corrections@eldorarecord.org">corrections@eldorarecord.org</a>.</li>
    </ul>
    <p class="src">Details and sources: <a href="{R}#get-involved">Get involved</a></p>
  </section>

  <footer>
    <p>This is an independent compilation, not affiliated with, endorsed by, or produced by the Town of Nederland, Eldora Mountain Resort, or POWDR. It is updated with <a href="{R}">the Eldora Record</a>, and the record governs if the two ever differ.</p>
  </footer>
</main>
'''

if __name__ == '__main__':
    main()
