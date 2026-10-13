"""Write analysis/faq.html, the Eldora FAQ: a short-form version of the Eldora Record in question-and-answer form.

Facts only, like the record: each answer restates what the record says and links to the part of the record that
has the sources. Opinions stay on the opinion page; the FAQ only points to it (question 12).

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
.note {{ background: var(--accent-soft); border-left: 4px solid var(--accent); padding: 12px 16px; margin: 0; border-radius: 0 6px 6px 0; }}
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
    <p class="note">The questions residents have asked about the Town's pursuit of Eldora Mountain Resort, answered from <a href="{R}">the Eldora Record</a>, which links every fact to its Town source. Each answer ends with a link to the part of the record that has the details and sources. Like the record, this page is facts only. My opinions are on <a href="{R}opinion.html">a separate page</a>.</p>
    <nav class="toc" aria-label="Questions">
      <b>Why and how</b><ol start="1"><li><a href="#q1">Why does the Eldora Record exist?</a></li><li><a href="#q2">Where does it come from, and how can I check it?</a></li></ol>
      <b>Who decided, and what they knew</b><ol start="3"><li><a href="#q3">Who makes the decisions?</a></li><li><a href="#q4">How much has the Town paid, and how is it recorded?</a></li><li><a href="#q5">Did the Board know about the costs and the risk?</a></li></ol>
      <b>What the Town would owe</b><ol start="6"><li><a href="#q6">If the deal fails, how much would be owed?</a></li></ol>
      <b>Could the Town pay?</b><ol start="7"><li><a href="#q7">Does the General Fund have the cash?</a></li><li><a href="#q8">Could the Town go bankrupt or dissolve?</a></li><li><a href="#q9">How does this meet the 2027 budget?</a></li></ol>
      <b>If the purchase closes</b><ol start="10"><li><a href="#q10">What would the purchase commit the Town to?</a></li><li><a href="#q11">What would bondholders control?</a></li><li><a href="#q12">What would it mean for the fire and library districts?</a></li><li><a href="#q13">Where does the deal stand, and who would run the resort?</a></li></ol>
      <b>What's next</b><ol start="14"><li><a href="#q14">What don't we know yet?</a></li><li><a href="#q15">Where are your opinions and your resolution?</a></li><li><a href="#q16">What happens next, and what can I do?</a></li></ol>
    </nav>
  </header>

  <p class="part">Why and how</p>

  <section class="q" id="q1">
    <h2><span class="n">1.</span>Why does the Eldora Record exist?</h2>
    <p>On Sept. 30, 2026, the Mayor and Board of Trustees told residents that if the purchase doesn't close, the Town would owe about $2.5 million in transaction costs, which "would be paid through our CSAFE investments" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/21" target="_blank" rel="noopener">Town update</a>). The Town's estimate is now about $2.76 million, in a draft resolution for the Nov. 9 meeting (<a href="https://nederlandco.civicweb.net/document/133099/" target="_blank" rel="noopener">Res. 2026-31</a>). The Town expects to recover the costs from bond proceeds, so they would be repaid only if the purchase closes.</p>
    <p>The record tracks those costs from the Town's own records and gathers information scattered across thousands of documents, so residents can see what has been spent, what is owed, and what would happen if the sale fails.</p>
    <p class="src">Details and sources: <a href="{R}#statement">Why I made this page</a> · <a href="{R}#funding">Where the money comes from</a></p>
  </section>

  <section class="q" id="q2">
    <h2><span class="n">2.</span>Where does the record come from, and how can I check it?</h2>
    <p>From the Town's own public records: Board of Trustees meeting records from {cov_from} through {cov_through}, on the Town's CivicWeb portal; resolutions, ordinances, finance documents, and staff reports from all years; posts on the Town website and Facebook page; and Town records released in response to public records requests under the Colorado Open Records Act (CORA). The section on property taxes also uses Boulder County records.</p>
    <p>Every figure links to its source document. Where the record does its own math, it says "this page's calculation." Where it can't find something, it says "not in the records searched," because closed-session discussions and staff files may not be public. Meeting items are linked to the Town's video recordings, and the minutes are the official record. Corrections are welcome, and each one is logged.</p>
    <p class="src">Details and sources: <a href="{R}#method-ai">How this research was done</a> · <a href="{R}#changes">Corrections and updates</a></p>
  </section>

  <p class="part">Who decided, and what they knew</p>

  <section class="q" id="q3">
    <h2><span class="n">3.</span>Who makes the acquisition decisions, and were advisory boards or residents asked?</h2>
    <p>The Board of Trustees, which includes the Mayor. It approved the $120 million purchase agreement (Ord. 882), the bond ordinance (Ord. 885), and the resolutions behind the effort. Every recorded vote on the acquisition passed unanimously among the trustees present. The Board made {n_actions} decisions and {n_sessions} votes to meet in closed session on the acquisition since {first_es}. The closed-session discussions aren't public.</p>
    <p>Five resolutions in 2025 delegated authority to hire counsel and consultants, with no dollar limit (Res. 2025-03, 2025-11, 2025-16, 2025-19, and 2025-22).</p>
    <p>In 2012 the Board adopted a review process for Town projects in which advisory boards and the public review a proposal before the Board decides. No record found shows it was invoked for the Eldora purchase. In July 2025 the Sustainability Advisory Board listed the "Decision to purchase Eldora Mtn Resort" among projects its scorecard could evaluate.</p>
    <p class="src">Details and sources: <a href="{R}#board-votes">How the Board voted</a> · <a href="{R}#no-limits">Budget and limits</a> · <a href="{R}#get-involved">Public review process</a></p>
  </section>

  <section class="q" id="q4">
    <h2><span class="n">4.</span>How much has the Town paid, and how is it recorded?</h2>
    <p>{balance} through the {asof} warrant list, mostly to lawyers and consultants. The largest payees are {top_payees}. All of it is charged to the General Fund, which pays for day-to-day Town services.</p>
    <p>{none} went to firms that appear in no Board document searched except the warrant lists, including Hogan Lovells ({hogan}). Two firms that confirmed amounts owed, Williams Weese Pepple &amp; Ferguson and Taft Stettinius &amp; Hollister, appear in no Board document or warrant list searched, and the records don't state the purpose of POWDR's three invoices ({powdr}).</p>
    <p>The payments are recorded in one General Fund account, "Due From," as money the Town expects to get back from revenue bonds if the purchase closes. That suggests the costs are carried as a receivable, so they don't yet reduce the General Fund's balance; the Town hasn't said so directly. If the sale fails, the receivable would be written off. Neither the 2025 nor the 2026 budget includes the costs, and the separate Mountain Recreation Fund the Board created for the acquisition hasn't been used.</p>
    <figure class="figure" role="figure" aria-label="Eldora acquisition costs: the running total">
      <figcaption>Eldora acquisition costs: the running total</figcaption>
      {costs_chart}
      <span class="cap">Paid from the General Fund after each warrant list, then what firms confirmed is still owed as of Oct. 16, 2026. The dashed line is the Town's estimate, about $2.76 million, not itemized.</span>
    </figure>
    <p class="src">Details and sources: <a href="{R}#costs">What has been spent</a> · <a href="{R}#payees">Who was paid</a> · <a href="{R}#receivable">How the costs are recorded</a> · <a href="{R}#enterprise-fund">The separate fund</a></p>
  </section>

  <section class="q" id="q5">
    <h2><span class="n">5.</span>Did the Board know about the mounting costs and the risk?</h2>
    <p>The running total was in the packets the Board approved. Each warrant list showed the Eldora payments with the account's running balance, which was $915,922 on July 7, 2026, the night the Board approved Stifel's advisory agreement. The minutes searched record no discussion of the warrant lists or the "Due From" entries. Each list was approved with the rest of the consent agenda.</p>
    <p>The risk was raised when the Board delegated authority to hire special counsel on Jan. 7, 2025. Trustee Luke Miller asked how counsel would be paid "if we don't end up moving forward and issuing bonds." Town Administrator Jon Cain answered, "We have that obligation," and Town Attorney Jennifer Madsen said that if the deal doesn't close, bond counsel "would need to be paid by the town" (<a href="https://www.youtube.com/watch?v=F3Kb-cwTvS8&amp;t=2313s" target="_blank" rel="noopener">video, 0:38:33</a>). The resolution's memo said the Town Administrator "will provide updates to the Board of Trustees regarding cost estimates." Asked for written updates, the Town said on Oct. 29, 2026, that "No records exist." An update given aloud or in a closed session wouldn't appear in the records.</p>
    <p>Residents asked about the costs at the Board's July 2025 town hall, in a November 2025 comment, and in comments in July and September 2026.</p>
    <p class="src">Details and sources: <a href="{R}#running-total">The running total was in the meeting packets</a> · <a href="{R}#estimates">Estimates compared with spending</a> · <a href="{R}#questions">Questions from the public</a></p>
  </section>

  <p class="part">What the Town would owe</p>

  <section class="q" id="q6">
    <h2><span class="n">6.</span>If the deal fails, how much would be owed?</h2>
    <div class="figs">
      <div class="fig"><span>Already paid</span><b>{balance}</b><span>through the {asof} warrant list</span></div>
      <div class="fig"><span>Confirmed owed</span><b>{conf}</b><span>by the firms, as of Oct. 16, 2026</span></div>
      <div class="fig total"><span>Total</span><b>~{owed_short}</b><span>about {hh_est} per household</span></div>
    </div>
    <p><strong>This total is the one that can be traced, firm by firm, to Town records:</strong> the warrant lists and the Town's ledger for what has been paid, and the firms' signed confirmations for what is owed. The Town's estimate, now about $2.76 million in a draft resolution for Nov. 9, isn't itemized in the records searched, nor was its Sept. 30 estimate of about $2.5 million.</p>
    <p>On Oct. 19, 2026, the interim Town Manager asked firms to confirm what they were owed as of Oct. 16. The Town released the replies on Oct. 29 in response to a records request. Of what is owed, {conf_inv} had been invoiced and not paid, some of it for more than a year. Most of the rest is real estate counsel Brownstein Hyatt Farber Schreck's $1,214,083, which its agreement bills when the transaction is completed or terminated, with a 10% discount if the deal fails. Its confirmation doesn't say whether that discount is applied.</p>
    <p>The total could change. It doesn't include firms that sent no confirmation, such as Hogan Lovells, Plante Moran, and POWDR, or work after Oct. 16, and it would be lower if Brownstein's 10% discount for a failed deal applies ({disc_total} if it applies to all of Brownstein's fees). Asked for the records behind its Sept. 30 estimate, the Town released no worksheet. The Town doesn't say whether its estimates include the {balance} already paid.</p>
    <p class="src">Details and sources: <a href="{R}#bottom-line">The bottom line</a> · <a href="{R}#payees">Who was paid and who is owed</a> · <a href="{R}#per-household">Per household</a></p>
  </section>

  <p class="part">Could the Town pay?</p>

  <section class="q" id="q7">
    <h2><span class="n">7.</span>Does the General Fund have the cash? Could other Town funds cover it?</h2>
    <p>Barely any of the cash is the General Fund's. The Town keeps all its funds' cash in one pool, including CSAFE. By the record's calculation, the General Fund's share at the end of 2025 was about $698,751, less than the {since_2025} it has paid for Eldora in 2026. Paying the rest would likely use the Water and Sewer Funds' cash, leaving them roughly {left_lo} to {left_hi} above their reserves.</p>
    <p>Other funds' money comes with limits, whether it moves as a loan or a transfer. The 2025 audit reports all of the Community Center Fund's and the Downtown Development Authority's balances as restricted. The utilities' cash is planned for about $7.9 million in fire-flow improvements in 2030&ndash;2031, and their $3,070,436 in state loans is repaid from their revenue and a dedicated share of the sales tax. Repaying $1.7 million to the Water Fund by 2030, before its fire-flow project, would take about $418,000 a year, well above the General Fund's average yearly gain of {avg_op} to {avg_rep}. The General Fund has never borrowed from another fund in the audits searched. Whether a loan or transfer is allowed, and whether a multi-year loan needs voter approval under TABOR, is a question for the Town attorney or auditor.</p>
    <p class="src">Details and sources: <a href="{R}#other-funds">Could other funds cover it?</a> · <a href="{R}#csafe">CSAFE and the pooled cash</a> · <a href="{R}#utility-loan">The utility funds</a></p>
  </section>

  <section class="q" id="q8">
    <h2><span class="n">8.</span>Could the Town go bankrupt or dissolve? How would a deficit be paid off?</h2>
    <p>By the record's calculation, if the sale fails in 2026, the General Fund would end the year {fb_end_m} below zero ({fb_end}), for a fund that spends about $3.2 million a year.</p>
    <figure class="figure" role="figure" aria-label="The General Fund if the sale fails in 2026">
      <figcaption>If the sale fails in 2026: the General Fund</figcaption>
      {gf_chart}
      <span class="cap">The record's calculation from the 2025 audit, the adopted 2026 budget, the warrant lists, and the firms' confirmations. It assumes the rest of 2026 goes as budgeted and leaves out firms that sent no confirmation.</span>
    </figure>
    <p>Neither bankruptcy nor dissolving would remove the costs. A town can file for municipal bankruptcy only if its state authorizes it, and Colorado's statute names only irrigation and drainage districts. A town can dissolve only after providing for all its debts, levying taxes if needed. By the record's reading, this is a General Fund budget problem for the Board to address through its budgets, not a threat to the Town's existence.</p>
    <p>State law doesn't allow a budget that spends more than the money available, so the Board would have to close the gap over later budgets. Its options include cutting or delaying spending (which could mean fewer staff or reduced services), negotiating payment terms with the firms, selling Town property (land used for parks needs voter approval), or asking voters to approve a new tax or multi-year borrowing. The TABOR emergency reserve can't be used for a revenue shortfall. At the General Fund's past rate of gains, rebuilding {fb_end_m} would take roughly {yrs_def} years. That is a measure of scale, not a forecast.</p>
    <p class="src">Details and sources: <a href="{R}#gf-deficit">If the General Fund ends in deficit</a> · <a href="{R}#bankruptcy">Bankruptcy and dissolution</a> · <a href="{R}#gf-recovery">The General Fund year by year</a></p>
  </section>

  <section class="q" id="q9">
    <h2><span class="n">9.</span>How does this meet the 2027 budget, and who is managing it?</h2>
    <p>The Board began discussing the 2027 budget at its Nov. 9, 2026, meeting, where staff planned to review Eldora-related spending; the presentation and minutes aren't posted yet. No budget yet includes the costs, so paying what is owed would need a Board appropriation. Draft Resolution 2026-31 would have the Town Manager present &ldquo;any or all&rdquo; of a 2026 appropriation for the costs, a 2027 budget line, and a plan for the General Fund if the acquisition doesn't close. The adopted 2026 budget already projected the General Fund's balance falling to $583,730 by the end of 2026, before any write-off.</p>
    <p>The Town Manager resigned in August 2026. The previous Town Manager returned as interim on Sept. 25, under a contract through Feb. 28, 2027, and says the budget is her priority, to "identify potential opportunities for expenditure reductions and alternative revenue sources." Recruiting a permanent Town Administrator is expected to begin after the 2027 budget is developed. The Town Treasurer retired in 2026, and since July 2026 the Town's monthly treasurer reports have been issued by Plante Moran as Town Treasurer. An Oct. 20 staff memo says the Eldora work "is primarily being performed by the Mayor" and that "the Town is not paying outside consultants to perform this work."</p>
    <p class="src">Details and sources: <a href="{R}#revised-plan">Where things stand</a> · <a href="{R}#get-involved">Decisions to watch</a></p>
  </section>

  <p class="part">If the purchase closes</p>

  <section class="q" id="q10">
    <h2><span class="n">10.</span>What would the purchase commit the Town to, and what did the Town project?</h2>
    <ul>
      <li>A $120 million price, with no deposit, in the agreement approved Jan. 6, 2026, which has expired.</li>
      <li>Revenue bonds of up to $225 million, for up to 40 years at no more than 9%, repaid only from the resort's income, not taxes. When the Board declared its intent to repay early costs from the bonds, it expected to borrow $180 million.</li>
      <li>In a January 2026 draft, at least $1 million a year to POWDR for two years of transition services after closing.</li>
    </ul>
    <p>In July 2025, FAQ 3.0 projected a reserve of $10 million "in the first couple of years" and free cash flow of "$2M - $5M+" after the subordinate bonds are paid off. The Town's Sept. 30, 2026, update gives no revenue or profit figures and says the first "approximately ten years" are "more financially constrained." No financial model, feasibility study, or bond-offering document is in the records searched.</p>
    <p class="pointer">Whether the numbers can work is a judgment, so it isn't here. My rough review of the price and the revenue it would take is on the <a href="{R}opinion.html#debt-check">opinion page</a>.</p>
    <p class="src">Details and sources: <a href="{R}#commitments">Commitments</a> · <a href="{R}#profit">Profit</a></p>
  </section>

  <section class="q" id="q11">
    <h2><span class="n">11.</span>What would bondholders control if the purchase closes?</h2>
    <p>The bonds would be repaid only from the resort's income. The January 2026 draft indenture says they "shall not constitute or become an indebtedness, a debt, or a liability or a charge against the general credit or taxing power of the Town." The draft bond documents also set terms on how the Town and the resort would operate while the bonds are outstanding. The May 2026 draft, the newest the Town has released, includes these terms, some still marked as tentative:</p>
    <ul>
      <li>An independent consultant would approve the resort's annual budgets.</li>
      <li>The Town couldn't end POWDR's transition agreement early without bondholder consent. The January draft of that agreement would let the Town end it on 60 days' notice.</li>
      <li>The Town would keep its corporate existence and not seek bankruptcy or dissolution.</li>
      <li>Revenue left after operations, debt payments, and reserves would go first to paying off the senior bonds early. Money in the Surplus Fund after that "may be used for any lawful purpose by the Town."</li>
      <li>Part of the price would be paid in subordinate bonds "delivered to or at the direction of the Seller," with the investor letter drafted for POWDR. They pay no current interest, grow in value until paid, and are paid only after the senior bonds, beginning in November 2036.</li>
    </ul>
    <p>Under the sale-leaseback the Town described in October 2026, the bond trustee would hold title to the land and buildings and lease the resort back to the Town's enterprise. If the bonds defaulted, the trustee could exercise its remedies "without first completing a traditional foreclosure process," and "those remedies could affect who operates or leases the resort." Title would return to the enterprise once the bonds are paid. The lease and the final bond terms aren't public, and they may differ from the drafts.</p>
    <p class="src">Details and sources: <a href="{R}#may-draft">The May 2026 draft</a> · <a href="{R}#profit">Profit</a> · <a href="{R}#revised-plan">Where things stand</a> · <a href="{R}#bankruptcy">Bankruptcy and dissolution</a></p>
  </section>

  <section class="q" id="q12">
    <h2><span class="n">12.</span>What would the purchase mean for the fire and library districts' tax revenue?</h2>
    <p>Property a town owns is generally exempt from property tax, so if the purchase closes and the resort becomes Town property, the local districts would stop collecting tax on it. The sellers' property now pays {dt_total} a year in property taxes to all taxing authorities, according to Boulder County records.</p>
    <p>By the record's estimate at 2025 tax rates, the Nederland Fire Protection District would stop collecting {dt_fire} a year ({dt_fire_pct} of its property tax), the Nederland Community Library District {dt_lib} ({dt_lib_pct}), and the Nederland EcoPass district {dt_eco}. Part of the library's rate repays bonds, and that part would likely shift to other property owners rather than be lost.</p>
    <p>These are estimates, not rulings. Whether each account becomes exempt is for the County Assessor to decide, and Town property leased to a private party can remain taxable. The range depends on the Forest Service permit interest, which is taxed while a private company holds it. Under the sale-leaseback, a bond trustee, not the Town, would hold title until the bonds are repaid, and the records searched don't say whether the property would be exempt under that structure. Any change would show up in tax bills a year or more after a closing.</p>
    <p>In April 2026, FAQ 6.0 said the Town was "working directly with the County Assessor to identify which parcels, if any, would become Town-owned" and would share what it learned. FAQ 7.0 doesn't include the question, and no results of that review are in the records searched.</p>
    <p class="src">Details and sources: <a href="{R}#district-taxes">Property taxes on the resort</a> · <a href="{R}#district-taxes-estimate">If the property became the Town's</a></p>
  </section>

  <section class="q" id="q13">
    <h2><span class="n">13.</span>Where does the deal stand, and who would run the resort?</h2>
    <p>No purchase agreement is in force. The closing deadline of April 30, 2026, passed without a closing, and the Town said Sept. 30 that the agreement "has expired." No bonds have been sold, and the Board's authority to sell them ran out July 19, 2026. The Town says talks with POWDR "remain active." It remains bound by its January 2025 confidentiality agreement with POWDR, and each side pays its own costs.</p>
    <p>The Town's new plan is a sale-leaseback: a bond trustee would hold title to the resort and lease it back to the Town's enterprise. The plan was "at the beginning stages" on Sept. 30, and on Oct. 22 the interim Town Manager wrote that the lease "has not been drafted." A new agreement, lease, or bond ordinance would each need Board approval at a public meeting.</p>
    <p>In July 2025 the Town announced a partnership with 303 Ski, a group of Front Range ski-industry veterans who had vetted operating plans and would "support the mountain once POWDR's contract expires" (<a href="https://web.archive.org/web/20250709224556/https://townofnederland.colorado.gov/press-release/eldora-mountain-acquisition-faqs-30" target="_blank" rel="noopener">FAQ 3.0</a>). By April 2026 the Town had decided not to go forward with 303 Ski. It said it would rely on Eldora's existing management, with "direct integration" between the Town Manager and the resort's CEO, and that it had declined 303 Ski's requests for reimbursement of time and expenses. After the two-year transition agreement, it "anticipates relying on professional on-mountain management" (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0</a>).</p>
    <p class="src">Details and sources: <a href="{R}#in-brief">The acquisition in brief</a> · <a href="{R}#revised-plan">Where things stand</a> · <a href="{R}#no-sale">What happens to the costs</a> · <a href="{R}#transition-services">Transition services</a></p>
  </section>

  <p class="part">What's next</p>

  <section class="q" id="q14">
    <h2><span class="n">14.</span>What don't we know yet?</h2>
    <p>The record lists what the records searched don't show, along with the records that could. Among the most important:</p>
    <ul>
      <li>What makes up the Town's estimate, now about $2.76 million, and what the firms that sent no confirmation, such as Hogan Lovells, Plante Moran, and POWDR, are owed.</li>
      <li>Hogan Lovells' role and engagement letter, and the purpose of POWDR's invoices.</li>
      <li>The financial projections behind the purchase: SE Group's final due-diligence report and five-year pro forma, the model behind FAQ 3.0's projections, and the documents prepared for bond buyers. Plante Moran's review of Eldora's earnings, prepared for the Town, isn't public either: POWDR has told the Town it is confidential in its entirety, and the Town has asked POWDR to reconsider.</li>
      <li>The full bond offering memorandum, including any revenue forecast, and the amount of each deposit at closing. The Town has posted one page, showing only the debt payments.</li>
      <li>What the new &ldquo;Eldora Expense&rdquo; account on the Nov. 9 warrant list includes: its year-to-date balance is ($2,188,218.53), about $933,000 more than the costs paid through Oct. 20 by the record's reading.</li>
      <li>The role and cost of Causey Public Finance, which the draft resolution says prepared analyses.</li>
      <li>The sale-leaseback's lease, its bond amount, and any pledges.</li>
      <li>The complete transition agreement with POWDR, and what it would cost to replace POWDR's services after two years.</li>
      <li>Which reserves FAQ 7.0 called "sufficient to cover the current expenses," and whether other Town funds could lawfully lend or transfer money to the General Fund.</li>
    </ul>
    <p>Some of these may be in staff or contract files or closed-session records. Anyone can request them from the Town Clerk under CORA.</p>
    <p class="src">Details and sources: <a href="{R}#open-questions">Not in the records searched</a> · <a href="{R}#eldora-expense">The new account</a> · <a href="{R}#questions">Records requests from the public</a></p>
  </section>

  <section class="q" id="q15">
    <h2><span class="n">15.</span>Where are your opinions and your resolution?</h2>
    <p class="pointer">On separate pages, so they stay apart from the record. <a href="{R}opinion.html">My opinions</a> cover the odds that the sale closes, the price the resort's earnings could support, and what I think the Town should do. The Town Attorney revised <a href="{R}resolution.html">my draft resolution</a> as Resolution 2026-31; my page shows it with the amendments I recommend. <a href="{R}cliffs-notes.html">The Eldora Deal Cliffs Notes</a> tells the whole story in order, in plain language, with my view of what happens if the deal fails. A version of this FAQ with my opinions ran as an invited guest commentary in The Mountain-Ear on Nov. 5, 2026: <a href="https://www.themtnear.com/stories/eldora-faq-deserved-nederland-resident-proposal-deal,114671" target="_blank" rel="noopener">"The Eldora FAQ we deserved"</a>.</p>
  </section>

  <section class="q" id="q16">
    <h2><span class="n">16.</span>What happens next, and what can I do?</h2>
    <p><a href="{R}#res-2026-31">Resolution 2026-31</a>, the Town Attorney's revision of a resident's draft, was on the Board's Nov. 9, 2026, agenda; the minutes, which will record the Board's action, aren't posted yet. As drafted, it would allow up to $150,000 more in acquisition costs for work toward a term sheet without a further resolution, require Board approval of new engagements, and require monthly cost reports. It sets no milestone dates. The Board also began discussing the 2027 budget on Nov. 9.</p>
    <ul>
      <li><strong>Speak</strong> during public comment (3 minutes), or <strong>write</strong> to the Board at BOT@nederlandco.org and ask that your email be included as public comment.</li>
      <li><strong>Petition.</strong> Registered voters can petition to send most ordinances to a public vote, with signatures from 5% of registered voters within 30 days after the ordinance is published. That includes an ordinance approving a new purchase agreement or bonds, even though the bonds themselves need no election. Residents used it in 2024 on a child-care ordinance.</li>
      <li><strong>Ask for records</strong> from the Town Clerk under CORA. The first hour of staff time is free. The Town now posts records it has released on <a href="https://www.nederlandco.gov/m/newsflash/home/detail/27" target="_blank" rel="noopener">its website</a>.</li>
      <li><strong>Follow updates</strong> to the record by email or feed, and send corrections to <a href="mailto:corrections@eldorarecord.org">corrections@eldorarecord.org</a>.</li>
    </ul>
    <p class="src">Details and sources: <a href="{R}#get-involved">Get involved</a> · <a href="{R}#open-questions">Not in the records searched</a></p>
  </section>

  <footer>
    <p>This is an independent compilation, not affiliated with, endorsed by, or produced by the Town of Nederland, Eldora Mountain Resort, or POWDR. It is updated with <a href="{R}">the Eldora Record</a>, and the record governs if the two ever differ.</p>
  </footer>
</main>
'''

if __name__ == '__main__':
    main()
